use archeaxis_api::project_handoff as handoff;
use archeaxis_contracts::{
    project_handoff::{Handoff, Payload, PrepareError, ReceiptReason, ReceiptState, RetryClass},
    project_observer::{
        NavigationState, ObjectReference, ObjectState, Payload as ReadPayload, ReadResponse,
    },
};
use serde_json::{Value, json};

fn cases() -> Vec<Value> {
    serde_json::from_str(include_str!(
        "../../../packages/contracts/v2/project-handoff.cases.json"
    ))
    .unwrap()
}
fn example(name: &str) -> Handoff {
    serde_json::from_value(
        cases().into_iter().find(|c| c["name"] == name).unwrap()["value"].clone(),
    )
    .unwrap()
}
fn snapshot() -> ReadResponse {
    serde_json::from_value(json!({"schema":"archeaxis.project-observer-response/v1","protocol":"archeaxis.project-observer/v1","producer":{"namespace":"archeaxis","workspace_id":"a".repeat(32),"restore_epoch":"initial"},"consumer":{"namespace":"work-lab","instance_id":"b".repeat(32)},"checked_at_ms":10000,"expires_at_ms":40000,"payload":{"kind":"objects","objects":[{"document_id":"doc_a","version":2,"content_sha256":"a".repeat(64)},{"document_id":"doc_b","version":1,"content_sha256":"b".repeat(64)},{"document_id":"loss_receipt","version":1,"content_sha256":"c".repeat(64)}],"navigation":"UNAVAILABLE"}})).unwrap()
}
fn first_reference() -> ObjectReference {
    match snapshot().payload {
        ReadPayload::Objects { objects, .. } => objects[0].clone(),
        _ => unreachable!(),
    }
}

#[test]
fn all_nonreceipt_positive_kinds_have_real_reference_bound_projection() {
    let snapshot = snapshot();
    let mut count = 0;
    for case in cases().into_iter().filter(|c| c["runtime_valid"] == true) {
        let message: Handoff = serde_json::from_value(case["value"].clone()).unwrap();
        if matches!(message.payload, Payload::Receipt { .. }) {
            continue;
        }
        let projected = handoff::prepare(
            &snapshot,
            &message.idempotency_key,
            message.payload.clone(),
            10000,
        )
        .unwrap();
        assert_eq!(projected, message, "{}", case["name"]);
        assert_eq!(
            handoff::proposal_fingerprint(&message).unwrap(),
            case["expected_proposal_sha256"].as_str().unwrap(),
            "cross-language fingerprint: {}",
            case["name"]
        );
        assert!(projected.valid(10000));
        assert_eq!(projected.expires_at_ms, snapshot.expires_at_ms);
        assert_eq!(
            serde_json::to_value(&projected).unwrap()["authority"],
            "PREPARATION_ONLY"
        );
        count += 1;
    }
    assert_eq!(count, 11);
    eprintln!("reference-bound nonreceipt projections={count}");
}

#[test]
fn stale_expired_unlisted_and_wrong_revision_are_not_projected_as_current() {
    let payload = example("valid_context").payload;
    let mut view = snapshot();
    view.expires_at_ms = 10000;
    assert_eq!(
        handoff::prepare(&view, &"2".repeat(32), payload.clone(), 10000),
        Err(PrepareError::InvalidSnapshot)
    );
    view = snapshot();
    view.payload = ReadPayload::ObjectStatus {
        reference: first_reference(),
        state: ObjectState::Stale,
        navigation: NavigationState::Unavailable,
    };
    assert_eq!(
        handoff::prepare(&view, &"2".repeat(32), payload.clone(), 10000),
        Err(PrepareError::ReferenceNotCurrent)
    );
    for field in ["version", "content_sha256", "document_id"] {
        let mut value = serde_json::to_value(&payload).unwrap();
        value["source"]["reference"][field] = match field {
            "version" => json!(3),
            "content_sha256" => json!("f".repeat(64)),
            _ => json!("unlisted_document"),
        };
        let changed = serde_json::from_value(value).unwrap();
        assert_eq!(
            handoff::prepare(&snapshot(), &"2".repeat(32), changed, 10000),
            Err(PrepareError::ReferenceNotCurrent)
        );
    }
    view = snapshot();
    view.payload = ReadPayload::ObjectStatus {
        reference: first_reference(),
        state: ObjectState::Current,
        navigation: NavigationState::Unavailable,
    };
    assert!(handoff::prepare(&view, &"2".repeat(32), payload, 10000).is_ok());
}

