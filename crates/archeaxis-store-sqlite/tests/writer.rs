use archeaxis_store_sqlite::writer::{Store, StoreError};
use std::{
    future::Future,
    pin::Pin,
    sync::mpsc,
    task::{Context, Poll, Waker},
    time::Duration,
};

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
        conn.execute_batch(
            "BEGIN; INSERT INTO workspace_meta(key,value) VALUES('must_rollback','yes');",
        )
        .unwrap();
        started.send(()).unwrap();
        wait.recv_timeout(Duration::from_secs(5)).unwrap();
        panic!("injected domain panic");
    }));
    assert!(poll_once(first.as_mut()).is_pending());
    ready.recv_timeout(Duration::from_secs(5)).unwrap();
    let mut pending = Box::pin(store.submit(|_| 2));
    assert!(poll_once(pending.as_mut()).is_pending());
    release.send(()).unwrap();
    assert!(matches!(
        tokio::time::timeout(Duration::from_secs(5), first)
            .await
            .unwrap(),
        Err(StoreError::Closed)
    ));
    assert!(matches!(
        tokio::time::timeout(Duration::from_secs(5), pending)
            .await
            .unwrap(),
        Err(StoreError::Closed)
    ));
    drop(store);
    let reopened = Store::open(&path).unwrap();
    let count = reopened
        .submit(|conn| {
            conn.query_row(
                "SELECT count(*) FROM workspace_meta WHERE key='must_rollback'",
                [],
                |r| r.get::<_, i64>(0),
            )
            .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(count, 0);
    assert!(matches!(
        reopened
            .submit(|conn| conn.execute_batch("BEGIN").unwrap())
            .await,
        Err(StoreError::Closed)
    ));
}

#[tokio::test]
async fn dropping_a_reply_does_not_pretend_an_accepted_write_was_cancelled() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("cancel.sqlite");
    let store = Store::open(&path).unwrap();
    let (release, wait) = mpsc::channel();
    let mut operation = Box::pin(store.submit(move |conn| {
        wait.recv_timeout(Duration::from_secs(5)).unwrap();
        conn.execute(
            "INSERT INTO workspace_meta(key,value) VALUES('accepted','yes')",
            [],
        )
        .unwrap();
    }));
    assert!(poll_once(operation.as_mut()).is_pending());
    drop(operation);
    release.send(()).unwrap();
    drop(store); // Must drain accepted operations before returning/allowing reopen.
    let reopened = Store::open(&path).unwrap();
    let value = reopened
        .submit(|conn| {
            conn.query_row(
                "SELECT value FROM workspace_meta WHERE key='accepted'",
                [],
                |r| r.get::<_, String>(0),
            )
            .unwrap()
        })
        .await
        .unwrap();
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

#[test]
fn schema_ten_nonempty_documents_migrate_without_losing_versions_blocks_or_foreign_keys() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("v10.sqlite");
    let conn = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    // A synthetic v10-shaped fixture with pre-existing Source, editor version and block.
    // Remove every post-v10 object from the current initializer before changing its version.
    conn.execute_batch("PRAGMA foreign_keys=OFF;
        DROP TABLE teaching_withdrawals;
        DROP TABLE teaching_records;
        DROP TABLE document_checks;
        ALTER TABLE document_versions DROP COLUMN revision_basis;
        CREATE TABLE old_documents(document_id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES sources(source_id),source_revision TEXT NOT NULL,title TEXT NOT NULL,current_version INTEGER NOT NULL CHECK(current_version>=0),created_at TEXT NOT NULL DEFAULT(datetime('now')));
        DROP TABLE documents; ALTER TABLE old_documents RENAME TO documents;
        INSERT INTO sources(source_id,sha256,original_name) VALUES('src_migration','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','v10.txt');
        INSERT INTO documents(document_id,source_id,source_revision,title,current_version) VALUES('doc_migration','src_migration','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','retained',1);
        INSERT INTO document_versions(document_id,version,editor_json,text_projection,content_sha256) VALUES('doc_migration',1,'{\"type\":\"doc\",\"content\":[]}','retained projection','bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb');
        INSERT INTO document_blocks VALUES('doc_migration',1,'blk_retained',0,'paragraph','{}','retained projection','known');
        UPDATE workspace_meta SET value='10' WHERE key='schema_version'; PRAGMA foreign_keys=ON;").unwrap();
    assert_eq!(
        conn.query_row(
            "SELECT count(*) FROM sqlite_master WHERE name IN ('teaching_records','teaching_withdrawals','teaching_records_parent_idx','teaching_withdrawals_record_idx','teaching_records_no_update','teaching_records_no_delete','teaching_withdrawals_no_update','teaching_withdrawals_no_delete')",
            [], |r| r.get::<_, i64>(0)
        ).unwrap(),
        0
    );
    let before: String = conn
        .query_row("SELECT editor_json FROM document_versions", [], |r| {
            r.get(0)
        })
        .unwrap();
    drop(conn);
    let conn = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(archeaxis_store_sqlite::SCHEMA_VERSION, 12);
    assert_eq!(
        conn.query_row(
            "SELECT value FROM workspace_meta WHERE key='schema_version'",
            [],
            |r| r.get::<_, String>(0)
        )
        .unwrap(),
        "12"
    );
    assert_eq!(
        conn.query_row("SELECT editor_json FROM document_versions", [], |r| r
            .get::<_, String>(0))
            .unwrap(),
        before
    );
    assert_eq!(
        conn.query_row(
            "SELECT count(*) FROM document_blocks WHERE block_id='blk_retained'",
            [],
            |r| r.get::<_, i64>(0)
        )
        .unwrap(),
        1
    );
    assert_eq!(
        conn.query_row(
            "SELECT EXISTS(SELECT 1 FROM pragma_foreign_key_check)",
            [],
            |r| r.get::<_, bool>(0)
        )
        .unwrap(),
        false
    );
    assert_eq!(
        conn.query_row("PRAGMA foreign_keys", [], |r| r.get::<_, i64>(0))
            .unwrap(),
        1
    );
    assert_eq!(
        conn.query_row("SELECT count(*) FROM document_checks", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        0
    );
    conn.execute("INSERT INTO documents(document_id,title,current_version) VALUES('doc_original','no fabricated source',0)",[]).unwrap();
    assert!(conn.execute("INSERT INTO documents(document_id,source_id,title,current_version) VALUES('half','src_migration','invalid',0)",[]).is_err());
    for table in ["teaching_records", "teaching_withdrawals"] {
        assert_eq!(
            conn.query_row(&format!("SELECT count(*) FROM {table}"), [], |r| r
                .get::<_, i64>(0))
                .unwrap(),
            0
        );
    }
    assert_eq!(conn.query_row(
        "SELECT count(*) FROM sqlite_master WHERE type='trigger' AND name IN ('teaching_records_no_update','teaching_records_no_delete','teaching_withdrawals_no_update','teaching_withdrawals_no_delete')",
        [], |r| r.get::<_, i64>(0)
    ).unwrap(), 4);
}
