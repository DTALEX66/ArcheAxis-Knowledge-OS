use archeaxis_domain::readiness::*;
#[test]
fn registration_never_implies_connection_or_qualification() {
    let o = observe("machine.answer".into(), true, true, Some(true), 100);
    assert_eq!(o.status, Status::Unverified);
    assert_eq!(o.connection, "UNKNOWN");
    assert_eq!(o.qualification, "UNVERIFIED");
    let s = snapshot("current-view".into(), 50, vec![o]);
    assert_eq!(s.aggregate, Status::Unverified);
    assert!(!s.execution_authorized);
    assert!(!s.models_loaded);
    assert!(!s.network_performed);
}
#[test]
fn one_ready_child_cannot_make_unknown_or_expired_parent_ready() {
    let mut ready = observe("one".into(), true, true, Some(true), 100);
    ready.status = Status::Ready;
    let unknown = observe("two".into(), true, true, None, 100);
    assert_eq!(aggregate(&[ready.clone(), unknown], 50), Status::Unknown);
    assert_eq!(aggregate(&[ready.clone()], 100), Status::Expired);
    let missing = observe("three".into(), false, false, Some(true), 100);
    assert_eq!(aggregate(&[ready, missing], 50), Status::NotReady);
    assert_eq!(aggregate(&[], 50), Status::Unknown);
}
