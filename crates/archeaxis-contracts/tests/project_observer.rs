use archeaxis_contracts::project_observer::ReadResponse;
#[test]
fn shared_contract_cases_exercise_real_strict_deserializer_and_semantic_validation() {
    let cases: serde_json::Value = serde_json::from_str(include_str!(
        "../../../packages/contracts/v2/project-observer.cases.json"
    ))
    .unwrap();
    for case in cases.as_array().unwrap() {
        let result = serde_json::from_value::<ReadResponse>(case["value"].clone());
        let valid = result.is_ok_and(|response| response.valid(case["now_ms"].as_u64().unwrap()));
        assert_eq!(
            valid,
            case["runtime_valid"].as_bool().unwrap(),
            "{}",
            case["name"]
        );
    }
}
