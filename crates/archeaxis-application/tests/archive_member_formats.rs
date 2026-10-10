//! Real existing workers and SQLite; project-authored fixtures, no cloud/media execution.
use archeaxis_application::{
    container,
    executor::{Cancellation, Executor},
    jobs,
};
use archeaxis_domain::source::{self, ImportOutcome};
use serde_json::Value;
use std::path::{Path, PathBuf};
fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON")
        .expect("registered product Python")
        .into()
}
fn repo() -> PathBuf {
    std::env::var_os("ARCHEAXIS_TEST_SOURCE_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."))
        .canonicalize()
        .unwrap()
}
async fn open(dir: &Path) -> Executor {
    Executor::open_routes(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python(),
        &repo().join("services/python-workers/transport/text_ndjson.py"),
        &[
            (
                "archive.inventory",
                repo().join("services/python-workers/document/worker_archive.py"),
            ),
            (
                "office.structure",
                repo().join("services/python-workers/document/worker_office.py"),
            ),
            (
                "html.structure",
                repo().join("services/python-workers/web/worker_html.py"),
            ),
            (
                "canvas.structure",
                repo().join("services/python-workers/document/worker_canvas.py"),
            ),
            (
                "subtitles.structure",
                repo().join("services/python-workers/document/worker_subtitles.py"),
            ),
        ],
    )
    .await
    .unwrap()
}
fn payload() -> Vec<u8> {
    let script = r#"import io,sys,tarfile,zipfile
from pathlib import Path
root=Path(sys.argv[1])/'tests/fixtures/golden'
inner=io.BytesIO()
with zipfile.ZipFile(inner,'w') as q: q.writestr('deep/inside.txt','nested archive value 6371\n')
tbody=io.BytesIO()
with tarfile.open(fileobj=tbody,mode='w') as t:
 data=b'nested tar value 6371\n'
 info=tarfile.TarInfo('deep/tarinside.txt'); info.size=len(data)
 t.addfile(info,io.BytesIO(data))
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w') as z:
 for name in ('golden-xlsx-anchor.xlsx','golden-pptx-anchor.pptx','golden-web-anchor.html','golden-canvas-anchor.canvas','golden-subtitles-anchor.srt'): z.write(root/name,'members/'+name)
 z.writestr('members/ordinary.json','{"known":"ordinary-json-value"}')
 z.writestr('members/nested.zip',inner.getvalue())
 z.writestr('members/nested.tar',tbody.getvalue())
 z.writestr('members/media.wav',b'opaque media no decode')
sys.stdout.buffer.write(buf.getvalue())
"#;
    let output = std::process::Command::new(python())
        .args(["-B", "-c", script])
        .arg(repo())
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "fixture generation must execute, never skip"
    );
    output.stdout
}
#[tokio::test]
async fn existing_format_members_execute_preserving_structure_origin_loss_and_reopen() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open(dir.path()).await;
    let bytes = payload();
    let parent = executor
        .store()
        .submit(move |conn| {
            let id = match source::import_source(conn, &bytes, "formats.zip", None).unwrap() {
                ImportOutcome::Imported { source_id, .. }
                | ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "formats", "archive", &id).unwrap();
            id
        })
        .await
        .unwrap();
    executor
        .execute("formats", "archive-formats", 120000, &Cancellation::new())
        .await
        .unwrap();
    let query = parent.clone();
    let rows = executor
        .store()
        .submit(move |conn| container::members_of(conn, &query).unwrap())
        .await
        .unwrap();
    assert_eq!(rows.len(), 9);
    let mut snapshots = Vec::new();
    for row in rows {
        let kind = match row.member.rsplit('.').next().unwrap() {
            "xlsx" | "pptx" => Some("office"),
            "html" => Some("html"),
            "canvas" => Some("canvas"),
            "srt" => Some("subtitles"),
            "json" => Some("text"),
            // a nested container is a member like any other now: its own archive job opens it
            "zip" | "tar" => Some("archive"),
            _ => None,
        };
        let Some(kind) = kind else {
            assert!(
                row.job_id.is_none(),
                "media with no member route stays custody: {}",
                row.member
            );
            continue;
        };
        let job = row.job_id.expect("supported member must be enqueued");
        let check = job.clone();
        let actual = executor
            .store()
            .submit(move |conn| {
                conn.query_row("SELECT kind FROM jobs WHERE job_id=?1", [check], |r| {
                    r.get::<_, String>(0)
                })
                .unwrap()
            })
            .await
            .unwrap();
        assert_eq!(actual, kind);
        executor
            .execute(
                &job,
                &format!("execute-{job}"),
                120000,
                &Cancellation::new(),
            )
            .await
            .unwrap();
        let id = row.source_id.clone();
        let source_revision = row.sha256.clone();
        let member = row.member.clone();
        let original = parent.clone();
        let job_clone = job.clone();
        let stored=executor.store().submit(move |conn| {
            assert_eq!(jobs::job_state(conn,&job_clone).unwrap().unwrap(),"succeeded");
            let text:String=conn.query_row("SELECT content FROM job_outputs WHERE job_id=?1 AND kind='text' ORDER BY attempt DESC LIMIT 1",[&job_clone],|r|r.get(0)).unwrap();
            let structure:String=conn.query_row("SELECT content FROM job_outputs WHERE job_id=?1 AND kind='document_structure' ORDER BY attempt DESC LIMIT 1",[&job_clone],|r|r.get(0)).unwrap();
            let loss:String=conn.query_row("SELECT content FROM job_outputs WHERE job_id=?1 AND kind='loss_report' ORDER BY attempt DESC LIMIT 1",[&job_clone],|r|r.get(0)).unwrap();
            let reference:String=conn.query_row("SELECT origin_ref FROM source_origins WHERE source_id=?1 AND origin_kind='import'",[&id],|r|r.get(0)).unwrap();assert_eq!(reference,format!("{original}#{member}"));
            let revision:String=conn.query_row("SELECT sha256 FROM sources WHERE source_id=?1",[&id],|r|r.get(0)).unwrap();assert_eq!(revision,source_revision);
            assert!(!serde_json::from_str::<Value>(&structure).unwrap().as_array().unwrap().is_empty());
            let receipt:Value=serde_json::from_str(&loss).unwrap();assert!(!receipt["loss_note"].as_str().unwrap().is_empty());
            let expected=if member.ends_with("xlsx") {"Sheet evidence anchor"}else if member.ends_with("pptx"){"Slide evidence anchor"}else if member.ends_with("html"){"Web evidence anchor"}else if member.ends_with("json"){"ordinary-json-value"}else if member.ends_with("zip"){"deep/inside.txt"}else if member.ends_with("tar"){"deep/tarinside.txt"}else{"Golden Journey Evidence"};assert!(text.contains(expected),"known member text not extracted: {member}");
            if member.ends_with("zip") || member.ends_with("tar") {
                // the second level: the nested container's own job opened it, so its file is a
                // member of it, recorded with this archive as its container
                let inner = container::members_of(conn, &id).unwrap();
                let named = inner.iter().any(|row| {
                    row.member == "deep/inside.txt" || row.member == "deep/tarinside.txt"
                });
                assert!(named, "the nested container was opened by its own job: {inner:?}");
            }
            if !(member.ends_with("json") || member.ends_with("zip") || member.ends_with("tar")) {
                let anchors=receipt["params"]["worker_structure"].as_array().unwrap();assert!(!anchors.is_empty(),"format structure retained in loss receipt");
                let first=&anchors[0];assert!(!first["path"].as_array().unwrap().is_empty());
                if member.ends_with("xlsx") {assert_eq!(first["kind"],"sheet_row");assert!(first["path"][0].as_str().unwrap().starts_with("sheet-"));}
                else if member.ends_with("pptx") {assert_eq!(first["path"][0],"slide-1");assert_eq!(first["kind"],"slide");}
                else if member.ends_with("html") {assert_eq!(first["kind"],"block");}
                else if member.ends_with("canvas") {assert_eq!(first["kind"],"text_node");assert_eq!(first["path"][0],"n1");}
                else if member.ends_with("srt") {assert_eq!(first["kind"],"cue");assert_eq!(first["offset_ms"],0);assert_eq!(first["duration_ms"],2000);}
            }
            (id,job_clone,text,structure,loss,reference,revision)
        }).await.unwrap();
        snapshots.push(stored);
    }
    assert_eq!(snapshots.len(), 8);
    drop(executor);
    let reopened = open(dir.path()).await;
    reopened.store().submit(move |conn| {
        for (id,job,text,structure,loss,origin,revision) in snapshots {
            assert_eq!(jobs::job_state(conn,&job).unwrap().unwrap(),"succeeded");
            for (kind,expected) in [("text",text),("document_structure",structure),("loss_report",loss)] {let actual:String=conn.query_row("SELECT content FROM job_outputs WHERE job_id=?1 AND kind=?2 ORDER BY attempt DESC LIMIT 1",rusqlite::params![job,kind],|r|r.get(0)).unwrap();assert_eq!(actual,expected);}
            let actual:String=conn.query_row("SELECT origin_ref FROM source_origins WHERE source_id=?1 AND origin_kind='import'",[&id],|r|r.get(0)).unwrap();assert_eq!(actual,origin);
            let actual:String=conn.query_row("SELECT sha256 FROM sources WHERE source_id=?1",[&id],|r|r.get(0)).unwrap();assert_eq!(actual,revision);
        }
        let count:i64=conn.query_row("SELECT count(*) FROM jobs WHERE job_id LIKE 'formats-member-%'",[],|r|r.get(0)).unwrap();assert_eq!(count,10,"the eight routed members plus one file job inside each nested container");
        let media:i64=conn.query_row("SELECT count(*) FROM jobs j JOIN source_origins o ON o.source_id=j.input_ref WHERE o.origin_ref LIKE '%media.wav'",[],|r|r.get(0)).unwrap();assert_eq!(media,0,"a member no route can read still gets no job");
    }).await.unwrap();
}
