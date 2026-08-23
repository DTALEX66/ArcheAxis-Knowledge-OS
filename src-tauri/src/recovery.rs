use serde::Serialize;
use std::collections::VecDeque;
use std::ffi::c_void;
use std::fs::{File, OpenOptions};
use std::io::{self, Write};
use std::os::windows::fs::{MetadataExt, OpenOptionsExt};
use std::os::windows::io::AsRawHandle;
use std::path::{Component, Path, PathBuf};

const MAX_RECOVERY_MESSAGE_CHARS: usize = 240;
const MAX_RECOVERY_LOG_LINES: usize = 200;
const MAX_RECOVERY_BACKUPS: usize = 200;
const REDACTED: &str = "[redacted]";
const FILE_ATTRIBUTE_DIRECTORY: u32 = 0x0000_0010;
const FILE_ATTRIBUTE_REPARSE_POINT: u32 = 0x0000_0400;
const FILE_FLAG_OPEN_REPARSE_POINT: u32 = 0x0020_0000;
const FILE_FLAG_BACKUP_SEMANTICS: u32 = 0x0200_0000;
const FILE_SHARE_READ: u32 = 0x0000_0001;
const FILE_SHARE_WRITE: u32 = 0x0000_0002;
const FILE_SHARE_DELETE: u32 = 0x0000_0004;
const DELETE_ACCESS: u32 = 0x0001_0000;
const GENERIC_READ: u32 = 0x8000_0000;
const GENERIC_WRITE: u32 = 0x4000_0000;
const FILE_DISPOSITION_INFO_CLASS: i32 = 4;

#[repr(C)]
#[derive(Clone, Copy, Default)]
struct FileTime {
    low_date_time: u32,
    high_date_time: u32,
}

#[repr(C)]
#[derive(Clone, Copy, Default)]
struct ByHandleFileInformation {
    file_attributes: u32,
    creation_time: FileTime,
    last_access_time: FileTime,
    last_write_time: FileTime,
    volume_serial_number: u32,
    file_size_high: u32,
    file_size_low: u32,
    number_of_links: u32,
    file_index_high: u32,
    file_index_low: u32,
}

#[repr(C)]
struct FileDispositionInformation {
    delete_file: u8,
}

#[link(name = "Kernel32")]
extern "system" {
    fn GetFileInformationByHandle(
        file: *mut c_void,
        information: *mut ByHandleFileInformation,
    ) -> i32;
    fn SetFileInformationByHandle(
        file: *mut c_void,
        information_class: i32,
        information: *const c_void,
        buffer_size: u32,
    ) -> i32;
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct ObjectIdentity {
    volume_serial_number: u32,
    file_index: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct FileIdentity {
    volume_serial_number: u32,
    file_index: u64,
    size: u64,
    last_write_time: u64,
}

fn handle_information(file: &File) -> Result<ByHandleFileInformation, String> {
    let mut information = ByHandleFileInformation::default();
    let succeeded =
        unsafe { GetFileInformationByHandle(file.as_raw_handle().cast(), &mut information) };
    (succeeded != 0)
        .then_some(information)
        .ok_or_else(|| "filesystem handle identity is unavailable".to_owned())
}

fn object_identity(information: &ByHandleFileInformation) -> ObjectIdentity {
    ObjectIdentity {
        volume_serial_number: information.volume_serial_number,
        file_index: ((information.file_index_high as u64) << 32)
            | information.file_index_low as u64,
    }
}

fn file_identity(file: &File) -> Result<FileIdentity, String> {
    let information = handle_information(file)?;
    if information.file_attributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT) != 0
    {
        return Err("backup source is not a regular file".to_owned());
    }
    Ok(FileIdentity {
        volume_serial_number: information.volume_serial_number,
        file_index: ((information.file_index_high as u64) << 32)
            | information.file_index_low as u64,
        size: ((information.file_size_high as u64) << 32) | information.file_size_low as u64,
        last_write_time: ((information.last_write_time.high_date_time as u64) << 32)
            | information.last_write_time.low_date_time as u64,
    })
}

fn regular_file_object_identity(file: &File) -> Result<ObjectIdentity, String> {
    let information = handle_information(file)?;
    if information.file_attributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT) != 0
    {
        return Err("staging handle is not a regular file".to_owned());
    }
    Ok(object_identity(&information))
}

fn directory_object_identity(file: &File) -> Result<ObjectIdentity, String> {
    let information = handle_information(file)?;
    if information.file_attributes & FILE_ATTRIBUTE_DIRECTORY == 0
        || information.file_attributes & FILE_ATTRIBUTE_REPARSE_POINT != 0
    {
        return Err("staging handle is not a regular directory".to_owned());
    }
    Ok(object_identity(&information))
}

fn mark_delete_on_close(file: &File) -> Result<(), String> {
    let information = FileDispositionInformation { delete_file: 1 };
    let succeeded = unsafe {
        SetFileInformationByHandle(
            file.as_raw_handle().cast(),
            FILE_DISPOSITION_INFO_CLASS,
            (&information as *const FileDispositionInformation).cast(),
            std::mem::size_of::<FileDispositionInformation>() as u32,
        )
    };
    (succeeded != 0)
        .then_some(())
        .ok_or_else(|| "staging handle could not be marked for deletion".to_owned())
}

