//! Synthetic owned-worker protocol integration, not evidence of a real cloud/provider call.
use archeaxis_application::executor::{DocumentCheckConfig, Executor};
use axum::{Router, body::Body, http::Request};
use serde_json::{Value, json};
use tower::ServiceExt;
async fn call(router: &Router, method: &str, path: &str, body: Value, actor: &str) -> (u16, Value) {
    let mut body = body;
    // Existing lifecycle fixtures explicitly model the user's preview-confirm
    // sequence. raw_call remains available for no-confirmation refusal tests.
    if method == "POST"
        && path.ends_with("/checks/execute")
        && actor == "human"
        && body["preview"].is_null()
        && body["confirmed_egress_sha256"].is_null()
    {
        let mut preview = body.clone();
        preview["preview"] = json!(true);
        let (_, plan) = raw_call(router, method, path, preview, actor).await;
        if let Some(hash) = plan["egress_sha256"].as_str() {
            body["confirmed_egress_sha256"] = json!(hash);
        }
    }
    raw_call(router, method, path, body, actor).await
}
async fn raw_call(
    router: &Router,
    method: &str,
    path: &str,
    body: Value,
    actor: &str,
) -> (u16, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = axum::body::to_bytes(response.into_body(), 1048576)
        .await
        .unwrap();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

const READY_PREAMBLE: &str = "import os,json\nfrom pathlib import Path\n_d=Path(os.environ['ARCHEAXIS_DOCUMENT_CHECK_DISPATCH_DIR'])\n(_d/'ready.tmp').write_text(json.dumps({'schema':'archeaxis.egress-dispatch/v1','egress_sha256':os.environ['ARCHEAXIS_DOCUMENT_CHECK_DISPATCH_HASH']}))\n(_d/'ready.tmp').replace(_d/'ready.json')\n";

// Prepare real parser modules in the fixture worker itself, after main's
// unchanged dispatch-ready handshake and before the original execute function.
// Core's existing process deadline still covers preparation. These tests verify
// protocol behavior, not cold dependency startup performance.
const REAL_PARSER_PREPARATION: &str = r#"def prepare_real_retrieval_parsers():
    from bs4 import BeautifulSoup
    import trafilatura
    html = '<html><body><article><h1>Synthetic parser preparation</h1><p>Synthetic public background sentence for protocol testing only. No factual qualification is asserted.</p></article></body></html>'
    assert BeautifulSoup('<a class="result-link" href="https://source.invalid/public">source</a>', 'html.parser').select('a.result-link')[0]['href'] == 'https://source.invalid/public'
    text = trafilatura.extract(html, include_links=False, include_images=False)
    assert text and 'Synthetic public background sentence' in text
"#;

#[tokio::test]
async fn actual_check_worker_dispatches_only_exact_confirmed_material_with_synthetic_transports() {
    for tamper in [false, true] {
        let dir = tempfile::tempdir().unwrap();
        let script = dir.path().join("worker.py");
        let events = dir.path().join("events.json");
        let repo = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap()
            .parent()
            .unwrap();
        let source = format!(
            r#"import importlib.util,json,sys
from pathlib import Path
from types import SimpleNamespace
import faulthandler
_trace=Path(__file__).with_suffix(".stack").open("w")
faulthandler.dump_traceback_later(5,repeat=True,file=_trace)
root=Path({root})
sys.path.insert(0,str(root/'services/python-workers/machine'))
import document_check as worker
{parser_preparation}
events=Path({events})
def record(kind):
    values=json.loads(events.read_text()) if events.exists() else []
    events.write_text(json.dumps(values+[kind]))
original_donor=worker.donor
def donor(name):
    module=original_donor(name)
    if name=='safe_http':
        def fetch(url,**kwargs):
            assert kwargs['policy'].max_redirects==0
            body=(b'<html><a class="result-link" href="https://source.invalid/public?q=term">public source</a></html>' if 'duckduckgo' in url else b'<html><body><article><h1>Synthetic public source</h1><p>Synthetic public background sentence for protocol testing only. No factual qualification is asserted.</p></article></body></html>')
            return module.SafeHTTPResponse(url,200,{{'content-type':'text/html'}},body)
        module.fetch=fetch
    return module
worker.donor=donor
worker.read_product_credential=lambda reference: bytearray(b'SIMULATED synthetic credential')
original_dispatch=worker.authorize_dispatch
def dispatch(kind,destination,material):
    if kind=='model' and {tamper}:
        material=dict(material)
        material['prompt']+='\nUNSELECTED PRIVATE SYNTHETIC MATERIAL'
    original_dispatch(kind,destination,material)
    record(kind)
worker.authorize_dispatch=dispatch
def completion(**kwargs):
    assert kwargs['num_retries']==0 and kwargs['api_base']=='https://fixture.invalid/v1'
    assert kwargs['model']=='fixture/explicit'
    assert kwargs['api_key']=='SIMULATED synthetic credential'
    return {{'model':'SIMULATED-model','choices':[{{'message':{{'content':json.dumps({{'status':'uncertain','basis':'SIMULATED transport only'}})}},'finish_reason':'stop'}}],'usage':{{'total_tokens':3}}}}
sys.modules['litellm']=SimpleNamespace(completion=completion)
original_execute=worker.execute

def prepared_execute(request):
    prepare_real_retrieval_parsers()
    return original_execute(request)
worker.execute=prepared_execute
raise SystemExit(worker.main())
"#,
            parser_preparation = REAL_PARSER_PREPARATION,
            root = serde_json::to_string(&repo.to_string_lossy()).unwrap(),
            events = serde_json::to_string(&events.to_string_lossy()).unwrap(),
            tamper = if tamper { "True" } else { "False" }
        );
        std::fs::write(&script, source).unwrap();
        let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
        let executor = Executor::open_routes(
            &dir.path().join("db.sqlite"),
            &dir.path().join("staging"),
            &python,
            &script,
            &[("machine.answer", script.clone())],
        )
        .await
        .unwrap()
        .with_document_check_config(Some(DocumentCheckConfig {
            provider: "fixture".into(),
            model: "fixture/explicit".into(),
            credential_ref: format!("aak_cred_{}", "a".repeat(32)),
            endpoint: Some("https://fixture.invalid/v1".into()),
            max_tokens: 128,
            timeout_seconds: 30,
            search_limit: 1,
        }))
        .unwrap();
        let router = archeaxis_api::runtime::router(executor);
        let (status,document)=call(&router,"POST","/api/v1/documents",json!({"title":"synthetic","editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"synthetic saved body"}]}]}}),"human").await;
        assert_eq!(status, 201);
        let checks = format!(
            "/api/v1/documents/{}/checks",
            document["document_id"].as_str().unwrap()
        );
        let execute = format!("{checks}/execute");
        let (status,pending)=call(&router,"POST",&checks,json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud","search_query":"public synthetic query"}),"human").await;
        assert_eq!(status, 201);
        let body = json!({"check_id":pending["check_id"],"expected_content_sha256":document["content_sha256"]});
        assert_eq!(
            raw_call(&router, "POST", &execute, body.clone(), "human")
                .await
                .0,
            400
        );
        assert!(!events.exists());
        let (status, result) = call(&router, "POST", &execute, body, "human").await;
        assert_eq!(status, 201, "{result}");
        let diagnostics = || {
            format!(
                "tamper={tamper}; synthetic check result: {result}; synthetic worker stack: {}",
                std::fs::read_to_string(script.with_extension("stack")).unwrap_or_default()
            )
        };
        // HTTP 201 also persists failed attempts. Assert the expected outcome
        // before reading a file that is only created by an actual dispatch.
        if tamper {
            assert_eq!(
                result["reason"],
                "dispatch_actual_material_mismatch",
                "{}",
                diagnostics()
            );
            assert_eq!(result["execution_verified"], false, "{}", diagnostics());
        } else {
            assert_eq!(result["execution_verified"], true, "{}", diagnostics());
        }
        let events = std::fs::read(&events).unwrap_or_else(|error| {
            panic!(
                "Cannot read synthetic worker events: {error}; {}",
                diagnostics()
            )
        });
        let operations: Value = serde_json::from_slice(&events).unwrap_or_else(|error| {
            panic!(
                "Invalid synthetic worker events: {error}; {}",
                diagnostics()
            )
        });
        if tamper {
            assert_eq!(
                operations,
                json!(["search", "article"]),
                "{}",
                diagnostics()
            );
        } else {
            assert_eq!(
                operations,
                json!(["search", "article", "model"]),
                "{}",
                diagnostics()
            );
            assert_eq!(result["engine_receipt"]["model"], "SIMULATED-model");
        }
    }
}
#[tokio::test]
async fn configured_worker_is_outside_writer_transaction_and_old_version_readback_survives_restart()
{
    let dir = tempfile::tempdir().unwrap();
    let database = dir.path().join("db.sqlite");
    let ready = dir.path().join("ready");
    let release = dir.path().join("release");
    let script = dir.path().join("worker.py");
    let repo = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap();
    let source = format!(
        r#"import importlib.util,json,sys
from pathlib import Path
from types import SimpleNamespace
import faulthandler
_trace=Path(__file__).with_suffix(".stack").open("w")
faulthandler.dump_traceback_later(5,repeat=True,file=_trace)
root=Path({root})
sys.path.insert(0,str(root/'services/python-workers/machine'))
import document_check as worker
{parser_preparation}
events=Path({events})
def record(kind):
    values=json.loads(events.read_text()) if events.exists() else []
    events.write_text(json.dumps(values+[kind]))
original_donor=worker.donor
def donor(name):
    module=original_donor(name)
    if name=='safe_http':
        def fetch(url,**kwargs):
            assert kwargs['policy'].max_redirects==0
            body=(b'<html><a class="result-link" href="https://source.invalid/public?q=term">public source</a></html>' if 'duckduckgo' in url else b'<html><body><article><h1>Synthetic public source</h1><p>Synthetic public background sentence for protocol testing only. No factual qualification is asserted.</p></article></body></html>')
            return module.SafeHTTPResponse(url,200,{{'content-type':'text/html'}},body)
        module.fetch=fetch
    return module
worker.donor=donor
worker.read_product_credential=lambda reference: bytearray(b'SIMULATED synthetic credential')
original_dispatch=worker.authorize_dispatch
def dispatch(kind,destination,material):
    original_dispatch(kind,destination,material)
    record(kind)
worker.authorize_dispatch=dispatch
def completion(**kwargs):
    assert kwargs['num_retries']==0 and kwargs['api_base']=='https://fixture.invalid/v1'
    assert kwargs['model']=='fixture/explicit'
    assert kwargs['api_key']=='SIMULATED synthetic credential'
    return {{'model':'SIMULATED-model','choices':[{{'message':{{'content':json.dumps({{'status':'uncertain','basis':'SIMULATED transport only'}})}},'finish_reason':'stop'}}],'usage':{{'total_tokens':3}}}}
sys.modules['litellm']=SimpleNamespace(completion=completion)
original_execute=worker.execute
def delayed_execute(request):
    assert request['search_query']=='public synthetic terminology'
    assert request['text']=='saved original'
    ready=Path({ready});release=Path({release})
    ready.write_text('fixture-ready')
    deadline=__import__('time').monotonic()+10
    while not release.exists() and __import__('time').monotonic()<deadline: __import__('time').sleep(.01)
    assert release.exists(), 'fixture timeout'
    prepare_real_retrieval_parsers()
    return original_execute(request)
worker.execute=delayed_execute
raise SystemExit(worker.main())
"#,
        parser_preparation = REAL_PARSER_PREPARATION,
        root = serde_json::to_string(&repo.to_string_lossy()).unwrap(),
        events = serde_json::to_string(&dir.path().join("events.json").to_string_lossy()).unwrap(),
        ready = serde_json::to_string(&ready.to_string_lossy()).unwrap(),
        release = serde_json::to_string(&release.to_string_lossy()).unwrap()
    );
    std::fs::write(&script, source).unwrap();
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let executor = Executor::open_routes(
        &database,
        &dir.path().join("staging"),
        &python,
        &script,
        &[("machine.answer", script.clone())],
    )
    .await
    .unwrap()
    .with_document_check_config(Some(DocumentCheckConfig {
        provider: "fixture".into(),
        model: "fixture/explicit".into(),
        credential_ref: format!("aak_cred_{}", "a".repeat(32)),
        endpoint: Some("https://fixture.invalid/v1".into()),
        max_tokens: 128,
        timeout_seconds: 30,
        search_limit: 1,
    }))
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let full_text = format!(
        "{}saved original document{}",
        "private ".repeat(5000),
        "private ".repeat(5000)
    );
    let (status,document)=call(&router,"POST","/api/v1/documents",json!({"title":"ordinary","editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":full_text}]}]}}),"human").await;
    assert_eq!(status, 201);
    let id = document["document_id"].as_str().unwrap();
    let checks = format!("/api/v1/documents/{id}/checks");
    let execute = format!("{checks}/execute");
    for query in [" ".to_owned(), "x".repeat(1001)] {
        assert_eq!(call(&router, "POST", &checks,
            json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud","search_query":query}), "human").await.0, 400);
    }
    assert_eq!(call(&router, "POST", &checks,
        json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud","search_query":"public query"}), "machine").await.0, 400);
    let (status, pending) = call(
        &router,
        "POST",
        &checks,
        json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud","search_query":"public synthetic terminology"}),
        "human",
    )
    .await;
    assert_eq!(status, 201);
    assert_eq!(pending["search_query"], "public synthetic terminology");
    assert_eq!(raw_call(&router, "POST", &execute,
        json!({"check_id":pending["check_id"],"expected_content_sha256":document["content_sha256"],"preview":true}), "human").await.0, 400);
    let body = json!({"check_id":pending["check_id"],"expected_content_sha256":document["content_sha256"],"selected_text":"saved original"});
    assert_eq!(
        raw_call(&router, "POST", &execute, body.clone(), "human")
            .await
            .0,
        400
    );
    assert!(!ready.exists());
    let mut preview_body = body.clone();
    preview_body["preview"] = json!(true);
    let (preview_status, preview) =
        raw_call(&router, "POST", &execute, preview_body, "human").await;
    assert_eq!(preview_status, 200);
    assert_eq!(
        preview["egress_plan"]["search_query"],
        "public synthetic terminology"
    );
    assert_eq!(
        preview["egress_plan"]["document_text"]["text"],
        "saved original"
    );
    assert!(!ready.exists());
    assert_eq!(preview["egress_plan"]["scope"], "selected_text");
    let mut changed_material = body.clone();
    changed_material["confirmed_egress_sha256"] = preview["egress_sha256"].clone();
    changed_material["selected_text"] = json!("document");
    assert_eq!(
        raw_call(&router, "POST", &execute, changed_material, "human")
            .await
            .0,
        400
    );
    let mut stale = body.clone();
    stale["confirmed_egress_sha256"] = json!("0".repeat(64));
    assert_eq!(
        raw_call(&router, "POST", &execute, stale, "human").await.0,
        400
    );
    assert_eq!(
        call(&router, "POST", &execute, body.clone(), "machine")
            .await
            .0,
        403
    );
    assert!(!ready.exists());
    let launched_router = router.clone();
    let task =
        tokio::spawn(async move { call(&launched_router, "POST", &execute, body, "human").await });
    tokio::time::timeout(std::time::Duration::from_secs(5), async {
        while !ready.exists() {
            tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap();
    let (status,new)=call(&router,"PUT",&format!("/api/v1/documents/{id}/draft"),json!({"expected_version":1,"editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"save never waits for cloud"}]}]}}),"human").await;
    assert_eq!(status, 200);
    assert_eq!(new["version"], 2);
    std::fs::write(&release, b"release fixture").unwrap();
    let (status, terminal) = task.await.unwrap();
    assert_eq!(status, 201, "{terminal}");
    assert_eq!(terminal["version"], 1);
    assert_eq!(
        terminal["execution_verified"],
        true,
        "{terminal}; synthetic worker stack: {}",
        std::fs::read_to_string(script.with_extension("stack")).unwrap_or_default()
    );
    assert_eq!(terminal["status"], "uncertain");
    assert_eq!(terminal["actor"], "machine");
    assert_eq!(terminal["egress_plan"]["scope"], "selected_text");
    assert_eq!(
        terminal["egress_plan"]["document_text"]["text"],
        "saved original"
    );
    drop(router);
    drop(executor);
    let restarted = archeaxis_api::app(database.to_str().unwrap()).unwrap();
    let history = call(
        &restarted,
        "GET",
        &format!("{checks}?version=1"),
        Value::Null,
        "human",
    )
    .await
    .1;
    assert_eq!(history["historical"], true);
    assert_eq!(history["checks"].as_array().unwrap().len(), 3);
    assert_eq!(
        history["checks"].as_array().unwrap().last().unwrap()["egress_plan"],
        terminal["egress_plan"]
    );
    assert_eq!(
        call(
            &restarted,
            "GET",
            &format!("/api/v1/documents/{id}"),
            Value::Null,
            "human"
        )
        .await
        .1["text_projection"],
        "save never waits for cloud"
    );
}

#[tokio::test]
async fn withdrawal_while_waiting_for_worker_slot_prevents_worker_start() {
    let dir = tempfile::tempdir().unwrap();
    let release = dir.path().join("release");
    let script = dir.path().join("worker.py");
    let source = format!(
        r#"import json,sys,time
from pathlib import Path
request=json.load(sys.stdin)
directory=Path({directory})
(directory/('ready-'+request['request_check_id'])).write_text('synthetic worker started')
deadline=time.monotonic()+10
while not (directory/'release').exists() and time.monotonic()<deadline: time.sleep(.01)
assert (directory/'release').exists(), 'fixture timeout'
print(json.dumps({{'schema':'archeaxis.document-check.response/v1',**{{k:request[k] for k in ('attempt_id','request_check_id','document_id','version','content_sha256','dimension')}},'outcome':'failed','status':'failed','reason':'fixture_end','basis':'','raw_response':'','engine_receipt':None,'retrieval_receipts':[]}}))
sys.exit(1)
"#,
        directory = serde_json::to_string(&dir.path().to_string_lossy()).unwrap()
    );
    std::fs::write(&script, format!("{READY_PREAMBLE}{source}")).unwrap();
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let executor = Executor::open_routes(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python,
        &script,
        &[("machine.answer", script.clone())],
    )
    .await
    .unwrap()
    .with_document_check_config(Some(DocumentCheckConfig {
        provider: "fixture".into(),
        model: "fixture/explicit".into(),
        credential_ref: format!("aak_cred_{}", "a".repeat(32)),
        endpoint: Some("https://fixture.invalid/v1".into()),
        max_tokens: 128,
        timeout_seconds: 30,
        search_limit: 1,
    }))
    .unwrap();
    let router = archeaxis_api::runtime::router(executor);
    let (status, document) = call(&router,"POST","/api/v1/documents",json!({"title":"ordinary","editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"synthetic selected material"}]}]}}),"human").await;
    assert_eq!(status, 201);
    let checks = format!(
        "/api/v1/documents/{}/checks",
        document["document_id"].as_str().unwrap()
    );
    let execute = format!("{checks}/execute");
    let mut tasks = Vec::new();
    let mut last_body = Value::Null;
    let mut last_marker = dir.path().join("unused");
    let mut active_withdrawal = Value::Null;
    for index in 0..5 {
        let (status,pending) = call(&router,"POST",&checks,json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud","search_query":"public synthetic query"}),"human").await;
        assert_eq!(status, 201);
        let mut body = json!({"check_id":pending["check_id"],"expected_content_sha256":document["content_sha256"],"preview":true});
        let (status, plan) = raw_call(&router, "POST", &execute, body.clone(), "human").await;
        assert_eq!(status, 200);
        body.as_object_mut().unwrap().remove("preview");
        body["confirmed_egress_sha256"] = plan["egress_sha256"].clone();
        let marker = dir
            .path()
            .join(format!("ready-{}", pending["check_id"].as_str().unwrap()));
        last_body = json!({"check_id":pending["check_id"],"expected_content_sha256":document["content_sha256"],"withdraw":true});
        if index == 0 {
            active_withdrawal = last_body.clone();
        }
        last_marker = marker.clone();
        let owned = router.clone();
        let endpoint = execute.clone();
        tasks.push(tokio::spawn(async move {
            raw_call(&owned, "POST", &endpoint, body, "human").await
        }));
        if index < 4 {
            tokio::time::timeout(std::time::Duration::from_secs(5), async {
                while !marker.exists() {
                    tokio::time::sleep(std::time::Duration::from_millis(10)).await;
                }
            })
            .await
            .unwrap();
        }
    }
    let root = last_body["check_id"].clone();
    tokio::time::timeout(std::time::Duration::from_secs(5), async {
        loop {
            let (_, history) = raw_call(&router, "GET", &checks, Value::Null, "human").await;
            if history["checks"]
                .as_array()
                .unwrap()
                .iter()
                .any(|r| r["request_check_id"] == root && r["execution_state"] == "running")
            {
                break;
            }
            tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap();
    assert!(!last_marker.exists());
    let (status, withdrawal) = raw_call(&router, "POST", &execute, last_body, "human").await;
    assert_eq!(status, 200, "{withdrawal}");
    let (status, withdrawal) =
        raw_call(&router, "POST", &execute, active_withdrawal, "human").await;
    assert_eq!(status, 200, "{withdrawal}");
    let (status, cancelled) =
        tokio::time::timeout(std::time::Duration::from_secs(5), tasks.remove(0))
            .await
            .expect("active withdrawal must finish before fixture release")
            .unwrap();
    assert_eq!(status, 201, "{cancelled}");
    assert_eq!(cancelled["reason"], "egress_withdrawn");
    assert_eq!(cancelled["execution_verified"], false);
    std::fs::write(release, b"release fixtures").unwrap();
    let mut last_result = Value::Null;
    for task in tasks {
        let (status, receipt) = task.await.unwrap();
        assert_eq!(status, 201, "{receipt}");
        last_result = receipt;
    }
    assert_eq!(last_result["reason"], "egress_withdrawn");
    assert!(
        !last_marker.exists(),
        "withdrawn queued worker must never start"
    );
}

#[tokio::test]
async fn local_only_and_durable_withdrawal_preserve_save_with_or_without_engine() {
    for configured in [false, true] {
        let dir = tempfile::tempdir().unwrap();
        let marker = dir.path().join("unexpected-worker");
        let script = dir.path().join("worker.py");
        std::fs::write(
            &script,
            format!(
                "from pathlib import Path\nPath({}).write_text('unexpected synthetic worker')\n",
                serde_json::to_string(&marker.to_string_lossy()).unwrap()
            ),
        )
        .unwrap();
        let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
        let db = dir.path().join("db.sqlite");
        let executor = Executor::open_routes(
            &db,
            &dir.path().join("staging"),
            &python,
            &script,
            &[("machine.answer", script.clone())],
        )
        .await
        .unwrap()
        .with_document_check_config(configured.then(|| DocumentCheckConfig {
            provider: "fixture".into(),
            model: "fixture/explicit".into(),
            credential_ref: format!("aak_cred_{}", "a".repeat(32)),
            endpoint: Some("https://fixture.invalid/v1".into()),
            max_tokens: 128,
            timeout_seconds: 30,
            search_limit: 1,
        }))
        .unwrap();
        let router = archeaxis_api::runtime::router(executor.clone());
        let (status,document)=call(&router,"POST","/api/v1/documents",json!({"title":"ordinary","editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"synthetic material"}]}]}}),"human").await;
        assert_eq!(status, 201);
        let path = format!(
            "/api/v1/documents/{}",
            document["document_id"].as_str().unwrap()
        );
        let checks = format!("{path}/checks");
        let execute = format!("{checks}/execute");
        let (status,local)=call(&router,"POST",&checks,json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud","search_query":"public synthetic query","local_only":true}),"human").await;
        assert_eq!(status, 201);
        assert_eq!(local["local_only"], true);
        let local_body = json!({"check_id":local["check_id"],"expected_content_sha256":document["content_sha256"],"confirmed_egress_sha256":"0".repeat(64)});
        assert_eq!(
            raw_call(&router, "POST", &execute, local_body, "human")
                .await
                .0,
            400
        );
        let (status,pending)=call(&router,"POST",&checks,json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud","search_query":"public synthetic query"}),"human").await;
        assert_eq!(status, 201);
        let body = json!({"check_id":pending["check_id"],"expected_content_sha256":document["content_sha256"],"withdraw":true});
        assert_eq!(
            raw_call(&router, "POST", &execute, body.clone(), "machine")
                .await
                .0,
            403
        );
        let mut wrong = body.clone();
        wrong["expected_content_sha256"] = json!("wrong");
        assert_eq!(
            raw_call(&router, "POST", &execute, wrong, "human").await.0,
            400
        );
        let mut mixed = body.clone();
        mixed["preview"] = json!(true);
        assert_eq!(
            raw_call(&router, "POST", &execute, mixed, "human").await.0,
            400
        );
        let mut preview_body = body.clone();
        preview_body.as_object_mut().unwrap().remove("withdraw");
        preview_body["preview"] = json!(true);
        let (_, old_preview) =
            raw_call(&router, "POST", &execute, preview_body.clone(), "human").await;
        let (status, event) = raw_call(&router, "POST", &execute, body.clone(), "human").await;
        assert_eq!(status, 200);
        assert_eq!(event["execution_state"], "withdrawn");
        assert!(event["attempt_id"].is_null());
        assert!(event["request_check_id"].is_null());
        assert_eq!(
            raw_call(&router, "POST", &execute, body.clone(), "human").await,
            (200, event.clone())
        );
        assert_eq!(
            raw_call(&router, "POST", &execute, preview_body, "human")
                .await
                .0,
            if configured { 400 } else { 503 }
        );
        let execute_body = json!({"check_id":pending["check_id"],"expected_content_sha256":document["content_sha256"],"confirmed_egress_sha256":old_preview["egress_sha256"]});
        assert_eq!(
            raw_call(&router, "POST", &execute, execute_body.clone(), "human")
                .await
                .0,
            400
        );
        assert!(!marker.exists());
        let (status,saved)=call(&router,"PUT",&format!("{path}/draft"),json!({"expected_version":1,"editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"saving remains independent"}]}]}}),"human").await;
        assert_eq!(status, 200);
        assert_eq!(saved["version"], 2);
        drop(router);
        drop(executor);
        let reopened = archeaxis_api::app(db.to_str().unwrap()).unwrap();
        assert_eq!(
            raw_call(&reopened, "POST", &execute, body, "human").await,
            (200, event.clone())
        );
        assert_eq!(
            raw_call(&reopened, "POST", &execute, execute_body, "human")
                .await
                .0,
            400
        );
        let (_, history) = raw_call(
            &reopened,
            "GET",
            &format!("{checks}?version=1"),
            Value::Null,
            "human",
        )
        .await;
        assert_eq!(history["checks"].as_array().unwrap().len(), 3);
        assert!(history["checks"].as_array().unwrap().contains(&event));
        assert_eq!(
            raw_call(&reopened, "GET", &path, Value::Null, "human")
                .await
                .1,
            saved
        );
        assert!(!marker.exists());
    }
}

#[tokio::test]
async fn malformed_flood_and_timeout_are_failed_and_explicitly_retryable() {
    for (script_body, expected_reason) in [
        (
            "import sys\nsys.stdin.read()\nprint('{}')\n",
            "invalid_worker_response",
        ),
        (
            "import sys\nsys.stdin.read()\nsys.stdout.write('x'*200000)\nsys.stdout.flush()\n",
            "output_exceeds_bound",
        ),
        (
            "import sys,time\nsys.stdin.read()\ntime.sleep(60)\n",
            "worker_timeout",
        ),
    ] {
        let dir = tempfile::tempdir().unwrap();
        let script = dir.path().join("worker.py");
        std::fs::write(&script, format!("{READY_PREAMBLE}{script_body}")).unwrap();
        let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
        let executor = Executor::open_routes(
            &dir.path().join("db.sqlite"),
            &dir.path().join("staging"),
            &python,
            &script,
            &[("machine.answer", script.clone())],
        )
        .await
        .unwrap()
        .with_document_check_config(Some(DocumentCheckConfig {
            provider: "fixture".into(),
            model: "fixture/explicit".into(),
            credential_ref: format!("aak_cred_{}", "a".repeat(32)),
            endpoint: Some("https://fixture.invalid/v1".into()),
            max_tokens: 128,
            timeout_seconds: 1,
            search_limit: 1,
        }))
        .unwrap();
        let router = archeaxis_api::runtime::router(executor);
        let (_, doc) = call(
            &router,
            "POST",
            "/api/v1/documents",
            json!({"title":"preserved","editor_json":{"type":"doc","content":[]}}),
            "human",
        )
        .await;
        let id = doc["document_id"].as_str().unwrap();
        let path = format!("/api/v1/documents/{id}/checks");
        let (_, request) = call(
            &router,
            "POST",
            &path,
            json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud","search_query":"public synthetic terminology"}),
            "human",
        )
        .await;
        let body =
            json!({"check_id":request["check_id"],"expected_content_sha256":doc["content_sha256"]});
        let started = std::time::Instant::now();
        let (status, result) = tokio::time::timeout(
            std::time::Duration::from_secs(24),
            call(
                &router,
                "POST",
                &format!("{path}/execute"),
                body.clone(),
                "human",
            ),
        )
        .await
        .unwrap();
        assert_eq!(status, 201, "{result}");
        assert_eq!(result["status"], "failed");
        assert_eq!(result["reason"], expected_reason);
        assert_eq!(result["execution_verified"], false);
        assert!(started.elapsed() < std::time::Duration::from_secs(24));
        assert_eq!(
            call(&router, "POST", &format!("{path}/execute"), body, "human")
                .await
                .0,
            400
        );
        let history = call(
            &router,
            "GET",
            &format!("{path}?version=1"),
            Value::Null,
            "human",
        )
        .await
        .1;
        assert_eq!(history["checks"].as_array().unwrap().len(), 3);
        drop(router);
        let restarted = archeaxis_api::app(dir.path().join("db.sqlite").to_str().unwrap()).unwrap();
        let recovered = call(
            &restarted,
            "GET",
            &format!("{path}?version=1"),
            Value::Null,
            "human",
        )
        .await
        .1;
        assert!(
            recovered["checks"].as_array().unwrap().contains(&result),
            "terminal must survive complete Store reopen unchanged"
        );

        assert_eq!(
            call(
                &restarted,
                "GET",
                &format!("/api/v1/documents/{id}"),
                Value::Null,
                "human"
            )
            .await
            .1["version"],
            1
        );
    }
}
#[tokio::test]
async fn invalid_owned_config_preserves_save_and_records_failed_attempt() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("never.py");
    std::fs::write(&script, "raise AssertionError('must not execute')").unwrap();
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let executor = Executor::open_routes(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python,
        &script,
        &[("machine.answer", script.clone())],
    )
    .await
    .unwrap()
    .with_document_check_config(Some(DocumentCheckConfig {
        provider: "invalid-provider".into(),
        model: "invalid-provider/explicit".into(),
        credential_ref: format!("aak_cred_{}", "a".repeat(32)),
        endpoint: Some("https://fixture.invalid/v1".into()),
        max_tokens: 128,
        timeout_seconds: 1,
        search_limit: 1,
    }))
    .unwrap()
    .with_document_check_config_error(None)
    .unwrap();
    let router = archeaxis_api::runtime::router(executor);
    let (status, doc) = call(
        &router,
        "POST",
        "/api/v1/documents",
        json!({"title":"ordinary save","editor_json":{"type":"doc","content":[]}}),
        "human",
    )
    .await;
    assert_eq!(status, 201);
    let id = doc["document_id"].as_str().unwrap();
    let path = format!("/api/v1/documents/{id}/checks");
    let (_, request) = call(
        &router,
        "POST",
        &path,
        json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud","search_query":"public synthetic terminology"}),
        "human",
    )
    .await;
    let body =
        json!({"check_id":request["check_id"],"expected_content_sha256":doc["content_sha256"]});
    let (status, result) = call(&router, "POST", &format!("{path}/execute"), body, "human").await;
    assert_eq!(status, 201);
    assert_eq!(result["reason"], "invalid_config");
    assert_eq!(result["execution_verified"], false);
    let (status, updated) = call(
        &router,
        "PUT",
        &format!("/api/v1/documents/{id}/draft"),
        json!({"expected_version":1,"editor_json":{"type":"doc","content":[]}}),
        "human",
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(updated["version"], 2);
}

#[tokio::test]
async fn legitimate_material_failure_is_persisted_retryable_and_never_runs_worker() {
    let dir = tempfile::tempdir().unwrap();
    let database = dir.path().join("db.sqlite");
    let script = dir.path().join("never.py");
    let marker = dir.path().join("worker-called");
    std::fs::write(&script,format!("from pathlib import Path\nPath({}).write_text('unexpected')\nraise AssertionError('must not run')",serde_json::to_string(&marker.to_string_lossy()).unwrap())).unwrap();
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let executor = Executor::open_routes(
        &database,
        &dir.path().join("staging"),
        &python,
        &script,
        &[("machine.answer", script.clone())],
    )
    .await
    .unwrap()
    .with_document_check_config(Some(DocumentCheckConfig {
        provider: "fixture".into(),
        model: "fixture/explicit".into(),
        credential_ref: format!("aak_cred_{}", "a".repeat(32)),
        endpoint: Some("https://fixture.invalid/v1".into()),
        max_tokens: 128,
        timeout_seconds: 1,
        search_limit: 1,
    }))
    .unwrap();
    let router = archeaxis_api::runtime::router(executor);
    let text = "x".repeat(65001);
    let editor = json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":text}]}]});
    let (status, doc) = call(
        &router,
        "POST",
        "/api/v1/documents",
        json!({"title":"large ordinary note","editor_json":editor}),
        "human",
    )
    .await;
    assert_eq!(status, 201);
    assert_eq!(doc["text_projection"], text);
    let id = doc["document_id"].as_str().unwrap();
    let path = format!("/api/v1/documents/{id}/checks");
    let (_, request) = call(
        &router,
        "POST",
        &path,
        json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud","search_query":"public synthetic terminology"}),
        "human",
    )
    .await;
    let body =
        json!({"check_id":request["check_id"],"expected_content_sha256":doc["content_sha256"]});
    assert_eq!(
        call(
            &router,
            "POST",
            &format!("{path}/execute"),
            body.clone(),
            "machine"
        )
        .await
        .0,
        403
    );
    let wrong = json!({"check_id":request["check_id"],"expected_content_sha256":"wrong"});
    assert_eq!(
        call(&router, "POST", &format!("{path}/execute"), wrong, "human")
            .await
            .0,
        400
    );
    assert_eq!(
        call(
            &router,
            "GET",
            &format!("{path}?version=1"),
            Value::Null,
            "human"
        )
        .await
        .1["checks"]
            .as_array()
            .unwrap()
            .len(),
        1
    );
    let (status, failed) = call(
        &router,
        "POST",
        &format!("{path}/execute"),
        body.clone(),
        "human",
    )
    .await;
    assert_eq!(status, 201);
    assert_eq!(failed["status"], "failed");
    assert_eq!(failed["reason"], "cloud_snapshot_exceeds_bound");
    assert_eq!(failed["execution_verified"], false);
    assert!(!marker.exists());
    let mut retry = body;
    retry["retry_of_task_id"] = failed["attempt_id"].clone();
    let (_, retried) = call(&router, "POST", &format!("{path}/execute"), retry, "human").await;
    assert_eq!(retried["reason"], "cloud_snapshot_exceeds_bound");
    assert_ne!(retried["attempt_id"], failed["attempt_id"]);
    assert!(!marker.exists());
    drop(router);
    let restarted = archeaxis_api::app(database.to_str().unwrap()).unwrap();
    let history = call(
        &restarted,
        "GET",
        &format!("{path}?version=1"),
        Value::Null,
        "human",
    )
    .await
    .1;
    let rows = history["checks"].as_array().unwrap();
    assert_eq!(rows.len(), 5);
    assert!(rows.contains(&failed));
    assert!(rows.contains(&retried));
    let readback = call(
        &restarted,
        "GET",
        &format!("/api/v1/documents/{id}"),
        Value::Null,
        "human",
    )
    .await
    .1;
    assert!(
        readback["editor_json"] == doc["editor_json"],
        "persisted editor including generated stable IDs must remain unchanged"
    );
    assert_eq!(readback["content_sha256"], doc["content_sha256"]);
    assert_eq!(readback["text_projection"], text);
}

#[tokio::test]
async fn retrieval_failure_details_survive_restart_without_blocking_ordinary_save() {
    for (reason, reported, details) in [
        (
            "retrieval_failed",
            "failed",
            json!({"kind":"retrieval_failure","reason":"retrieval_failed","failure_code":"dns","failure_stage":"dns"}),
        ),
        (
            "retrieval_failed",
            "failed",
            json!({"kind":"retrieval_failure","reason":"retrieval_failed","failure_code":"timeout","failure_stage":"transport"}),
        ),
        (
            "retrieval_failed",
            "failed",
            json!({"kind":"retrieval_failure","reason":"retrieval_failed","failure_code":"policy","failure_stage":"policy"}),
        ),
        (
            "retrieval_failed",
            "failed",
            json!({"kind":"retrieval_failure","reason":"retrieval_failed","failure_code":"http_status","failure_stage":"http_response","http_status":503}),
        ),
        (
            "no_search_results",
            "uncertain",
            json!({"kind":"search","body_sha256":"a".repeat(64),"http_status":200,"bytes":13,"retrieved_at":1.0}),
        ),
    ] {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("db.sqlite");
        let script = dir.path().join("controlled-worker.py");
        // Controlled protocol fixture: no SDK, network, model, or actual cloud acceptance.
        let response = json!({"outcome":"failed","status":reported,"reason":reason,"basis":"","raw_response":"","engine_receipt":null,"retrieval_receipts":[details.clone()]});
        let worker = format!(
            "import json,sys\nrequest=json.load(sys.stdin)\nresult=json.loads({})\nresult.update(schema='archeaxis.document-check.response/v1')\nresult.update({{k:request[k] for k in ('attempt_id','request_check_id','document_id','version','content_sha256','dimension')}})\nprint(json.dumps(result))\nsys.exit(1)\n",
            serde_json::to_string(&response.to_string()).unwrap()
        );
        std::fs::write(&script, format!("{READY_PREAMBLE}{worker}")).unwrap();
        let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
        let executor = Executor::open_routes(
            &db,
            &dir.path().join("staging"),
            &python,
            &script,
            &[("machine.answer", script.clone())],
        )
        .await
        .unwrap()
        .with_document_check_config(Some(DocumentCheckConfig {
            provider: "fixture".into(),
            model: "fixture/explicit".into(),
            credential_ref: format!("aak_cred_{}", "a".repeat(32)),
            endpoint: Some("https://fixture.invalid/v1".into()),
            max_tokens: 128,
            timeout_seconds: 30,
            search_limit: 1,
        }))
        .unwrap();
        let router = archeaxis_api::runtime::router(executor.clone());
        let (status,document)=call(&router,"POST","/api/v1/documents",json!({"title":"ordinary without external evidence","editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"OriginalNeverOverwritten"}]}]}}),"human").await;
        assert_eq!(status, 201);
        assert!(document["source_id"].is_null());
        let path = format!(
            "/api/v1/documents/{}",
            document["document_id"].as_str().unwrap()
        );
        let checks = format!("{path}/checks");
        let execute = format!("{checks}/execute");
        let (_, pending) = call(
            &router,
            "POST",
            &checks,
            json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud","search_query":"public synthetic terminology"}),
            "human",
        )
        .await;
        let body = json!({"check_id":pending["check_id"],"expected_content_sha256":document["content_sha256"]});
        assert_eq!(
            call(&router, "POST", &execute, body.clone(), "machine")
                .await
                .0,
            403
        );
        let mut wrong = body.clone();
        wrong["expected_content_sha256"] = json!("wrong");
        assert_eq!(call(&router, "POST", &execute, wrong, "human").await.0, 400);
        let (status, terminal) = call(&router, "POST", &execute, body.clone(), "human").await;
        assert_eq!(status, 201, "{terminal}");
        assert_eq!(terminal["reason"], reason, "{terminal}");
        assert_eq!(terminal["execution_state"], "failed", "{terminal}");
        assert_eq!(terminal["execution_verified"], false);
        assert_eq!(terminal["status"], "failed");
        assert_eq!(terminal["reported_status"], reported, "{terminal}");
        assert_eq!(terminal["retrieval_receipts"], json!([details]));
        assert!(terminal["engine_receipt"].is_null());
        let (_,saved)=call(&router,"PUT",&format!("{path}/draft"),json!({"expected_version":1,"editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"StillSaveableAfterRetrievalFailure"}]}]}}),"human").await;
        assert_eq!(saved["version"], 2);
        drop(router);
        drop(executor);
        let restarted = archeaxis_api::app(db.to_str().unwrap()).unwrap();
        let (_, history) = call(
            &restarted,
            "GET",
            &format!("{checks}?version=1"),
            json!(null),
            "human",
        )
        .await;
        assert_eq!(history["historical"], true);
        assert!(history["checks"].as_array().unwrap().contains(&terminal));
        assert_eq!(
            call(&restarted, "GET", &path, json!(null), "human").await.1,
            saved
        );
        let mut retry = body;
        retry["retry_of_task_id"] = terminal["attempt_id"].clone();
        let (status, retry_result) = call(&restarted, "POST", &execute, retry, "human").await;
        assert_eq!(status, 201);
        assert_ne!(retry_result["attempt_id"], terminal["attempt_id"]);
        assert_eq!(retry_result["reason"], "not_configured");
        let (_, history_after) = call(
            &restarted,
            "GET",
            &format!("{checks}?version=1"),
            json!(null),
            "human",
        )
        .await;
        assert!(
            history_after["checks"]
                .as_array()
                .unwrap()
                .contains(&terminal)
        );
    }
}