#[test]
fn every_asset_source_and_loss_receipt_must_be_in_the_observed_allowlist() {
    let payload = example("valid_derived_asset_with_loss_reference").payload;
    for omitted in ["doc_a", "doc_b", "loss_receipt"] {
        let mut view = snapshot();
        if let ReadPayload::Objects { objects, .. } = &mut view.payload {
            objects.retain(|r| r.document_id != omitted);
        }
        assert_eq!(
            handoff::prepare(&view, &"2".repeat(32), payload.clone(), 10000),
            Err(PrepareError::ReferenceNotCurrent)
        );
    }
    assert!(handoff::prepare(&snapshot(), &"2".repeat(32), payload, 10000).is_ok());
}

#[test]
fn candidate_evidence_does_not_gain_human_acceptance_or_verified_support() {
    let mut message = example("valid_candidate");
    let mut payload = message.payload.clone();
    if let Payload::KnowledgeCandidate { evidence, .. } = &mut payload {
        evidence[0].reference.version += 1;
    }
    assert_eq!(
        handoff::prepare(&snapshot(), &message.idempotency_key, payload, 10000),
        Err(PrepareError::ReferenceNotCurrent)
    );
    message = handoff::prepare(
        &snapshot(),
        &message.idempotency_key,
        message.payload,
        10000,
    )
    .unwrap();
    let value = serde_json::to_value(message).unwrap();
    assert_eq!(value["payload"]["review_state"], "PENDING_HUMAN_REVIEW");
    assert_eq!(value["payload"]["evidence_support"], "NOT_ASSESSED");
    assert!(value["payload"].get("claim_text").is_none());
}

#[test]
fn retry_equivalence_is_scoped_and_conflicting_payload_or_expiry_cannot_renew_key() {
    let original = example("valid_context");
    let same: Handoff = serde_json::from_str(&serde_json::to_string(&original).unwrap()).unwrap();
    assert_eq!(
        handoff::classify_retry(&original, &same),
        Ok(RetryClass::Equivalent)
    );
    let mut changed = original.clone();
    if let Payload::Context { purpose, .. } = &mut changed.payload {
        *purpose = archeaxis_contracts::project_handoff::ContextPurpose::Research;
    }
    assert_eq!(
        handoff::classify_retry(&original, &changed),
        Ok(RetryClass::Conflict)
    );
    changed = original.clone();
    changed.expires_at_ms -= 1;
    assert_eq!(
        handoff::classify_retry(&original, &changed),
        Ok(RetryClass::Conflict)
    );
    changed = original.clone();
    changed.producer.restore_epoch = "c".repeat(32);
    assert_eq!(
        handoff::classify_retry(&original, &changed),
        Ok(RetryClass::Unrelated)
    );
    changed = original.clone();
    changed.consumer.instance_id = "c".repeat(32);
    assert_eq!(
        handoff::classify_retry(&original, &changed),
        Ok(RetryClass::Unrelated)
    );
    changed = original.clone();
    changed.idempotency_key = "c".repeat(32);
    assert_eq!(
        handoff::classify_retry(&original, &changed),
        Ok(RetryClass::Unrelated)
    );
    changed = original.clone();
    changed.schema = "v999".into();
    assert_eq!(
        handoff::classify_retry(&original, &changed),
        Err(PrepareError::InvalidProposal)
    );
}

