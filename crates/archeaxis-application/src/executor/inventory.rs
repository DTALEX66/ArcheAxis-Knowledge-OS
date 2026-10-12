//! Explicit, input-free local inventory observation. Never inference evidence.
use super::*;
use serde_json::{Value, json};

fn outcome(status: &str, count: Option<usize>, listed: Option<bool>) -> Value {
    json!({"schema":"archeaxis.machine-inventory/v1", "status":status,
        "listed_model_count":count,"selected_model_listed":listed,
        "loaded_status":"UNKNOWN","inference_status":"NOT_EXECUTED",
        "usage":null,"cost":null,"evidence_scope":"MODEL_INVENTORY_ONLY"})
}

fn project(reply: &Value) -> Value {
    let doc = &reply["document"];
    if reply["exit_code"] != 0
        || doc["inventory_status"] != "READ_VERIFIED"
        || doc["loaded_status"] != "UNKNOWN"
        || doc["inference_status"] != "NOT_EXECUTED"
        || doc["evidence_scope"] != "MODEL_INVENTORY_ONLY"
    {
        return outcome("READ_FAILED", None, None);
    }
    let Some(models) = doc["available"].as_array() else {
        return outcome("READ_FAILED", None, None);
    };
    if models.len() > 256
        || models.iter().any(|v| {
            !v.as_str().is_some_and(|s| {
                !s.trim().is_empty() && s.len() <= 256 && !s.chars().any(char::is_control)
            })
        })
    {
        return outcome("READ_FAILED", None, None);
    }
    let mut result = match doc["availability"].as_str() {
        Some("MODEL_NOT_LISTED") if doc["capability"] == false => {
            outcome("READ_VERIFIED", Some(models.len()), Some(false))
        }
        Some("MODEL_LISTED_INFERENCE_UNVERIFIED")
            if doc["capability"] == true
                && doc["model"]
                    .as_str()
                    .is_some_and(|m| models.iter().any(|v| v.as_str() == Some(m))) =>
        {
            outcome("READ_VERIFIED", Some(models.len()), Some(true))
        }
        _ => outcome("READ_FAILED", None, None),
    };
    if result["status"] == "READ_VERIFIED" {
        result["model_choices"] = json!(models);
    }
    result
}

impl Executor {
    async fn inventory_enabled(&self) -> Option<bool> {
        match self
            .store
            .submit_wait(|conn| capability_settings::disabled_capabilities(conn))
            .await
        {
            Ok(Ok(names)) => Some(!names.iter().any(|n| n == "machine.answer")),
            _ => None,
        }
    }

