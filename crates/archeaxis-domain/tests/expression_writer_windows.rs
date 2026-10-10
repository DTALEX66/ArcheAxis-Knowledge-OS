#![cfg(windows)]
use archeaxis_domain::{document, source};
use archeaxis_store_sqlite::{raw_objects, writer::Store};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{
    future::Future,
    sync::Arc,
    task::{Context, Poll, Wake, Waker},
    time::{Duration, Instant},
};
struct ThreadWake(std::thread::Thread);
impl Wake for ThreadWake {
    fn wake(self: Arc<Self>) {
        self.0.unpark();
    }
    fn wake_by_ref(self: &Arc<Self>) {
        self.0.unpark();
    }
}
fn wait<T>(future: impl Future<Output = T>) -> T {
    let waker = Waker::from(Arc::new(ThreadWake(std::thread::current())));
    let mut context = Context::from_waker(&waker);
    let mut future = Box::pin(future);
    let deadline = Instant::now() + Duration::from_secs(15);
    loop {
        match future.as_mut().poll(&mut context) {
            Poll::Ready(value) => return value,
            Poll::Pending => {
                assert!(Instant::now() < deadline, "Store callback did not finish");
                std::thread::park_timeout(Duration::from_millis(10));
            }
        }
    }
}
#[test]
fn real_store_verbatim_disk_media_write_and_reopen_retains_bound_cas() {
    let d = tempfile::tempdir().unwrap();
    let db = d.path().join("actual-writer.sqlite");
    let store = Store::open(&db).unwrap();
    let (id,digest)=wait(store.submit(|conn|->Result<(String,String),document::Error>{
 let raw_path=std::path::Path::new(conn.path().unwrap());assert!(matches!(raw_path.components().next(),Some(std::path::Component::Prefix(p)) if matches!(p.kind(),std::path::Prefix::VerbatimDisk(_))),"regression must exercise actual canonical Windows Store path");
 let bytes=include_bytes!("../../../tests/fixtures/golden/golden-screenshot-ocr.png");let digest=hex::encode(Sha256::digest(bytes));let sid=match source::import_source(conn,bytes,"actually-image.not-png",None)?{source::ImportOutcome::Imported{source_id,..}=>source_id,_=>panic!("source")};
 let cas=raw_objects::root(conn)?.join(&digest);assert!(raw_objects::read_staged(&cas,bytes.len()).is_err(),"external staging prefix policy remains strict");assert_eq!(raw_objects::read_bounded(conn,&digest,bytes.len())?,bytes);
 let expression=json!({"schema":"archeaxis.expression/v1","nodes":[{"id":"image","type":"media","x":-42,"y":30,"width":120,"height":80,"text":"真实Store媒体回归","media":{"source_id":sid,"sha256":digest,"media_type":"image/png"}}],"edges":[]});
 let editor=json!({"type":"doc","attrs":{"archeaxis_expression":expression},"content":[]});let value=document::create_optional_with_request(conn,None,None,"Writer media",editor,Some("writer-media-regression"))?;assert_eq!(value["version"],1);Ok((value["document_id"].as_str().unwrap().to_owned(),digest))
 })).unwrap().unwrap();
    drop(store);
    let store = Store::open(&db).unwrap();
    wait(store.submit(move |conn| {
        let value = document::read(conn, &id, None).unwrap();
        assert_eq!(
            value["editor_json"]["attrs"]["archeaxis_expression"]["nodes"][0]["x"],
            -42
        );
        assert_eq!(value["text_projection"], "真实Store媒体回归");
        assert!(raw_objects::read_bounded(conn, &digest, 0).is_err());
        assert_eq!(
            raw_objects::read_bounded(conn, &digest, 32 * 1024 * 1024).unwrap(),
            include_bytes!("../../../tests/fixtures/golden/golden-screenshot-ocr.png")
        );
    }))
    .unwrap();
}
