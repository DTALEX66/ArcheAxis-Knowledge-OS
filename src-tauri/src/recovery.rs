use serde::Serialize;
use std::collections::VecDeque;
use std::path::{Component, Path, PathBuf};

const MAX_RECOVERY_MESSAGE_CHARS: usize = 240;
const MAX_RECOVERY_LOG_LINES: usize = 200;
const MAX_RECOVERY_BACKUPS: usize = 200;
const REDACTED: &str = "[redacted]";

fn token_is_sensitive(token: &str) -> bool {
    let lower = token.to_ascii_lowercase();
    lower.contains("token")
        || lower.contains("secret")
        || lower.contains("password")
        || lower.contains("authorization")
        || lower.contains("cookie")
        || lower.contains("request")
        || lower.contains("response")
        || lower.contains("body")
        || lower.contains("path")
        || lower.contains("url")
        || lower.contains("uri")
        || lower.contains("port")
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
    let normalized = message
        .chars()
        .map(|character| {
            if character.is_control() {
                ' '
            } else {
                character
            }
        })
        .collect::<String>();
    let mut sanitized = Vec::new();
    let mut redact_next = false;
    for token in normalized.split_whitespace() {
        let sensitive = token_is_sensitive(token);
        if redact_next || sensitive || token_looks_private(token) {
            if sanitized.last().copied() != Some(REDACTED) {
                sanitized.push(REDACTED);
            }
            redact_next = sensitive
                && !token.contains('=')
                && !token.contains(':')
                && !token_looks_private(token);
            continue;
        }
        redact_next = false;
        sanitized.push(token);
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
}

pub fn enumerate_backups(data_dir: &Path) -> Result<Vec<EnumeratedBackup>, String> {
    let backup_dir = data_dir.join("backups");
    if !backup_dir.exists() {
        return Ok(Vec::new());
    }
    let directory_metadata = std::fs::symlink_metadata(&backup_dir)
        .map_err(|_| "backup directory metadata is unavailable".to_owned())?;
    if directory_metadata.file_type().is_symlink() || !directory_metadata.is_dir() {
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
        let file_type = entry
            .file_type()
            .map_err(|_| "backup file type is unavailable".to_owned())?;
        if file_type.is_symlink() || !file_type.is_file() {
            continue;
        }
        let backup_path = entry.path();
        let manifest_path = backup_dir.join(format!("{name}.manifest.json"));
        let Ok(manifest_metadata) = std::fs::symlink_metadata(&manifest_path) else {
            continue;
        };
        if manifest_metadata.file_type().is_symlink() || !manifest_metadata.is_file() {
            continue;
        }
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
        backups.push(EnumeratedBackup {
            name,
            canonical_path,
        });
    }
    backups.sort_by(|left, right| right.name.cmp(&left.name));
    backups.truncate(MAX_RECOVERY_BACKUPS);
    Ok(backups)
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
        for line in message.lines() {
            self.push_log(line);
        }
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
        if self.logs.len() == MAX_RECOVERY_LOG_LINES {
            self.logs.pop_front();
        }
        self.logs.push_back(sanitize_recovery_message(message));
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
        RecoveryLogTailDto, RecoveryState,
    };
    use std::fs;
    use tempfile::tempdir;

    const BACKUP_NAME: &str = "cognitive_os_20260823T010203_000000Z.sqlite";

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
        fs::create_dir_all(&backup_dir).expect("create backup directory");
        fs::write(backup_dir.join(BACKUP_NAME), b"sqlite").expect("create backup");
        fs::write(
            backup_dir.join(format!("{BACKUP_NAME}.manifest.json")),
            b"{}",
        )
        .expect("create manifest");
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
}
