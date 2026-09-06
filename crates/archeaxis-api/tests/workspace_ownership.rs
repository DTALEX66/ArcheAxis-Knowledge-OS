use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc;
use std::time::Duration;

struct OwnedCore(Child);
impl Drop for OwnedCore {
    fn drop(&mut self) { let _ = self.0.kill(); let _ = self.0.wait(); }
}

fn launch(db: &std::path::Path) -> (OwnedCore, mpsc::Receiver<String>) {
    let mut command = Command::new(env!("CARGO_BIN_EXE_archeaxis-api"));
    command.arg(db).arg("0").stdout(Stdio::piped()).stderr(Stdio::null());
    #[cfg(windows)] {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = OwnedCore(command.spawn().unwrap());
    let stdout = child.0.stdout.take().unwrap();
    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            if tx.send(line).is_err() { break; }
        }
    });
    (child, rx)
}

#[test]
fn same_workspace_is_exclusive_until_last_router_clone_is_dropped() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let first = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let last_clone = first.clone();
    assert!(archeaxis_api::app(db.to_str().unwrap()).is_err(), "second writer was admitted");
    drop(first);
    assert!(archeaxis_api::app(db.to_str().unwrap()).is_err(), "clone lost ownership");
    let independent = archeaxis_api::app(dir.path().join("other.sqlite").to_str().unwrap()).unwrap();
    drop(independent);
    drop(last_clone);
    let reopened = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    drop(reopened);
}

#[test]
fn another_core_process_is_refused_and_a_crashed_owner_does_not_leave_a_stale_lock() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("cross process.sqlite");
    let (first, ready) = launch(&db);
    assert!(ready.recv_timeout(Duration::from_secs(10)).unwrap().starts_with("archeaxis-api ready on"));
    let (mut second, messages) = launch(&db);
    assert!(messages.recv_timeout(Duration::from_secs(5)).is_err(), "second process announced readiness");
    assert!(!second.0.wait().unwrap().success());
    drop(first); // kills only our fixture child; OS must release the held lock.
    let (recovered, ready) = launch(&db);
    assert!(ready.recv_timeout(Duration::from_secs(10)).unwrap().starts_with("archeaxis-api ready on"));
    drop(recovered);
}

#[test]
fn hardlinked_database_alias_cannot_acquire_a_second_writer() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let first = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let alias = dir.path().join("alias.sqlite");
    std::fs::hard_link(&db, &alias).unwrap();
    assert!(archeaxis_api::app(alias.to_str().unwrap()).is_err());
    drop(first);
    assert!(archeaxis_api::app(db.to_str().unwrap()).is_err(), "ambiguous hardlinks must fail closed");
}