#[test]
fn receipt_requires_original_and_preserves_unknown_conflict_and_identity_binding() {
    let original = example("valid_context");
    for (state, reason) in [
        (ReceiptState::Unknown, ReceiptReason::Timeout),
        (ReceiptState::Conflict, ReceiptReason::IdempotencyConflict),
        (ReceiptState::Prepared, ReceiptReason::None),
    ] {
        let receipt = handoff::prepare_receipt(
            &snapshot(),
            &original,
            &"3".repeat(32),
            state.clone(),
            reason,
            10000,
        )
        .unwrap();
        assert!(handoff::receipt_matches(&receipt, &original, 10000));
        assert!(matches!(&receipt.payload,Payload::Receipt{state:actual,..} if *actual==state));
        let mut unrelated = original.clone();
        unrelated.idempotency_key = "4".repeat(32);
        assert!(!handoff::receipt_matches(&receipt, &unrelated, 10000));
        let mut wrong_kind = original.clone();
        wrong_kind.payload = example("valid_task").payload;
        assert!(!handoff::receipt_matches(&receipt, &wrong_kind, 10000));
        assert_eq!(
            handoff::prepare(&snapshot(), &"3".repeat(32), receipt.payload.clone(), 10000),
            Err(PrepareError::OriginalRequired)
        );
    }
    let mut wrong = snapshot();
    wrong.producer.restore_epoch = "d".repeat(32);
    assert_eq!(
        handoff::prepare_receipt(
            &wrong,
            &original,
            &"3".repeat(32),
            ReceiptState::Prepared,
            ReceiptReason::None,
            10000
        ),
        Err(PrepareError::IdentityMismatch)
    );
    assert_eq!(
        handoff::prepare_receipt(
            &snapshot(),
            &original,
            &original.idempotency_key,
            ReceiptState::Prepared,
            ReceiptReason::None,
            10000
        ),
        Err(PrepareError::InvalidProposal)
    );
    assert_eq!(
        handoff::prepare_receipt(
            &snapshot(),
            &original,
            &"3".repeat(32),
            ReceiptState::Unknown,
            ReceiptReason::None,
            10000
        ),
        Err(PrepareError::InvalidProposal)
    );
}

#[test]
fn prepared_receipt_cannot_resurrect_expired_or_stale_proposal() {
    let original = example("valid_context");
    let mut view = snapshot();
    view.checked_at_ms = 50000;
    view.expires_at_ms = 80000;
    assert_eq!(
        handoff::prepare_receipt(
            &view,
            &original,
            &"3".repeat(32),
            ReceiptState::Prepared,
            ReceiptReason::None,
            50000
        ),
        Err(PrepareError::InvalidProposal)
    );
    let rejected = handoff::prepare_receipt(
        &view,
        &original,
        &"3".repeat(32),
        ReceiptState::Rejected,
        ReceiptReason::Expired,
        50000,
    )
    .unwrap();
    assert!(handoff::receipt_matches(&rejected, &original, 50000));
    view = snapshot();
    view.payload = ReadPayload::ObjectStatus {
        reference: first_reference(),
        state: ObjectState::Stale,
        navigation: NavigationState::Unavailable,
    };
    assert_eq!(
        handoff::prepare_receipt(
            &view,
            &original,
            &"3".repeat(32),
            ReceiptState::Prepared,
            ReceiptReason::None,
            10000
        ),
        Err(PrepareError::ReferenceNotCurrent)
    );
    let unknown = handoff::prepare_receipt(
        &view,
        &original,
        &"3".repeat(32),
        ReceiptState::Unknown,
        ReceiptReason::Unobserved,
        10000,
    )
    .unwrap();
    assert!(matches!(
        unknown.payload,
        Payload::Receipt {
            state: ReceiptState::Unknown,
            ..
        }
    ));
}

#[test]
fn receipt_fingerprint_rejects_same_key_kind_with_changed_payload() {
    let original = example("valid_context");
    let receipt = handoff::prepare_receipt(
        &snapshot(),
        &original,
        &"3".repeat(32),
        ReceiptState::Prepared,
        ReceiptReason::None,
        10000,
    )
    .unwrap();
    let mut conflicting = original.clone();
    if let Payload::Context { purpose, .. } = &mut conflicting.payload {
        *purpose = archeaxis_contracts::project_handoff::ContextPurpose::Research;
    }
    assert_eq!(
        handoff::classify_retry(&original, &conflicting),
        Ok(RetryClass::Conflict)
    );
    assert_ne!(
        handoff::proposal_fingerprint(&original).unwrap(),
        handoff::proposal_fingerprint(&conflicting).unwrap()
    );
    assert!(
        !handoff::receipt_matches(&receipt, &conflicting, 10000),
        "key/kind-only receipt incorrectly matched conflicting proposal contents"
    );
    assert!(handoff::receipt_matches(&receipt, &original, 10000));
}
