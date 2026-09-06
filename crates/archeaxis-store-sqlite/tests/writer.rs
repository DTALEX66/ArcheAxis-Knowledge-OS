use archeaxis_store_sqlite::writer::{Store, StoreError};
use std::{future::Future, pin::Pin, sync::mpsc, task::{Context, Poll, Waker}, time::Duration};

fn poll_once<T>(future: Pin<&mut impl Future<Output = T>>) -> Poll<T> {
    future.poll(&mut Context::from_waker(Waker::noop()))
}

#[tokio::test]
async fn bounded_queue_keeps_order_and_uses_one_non_caller_thread() {
    let dir = tempfile::tempdir().unwrap();
    let store = Store::open_with_capacity(&dir.path().join("q.sqlite"), 1).unwrap();
    let (started, ready) = mpsc::channel();
    let (release, wait) = mpsc::channel();
    let caller = std::thread::current().id();
    let mut first = Box::pin(store.submit(move |_| {
        started.send(()).unwrap();
        wait.recv_timeout(Duration::from_secs(5)).unwrap();
        std::thread::current().id()
    }));
    assert!(poll_once(first.as_mut()).is_pending());
    ready.recv_timeout(Duration::from_secs(5)).unwrap();
    let mut queued = Box::pin(store.submit(|conn| {
        assert!(conn.is_autocommit());
        std::thread::current().id()
    }));
    assert!(poll_once(queued.as_mut()).is_pending());
    assert!(matches!(store.submit(|_| ()).await, Err(StoreError::Busy)));
    release.send(()).unwrap();
    let writer = first.await.unwrap();
    assert_ne!(caller, writer);
    assert_eq!(queued.await.unwrap(), writer);
}

#[tokio::test]
async fn panic_closes_pending_replies_and_unfinished_transactions_roll_back() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("panic.sqlite");
    let store = Store::open_with_capacity(&path, 2).unwrap();
    let (started, ready) = mpsc::channel();
    let (release, wait) = mpsc::channel();
    let mut first = Box::pin(store.submit(move |conn| {
        conn.execute_batch("BEGIN; INSERT INTO workspace_meta(key,value) VALUES('must_rollback','yes');").unwrap();
        started.send(()).unwrap();
        wait.recv_timeout(Duration::from_secs(5)).unwrap();
        panic!("injected domain panic");
    }));
    assert!(poll_once(first.as_mut()).is_pending());
    ready.recv_timeout(Duration::from_secs(5)).unwrap();
    let mut pending = Box::pin(store.submit(|_| 2));
    assert!(poll_once(pending.as_mut()).is_pending());
    release.send(()).unwrap();
    assert!(matches!(tokio::time::timeout(Duration::from_secs(5), first).await.unwrap(), Err(StoreError::Closed)));
    assert!(matches!(tokio::time::timeout(Duration::from_secs(5), pending).await.unwrap(), Err(StoreError::Closed)));
    drop(store);
    let reopened = Store::open(&path).unwrap();
    let count = reopened.submit(|conn| conn.query_row("SELECT count(*) FROM workspace_meta WHERE key='must_rollback'", [], |r| r.get::<_, i64>(0)).unwrap()).await.unwrap();
    assert_eq!(count, 0);
    assert!(matches!(reopened.submit(|conn| conn.execute_batch("BEGIN").unwrap()).await, Err(StoreError::Closed)));
}

#[tokio::test]
async fn dropping_a_reply_does_not_pretend_an_accepted_write_was_cancelled() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("cancel.sqlite");
    let store = Store::open(&path).unwrap();
    let (release, wait) = mpsc::channel();
    let mut operation = Box::pin(store.submit(move |conn| {
        wait.recv_timeout(Duration::from_secs(5)).unwrap();
        conn.execute("INSERT INTO workspace_meta(key,value) VALUES('accepted','yes')", []).unwrap();
    }));
    assert!(poll_once(operation.as_mut()).is_pending());
    drop(operation);
    release.send(()).unwrap();
    drop(store); // Must drain accepted operations before returning/allowing reopen.
    let reopened = Store::open(&path).unwrap();
    let value = reopened.submit(|conn| conn.query_row("SELECT value FROM workspace_meta WHERE key='accepted'", [], |r| r.get::<_, String>(0)).unwrap()).await.unwrap();
    assert_eq!(value, "yes");
}

#[test]
fn parent_creation_and_stale_lock_content_do_not_create_another_identity() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("nested dir/new.sqlite");
    drop(Store::open(&path).unwrap());
    let lock = path.with_file_name("new.sqlite.writer.lock");
    std::fs::write(&lock, b"untrusted old PID text").unwrap();
    let store = Store::open(&path).unwrap();
    drop(store);
    assert_eq!(std::fs::read(lock).unwrap(), b"untrusted old PID text");
}