fn open_backup_source(path: &Path) -> Result<(File, FileIdentity), String> {
    let file = OpenOptions::new()
        .read(true)
        .share_mode(FILE_SHARE_READ)
        .custom_flags(FILE_FLAG_OPEN_REPARSE_POINT)
        .open(path)
        .map_err(|_| "backup source cannot be opened".to_owned())?;
    let identity = file_identity(&file)?;
    Ok((file, identity))
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum SensitiveKey {
    Authorization,
    Other,
}

fn sensitive_key(token: &str) -> Option<SensitiveKey> {
    let key = token.trim_matches(|character: char| {
        !character.is_ascii_alphanumeric() && !matches!(character, '_' | '-')
    });
    match key.to_ascii_lowercase().as_str() {
        "authorization" => Some(SensitiveKey::Authorization),
        "password" | "passwd" | "token" | "launch_token" | "launch-token" | "access_token"
        | "secret" | "cookie" | "body" | "request" | "response" | "path" | "url" | "uri"
        | "port" | "api_key" | "apikey" => Some(SensitiveKey::Other),
        _ => None,
    }
}

fn sensitive_assignment(token: &str) -> Option<(SensitiveKey, bool)> {
    let separator = token.find([':', '='])?;
    let kind = sensitive_key(&token[..separator])?;
    let inline_value = !token[separator + 1..]
        .trim_matches(|character: char| !character.is_ascii_alphanumeric())
        .is_empty();
    Some((kind, inline_value))
}

fn token_is_authorization_scheme(token: &str) -> bool {
    matches!(
        token
            .trim_matches(|character: char| !character.is_ascii_alphanumeric())
            .to_ascii_lowercase()
            .as_str(),
        "bearer" | "basic" | "digest" | "negotiate"
    )
}

fn assignment_has_inline_authorization_scheme(token: &str) -> bool {
    token
        .find([':', '='])
        .is_some_and(|separator| token_is_authorization_scheme(&token[separator + 1..]))
}

fn normalize_recovery_text(message: &str) -> String {
    let mut normalized = String::with_capacity(message.len());
    let mut characters = message.chars().peekable();
    while let Some(character) = characters.next() {
        if character == '\u{1b}' {
            match characters.peek().copied() {
                Some('[') => {
                    characters.next();
                    for control in characters.by_ref() {
                        if ('@'..='~').contains(&control) {
                            break;
                        }
                    }
                }
                Some(']') => {
                    characters.next();
                    while let Some(control) = characters.next() {
                        if control == '\u{7}' {
                            break;
                        }
                        if control == '\u{1b}' && characters.next_if_eq(&'\\').is_some() {
                            break;
                        }
                    }
                }
                Some(_) => {
                    characters.next();
                }
                None => {}
            }
            continue;
        }
        normalized.push(if character.is_control() {
            ' '
        } else {
            character
        });
    }
    normalized
}

fn token_looks_private(token: &str) -> bool {
    let lower = token.to_ascii_lowercase();
    let endpoint = token.trim_matches(|character: char| {
        !character.is_ascii_alphanumeric() && !matches!(character, '.' | ':')
    });
    let endpoint_lower = endpoint.to_ascii_lowercase();
    let bare_port =
        (2..=5).contains(&endpoint.len()) && endpoint.bytes().all(|byte| byte.is_ascii_digit());
    let port_endpoint = endpoint.rsplit_once(':').is_some_and(|(_, port)| {
        (2..=5).contains(&port.len()) && port.bytes().all(|byte| byte.is_ascii_digit())
    });
    let sensitive_file = [
        ".sqlite", ".sqlite3", ".db", ".json", ".exe", ".py", ".toml", ".yaml", ".yml",
    ]
    .iter()
    .any(|suffix| endpoint_lower.ends_with(suffix));
    token.contains(['\\', '/', '{', '}'])
        || lower.starts_with("http:")
        || lower.starts_with("https:")
        || lower.starts_with("file:")
        || token
            .as_bytes()
            .get(1)
            .is_some_and(|separator| *separator == b':')
        || bare_port
        || port_endpoint
        || sensitive_file
        || (token.is_ascii() && token.len() >= 32 && !token.chars().any(char::is_whitespace))
}

pub fn sanitize_recovery_message(message: &str) -> String {
    #[derive(Clone, Copy)]
    enum State<'a> {
        Normal,
        AwaitSeparator { key: SensitiveKey, token: &'a str },
        AwaitValue(SensitiveKey),
        AwaitAuthorizationCredential,
    }

    let normalized = normalize_recovery_text(message);
    let mut sanitized = Vec::new();
    let mut state = State::Normal;
    for token in normalized.split_whitespace() {
        let mut reprocess = true;
        while reprocess {
            reprocess = false;
            state = match state {
                State::Normal => {
                    if let Some((key, inline_value)) = sensitive_assignment(token) {
                        if sanitized.last().copied() != Some(REDACTED) {
                            sanitized.push(REDACTED);
                        }
                        if !inline_value {
                            State::AwaitValue(key)
                        } else if key == SensitiveKey::Authorization
                            && assignment_has_inline_authorization_scheme(token)
                        {
                            State::AwaitAuthorizationCredential
                        } else {
                            State::Normal
                        }
                    } else if let Some(key) = sensitive_key(token) {
                        State::AwaitSeparator { key, token }
                    } else {
                        if token_looks_private(token) {
                            if sanitized.last().copied() != Some(REDACTED) {
                                sanitized.push(REDACTED);
                            }
                        } else {
                            sanitized.push(token);
                        }
                        State::Normal
                    }
                }
                State::AwaitSeparator {
                    key,
                    token: pending,
                } => {
                    if matches!(token, ":" | "=") {
                        if sanitized.last().copied() != Some(REDACTED) {
                            sanitized.push(REDACTED);
                        }
                        State::AwaitValue(key)
                    } else if let Some(attached_value) =
                        token.strip_prefix(':').or_else(|| token.strip_prefix('='))
                    {
                        if sanitized.last().copied() != Some(REDACTED) {
                            sanitized.push(REDACTED);
                        }
                        if key == SensitiveKey::Authorization
                            && token_is_authorization_scheme(attached_value)
                        {
                            State::AwaitAuthorizationCredential
                        } else {
                            State::Normal
                        }
                    } else {
                        sanitized.push(pending);
                        reprocess = true;
                        State::Normal
                    }
                }
                State::AwaitValue(key) => {
                    if sanitized.last().copied() != Some(REDACTED) {
                        sanitized.push(REDACTED);
                    }
                    if key == SensitiveKey::Authorization && token_is_authorization_scheme(token) {
                        State::AwaitAuthorizationCredential
                    } else {
                        State::Normal
                    }
                }
                State::AwaitAuthorizationCredential => {
                    if sanitized.last().copied() != Some(REDACTED) {
                        sanitized.push(REDACTED);
                    }
                    State::Normal
                }
            };
        }
    }
    if let State::AwaitSeparator { token, .. } = state {
        if token_looks_private(token) {
            if sanitized.last().copied() != Some(REDACTED) {
                sanitized.push(REDACTED);
            }
        } else {
            sanitized.push(token);
        }
    }
    let joined = sanitized.join(" ");
    let bounded = joined
        .chars()
        .take(MAX_RECOVERY_MESSAGE_CHARS)
        .collect::<String>();
    if bounded.is_empty() {
        "Recovery diagnostic unavailable".to_owned()
    } else {
        bounded
    }
}

fn valid_backup_timestamp(timestamp: &str) -> bool {
    if timestamp.len() != 23
        || timestamp.as_bytes().get(8) != Some(&b'T')
        || timestamp.as_bytes().get(15) != Some(&b'_')
        || timestamp.as_bytes().get(22) != Some(&b'Z')
    {
        return false;
    }
    for range in [0..8, 9..15, 16..22] {
        if !timestamp[range].bytes().all(|byte| byte.is_ascii_digit()) {
            return false;
        }
    }
    let parse = |range: std::ops::Range<usize>| timestamp[range].parse::<u32>().ok();
    let (Some(year), Some(month), Some(day), Some(hour), Some(minute), Some(second)) = (
        parse(0..4),
        parse(4..6),
        parse(6..8),
        parse(9..11),
        parse(11..13),
        parse(13..15),
    ) else {
        return false;
    };
    let leap_year =
        year.is_multiple_of(4) && (!year.is_multiple_of(100) || year.is_multiple_of(400));
    let days_in_month = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if leap_year => 29,
        2 => 28,
        _ => return false,
    };
    year != 0 && day != 0 && day <= days_in_month && hour < 24 && minute < 60 && second < 60
}

