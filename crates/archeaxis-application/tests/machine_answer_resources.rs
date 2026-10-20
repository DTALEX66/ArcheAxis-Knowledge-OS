//! Executor resource and admission regressions with SYNTHETIC owned Python workers.
use archeaxis_application::executor::Executor;
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

const MARKER: &str = "ARCHEAXIS_TEST_PRIVATE_GLOBAL_MARKER";
const SENTINEL: &str = "SYNTHETIC_PRIVATE_NOT_A_CREDENTIAL";

#[tokio::test]
async fn explicit_cancellation_reaps_only_the_owned_worker_before_return() {
    use archeaxis_application::executor::Cancellation;
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(dir.path(), "time.sleep(30)").await;
    let cancel = Cancellation::new();
    let token = cancel.clone();
    let task = tokio::spawn(async move {
        executor
            .machine_answer_cancellable(
                "Synthetic context".into(),
                "Synthetic question".into(),
                2048,
                Duration::from_secs(30),
                None,
                token,
            )
            .await
    });
    tokio::time::timeout(Duration::from_secs(5), async {
        while !dir.path().join("machine_resource_fixture.pid").exists() {
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap();
    cancel.cancel();
    let result = tokio::time::timeout(Duration::from_secs(3), task)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(result.unwrap_err(), "machine worker cancelled");
    assert_owned_child_stopped(dir.path());
}

#[tokio::test]
async fn pre_cancelled_machine_never_spawns_a_worker() {
    use archeaxis_application::executor::Cancellation;
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(dir.path(), "print('{}')").await;
    let cancel = Cancellation::new();
    cancel.cancel();
    assert_eq!(
        executor
            .machine_answer_cancellable(
                "Synthetic".into(),
                "Question".into(),
                2048,
                Duration::from_secs(30),
                None,
                cancel
            )
            .await
            .unwrap_err(),
        "machine worker cancelled"
    );
    assert!(!dir.path().join("machine_resource_fixture.pid").exists());
}
fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON")
        .expect("use existing canonical declared Python")
        .into()
}
async fn fixture(dir: &Path, body: &str) -> Executor {
    let script = dir.join("machine_resource_fixture.py");
    std::fs::write(&script,format!(
        "import os,sys,json,time\nfrom pathlib import Path\nPath(__file__).with_suffix('.pid').write_text(str(os.getpid()))\n{body}\n"
    )).unwrap();
    Executor::open_routes(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python(),
        &PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../services/python-workers/transport/text_ndjson.py"),
        &[("machine.answer", script)],
    )
    .await
    .unwrap()
}
fn owned_pid(dir: &Path) -> u32 {
    std::fs::read_to_string(dir.join("machine_resource_fixture.pid"))
        .expect("fixture must prove actual child admission")
        .trim()
        .parse()
        .unwrap()
}

#[cfg(windows)]
fn pid_running(pid: u32) -> Result<bool, String> {
    use std::ffi::c_void;
    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn OpenProcess(access: u32, inherit: i32, pid: u32) -> *mut c_void;
        fn GetExitCodeProcess(process: *mut c_void, code: *mut u32) -> i32;
        fn CloseHandle(handle: *mut c_void) -> i32;
        fn GetLastError() -> u32;
    }
    // Query only the exact fixture PID. No termination/enumeration/ACL change.
    let handle = unsafe { OpenProcess(0x1000, 0, pid) };
    if handle.is_null() {
        let error = unsafe { GetLastError() };
        return if error == 87 {
            Ok(false)
        } else {
            Err(format!("owned PID probe unavailable ({error})"))
        };
    }
    let mut code = 0;
    let status = unsafe { GetExitCodeProcess(handle, &mut code) };
    unsafe { CloseHandle(handle) };
    if status == 0 {
        Err("owned PID exit state unavailable".into())
    } else {
        Ok(code == 259)
    }
}
#[cfg(target_os = "linux")]
fn pid_running(pid: u32) -> Result<bool, String> {
    // Only this owned PID, no /proc enumeration. Executor already waits/reaps the child.
    match std::fs::metadata(format!("/proc/{pid}/stat")) {
        Ok(_) => Ok(true),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(_) => Err("owned PID probe unavailable".into()),
    }
}
#[cfg(not(any(windows, target_os = "linux")))]
fn pid_running(_pid: u32) -> Result<bool, String> {
    Err("owned PID readback unsupported on this platform; NOT_EXECUTED".into())
}
fn assert_owned_child_stopped(dir: &Path) {
    let pid = owned_pid(dir);
    assert!(
        !pid_running(pid).expect("UNKNOWN PID status cannot qualify cleanup"),
        "owned worker {pid} is still running"
    );
}

#[tokio::test]
async fn inventory_settings_failure_refuses_before_owned_child_spawn() {
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(dir.path(), "raise AssertionError('must not start')").await;
    executor
        .store()
        .submit_wait(|conn| conn.execute("DROP TABLE capability_settings", []))
        .await
        .unwrap()
        .unwrap();
    let result = executor.machine_inventory().await;
    assert_eq!(result["status"], "UNAVAILABLE");
    assert!(result["listed_model_count"].is_null());
    assert!(!dir.path().join("machine_resource_fixture.pid").exists());
}

#[tokio::test]
async fn disabled_machine_refuses_all_model_choices_and_policies_before_spawn() {
    use archeaxis_application::executor::{AnswerPolicy, Cancellation};
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(
        dir.path(),
        "print(json.dumps({'answer':'must not execute'}))",
    )
    .await;
    executor
        .store()
        .submit_wait(|conn| {
            archeaxis_store_sqlite::capability_settings::set_enabled(conn, "machine.answer", false)
        })
        .await
        .unwrap()
        .unwrap();
    for model in [None, Some("synthetic-model".into())] {
        for policy in [AnswerPolicy::Grounded, AnswerPolicy::CompanionGeneral] {
            let error = executor
                .machine_answer_with_policy_detailed(
                    "Synthetic context".into(),
                    "Synthetic question".into(),
                    128,
                    Duration::from_secs(5),
                    model.clone(),
                    Cancellation::new(),
                    None,
                    policy,
                )
                .await
                .unwrap_err();
            assert_eq!(error.to_string(), "machine.answer capability disabled");
            assert!(!dir.path().join("machine_resource_fixture.pid").exists());
            assert_eq!(
                std::fs::read_dir(dir.path().join("staging"))
                    .unwrap()
                    .count(),
                0
            );
        }
    }
}

#[tokio::test]
async fn unreadable_machine_settings_refuses_all_model_choices_before_spawn() {
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(
        dir.path(),
        "print(json.dumps({'answer':'must not execute'}))",
    )
    .await;
    executor
        .store()
        .submit_wait(|conn| conn.execute("DROP TABLE capability_settings", []))
        .await
        .unwrap()
        .unwrap();
    for model in [None, Some("synthetic-model".into())] {
        let error = executor
            .machine_answer_selected(
                "Synthetic context".into(),
                "Synthetic question".into(),
                128,
                Duration::from_secs(5),
                model,
            )
            .await
            .unwrap_err();
        assert_eq!(error, "machine capability settings unavailable");
        assert!(!dir.path().join("machine_resource_fixture.pid").exists());
        assert_eq!(
            std::fs::read_dir(dir.path().join("staging"))
                .unwrap()
                .count(),
            0
        );
    }
}

#[tokio::test]
async fn default_machine_preserves_absent_setting_and_explicit_reenable() {
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(
        dir.path(),
        "print(json.dumps({'answer':'synthetic candidate'}))",
    )
    .await;
    let first = executor
        .machine_answer(
            "Synthetic context".into(),
            "Question".into(),
            128,
            Duration::from_secs(5),
        )
        .await
        .unwrap();
    assert_eq!(first["answer"], "synthetic candidate");
    assert_owned_child_stopped(dir.path());
    std::fs::remove_file(dir.path().join("machine_resource_fixture.pid")).unwrap();
    executor
        .store()
        .submit_wait(|conn| {
            archeaxis_store_sqlite::capability_settings::set_enabled(conn, "machine.answer", false)
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(
        executor
            .machine_answer(
                "Synthetic context".into(),
                "Question".into(),
                128,
                Duration::from_secs(5)
            )
            .await
            .unwrap_err(),
        "machine.answer capability disabled"
    );
    assert!(!dir.path().join("machine_resource_fixture.pid").exists());
    executor
        .store()
        .submit_wait(|conn| {
            archeaxis_store_sqlite::capability_settings::set_enabled(conn, "machine.answer", true)
        })
        .await
        .unwrap()
        .unwrap();
    let restored = executor
        .machine_answer(
            "Synthetic context".into(),
            "Question".into(),
            128,
            Duration::from_secs(5),
        )
        .await
        .unwrap();
    assert_eq!(restored["answer"], "synthetic candidate");
    assert_owned_child_stopped(dir.path());
}

#[tokio::test]
async fn selected_machine_rechecks_disable_after_inventory_before_answer_spawn() {
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(dir.path(), r#"base=Path(__file__)
if '--probe' in sys.argv:
    base.with_suffix('.probe-started').write_text('ready')
    deadline=time.monotonic()+8
    while not base.with_suffix('.probe-release').exists():
        if time.monotonic() >= deadline:
            raise RuntimeError('test release deadline')
        time.sleep(0.01)
    print(json.dumps({'inventory_status':'READ_VERIFIED','loaded_status':'UNKNOWN','inference_status':'NOT_EXECUTED','evidence_scope':'MODEL_INVENTORY_ONLY','available':['synthetic-model'],'model':'synthetic-model','capability':True,'availability':'MODEL_LISTED_INFERENCE_UNVERIFIED'}))
else:
    base.with_suffix('.answer-started').write_text('unexpected')
    print(json.dumps({'answer':'must not execute','model':'synthetic-model','requested_model':'synthetic-model'}))"#).await;
    let request_executor = executor.clone();
    let pending = tokio::spawn(async move {
        request_executor
            .machine_answer_selected(
                "Synthetic context".into(),
                "Question".into(),
                128,
                Duration::from_secs(10),
                Some("synthetic-model".into()),
            )
            .await
    });
    tokio::time::timeout(Duration::from_secs(5), async {
        while !dir
            .path()
            .join("machine_resource_fixture.probe-started")
            .exists()
        {
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap();
    executor
        .store()
        .submit_wait(|conn| {
            archeaxis_store_sqlite::capability_settings::set_enabled(conn, "machine.answer", false)
        })
        .await
        .unwrap()
        .unwrap();
    std::fs::write(
        dir.path().join("machine_resource_fixture.probe-release"),
        "release",
    )
    .unwrap();
    let error = pending.await.unwrap().unwrap_err();
    assert_eq!(error, "machine.answer capability disabled");
    assert!(
        dir.path()
            .join("machine_resource_fixture.probe-started")
            .exists()
    );
    assert!(
        !dir.path()
            .join("machine_resource_fixture.answer-started")
            .exists()
    );
    assert_owned_child_stopped(dir.path());
}

#[tokio::test]
async fn machine_admission_wait_uses_the_original_deadline_without_spawn() {
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(
        dir.path(),
        "print(json.dumps({'answer':'must not execute'}))",
    )
    .await;
    let store = executor.store().clone();
    let (started, ready) = tokio::sync::oneshot::channel();
    let (release, blocked) = std::sync::mpsc::channel();
    let hold = tokio::spawn(async move {
        store
            .submit_wait(move |_| {
                started.send(()).unwrap();
                blocked.recv_timeout(Duration::from_secs(5)).unwrap();
            })
            .await
            .unwrap();
    });
    ready.await.unwrap();
    let started = Instant::now();
    let result = executor
        .machine_answer(
            "Synthetic context".into(),
            "Question".into(),
            128,
            Duration::from_secs(1),
        )
        .await;
    let elapsed = started.elapsed();
    release.send(()).unwrap();
    hold.await.unwrap();
    assert_eq!(
        result.unwrap_err(),
        "machine capability admission timed out"
    );
    assert!(elapsed < Duration::from_secs(3));
    assert!(!dir.path().join("machine_resource_fixture.pid").exists());
}

#[tokio::test]
async fn cancellation_interrupts_machine_admission_without_releasing_busy_store() {
    use archeaxis_application::executor::Cancellation;
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(
        dir.path(),
        "print(json.dumps({'answer':'must not execute'}))",
    )
    .await;
    let store = executor.store().clone();
    let (started, ready) = tokio::sync::oneshot::channel();
    let (release, blocked) = std::sync::mpsc::channel();
    let hold = tokio::spawn(async move {
        store
            .submit_wait(move |_| {
                started.send(()).unwrap();
                blocked.recv_timeout(Duration::from_secs(8)).unwrap();
            })
            .await
            .unwrap();
    });
    ready.await.unwrap();
    let cancel = Cancellation::new();
    let request = executor.machine_answer_configured_detailed(
        "Synthetic context".into(),
        "Question".into(),
        128,
        Duration::from_secs(10),
        None,
        cancel.clone(),
        None,
    );
    tokio::pin!(request);
    let waiting = tokio::time::timeout(Duration::from_millis(50), &mut request).await;
    cancel.cancel();
    let result = tokio::time::timeout(Duration::from_secs(2), &mut request).await;
    // 即使断言失败，也先释放自有writer；取消必须在释放前返回，不能依赖队列完成。
    release.send(()).unwrap();
    hold.await.unwrap();
    assert!(
        waiting.is_err(),
        "request must actually wait on the busy store"
    );
    assert_eq!(
        result
            .expect("cancellation must interrupt admission")
            .unwrap_err()
            .to_string(),
        "machine worker cancelled"
    );
    assert!(!dir.path().join("machine_resource_fixture.pid").exists());
}

#[tokio::test]
async fn unregistered_machine_does_not_fall_back_to_text_worker() {
    let dir = tempfile::tempdir().unwrap();
    let worker = dir.path().join("text_only.py");
    std::fs::write(&worker, "from pathlib import Path\nPath(__file__).with_suffix('.spawned').write_text('unexpected')\n").unwrap();
    let executor = Executor::open(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python(),
        &worker,
    )
    .await
    .unwrap();
    let error = executor
        .machine_answer(
            "Synthetic context".into(),
            "Question".into(),
            128,
            Duration::from_secs(5),
        )
        .await
        .unwrap_err();
    assert_eq!(error, "no worker is registered for machine.answer");
    assert!(!worker.with_extension("spawned").exists());
}

#[tokio::test]
async fn inventory_overflow_is_unknown_and_owned_worker_is_reaped() {
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(dir.path(), "assert sys.argv[1:] == ['--probe']\nsys.stdout.write('x'*1000001)\nsys.stdout.flush()\ntime.sleep(60)").await;
    let started = Instant::now();
    let result = executor.machine_inventory().await;
    assert!(started.elapsed() < Duration::from_secs(18));
    assert_eq!(result["status"], "READ_FAILED");
    assert!(result["listed_model_count"].is_null());
    assert!(result["selected_model_listed"].is_null());
    assert_owned_child_stopped(dir.path());
}

#[tokio::test]
async fn inventory_timeout_is_unknown_and_owned_worker_is_reaped() {
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(
        dir.path(),
        "assert sys.argv[1:] == ['--probe']\ntime.sleep(60)",
    )
    .await;
    let started = Instant::now();
    let result = executor.machine_inventory().await;
    assert!(started.elapsed() < Duration::from_secs(18));
    assert_eq!(result["status"], "READ_FAILED");
    assert!(result["selected_model_listed"].is_null());
    assert_owned_child_stopped(dir.path());
}

#[tokio::test]
async fn stdout_over_128k_is_rejected_and_direct_owned_child_is_reaped() {
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(
        dir.path(),
        "sys.stdout.write('x'*128001)\nsys.stdout.flush()\ntime.sleep(60)",
    )
    .await;
    let started = Instant::now();
    let error = executor
        .machine_answer(
            "SYNTHETIC context".into(),
            "SYNTHETIC question".into(),
            128,
            Duration::from_secs(10),
        )
        .await
        .unwrap_err();
    assert_eq!(error, "machine worker output exceeds bound");
    assert!(
        started.elapsed() < Duration::from_secs(10),
        "overflow must not merely time out"
    );
    assert_owned_child_stopped(dir.path());
}

#[tokio::test]
async fn one_second_timeout_proves_actual_owned_pid_is_no_longer_running() {
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(dir.path(), "time.sleep(60)").await;
    let started = Instant::now();
    let error = executor
        .machine_answer(
            "SYNTHETIC context".into(),
            "SYNTHETIC question".into(),
            128,
            Duration::from_secs(1),
        )
        .await
        .unwrap_err();
    assert_eq!(error, "machine worker timed out");
    assert!(
        started.elapsed() < Duration::from_secs(5),
        "one-second deadline plus cleanup must remain bounded"
    );
    assert_owned_child_stopped(dir.path());
}

#[tokio::test]
async fn answer_passes_a_bounded_timeout_to_the_owned_worker() {
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(dir.path(), "budget=int(sys.argv[sys.argv.index('--timeout-s')+1])\nprint(json.dumps({'answer':'synthetic','received_timeout_s':budget}))").await;
    let answer = executor
        .machine_answer(
            "synthetic".into(),
            "question".into(),
            128,
            Duration::from_secs(10),
        )
        .await
        .unwrap();
    let budget = answer["received_timeout_s"].as_u64().unwrap();
    assert!((1..=10).contains(&budget));
    assert_owned_child_stopped(dir.path());
}

#[tokio::test]
async fn hard_deadline_retains_bounded_measurements_and_reaps_owned_worker() {
    use archeaxis_application::executor::Cancellation;
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(dir.path(), "time.sleep(60)").await;
    let error = executor
        .machine_answer_configured_detailed(
            "SYNTHETIC_PRIVATE_CONTEXT".into(),
            "SYNTHETIC_PRIVATE_QUESTION".into(),
            128,
            Duration::from_secs(1),
            None,
            Cancellation::new(),
            None,
        )
        .await
        .unwrap_err();
    assert_eq!(error.reason_code(), "WORKER_TIMEOUT");
    let diagnostics = error
        .diagnostics()
        .expect("hard deadlines retain Core measurements");
    assert_eq!(diagnostics["timeout_s"], 1);
    assert_eq!(diagnostics["max_tokens"], 128);
    assert_eq!(diagnostics["error_type"], "TimeoutError");
    assert!(diagnostics["requested_model"].is_null());
    assert!(diagnostics.get("observed_model").is_none());
    assert!(diagnostics["elapsed_s"].as_f64().unwrap() >= 1.0);
    assert!(!diagnostics.to_string().contains("SYNTHETIC_PRIVATE"));
    assert_owned_child_stopped(dir.path());
}

#[tokio::test]
async fn invalid_input_and_budget_are_rejected_before_worker_spawn() {
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(
        dir.path(),
        "print(json.dumps({'answer':'unexpected worker','model':'synthetic'}))",
    )
    .await;
    let cases = vec![
        ("x".repeat(128001), "question".to_string(), 128, 1),
        ("context".to_string(), "x".repeat(8193), 128, 1),
        ("context".to_string(), "bad\0question".to_string(), 128, 1),
        (" ".to_string(), "question".to_string(), 128, 1),
        ("context".to_string(), " ".to_string(), 128, 1),
        ("context".to_string(), "question".to_string(), 127, 1),
        ("context".to_string(), "question".to_string(), 4097, 1),
        ("context".to_string(), "question".to_string(), 128, 0),
        ("context".to_string(), "question".to_string(), 128, 121),
    ];
    for (context, question, tokens, seconds) in cases {
        assert_eq!(
            executor
                .machine_answer(context, question, tokens, Duration::from_secs(seconds))
                .await
                .unwrap_err(),
            "invalid machine answer budget or input"
        );
        assert!(
            !dir.path().join("machine_resource_fixture.pid").exists(),
            "rejected input must not run a worker"
        );
    }
}

#[tokio::test]
async fn valid_utf8_context_and_question_round_trip_normally() {
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(
        dir.path(),
        concat!(
            "context=Path(sys.argv[1]).read_text(encoding='utf-8')\n",
            "question=sys.argv[sys.argv.index('--question')+1]\n",
            "tokens=int(sys.argv[sys.argv.index('--max-tokens')+1])\n",
            "assert context=='事实\\n中😀' and question=='问题😀' and tokens==128\n",
            "print(json.dumps({'answer':'中文候选😀','model':'synthetic/utf8'},ensure_ascii=False))"
        ),
    )
    .await;
    let result = executor
        .machine_answer(
            "事实\n中😀".into(),
            "问题😀".into(),
            128,
            Duration::from_secs(10),
        )
        .await
        .unwrap();
    assert_eq!(result["answer"], "中文候选😀");
    assert_eq!(result["model"], "synthetic/utf8");
    assert_owned_child_stopped(dir.path());
}

#[test]
fn private_parent_marker_isolated_without_mutating_global_test_environment() {
    // Rust 2024 std::env mutation would be unsafe in a parallel test process.
    // Launch only this same exact test with a synthetic marker instead.
    if std::env::var(MARKER).ok().as_deref() == Some(SENTINEL) {
        tokio::runtime::Builder::new_current_thread()
            .enable_time()
            .build()
            .unwrap()
            .block_on(environment_probe_child());
        return;
    }
    let mut command = std::process::Command::new(std::env::current_exe().unwrap());
    command
        .args([
            "--exact",
            "private_parent_marker_isolated_without_mutating_global_test_environment",
            "--nocapture",
        ])
        .env(MARKER, SENTINEL);
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let output = command.output().unwrap();
    assert!(
        output.status.success(),
        "isolated environment child failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    // Ensure the exact child test actually ran; an empty test filter is not evidence.
    assert!(String::from_utf8_lossy(&output.stdout).contains("ENVIRONMENT_PROBE_CHILD_EXECUTED"));
}

async fn environment_probe_child() {
    assert_eq!(std::env::var(MARKER).unwrap(), SENTINEL);
    let dir = tempfile::tempdir().unwrap();
    let staging = dir.path().join("staging");
    let executor = fixture(
        dir.path(),
        concat!(
            "keys=['TEMP','TMP','TMPDIR','HOME','USERPROFILE','APPDATA','LOCALAPPDATA']\n",
            "print(json.dumps({'answer':'SYNTHETIC isolated env','model':'synthetic/environment',",
            "'marker':os.environ.get('ARCHEAXIS_TEST_PRIVATE_GLOBAL_MARKER'),",
            "'cwd':os.getcwd(),'roots':{key:os.environ.get(key) for key in keys},",
            "'isolated':sys.flags.isolated,'no_user_site':sys.flags.no_user_site,",
            "'dont_write_bytecode':sys.flags.dont_write_bytecode}))"
        ),
    )
    .await;
    let response: Value = executor
        .machine_answer(
            "SYNTHETIC env context".into(),
            "SYNTHETIC question".into(),
            128,
            Duration::from_secs(10),
        )
        .await
        .unwrap();
    assert!(
        response["marker"].is_null(),
        "private synthetic parent marker must not reach worker"
    );
    assert_eq!(response["isolated"], 1);
    assert_eq!(response["no_user_site"], 1);
    assert_eq!(response["dont_write_bytecode"], 1);
    let cwd = response["cwd"].as_str().unwrap();
    assert_eq!(
        Path::new(cwd).parent(),
        Some(staging.as_path()),
        "worker must run in a direct owned staging child"
    );
    for key in [
        "TEMP",
        "TMP",
        "TMPDIR",
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
    ] {
        assert_eq!(
            response["roots"][key].as_str(),
            Some(cwd),
            "{key} must point to the owned staging child"
        );
    }
    assert_owned_child_stopped(dir.path());
    println!("ENVIRONMENT_PROBE_CHILD_EXECUTED");
}

#[tokio::test]
async fn nonzero_worker_keeps_only_allowlisted_reason_and_never_accepts_answer() {
    for (code, expected) in [
        ("NO_FINAL_ANSWER", "NO_FINAL_ANSWER"),
        ("MODEL_CALL_TIMEOUT", "MODEL_CALL_TIMEOUT"),
        ("SYNTHETIC_PRIVATE", "WORKER_FAILED"),
    ] {
        let dir = tempfile::tempdir().unwrap();
        let executor=fixture(dir.path(), &format!("print(json.dumps({{\"schema\":\"archeaxis.machine-worker-failure/v1\",\"reason_code\":\"{code}\",\"answer\":\"SYNTHETIC_PRIVATE\",\"error\":\"SYNTHETIC_PRIVATE\"}}))\nsys.exit(1)")).await;
        let error = executor
            .machine_answer(
                "SYNTHETIC context".into(),
                "SYNTHETIC question".into(),
                128,
                Duration::from_secs(10),
            )
            .await
            .unwrap_err();
        assert_eq!(error, format!("machine failure: {expected}"));
        assert_owned_child_stopped(dir.path());
    }
}

// 实际启动隔离的自有合成worker读取argv；不调用真实模型服务。
#[tokio::test]
async fn legacy_detailed_answer_keeps_grounded_policy_and_prompt_version() {
    use archeaxis_application::executor::Cancellation;
    let dir = tempfile::tempdir().unwrap();
    let executor = fixture(
        dir.path(),
        concat!(
            "policy=sys.argv[sys.argv.index('--answer-policy')+1]\n",
            "version=sys.argv[sys.argv.index('--prompt-version')+1]\n",
            "print(json.dumps({'answer':'synthetic candidate','answer_policy':policy,'prompt_version':version}))"
        ),
    )
    .await;
    let answer = executor
        .machine_answer_configured_detailed(
            "Synthetic context".into(),
            "Synthetic question".into(),
            128,
            Duration::from_secs(10),
            None,
            Cancellation::new(),
            None,
        )
        .await
        .unwrap();
    assert_eq!(answer["answer_policy"], "grounded");
    assert_eq!(answer["prompt_version"], "archeaxis.vnext/v1 2026-10-02");
    assert_owned_child_stopped(dir.path());
}

#[tokio::test]
async fn explicit_finite_answer_policy_reaches_owned_worker_with_matching_version() {
    use archeaxis_application::executor::{AnswerPolicy, Cancellation};
    for (policy, expected_policy, expected_version) in [
        (
            AnswerPolicy::Grounded,
            "grounded",
            "archeaxis.vnext/v1 2026-10-02",
        ),
        (
            AnswerPolicy::CompanionGeneral,
            "companion_general",
            "archeaxis.companion/v1 2026-10-19",
        ),
    ] {
        let dir = tempfile::tempdir().unwrap();
        let executor = fixture(
            dir.path(),
            concat!(
                "policy=sys.argv[sys.argv.index('--answer-policy')+1]\n",
                "version=sys.argv[sys.argv.index('--prompt-version')+1]\n",
                "print(json.dumps({'answer':'synthetic candidate','answer_policy':policy,'prompt_version':version}))"
            ),
        )
        .await;
        let answer = executor
            .machine_answer_with_policy_detailed(
                "Synthetic context".into(),
                "Synthetic question".into(),
                128,
                Duration::from_secs(10),
                None,
                Cancellation::new(),
                None,
                policy,
            )
            .await
            .unwrap();
        assert_eq!(answer["answer_policy"], expected_policy);
        assert_eq!(answer["prompt_version"], expected_version);
        assert_owned_child_stopped(dir.path());
    }
}