    pub async fn machine_inventory(&self) -> Value {
        match self.inventory_enabled().await {
            Some(true) => {}
            Some(false) => return outcome("DISABLED", None, None),
            None => return outcome("UNAVAILABLE", None, None),
        }
        let Some((worker, site)) = self.worker_for("machine.answer") else {
            return outcome("UNAVAILABLE", None, None);
        };
        let deadline = Instant::now() + Duration::from_secs(15);
        let Ok(Ok(permit)) = tokio::time::timeout(
            Duration::from_secs(2),
            self.health_slots.clone().acquire_owned(),
        )
        .await
        else {
            return outcome("BUSY", None, None);
        };
        match self.inventory_enabled().await {
            Some(true) => {}
            Some(false) => return outcome("DISABLED", None, None),
            None => return outcome("UNAVAILABLE", None, None),
        }
        let staging = self.staging.clone();
        let python = self.python.clone();
        tokio::task::spawn_blocking(move || {
            let _permit = permit;
            let remaining = deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() {
                return outcome("READ_FAILED", None, None);
            }
            match derived::inventory(&staging, &python, &worker, site, remaining) {
                Ok(reply) => project(&reply),
                Err(_) => outcome("READ_FAILED", None, None),
            }
        })
        .await
        .unwrap_or_else(|_| outcome("READ_FAILED", None, None))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::future::{Future, poll_fn};
    use std::task::Poll;

    async fn queued_fixture(dir: &Path) -> Executor {
        let worker = dir.join("inventory.py");
        std::fs::write(&worker, "from pathlib import Path\nPath(__file__).with_suffix('.spawned').write_text('unexpected')\n").unwrap();
        let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON")
            .expect("canonical declared Python required")
            .into();
        Executor::open_routes(
            &dir.join("db.sqlite"),
            &dir.join("staging"),
            &python,
            &worker,
            &[("machine.answer", worker.clone())],
        )
        .await
        .unwrap()
    }

    #[tokio::test]
    async fn queued_inventory_rechecks_disable_after_initial_read() {
        let dir = tempfile::tempdir().unwrap();
        let executor = queued_fixture(dir.path()).await;
        let permits = executor
            .health_slots
            .clone()
            .acquire_many_owned(4)
            .await
            .unwrap();
        let pending = executor.machine_inventory();
        tokio::pin!(pending);
        // First poll queues the settings read; writer barrier proves it completed.
        poll_fn(|cx| {
            assert!(pending.as_mut().poll(cx).is_pending());
            Poll::Ready(())
        })
        .await;
        executor
            .store
            .submit_wait(|_| Ok::<_, rusqlite::Error>(()))
            .await
            .unwrap()
            .unwrap();
        // With the settings result ready, this poll advances to the held semaphore.
        poll_fn(|cx| {
            assert!(pending.as_mut().poll(cx).is_pending());
            Poll::Ready(())
        })
        .await;
        executor
            .store
            .submit_wait(|conn| capability_settings::set_enabled(conn, "machine.answer", false))
            .await
            .unwrap()
            .unwrap();
        drop(permits);
        let result = pending.await;
        assert_eq!(result["status"], "DISABLED");
        assert!(result["selected_model_listed"].is_null());
        assert!(!dir.path().join("inventory.spawned").exists());
    }

    #[tokio::test]
    async fn full_inventory_queue_times_out_without_spawn() {
        let dir = tempfile::tempdir().unwrap();
        let executor = queued_fixture(dir.path()).await;
        let _permits = executor
            .health_slots
            .clone()
            .acquire_many_owned(4)
            .await
            .unwrap();
        let started = Instant::now();
        let result = executor.machine_inventory().await;
        assert!(started.elapsed() < Duration::from_secs(4));
        assert_eq!(result["status"], "BUSY");
        assert!(!dir.path().join("inventory.spawned").exists());
    }
    #[test]
    fn failed_inventory_is_unknown_and_does_not_echo_worker_content() {
        let result = project(
            &json!({"exit_code":0,"document":{"endpoint":"SYNTHETIC_PRIVATE","inventory_status":"READ_FAILED"}}),
        );
        assert_eq!(result["status"], "READ_FAILED");
        assert!(result["listed_model_count"].is_null());
        assert!(result["selected_model_listed"].is_null());
        assert!(!result.to_string().contains("SYNTHETIC_PRIVATE"));
    }
    #[test]
    fn listed_model_is_not_loaded_or_inference_evidence() {
        let result = project(
            &json!({"exit_code":0,"document":{"inventory_status":"READ_VERIFIED","loaded_status":"UNKNOWN","inference_status":"NOT_EXECUTED","evidence_scope":"MODEL_INVENTORY_ONLY","available":["m"],"model":"m","capability":true,"availability":"MODEL_LISTED_INFERENCE_UNVERIFIED","endpoint":"SYNTHETIC_PRIVATE"}}),
        );
        assert_eq!(result["selected_model_listed"], true);
        assert_eq!(result["listed_model_count"], 1);
        assert_eq!(result["loaded_status"], "UNKNOWN");
        assert!(result["usage"].is_null());
        assert!(!result.to_string().contains("SYNTHETIC_PRIVATE"));
    }
}