pub fn is_valid_backup_display_name(name: &str) -> bool {
    if name.contains(['/', '\\'])
        || Path::new(name).is_absolute()
        || !matches!(
            Path::new(name).components().collect::<Vec<_>>().as_slice(),
            [Component::Normal(_)]
        )
    {
        return false;
    }
    let Some(timestamp) = name
        .strip_prefix("cognitive_os_")
        .and_then(|value| value.strip_suffix(".sqlite"))
    else {
        return false;
    };
    valid_backup_timestamp(timestamp)
}

pub fn validate_enumerated_backup_name<I, S>(backups: I, name: &str) -> Result<(), &'static str>
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    if !is_valid_backup_display_name(name) {
        return Err("invalid backup selection");
    }
    backups
        .into_iter()
        .any(|candidate| {
            candidate.as_ref() == name && is_valid_backup_display_name(candidate.as_ref())
        })
        .then_some(())
        .ok_or("unknown backup selection")
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EnumeratedBackup {
    pub name: String,
    pub canonical_path: PathBuf,
    canonical_manifest: PathBuf,
    backup_identity: FileIdentity,
    manifest_identity: FileIdentity,
}

impl EnumeratedBackup {
    pub(crate) fn same_source_identity(&self, other: &Self) -> bool {
        self.name == other.name
            && self.backup_identity == other.backup_identity
            && self.manifest_identity == other.manifest_identity
    }
}

pub fn enumerate_backups(data_dir: &Path) -> Result<Vec<EnumeratedBackup>, String> {
    let backup_dir = data_dir.join("backups");
    if !backup_dir.exists() {
        return Ok(Vec::new());
    }
    let directory_metadata = std::fs::symlink_metadata(&backup_dir)
        .map_err(|_| "backup directory metadata is unavailable".to_owned())?;
    if directory_metadata.file_type().is_symlink()
        || directory_metadata.file_attributes() & FILE_ATTRIBUTE_REPARSE_POINT != 0
        || !directory_metadata.is_dir()
    {
        return Err("backup directory is not a regular directory".to_owned());
    }
    let canonical_data_dir = std::fs::canonicalize(data_dir)
        .map_err(|_| "runtime data directory cannot be canonicalized".to_owned())?;
    let canonical_backup_dir = std::fs::canonicalize(&backup_dir)
        .map_err(|_| "backup directory cannot be canonicalized".to_owned())?;
    if !canonical_backup_dir.starts_with(&canonical_data_dir) {
        return Err("backup directory is outside the runtime data directory".to_owned());
    }

    let mut backups = Vec::new();
    let entries = std::fs::read_dir(&backup_dir)
        .map_err(|_| "backup directory cannot be enumerated".to_owned())?;
    for entry in entries {
        let entry = entry.map_err(|_| "backup directory entry is unavailable".to_owned())?;
        let Some(name) = entry.file_name().to_str().map(str::to_owned) else {
            continue;
        };
        if !is_valid_backup_display_name(&name) {
            continue;
        }
        let backup_path = entry.path();
        let manifest_path = backup_dir.join(format!("{name}.manifest.json"));
        let Ok((backup_file, backup_identity)) = open_backup_source(&backup_path) else {
            continue;
        };
        let Ok((manifest_file, manifest_identity)) = open_backup_source(&manifest_path) else {
            continue;
        };
        let Ok(canonical_path) = std::fs::canonicalize(&backup_path) else {
            continue;
        };
        let Ok(canonical_manifest) = std::fs::canonicalize(&manifest_path) else {
            continue;
        };
        if !canonical_path.starts_with(&canonical_backup_dir)
            || canonical_path.parent() != Some(canonical_backup_dir.as_path())
            || !canonical_manifest.starts_with(&canonical_backup_dir)
            || canonical_manifest.parent() != Some(canonical_backup_dir.as_path())
        {
            continue;
        }
        if file_identity(&backup_file).ok() != Some(backup_identity)
            || file_identity(&manifest_file).ok() != Some(manifest_identity)
        {
            continue;
        }
        backups.push(EnumeratedBackup {
            name,
            canonical_path,
            canonical_manifest,
            backup_identity,
            manifest_identity,
        });
    }
    backups.sort_by(|left, right| right.name.cmp(&left.name));
    backups.truncate(MAX_RECOVERY_BACKUPS);
    Ok(backups)
}

pub struct StagedBackup {
    data_dir: PathBuf,
    data_dir_identity: ObjectIdentity,
    data_dir_handle: Option<File>,
    backup_path: PathBuf,
    manifest_path: PathBuf,
    backup_identity: ObjectIdentity,
    manifest_identity: ObjectIdentity,
    backup_file: Option<File>,
    manifest_file: Option<File>,
}

impl StagedBackup {
    pub fn backup_path(&self) -> &Path {
        &self.backup_path
    }

    pub fn revalidate_for_restore(&self) -> Result<(), String> {
        let data_dir_handle = self
            .data_dir_handle
            .as_ref()
            .ok_or_else(|| "runtime data directory handle is unavailable".to_owned())?;
        if directory_object_identity(data_dir_handle)? != self.data_dir_identity
            || revalidate_directory_path(&self.data_dir, self.data_dir_identity).is_err()
        {
            return Err("runtime data directory identity changed".to_owned());
        }
        let backup_file = self
            .backup_file
            .as_ref()
            .ok_or_else(|| "restore staging backup handle is unavailable".to_owned())?;
        let manifest_file = self
            .manifest_file
            .as_ref()
            .ok_or_else(|| "restore staging manifest handle is unavailable".to_owned())?;
        if regular_file_object_identity(backup_file)? != self.backup_identity
            || regular_file_object_identity(manifest_file)? != self.manifest_identity
            || revalidate_file_path(&self.backup_path, self.backup_identity).is_err()
            || revalidate_file_path(&self.manifest_path, self.manifest_identity).is_err()
        {
            return Err("restore staging file identity changed".to_owned());
        }
        for path in [&self.backup_path, &self.manifest_path] {
            let canonical = std::fs::canonicalize(path)
                .map_err(|_| "restore staging file cannot be canonicalized".to_owned())?;
            if canonical.parent() != Some(self.data_dir.as_path()) {
                return Err("restore staging file escaped the runtime data directory".to_owned());
            }
        }
        Ok(())
    }
}

