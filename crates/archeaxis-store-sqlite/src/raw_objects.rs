//! Immutable original objects owned by this vNext database, never external input paths.
use rusqlite::Connection;
use sha2::{Digest, Sha256};
use std::{io::Write, path::{Path, PathBuf}};

/// Bounded staging read; validate ancestors before traversing children and hold
/// a regular single-link file identity. The caller independently binds the hash.
pub fn read_staged(path:&Path, limit:usize) -> rusqlite::Result<Vec<u8>> {
    use std::io::Read;
    let text=path.to_string_lossy().replace('\\',"/").to_ascii_lowercase();
    if text.starts_with("e:") || text.starts_with("//") || !path.is_absolute()
        || path.components().any(|p|matches!(p,std::path::Component::ParentDir)) {
        return Err(rusqlite::Error::InvalidPath(path.to_owned()));
    }
    let mut part=PathBuf::new();
    for component in path.components() {part.push(component);reject_links(&part)?;}
    let file=crate::writer::hold_identity(path).map_err(|e|rusqlite::Error::ToSqlConversionFailure(Box::new(e)))?
        .ok_or(rusqlite::Error::InvalidQuery)?;
    let size=file.metadata().map_err(io_error)?.len();
    if size>limit as u64 {return Err(rusqlite::Error::InvalidQuery);}
    let mut bytes=Vec::new(); file.take(limit as u64+1).read_to_end(&mut bytes).map_err(io_error)?;
    if bytes.len() as u64!=size {return Err(rusqlite::Error::InvalidQuery);}
    Ok(bytes)
}

fn io_error(error: std::io::Error) -> rusqlite::Error {
    rusqlite::Error::ToSqlConversionFailure(Box::new(error))
}

pub fn reject_links(path: &Path) -> rusqlite::Result<()> {
    for part in path.ancestors() {
        match std::fs::symlink_metadata(part) {
            Ok(meta) => {
                #[cfg(windows)]
                let reparse = {
                    use std::os::windows::fs::MetadataExt;
                    meta.file_attributes() & 0x400 != 0
                };
                #[cfg(not(windows))]
                let reparse = false;
                if meta.file_type().is_symlink() || reparse {
                    return Err(rusqlite::Error::InvalidPath(part.to_owned()));
                }
            },
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {},
            Err(error) => return Err(io_error(error)),
        }
    }
    Ok(())
}

pub fn root(conn: &Connection) -> rusqlite::Result<PathBuf> {
    let db = conn.path().filter(|p| !p.is_empty()).ok_or(rusqlite::Error::InvalidQuery)?;
    let root = PathBuf::from(format!("{db}.objects"));
    reject_links(&root)?;
    Ok(root)
}

fn object_path(conn: &Connection, digest: &str) -> rusqlite::Result<PathBuf> {
    if digest.len() != 64 || !digest.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)) {
        return Err(rusqlite::Error::InvalidQuery);
    }
    let path = root(conn)?.join(digest);
    reject_links(&path)?;
    Ok(path)
}

pub fn read(conn: &Connection, digest: &str) -> rusqlite::Result<Vec<u8>> {
    let bytes = std::fs::read(object_path(conn, digest)?).map_err(io_error)?;
    if hex::encode(Sha256::digest(&bytes)) != digest {
        return Err(rusqlite::Error::InvalidQuery);
    }
    Ok(bytes)
}

/// Publish complete, synced bytes without ever overwriting a content address.
/// An unregistered orphan is recoverable if a subsequent database write fails.
pub fn persist(conn: &Connection, bytes: &[u8]) -> rusqlite::Result<String> {
    let digest = hex::encode(Sha256::digest(bytes));
    let path = object_path(conn, &digest)?;
    if path.exists() {
        read(conn, &digest)?;
        return Ok(digest);
    }
    let parent = path.parent().ok_or(rusqlite::Error::InvalidQuery)?;
    std::fs::create_dir_all(parent).map_err(io_error)?;
    reject_links(parent)?;
    let mut staged = tempfile::NamedTempFile::new_in(parent).map_err(io_error)?;
    staged.write_all(bytes).map_err(io_error)?;
    staged.as_file().sync_all().map_err(io_error)?;
    match staged.persist_noclobber(&path) {
        Ok(_) => {},
        Err(error) if error.error.kind() == std::io::ErrorKind::AlreadyExists => {
            read(conn, &digest)?;
        },
        Err(error) => return Err(io_error(error.error)),
    }
    Ok(digest)
}
