//! Runtime owner: bounded single-connection thread and process-held workspace lock.
//! Low-level maintenance/migration APIs remain separate; this is not an OS sandbox.
use rusqlite::Connection;
use std::{fs::{File, OpenOptions, TryLockError}, io, path::{Component, Path, PathBuf},
    sync::{Arc, mpsc::{self, SyncSender, TrySendError}}, thread::{self, JoinHandle}};
use tokio::sync::oneshot;

#[derive(Debug)]
pub enum StoreError { Io(io::Error), Sql(rusqlite::Error), Busy, Closed, InvalidPath }
impl std::fmt::Display for StoreError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(e) => write!(f, "workspace I/O: {e}"),
            Self::Sql(e) => write!(f, "workspace database: {e}"),
            Self::Busy => write!(f, "workspace writer is owned or its queue is full"),
            Self::Closed => write!(f, "workspace writer is closed"),
            Self::InvalidPath => write!(f, "workspace path is not an unambiguous local regular file"),
        }
    }
}
impl std::error::Error for StoreError {}
impl From<io::Error> for StoreError { fn from(e: io::Error) -> Self { Self::Io(e) } }
impl From<rusqlite::Error> for StoreError { fn from(e: rusqlite::Error) -> Self { Self::Sql(e) } }

type Work = Box<dyn FnOnce(&mut Connection) + Send>;
struct Inner { sender: Option<SyncSender<Work>>, thread: Option<JoinHandle<()>> }
impl Drop for Inner {
    fn drop(&mut self) {
        self.sender.take(); // Close input before joining; queued writes finish first.
        if let Some(thread) = self.thread.take() {
            if thread.thread().id() != std::thread::current().id() { let _ = thread.join(); }
        }
    }
}

#[derive(Clone)]
pub struct Store(Arc<Inner>);
impl Store {
    pub fn open(path: &Path) -> Result<Self, StoreError> { Self::open_with_capacity(path, 64) }

    pub fn open_with_capacity(path: &Path, capacity: usize) -> Result<Self, StoreError> {
        if capacity == 0 { return Err(StoreError::InvalidPath); }
        let path = checked_path(path)?;
        let parent = path.parent().ok_or(StoreError::InvalidPath)?;
        std::fs::create_dir_all(parent)?;
        checked_path(parent)?;
        let path = parent.canonicalize()?.join(path.file_name().ok_or(StoreError::InvalidPath)?);
        // Existing-file canonicalization also resolves Windows short names.
        let path = if path.try_exists()? { path.canonicalize()? } else { path };
        let _preflight_identity = hold_identity(&path)?;
        let lock_path = path.with_file_name(format!("{}.writer.lock", path.file_name().unwrap().to_string_lossy()));
        // Existing lock files are permanent identity, never PID-based stale state.
        // Never unlink, truncate, steal, or interpret their content.
        crate::raw_objects::reject_links(&lock_path)?;
        let _lock_identity = hold_identity(&lock_path)?;
        let mut options = OpenOptions::new();
        options.read(true).write(true).create(true).truncate(false);
        #[cfg(windows)] {
            use std::os::windows::fs::OpenOptionsExt;
            options.share_mode(3); // FILE_SHARE_READ | WRITE; deny deletion while open.
        }
        #[cfg(unix)] {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(0o600);
        }
        let lock = options.open(lock_path)?;
        match lock.try_lock() {
            Ok(()) => (),
            Err(TryLockError::WouldBlock) => return Err(StoreError::Busy),
            Err(TryLockError::Error(e)) => return Err(e.into()),
        }
        // Repeat after acquiring ownership before any SQLite initialization.
        let identity = hold_identity(&path)?;
        let mut conn = crate::init_workspace(path.to_str().ok_or(StoreError::InvalidPath)?)?;
        let identity = match identity { Some(file) => Some(file), None => hold_identity(&path)? };
        let (sender, receiver) = mpsc::sync_channel::<Work>(capacity);
        let thread = thread::Builder::new().name("archeaxis-store".into()).spawn(move || {
            let _lock = lock;
            let _identity = identity;
            while let Ok(work) = receiver.recv() {
                // Fail closed on a panicking domain operation: do not reuse a
                // connection with unknown transaction state. Pending replies close.
                if std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| work(&mut conn))).is_err() {
                    break;
                }
            }
            drop(conn); // Database closes before the OS lock is released.
        })?;
        Ok(Self(Arc::new(Inner { sender: Some(sender), thread: Some(thread) })))
    }

    /// Core-owned bounded DB operations only: no worker/network/process waits in
    /// a callback. Trusted callbacks return owned data and must not replace the
    /// connection. This is an internal Core integration API, not a sandbox API.
    pub async fn submit<T: Send + 'static>(&self, work: impl FnOnce(&mut Connection) -> T + Send + 'static) -> Result<T, StoreError> {
        let (reply, result) = oneshot::channel();
        let task = Box::new(move |conn: &mut Connection| {
            let value = work(conn);
            assert!(conn.is_autocommit(), "writer operation left an unfinished transaction");
            let _ = reply.send(value);
        });
        self.0.sender.as_ref().ok_or(StoreError::Closed)?.try_send(task).map_err(|e| match e {
            TrySendError::Full(_) => StoreError::Busy,
            TrySendError::Disconnected(_) => StoreError::Closed,
        })?;
        result.await.map_err(|_| StoreError::Closed)
    }
}

fn checked_path(path: &Path) -> Result<PathBuf, StoreError> {
    fn forbidden(path: &Path) -> bool {
        let text = path.to_string_lossy().replace('\\', "/").to_ascii_lowercase();
        text.starts_with("e:") || text.starts_with("//") || text == ":memory:"
    }
    if forbidden(path) || path.components().any(|p| matches!(p, Component::ParentDir)) {
        return Err(StoreError::InvalidPath);
    }
    let absolute = std::path::absolute(path)?;
    if forbidden(&absolute) { return Err(StoreError::InvalidPath); }
    // Walk from the root, not the leaf: never traverse a known reparse parent
    // before checking it. Checks are fail-closed, not a hostile-filesystem sandbox.
    let mut current = PathBuf::new();
    for component in absolute.components() {
        current.push(component);
        crate::raw_objects::reject_links(&current)?;
    }
    Ok(absolute)
}

fn hold_identity(path: &Path) -> Result<Option<File>, StoreError> {
    let mut options = OpenOptions::new();
    options.read(true);
    #[cfg(windows)] {
        use std::os::windows::fs::OpenOptionsExt;
        options.share_mode(3); // Keep this DB identity from being renamed/replaced.
    }
    let file = match options.open(path) {
        Ok(file) => file,
        Err(e) if e.kind() == io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(e.into()),
    };
    if !file.metadata()?.is_file() { return Err(StoreError::InvalidPath); }
    #[cfg(windows)] {
        use std::os::windows::io::AsRawHandle;
        use windows_sys::Win32::Storage::FileSystem::{BY_HANDLE_FILE_INFORMATION, GetFileInformationByHandle};
        let mut info: BY_HANDLE_FILE_INFORMATION = unsafe { std::mem::zeroed() };
        // SAFETY: valid live File handle and correctly sized writable output.
        if unsafe { GetFileInformationByHandle(file.as_raw_handle(), &mut info) } == 0 {
            return Err(io::Error::last_os_error().into());
        }
        if info.nNumberOfLinks != 1 { return Err(StoreError::InvalidPath); }
    }
    #[cfg(unix)] {
        use std::os::unix::fs::MetadataExt;
        if file.metadata()?.nlink() != 1 { return Err(StoreError::InvalidPath); }
    }
    Ok(Some(file))
}
