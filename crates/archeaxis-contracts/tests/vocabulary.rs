use serde_json::Value;

#[test]
fn shared_wire_cases_are_parsed_by_the_production_binding() {
    let cases: Vec<Value> = serde_json::from_str(include_str!("../../../tests/contract/fixtures/vocabulary-cases.json")).unwrap();
    for case in cases {
        let result = match (case["category"].as_str(), case["value"].as_str()) {
            (Some(category), Some(value)) => archeaxis_contracts::parse_value(category, value).is_ok(),
            _ => false,
        };
        assert_eq!(result, case["valid"].as_bool().unwrap(), "{case}");
    }
}