impl Drop for StagedBackup {
    fn drop(&mut self) {
        if self.revalidate_for_restore().is_err() {
            self.backup_file.take();
            self.manifest_file.take();
            self.data_dir_handle.take();
            return;
        }
        self.backup_file.take();
        self.manifest_file.take();
        let data_dir_valid = self.data_dir_handle.as_ref().is_some_and(|handle| {
            held_data_directory_matches(handle, &self.data_dir, self.data_dir_identity)
        });
        if data_dir_valid {
            cleanup_staging_file_by_path(&self.backup_path, self.backup_identity);
            cleanup_staging_file_by_path(&self.manifest_path, self.manifest_identity);
        }
        self.data_dir_handle.take();
    }
}

fn verified_source(path: &Path, expected: FileIdentity) -> Result<File, String> {
    let (file, actual) = open_backup_source(path)?;
    let canonical = std::fs::canonicalize(path)
        .map_err(|_| "backup source cannot be canonicalized".to_owned())?;
    if canonical != path || actual != expected || file_identity(&file).ok() != Some(expected) {
        return Err("backup source identity changed".to_owned());
    }
    Ok(file)
}

fn open_data_directory(path: &Path, held: bool) -> Result<(File, ObjectIdentity), String> {
    let share = FILE_SHARE_READ | FILE_SHARE_WRITE | if held { 0 } else { FILE_SHARE_DELETE };
    let directory = OpenOptions::new()
        .read(true)
        .access_mode(GENERIC_READ)
        .share_mode(share)
        .custom_flags(FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS)
        .open(path)
        .map_err(|_| "runtime data directory cannot be opened".to_owned())?;
    let identity = directory_object_identity(&directory)?;
    Ok((directory, identity))
}

fn revalidate_directory_path(path: &Path, expected: ObjectIdentity) -> Result<(), String> {
    let (_, actual) = open_data_directory(path, false)?;
    (actual == expected)
        .then_some(())
        .ok_or_else(|| "runtime data directory path identity changed".to_owned())
}

enum StagingFileCreateError {
    Collision,
    Failed(String),
}

struct HeldStagingFile {
    path: PathBuf,
    identity: ObjectIdentity,
    file: Option<File>,
}

impl HeldStagingFile {
    fn into_parts(mut self) -> (PathBuf, ObjectIdentity, File) {
        let path = std::mem::take(&mut self.path);
        let identity = self.identity;
        let file = self.file.take().expect("held staging file is available");
        (path, identity, file)
    }

    fn cleanup_with_data_directory(
        &mut self,
        data_dir_handle: &File,
        data_dir: &Path,
        data_dir_identity: ObjectIdentity,
    ) {
        let file_valid = self.file.as_ref().is_some_and(|file| {
            regular_file_object_identity(file).ok() == Some(self.identity)
                && revalidate_file_path(&self.path, self.identity).is_ok()
        });
        let data_dir_valid =
            held_data_directory_matches(data_dir_handle, data_dir, data_dir_identity);
        self.file.take();
        if file_valid && data_dir_valid {
            cleanup_staging_file_by_path(&self.path, self.identity);
        }
    }
}

impl Drop for HeldStagingFile {
    fn drop(&mut self) {
        self.file.take();
    }
}

fn create_staging_file(path: &Path) -> Result<HeldStagingFile, StagingFileCreateError> {
    let file = OpenOptions::new()
        .read(true)
        .write(true)
        .create_new(true)
        .access_mode(GENERIC_READ | GENERIC_WRITE)
        .share_mode(FILE_SHARE_READ | FILE_SHARE_WRITE)
        .custom_flags(FILE_FLAG_OPEN_REPARSE_POINT)
        .open(path)
        .map_err(|error| {
            if error.kind() == io::ErrorKind::AlreadyExists {
                StagingFileCreateError::Collision
            } else {
                StagingFileCreateError::Failed("restore staging file cannot be created".to_owned())
            }
        })?;
    let identity = regular_file_object_identity(&file).map_err(StagingFileCreateError::Failed)?;
    Ok(HeldStagingFile {
        path: path.to_path_buf(),
        identity,
        file: Some(file),
    })
}

fn revalidate_file_path(path: &Path, expected: ObjectIdentity) -> Result<(), String> {
    let file = OpenOptions::new()
        .read(true)
        .access_mode(GENERIC_READ)
        .share_mode(FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE)
        .custom_flags(FILE_FLAG_OPEN_REPARSE_POINT)
        .open(path)
        .map_err(|_| "restore staging file cannot be reopened".to_owned())?;
    (regular_file_object_identity(&file)? == expected)
        .then_some(())
        .ok_or_else(|| "restore staging file path identity changed".to_owned())
}

fn held_data_directory_matches(handle: &File, path: &Path, expected: ObjectIdentity) -> bool {
    directory_object_identity(handle).ok() == Some(expected)
        && revalidate_directory_path(path, expected).is_ok()
}

fn cleanup_staging_file_by_path(path: &Path, expected: ObjectIdentity) -> bool {
    let cleanup = OpenOptions::new()
        .read(true)
        .access_mode(GENERIC_READ | DELETE_ACCESS)
        .share_mode(FILE_SHARE_READ | FILE_SHARE_WRITE)
        .custom_flags(FILE_FLAG_OPEN_REPARSE_POINT)
        .open(path);
    let Ok(cleanup) = cleanup else {
        return false;
    };
    regular_file_object_identity(&cleanup).ok() == Some(expected)
        && mark_delete_on_close(&cleanup).is_ok()
}

fn copy_to_staging(source: &mut File, destination: &mut File) -> Result<(), String> {
    io::copy(source, destination).map_err(|_| "restore staging copy failed".to_owned())?;
    destination
        .flush()
        .and_then(|_| destination.sync_all())
        .map_err(|_| "restore staging copy could not be persisted".to_owned())
}

pub fn stage_backup_for_restore(
    data_dir: &Path,
    selected: &EnumeratedBackup,
) -> Result<StagedBackup, String> {
    stage_backup_for_restore_with_nonce(data_dir, selected, || {
        let mut nonce = [0_u8; 16];
        getrandom::fill(&mut nonce)
            .map_err(|_| "restore staging name cannot be generated".to_owned())?;
        Ok(nonce)
    })
}

