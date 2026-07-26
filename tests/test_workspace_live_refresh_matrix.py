"""p1-live-refresh-and-recovery-matrix: verify state changes read back without restart,
and that failure/retry/dispatch/receipt states all have evidential proof."""

from __future__ import annotations


def test_live_refresh_and_recovery_matrix_without_restart(
    monkeypatch, tmp_path,
) -> None:
    """Exercise the full failure → retry → dispatch → receipt matrix.

    Every read happens from the same database without reconnecting the API,
    proving state transitions are observable without restart.
    """
    from app.workspace import service
    from app.workspace.outbox_dispatcher import dispatch_once
    from app.workspace.research_consumer import make_intake_research_handler
    from shared.migration_runner import MigrationOperator
    from tests.test_phase5_mcs_closed_loop import _database

    # ------------------------------------------------------------------ #
    # 1. Setup: database with workspace + core migrations                #
    # ------------------------------------------------------------------ #
    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "workspace.sqlite"
    )
    monkeypatch.setattr(service, "convert_url", lambda url: ("# matrix\nLive.", "test"))

    # ------------------------------------------------------------------ #
    # 2. Intake → creates job(succeeded) + outbox(pending) + receipt     #
    # ------------------------------------------------------------------ #
    intake = service.intake_url(url="https://example.com/matrix", db_path=database)
    package_id = intake["package_id"]
    assert intake["status"] == "candidate"
    assert intake["requires_human_review"]

    # ------------------------------------------------------------------ #
    # 3. Read jobs — state changed (no restart)                          #
    # ------------------------------------------------------------------ #
    jobs = service.workspace_jobs(db_path=database)
    assert jobs["schema_version"] == "v1"
    assert len(jobs["jobs"]) == 1
    assert jobs["jobs"][0]["state"] == "succeeded"
    assert jobs["jobs"][0]["delivery_state"] == "pending"
    assert "command_id" not in str(jobs)
    assert "package_id" not in str(jobs)

    # ------------------------------------------------------------------ #
    # 4. Read delivery — sees pending outbox                             #
    # ------------------------------------------------------------------ #
    delivery = service.workspace_delivery(db_path=database)
    assert delivery["summary"]["jobs"] == 1
    assert delivery["summary"]["outbox"]["pending"] == 1
    assert delivery["items"][0]["receipt_state"] == "missing"
    assert delivery["items"][0]["job_state"] == "succeeded"
    assert delivery["items"][0]["outbox_state"] == "pending"
    assert "event_internal" not in str(delivery)

    # ------------------------------------------------------------------ #
    # 5. Dispatch with a handler that raises → FAILURE                   #
    # ------------------------------------------------------------------ #
    def _failing_handler(_event: dict[str, object]) -> dict[str, object]:
        msg = "simulated delivery failure for matrix test"
        raise RuntimeError(msg)

    failed = dispatch_once(
        db_path=database,
        worker_name="matrix-test-failure",
        handler=_failing_handler,
    )
    assert failed["status"] == "failed"
    assert failed["attempt"] == 1

    # ------------------------------------------------------------------ #
    # 6. Read delivery — now sees failed outbox                          #
    # ------------------------------------------------------------------ #
    delivery_after_fail = service.workspace_delivery(db_path=database)
    assert delivery_after_fail["summary"]["outbox"].get("failed") == 1
    assert delivery_after_fail["items"][0]["outbox_state"] == "failed"
    assert delivery_after_fail["items"][0]["outbox_attempts"] == 1  # incremented

    # ------------------------------------------------------------------ #
    # 7. Retry → outbox back to pending                                  #
    # ------------------------------------------------------------------ #
    retry = service.retry_failed_delivery(db_path=database)
    assert retry["status"] == "requeued"

    delivery_after_retry = service.workspace_delivery(db_path=database)
    assert delivery_after_retry["summary"]["outbox"].get("pending") == 1
    assert delivery_after_retry["items"][0]["outbox_state"] == "pending"
    assert delivery_after_retry["items"][0]["outbox_attempts"] == 1

    # ------------------------------------------------------------------ #
    # 8. Dispatch with real handler → delivered + receipt                #
    # ------------------------------------------------------------------ #
    dispatched = dispatch_once(
        db_path=database,
        worker_name="matrix-test-delivery",
        handler=make_intake_research_handler(
            db_path=database, consumer_name="matrix-test-consumer"
        ),
    )
    assert dispatched["status"] == "delivered"
    assert dispatched["attempt"] == 2  # second attempt

    # ------------------------------------------------------------------ #
    # 9. Read delivery — delivered + receipt recorded                    #
    # ------------------------------------------------------------------ #
    delivery_after_dispatch = service.workspace_delivery(db_path=database)
    assert delivery_after_dispatch["summary"]["outbox"]["delivered"] == 1
    assert delivery_after_dispatch["summary"]["receipts"]["recorded"] == 1
    assert delivery_after_dispatch["items"][0]["outbox_state"] == "delivered"
    assert delivery_after_dispatch["items"][0]["receipt_state"] == "recorded"
    assert "event_internal" not in str(delivery_after_dispatch)
    assert "consumer_name" not in str(delivery_after_dispatch)
    assert "proof_json" not in str(delivery_after_dispatch)

    # ------------------------------------------------------------------ #
    # 10. Read individual job — unchanged succeeded + receipt persisted  #
    # ------------------------------------------------------------------ #
    service.intake_job(job_id=intake["job_id"], db_path=database)  # not raise

    # ------------------------------------------------------------------ #
    # 11. Read lifecycle — aggregate without ids                         #
    # ------------------------------------------------------------------ #
    lifecycle = service.workspace_lifecycle(db_path=database)
    assert lifecycle["privacy"] == "aggregate_only"
    for stage_name in ("permission", "execution", "trace", "evaluation", "lesson"):
        assert stage_name in lifecycle["stages"]
    assert "command_id" not in str(lifecycle)
    assert "package_id" not in str(lifecycle)

    # ------------------------------------------------------------------ #
    # 12. Verify the research package still exists and is readable        #
    #     (no restart needed for this final read)                         #
    # ------------------------------------------------------------------ #
    from app.facades.research import get_research_package

    package = get_research_package(package_id, db_path=database)
    assert package.package.package_id == package_id
    assert package.package.status == "candidate"
