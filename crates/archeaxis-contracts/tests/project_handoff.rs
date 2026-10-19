use archeaxis_contracts::project_handoff::Handoff;
use serde_json::Value;
fn cases() -> Vec<Value> {
    serde_json::from_str(include_str!(
        "../../../packages/contracts/v2/project-handoff.cases.json"
    ))
    .unwrap()
}
#[test]
fn shared_cases_use_real_strict_dto_and_semantic_validation() {
    let cases = cases();
    assert_eq!(cases.len(), 67);
    for case in &cases {
        let actual = serde_json::from_value::<Handoff>(case["value"].clone())
            .is_ok_and(|v| v.valid(case["now_ms"].as_u64().unwrap()));
        assert_eq!(
            actual,
            case["runtime_valid"].as_bool().unwrap(),
            "{}",
            case["name"]
        );
    }
    eprintln!("shared handoff DTO cases={}", cases.len());
}