fn stage_backup_for_restore_with_nonce<F>(
    data_dir: &Path,
    selected: &EnumeratedBackup,
    mut next_nonce: F,
) -> Result<StagedBackup, String>
where
    F: FnMut() -> Result<[u8; 16], String>,
{
    let mut backup_source = verified_source(&selected.canonical_path, selected.backup_identity)?;
    let mut manifest_source =
        verified_source(&selected.canonical_manifest, selected.manifest_identity)?;

    let data_dir_metadata = std::fs::symlink_metadata(data_dir)
        .map_err(|_| "runtime data directory metadata is unavailable".to_owned())?;
    if data_dir_metadata.file_type().is_symlink()
        || data_dir_metadata.file_attributes() & FILE_ATTRIBUTE_REPARSE_POINT != 0
        || !data_dir_metadata.is_dir()
    {
        return Err("runtime data directory is not a regular directory".to_owned());
    }
    let canonical_data_dir = std::fs::canonicalize(data_dir)
        .map_err(|_| "runtime data directory cannot be canonicalized".to_owned())?;
    let (data_dir_handle, data_dir_identity) = open_data_directory(&canonical_data_dir, true)?;
    let mut pair = None;
    for _ in 0..8 {
        let nonce = next_nonce()?;
        let nonce = nonce
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>();
        let backup_path = canonical_data_dir.join(format!(".recovery-{nonce}.sqlite"));
        let manifest_path = backup_path.with_extension("sqlite.manifest.json");
        let mut backup = match create_staging_file(&backup_path) {
            Ok(file) => file,
            Err(StagingFileCreateError::Collision) => continue,
            Err(StagingFileCreateError::Failed(error)) => return Err(error),
        };
        let manifest = match create_staging_file(&manifest_path) {
            Ok(file) => file,
            Err(StagingFileCreateError::Collision) => {
                backup.cleanup_with_data_directory(
                    &data_dir_handle,
                    &canonical_data_dir,
                    data_dir_identity,
                );
                continue;
            }
            Err(StagingFileCreateError::Failed(error)) => {
                backup.cleanup_with_data_directory(
                    &data_dir_handle,
                    &canonical_data_dir,
                    data_dir_identity,
                );
                return Err(error);
            }
        };
        pair = Some((backup, manifest));
        break;
    }
    let (backup, manifest) =
        pair.ok_or_else(|| "restore staging file names are unavailable".to_owned())?;
    let (backup_path, backup_identity, backup_file) = backup.into_parts();
    let (manifest_path, manifest_identity, manifest_file) = manifest.into_parts();
    let mut staged = StagedBackup {
        data_dir: canonical_data_dir,
        data_dir_identity,
        data_dir_handle: Some(data_dir_handle),
        backup_path,
        manifest_path,
        backup_identity,
        manifest_identity,
        backup_file: Some(backup_file),
        manifest_file: Some(manifest_file),
    };
    copy_to_staging(
        &mut backup_source,
        staged
            .backup_file
            .as_mut()
            .ok_or_else(|| "restore staging backup handle is unavailable".to_owned())?,
    )?;
    copy_to_staging(
        &mut manifest_source,
        staged
            .manifest_file
            .as_mut()
            .ok_or_else(|| "restore staging manifest handle is unavailable".to_owned())?,
    )?;
    staged.revalidate_for_restore()?;
    Ok(staged)
}

#[derive(Debug, Clone)]
pub struct RecoveryState {
    state: String,
    safe_mode: bool,
    backend_available: bool,
    message: String,
    logs: VecDeque<String>,
    external_dev: bool,
}

impl RecoveryState {
    pub fn failed(message: &str) -> Self {
        let message = sanitize_recovery_message(message);
        let mut logs = VecDeque::with_capacity(MAX_RECOVERY_LOG_LINES);
        logs.push_back(message.clone());
        Self {
            state: "failed".to_owned(),
            safe_mode: false,
            backend_available: false,
            message,
            logs,
            external_dev: false,
        }
    }

    pub fn booting(external_dev: bool) -> Self {
        Self {
            state: "booting".to_owned(),
            safe_mode: false,
            backend_available: false,
            message: "Core startup is in progress".to_owned(),
            logs: VecDeque::with_capacity(MAX_RECOVERY_LOG_LINES),
            external_dev,
        }
    }

    pub fn enter_safe_mode(&mut self) {
        self.state = "stopped".to_owned();
        self.safe_mode = true;
        self.backend_available = false;
        self.message = "Safe mode is active".to_owned();
        self.push_log("Safe mode is active");
    }

    pub fn safe_mode(&self) -> bool {
        self.safe_mode
    }

    pub fn may_start_core(&self) -> bool {
        !self.safe_mode
    }

    pub fn may_run_migrations(&self) -> bool {
        !self.safe_mode
    }

    pub fn recovery_operations_available(&self) -> bool {
        true
    }

    pub fn begin_retry(&mut self) {
        self.state = "reconnecting".to_owned();
        self.safe_mode = false;
        self.backend_available = false;
        self.message = "Core retry is in progress".to_owned();
        self.push_log("Core retry is in progress");
    }

    pub fn mark_ready(&mut self) {
        self.state = "ready".to_owned();
        self.safe_mode = false;
        self.backend_available = true;
        self.message = "Core is ready".to_owned();
        self.push_log("Core is ready");
    }

    pub fn record_failure(&mut self, message: &str) {
        self.state = "failed".to_owned();
        self.safe_mode = false;
        self.backend_available = false;
        self.message = sanitize_recovery_message(message);
        self.record_diagnostic(message);
    }

    pub fn record_safe_mode_failure(&mut self, message: &str) {
        self.state = "stopped".to_owned();
        self.safe_mode = true;
        self.backend_available = false;
        self.message = sanitize_recovery_message(message);
        self.record_diagnostic(message);
    }

    pub fn mark_restore_success(&mut self) {
        self.state = "stopped".to_owned();
        self.safe_mode = true;
        self.backend_available = false;
        self.message = "Backup restored; retry Core when ready".to_owned();
        self.push_log("Backup restored; retry Core when ready");
    }

    pub fn set_external_dev(&mut self, external_dev: bool) {
        self.external_dev = external_dev;
    }

    pub fn record_diagnostic(&mut self, message: &str) {
        let sanitized = sanitize_recovery_message(message);
        self.push_sanitized_log(sanitized);
    }

    pub fn status(&self, backups: Vec<String>) -> RecoveryStatusDto {
        RecoveryStatusDto {
            state: self.state.clone(),
            safe_mode: self.safe_mode,
            backend_available: self.backend_available,
            message: sanitize_recovery_message(&self.message),
            backups: backups
                .into_iter()
                .filter(|name| is_valid_backup_display_name(name))
                .take(MAX_RECOVERY_BACKUPS)
                .collect(),
            external_dev: self.external_dev,
        }
    }

    pub fn log_tail(&self) -> RecoveryLogTailDto {
        RecoveryLogTailDto::new(self.logs.iter().cloned().collect())
    }

    fn push_log(&mut self, message: &str) {
        let sanitized = sanitize_recovery_message(message);
        self.push_sanitized_log(sanitized);
    }

