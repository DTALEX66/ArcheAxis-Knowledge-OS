use archeaxis_application::executor::Executor;
use serde_json::json;
use std::{path::PathBuf, time::Duration};

#[tokio::test]
async fn disabling_a_capability_while_queued_prevents_its_process_start() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("gate.py");
    std::fs::write(&script,"import pathlib,json,sys,time\nr=json.load(sys.stdin)\nroot=pathlib.Path(__file__).parent\n(root/str(r['id'])).touch()\nwhile not (root/'release').exists(): time.sleep(.01)\nprint('{}')\n").unwrap();
    let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON").unwrap().into();
    let executor = Executor::open_routes(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &python,
        &script,
        &[("search.semantic", script.clone())],
    )
    .await
    .unwrap();
    let mut tasks = Vec::new();
    for id in 0..4 {
        let owned = executor.clone();
        tasks.push(tokio::spawn(async move {
            owned
                .derived_json("search.semantic", json!({"id":id}), Duration::from_secs(5))
                .await
        }));
    }
    let deadline = std::time::Instant::now() + Duration::from_secs(4);
    while !(0..4).all(|id| dir.path().join(id.to_string()).exists()) {
        assert!(std::time::Instant::now() < deadline);
        tokio::time::sleep(Duration::from_millis(10)).await;
    }
    let owned = executor.clone();
    let queued = tokio::spawn(async move {
        owned
            .derived_json("search.semantic", json!({"id":4}), Duration::from_secs(5))
            .await
    });
    tokio::time::sleep(Duration::from_millis(100)).await;
    assert!(!queued.is_finished());
    executor
        .store()
        .submit_wait(|conn| {
            archeaxis_store_sqlite::capability_settings::set_enabled(conn, "search.semantic", false)
                .unwrap()
        })
        .await
        .unwrap();
    std::fs::write(dir.path().join("release"), "").unwrap();
    for task in tasks {
        task.await.unwrap().unwrap();
    }
    assert!(queued.await.unwrap().is_err());
    assert!(
        !dir.path().join("4").exists(),
        "queued worker must never spawn after disable"
    );
}

#[tokio::test]
async fn derived_workers_preserve_partial_outcomes_and_bound_failure() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("worker.py");
    std::fs::write(&script, "import os,json,sys\nrequest=json.loads(sys.stdin.readline())\nassert not any(k.lower().endswith('proxy') or k in ('PYTHONPATH','OPENAI_API_KEY') for k in os.environ)\nprint(json.dumps({'status':'PARTIAL','echo':request}))\nsys.exit(2)\n").unwrap();
    let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON").unwrap().into();
    let executor = Executor::open_routes(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &python,
        &script,
        &[("search.semantic", script.clone())],
    )
    .await
    .unwrap();
    let result = executor
        .derived_json(
            "search.semantic",
            json!({"query":"safe"}),
            Duration::from_secs(5),
        )
        .await
        .unwrap();
    assert_eq!(result["exit_code"], 2);
    assert_eq!(result["document"]["status"], "PARTIAL");
    assert!(
        executor
            .derived_json("text.extract", json!({}), Duration::from_secs(1))
            .await
            .is_err()
    );
    assert!(
        executor
            .derived_json(
                "search.semantic",
                json!({"x":"x".repeat(256000)}),
                Duration::from_secs(1)
            )
            .await
            .is_err()
    );
    std::fs::write(&script, "import time\ntime.sleep(20)\n").unwrap();
    let start = std::time::Instant::now();
    assert!(
        executor
            .derived_json("search.semantic", json!({}), Duration::from_millis(100))
            .await
            .is_err()
    );
    assert!(start.elapsed() < Duration::from_secs(3));
    std::fs::write(&script, "print('not JSON')\n").unwrap();
    assert!(
        executor
            .derived_json("search.semantic", json!({}), Duration::from_secs(2))
            .await
            .is_err()
    );
    std::fs::write(&script, "print('x'*1000001)\n").unwrap();
    assert!(
        executor
            .derived_json("search.semantic", json!({}), Duration::from_secs(2))
            .await
            .is_err()
    );
    std::fs::write(
        &script,
        "import sys\nsys.stderr.write('x'*8193)\nprint('{}')\n",
    )
    .unwrap();
    assert!(
        executor
            .derived_json("search.semantic", json!({}), Duration::from_secs(2))
            .await
            .is_err()
    );
    std::fs::write(
        &script,
        "import json\nprint(json.dumps({'message':'中文😀'},ensure_ascii=False))\n",
    )
    .unwrap();
    assert_eq!(
        executor
            .derived_json("search.semantic", json!({}), Duration::from_secs(2))
            .await
            .unwrap()["document"]["message"],
        "中文😀"
    );
}