    fn push_sanitized_log(&mut self, message: String) {
        if self.logs.len() == MAX_RECOVERY_LOG_LINES {
            self.logs.pop_front();
        }
        self.logs.push_back(message);
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct RecoveryStatusDto {
    pub state: String,
    pub safe_mode: bool,
    pub backend_available: bool,
    pub message: String,
    pub backups: Vec<String>,
    pub external_dev: bool,
}

impl RecoveryStatusDto {
    pub fn failed(message: &str, backups: Vec<String>) -> Self {
        Self {
            state: "failed".to_owned(),
            safe_mode: false,
            backend_available: false,
            message: sanitize_recovery_message(message),
            backups: backups
                .into_iter()
                .filter(|name| is_valid_backup_display_name(name))
                .take(MAX_RECOVERY_BACKUPS)
                .collect(),
            external_dev: false,
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct RecoveryLogTailDto {
    pub lines: Vec<String>,
}

impl RecoveryLogTailDto {
    pub fn new(lines: Vec<String>) -> Self {
        let start = lines.len().saturating_sub(MAX_RECOVERY_LOG_LINES);
        Self {
            lines: lines[start..]
                .iter()
                .map(|line| sanitize_recovery_message(line))
                .collect(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{
        enumerate_backups, is_valid_backup_display_name, sanitize_recovery_message,
        stage_backup_for_restore, RecoveryLogTailDto, RecoveryState,
    };
    use std::fs;
    use std::os::windows::fs::OpenOptionsExt;
    use std::process::Command;
    use tempfile::tempdir;

    const BACKUP_NAME: &str = "cognitive_os_20260823T010203_000000Z.sqlite";

    fn write_backup_pair(backup_dir: &std::path::Path, backup: &[u8], manifest: &[u8]) {
        fs::create_dir_all(backup_dir).expect("create backup directory");
        fs::write(backup_dir.join(BACKUP_NAME), backup).expect("create backup");
        fs::write(
            backup_dir.join(format!("{BACKUP_NAME}.manifest.json")),
            manifest,
        )
        .expect("create manifest");
    }

    #[test]
    fn unicode_recovery_message_is_truncated_by_characters() {
        let sanitized = sanitize_recovery_message(&"界".repeat(300));

        assert_eq!(sanitized.chars().count(), 240);
        assert!(sanitized.is_char_boundary(sanitized.len()));
    }

    #[test]
    fn recovery_message_redacts_bare_loopback_addresses_and_ports() {
        let sanitized = sanitize_recovery_message(
            "readiness failed at 127.0.0.1:4312 and localhost:4312 after port 4312; database private.sqlite was unavailable",
        );

        assert!(!sanitized.contains("127.0.0.1"));
        assert!(!sanitized.contains("localhost"));
        assert!(!sanitized.contains("4312"));
        assert!(!sanitized.contains("private.sqlite"));
    }

    #[test]
    fn recovery_message_redacts_boundary_keys_and_ansi_split_short_secrets() {
        let unsafe_message = concat!(
            "Authorization: Bearer abc123 ",
            "Authorization:Basic Zm9vOmJhcg== ",
            "password: p@ssw0rd ",
            "token= value ",
            "to\u{1b}[31mken=ansi-value\u{1b}[0m ",
            "important security"
        );

        let sanitized = sanitize_recovery_message(unsafe_message);

        for forbidden in [
            "Bearer",
            "abc123",
            "Basic",
            "Zm9vOmJhcg",
            "p@ssw0rd",
            "value",
            "ansi-value",
            "31m",
        ] {
            assert!(!sanitized.contains(forbidden), "leaked {forbidden}");
        }
        assert!(sanitized.contains("important"));
        assert!(sanitized.contains("security"));
    }

    #[test]
    fn recovery_message_redacts_ansi_and_whitespace_separated_assignments() {
        let unsafe_message = concat!(
            "Authorization \u{1b}[31m:\u{1b}[0m Bearer abc123 ",
            "token \u{1b}[32m=\u{1b}[0m short-secret ",
            "password : p@ss important security"
        );

        let sanitized = sanitize_recovery_message(unsafe_message);

        for forbidden in [
            "Authorization",
            "Bearer",
            "abc123",
            "token",
            "short-secret",
            "password",
            "p@ss",
            "31m",
            "32m",
        ] {
            assert!(!sanitized.contains(forbidden), "leaked {forbidden}");
        }
        assert!(sanitized.contains("important"));
        assert!(sanitized.contains("security"));
    }

    #[test]
    fn recovery_message_redacts_values_attached_to_separate_assignment_tokens() {
        let unsafe_message = concat!(
            "token \u{1b}[31m=short-secret\u{1b}[0m ",
            "Authorization :Bearer abc123 ",
            "password :p@ss important security"
        );

        let sanitized = sanitize_recovery_message(unsafe_message);

        for forbidden in [
            "token",
            "short-secret",
            "Authorization",
            "Bearer",
            "abc123",
            "password",
            "p@ss",
            "31m",
        ] {
            assert!(!sanitized.contains(forbidden), "leaked {forbidden}");
        }
        assert!(sanitized.contains("important"));
        assert!(sanitized.contains("security"));
    }

    #[test]
    fn recovery_diagnostic_preserves_sensitive_state_across_newlines_and_ansi() {
        let mut state = RecoveryState::failed("Core startup is unavailable");

        state.record_diagnostic(concat!(
            "token\n\u{1b}[31m=short-secret\u{1b}[0m ",
            "Authorization\r\n:Bearer abc123 important security"
        ));
        let logged = state.log_tail().lines.join(" ");

        for forbidden in [
            "token",
            "short-secret",
            "Authorization",
            "Bearer",
            "abc123",
            "31m",
        ] {
            assert!(!logged.contains(forbidden), "leaked {forbidden}");
        }
        assert!(logged.contains("important"));
        assert!(logged.contains("security"));
    }

    #[test]
    fn recovery_log_tail_keeps_only_the_latest_two_hundred_sanitized_lines() {
        let mut lines = vec!["discarded diagnostic".to_owned(); 50];
        lines.extend(vec!["retained diagnostic".to_owned(); 200]);
        let tail = RecoveryLogTailDto::new(lines);

        assert_eq!(tail.lines.len(), 200);
        assert!(tail.lines.iter().all(|line| line == "retained diagnostic"));
    }

    #[test]
    fn retry_exits_safe_mode_and_ready_transition_restores_backend_availability() {
        let mut state = RecoveryState::failed("Core startup is unavailable");
        state.enter_safe_mode();

        state.begin_retry();
        assert!(!state.safe_mode());
        assert!(state.may_start_core());
        assert!(state.may_run_migrations());
        assert_eq!(state.status(Vec::new()).state, "reconnecting");

        state.mark_ready();
        let status = state.status(Vec::new());
        assert_eq!(status.state, "ready");
        assert!(status.backend_available);
        assert!(!status.safe_mode);
    }

    #[test]
    fn restore_failure_keeps_core_stopped_in_safe_mode() {
        let mut state = RecoveryState::failed("Core startup is unavailable");
        state.enter_safe_mode();

        state.record_safe_mode_failure("restore path C:\\private\\backup.sqlite failed");

        let status = state.status(Vec::new());
        assert_eq!(status.state, "stopped");
        assert!(status.safe_mode);
        assert!(!status.backend_available);
        assert!(!status.message.contains("C:\\private"));
    }

    #[test]
    fn backup_name_grammar_rejects_malformed_dates_and_suffixes() {
        assert!(is_valid_backup_display_name(BACKUP_NAME));
        for invalid in [
            "cognitive_os_20260230T010203_000000Z.sqlite",
            "cognitive_os_20260823T250203_000000Z.sqlite",
            "cognitive_os_20260823T010203_00000Z.sqlite",
            "cognitive_os_20260823T010203_000000Z.sqlite.manifest.json",
            ".cognitive_os_20260823T010203_000000Z.sqlite",
        ] {
            assert!(!is_valid_backup_display_name(invalid), "accepted {invalid}");
        }
    }

    #[test]
    fn backup_enumeration_requires_regular_file_manifest_and_expected_directory() {
        let temp = tempdir().expect("temporary directory");
        let data_dir = temp.path().join("runtime-data");
        let backup_dir = data_dir.join("backups");
        write_backup_pair(&backup_dir, b"sqlite", b"{}");
        fs::write(
            backup_dir.join("cognitive_os_20260822T010203_000000Z.sqlite"),
            b"missing manifest",
        )
        .expect("create incomplete backup");
        fs::write(
            data_dir.join("cognitive_os_20260824T010203_000000Z.sqlite"),
            b"wrong directory",
        )
        .expect("create outside backup");

        let backups = enumerate_backups(&data_dir).expect("enumerate backups");

        assert_eq!(backups.len(), 1);
        assert_eq!(backups[0].name, BACKUP_NAME);
        assert_eq!(
            backups[0].canonical_path,
            fs::canonicalize(backup_dir.join(BACKUP_NAME)).expect("canonical backup")
        );
    }

    #[test]
    fn backup_identity_continuity_rejects_a_same_name_replacement() {
        let temp = tempdir().expect("temporary directory");
        let data_dir = temp.path().join("runtime-data");
        let backup_dir = data_dir.join("backups");
        write_backup_pair(&backup_dir, b"original-backup", b"original-manifest");
        let original = enumerate_backups(&data_dir)
            .expect("initial enumeration")
            .pop()
            .expect("initial selected backup");

        fs::remove_file(backup_dir.join(BACKUP_NAME)).expect("remove original backup");
        fs::remove_file(backup_dir.join(format!("{BACKUP_NAME}.manifest.json")))
            .expect("remove original manifest");
        write_backup_pair(&backup_dir, b"replacement-backup", b"replacement-manifest");
        let replacement = enumerate_backups(&data_dir)
            .expect("fresh enumeration")
            .pop()
            .expect("fresh same-name backup");

        assert_eq!(replacement.name, original.name);
        assert!(!original.same_source_identity(&replacement));
    }

    #[test]
    fn file_disposition_information_matches_windows_boolean_abi() {
        assert_eq!(std::mem::size_of::<super::FileDispositionInformation>(), 1);
        assert_eq!(std::mem::align_of::<super::FileDispositionInformation>(), 1);
    }

    #[test]
    fn restore_staging_allows_sqlite_compatible_read_write_open_and_then_cleans_up() {
        let temp = tempdir().expect("temporary directory");
        let data_dir = temp.path().join("runtime-data");
        let backup_dir = data_dir.join("backups");
        write_backup_pair(&backup_dir, b"original-backup", b"original-manifest");
        let selected = enumerate_backups(&data_dir)
            .expect("enumerate backups")
            .pop()
            .expect("selected backup");

        let staged = stage_backup_for_restore(&data_dir, &selected).expect("stage backup");
        let backup_path = staged.backup_path().to_path_buf();
        let manifest_path = staged.backup_path().with_extension("sqlite.manifest.json");
        let canonical_data_dir = fs::canonicalize(&data_dir).expect("canonical data directory");
        assert_eq!(backup_path.parent(), Some(canonical_data_dir.as_path()));
        assert_eq!(manifest_path.parent(), Some(canonical_data_dir.as_path()));
        assert!(backup_path
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| name.starts_with(".recovery-") && name.ends_with(".sqlite")));
        assert_eq!(
            fs::read(&backup_path).expect("read staged backup"),
            b"original-backup"
        );
        assert_eq!(
            fs::read(&manifest_path).expect("read staged manifest"),
            b"original-manifest"
        );
        let sqlite_like_handle = fs::OpenOptions::new()
            .read(true)
            .write(true)
            .access_mode(super::GENERIC_READ | super::GENERIC_WRITE)
            .share_mode(super::FILE_SHARE_READ | super::FILE_SHARE_WRITE)
            .custom_flags(super::FILE_FLAG_OPEN_REPARSE_POINT)
            .open(&backup_path)
            .expect("open staged backup with SQLite-compatible sharing");
        assert!(!data_dir.join(".recovery-staging").exists());
        drop(sqlite_like_handle);
        drop(staged);
        assert!(
            !backup_path.exists(),
            "staged backup residue was not removed"
        );
        assert!(
            !manifest_path.exists(),
            "staged manifest residue was not removed"
        );
    }

    #[test]
    fn restore_staging_does_not_touch_a_preexisting_legacy_staging_directory() {
        let temp = tempdir().expect("temporary directory");
        let data_dir = temp.path().join("runtime-data");
        let backup_dir = data_dir.join("backups");
        write_backup_pair(&backup_dir, b"original-backup", b"original-manifest");
        let staging_root = data_dir.join(".recovery-staging");
        fs::create_dir(&staging_root).expect("create preexisting staging root");
        fs::write(staging_root.join("sentinel"), b"keep").expect("write sentinel");
        let selected = enumerate_backups(&data_dir)
            .expect("enumerate backups")
            .pop()
            .expect("selected backup");

        let staged = stage_backup_for_restore(&data_dir, &selected).expect("stage backup");
        drop(staged);

        assert_eq!(
            fs::read(staging_root.join("sentinel")).expect("read sentinel"),
            b"keep"
        );
    }

    #[test]
    fn colliding_direct_staging_names_are_not_overwritten_and_partial_pairs_are_cleaned() {
        let temp = tempdir().expect("temporary directory");
        let data_dir = temp.path().join("runtime-data");
        let backup_dir = data_dir.join("backups");
        write_backup_pair(&backup_dir, b"original-backup", b"original-manifest");
        let selected = enumerate_backups(&data_dir)
            .expect("enumerate backups")
            .pop()
            .expect("selected backup");
        let first_backup =
            data_dir.join(concat!(".recovery-11111111111111111111111111111111.sqlite"));
        let second_backup =
            data_dir.join(concat!(".recovery-22222222222222222222222222222222.sqlite"));
        let second_manifest = second_backup.with_extension("sqlite.manifest.json");
        fs::write(&first_backup, b"preexisting-backup").expect("write colliding backup");
        fs::write(&second_manifest, b"preexisting-manifest").expect("write colliding manifest");
        let mut nonces = [[0x11; 16], [0x22; 16], [0x33; 16]].into_iter();

        let staged = super::stage_backup_for_restore_with_nonce(&data_dir, &selected, || {
            nonces
                .next()
                .ok_or_else(|| "test nonce sequence exhausted".to_owned())
        })
        .expect("stage after collisions");

        assert_eq!(
            fs::read(&first_backup).expect("read colliding backup"),
            b"preexisting-backup"
        );
        assert_eq!(
            fs::read(&second_manifest).expect("read colliding manifest"),
            b"preexisting-manifest"
        );
        assert!(
            !second_backup.exists(),
            "left the first half of a colliding pair"
        );
        assert!(staged
            .backup_path()
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| name.contains("33333333333333333333333333333333")));
        staged
            .revalidate_for_restore()
            .expect("revalidate collision-free pair");
        drop(staged);
    }

    #[test]
    fn restore_staging_cleanup_fails_closed_on_identity_mismatch() {
        let temp = tempdir().expect("temporary directory");
        let data_dir = temp.path().join("runtime-data");
        let backup_dir = data_dir.join("backups");
        write_backup_pair(&backup_dir, b"original-backup", b"original-manifest");
        let selected = enumerate_backups(&data_dir)
            .expect("enumerate backups")
            .pop()
            .expect("selected backup");
        let mut staged = stage_backup_for_restore(&data_dir, &selected).expect("stage backup");
        let backup_path = staged.backup_path.clone();
        let manifest_path = staged.manifest_path.clone();
        staged.backup_identity.file_index ^= 1;

        drop(staged);

        assert!(backup_path.is_file(), "deleted after an identity mismatch");
        assert!(
            manifest_path.is_file(),
            "deleted manifest after an identity mismatch"
        );
        fs::remove_file(backup_path).expect("clean test backup");
        fs::remove_file(manifest_path).expect("clean test manifest");
    }

    #[test]
    fn restore_staging_rejects_a_reparse_data_directory() {
        let temp = tempdir().expect("temporary directory");
        let real_data_dir = temp.path().join("real-runtime-data");
        let backup_dir = real_data_dir.join("backups");
        write_backup_pair(&backup_dir, b"original-backup", b"original-manifest");
        let selected = enumerate_backups(&real_data_dir)
            .expect("enumerate backups")
            .pop()
            .expect("selected backup");
        let linked_data_dir = temp.path().join("linked-runtime-data");
        let status = Command::new("cmd.exe")
            .args(["/d", "/c", "mklink", "/J"])
            .arg(&linked_data_dir)
            .arg(&real_data_dir)
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .status()
            .expect("run junction command");
        if !status.success() {
            return;
        }

        let result = stage_backup_for_restore(&linked_data_dir, &selected);

        assert!(result.is_err(), "staged through a reparse data directory");
        assert!(!real_data_dir.join(".recovery-staging").exists());
    }

    #[test]
    fn restore_staging_rejects_a_backup_replaced_after_enumeration() {
        let temp = tempdir().expect("temporary directory");
        let data_dir = temp.path().join("runtime-data");
        let backup_dir = data_dir.join("backups");
        write_backup_pair(&backup_dir, b"original-backup", b"original-manifest");
        let selected = enumerate_backups(&data_dir)
            .expect("enumerate backups")
            .pop()
            .expect("selected backup");
        fs::remove_file(backup_dir.join(BACKUP_NAME)).expect("remove selected backup");
        fs::write(backup_dir.join(BACKUP_NAME), b"replacement-backup")
            .expect("replace selected backup");

        let result = stage_backup_for_restore(&data_dir, &selected);

        assert!(result.is_err(), "staged a replaced backup identity");
        assert!(!data_dir.join(".recovery-staging").exists());
    }

    #[test]
    fn restore_staging_rejects_a_manifest_replaced_after_enumeration() {
        let temp = tempdir().expect("temporary directory");
        let data_dir = temp.path().join("runtime-data");
        let backup_dir = data_dir.join("backups");
        write_backup_pair(&backup_dir, b"original-backup", b"original-manifest");
        let selected = enumerate_backups(&data_dir)
            .expect("enumerate backups")
            .pop()
            .expect("selected backup");
        let manifest_path = backup_dir.join(format!("{BACKUP_NAME}.manifest.json"));
        fs::remove_file(&manifest_path).expect("remove selected manifest");
        fs::write(&manifest_path, b"replacement-manifest").expect("replace selected manifest");

        let result = stage_backup_for_restore(&data_dir, &selected);

        assert!(result.is_err(), "staged a replaced manifest identity");
        assert!(!data_dir.join(".recovery-staging").exists());
    }

    #[test]
    fn backup_enumeration_rejects_file_symlink_canonical_escape_when_supported() {
        let temp = tempdir().expect("temporary directory");
        let data_dir = temp.path().join("runtime-data");
        let backup_dir = data_dir.join("backups");
        let outside_dir = temp.path().join("outside");
        fs::create_dir_all(&backup_dir).expect("create backup directory");
        write_backup_pair(&outside_dir, b"outside-backup", b"outside-manifest");
        fs::write(
            backup_dir.join(format!("{BACKUP_NAME}.manifest.json")),
            b"{}",
        )
        .expect("create local manifest");
        if std::os::windows::fs::symlink_file(
            outside_dir.join(BACKUP_NAME),
            backup_dir.join(BACKUP_NAME),
        )
        .is_err()
        {
            return;
        }

        let backups = enumerate_backups(&data_dir).expect("enumerate backups");

        assert!(backups.is_empty(), "enumerated a symlink escape");
    }

    #[test]
    fn backup_enumeration_rejects_junction_escape() {
        let temp = tempdir().expect("temporary directory");
        let data_dir = temp.path().join("runtime-data");
        let backup_dir = data_dir.join("backups");
        let outside_dir = temp.path().join("outside");
        fs::create_dir_all(&data_dir).expect("create data directory");
        write_backup_pair(&outside_dir, b"outside-backup", b"outside-manifest");
        let status = Command::new("cmd.exe")
            .args(["/d", "/c", "mklink", "/J"])
            .arg(&backup_dir)
            .arg(&outside_dir)
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .status()
            .expect("run junction command");
        if !status.success() {
            return;
        }

        let result = enumerate_backups(&data_dir);

        assert!(result.is_err(), "enumerated through a junction escape");
    }
}
