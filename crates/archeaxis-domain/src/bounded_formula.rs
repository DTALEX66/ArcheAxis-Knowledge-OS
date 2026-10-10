//! Core-only, pure scalar formulas. No source code, IO, clocks or providers.
use serde::Deserialize;
use serde_json::{Number, Value};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
pub enum Formula {
    Literal {
        value: Value,
    },
    Property {
        key: String,
    },
    Add {
        left: Box<Formula>,
        right: Box<Formula>,
    },
    Subtract {
        left: Box<Formula>,
        right: Box<Formula>,
    },
    Multiply {
        left: Box<Formula>,
        right: Box<Formula>,
    },
    Divide {
        left: Box<Formula>,
        right: Box<Formula>,
    },
    Concat {
        left: Box<Formula>,
        right: Box<Formula>,
    },
    Equal {
        left: Box<Formula>,
        right: Box<Formula>,
    },
    If {
        condition: Box<Formula>,
        then: Box<Formula>,
        otherwise: Box<Formula>,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FormulaError {
    Limit,
    InvalidScalar,
    InvalidKey,
    MissingProperty(String),
    Type,
    DivisionByZero,
    NonFinite,
    NumberRange,
}
impl std::fmt::Display for FormulaError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for FormulaError {}

fn scalar(value: &Value) -> Result<(), FormulaError> {
    match value {
        Value::Array(_) | Value::Object(_) => Err(FormulaError::InvalidScalar),
        Value::String(s) if s.len() > 16_384 => Err(FormulaError::Limit),
        Value::Number(n)
            if n.as_i64()
                .is_some_and(|v| v.unsigned_abs() > 9_007_199_254_740_991)
                || n.as_u64().is_some_and(|v| v > 9_007_199_254_740_991) =>
        {
            Err(FormulaError::NumberRange)
        }
        Value::Number(n) if !n.as_f64().is_some_and(f64::is_finite) => Err(FormulaError::NonFinite),
        _ => Ok(()),
    }
}
fn key_valid(key: &str) -> bool {
    !key.is_empty()
        && key.len() <= 128
        && key
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-' | b'.'))
}

/// Validate every branch before evaluation, including a branch not selected by If.
pub fn validate(formula: &Formula) -> Result<(), FormulaError> {
    fn visit(f: &Formula, depth: usize, count: &mut usize) -> Result<(), FormulaError> {
        *count += 1;
        if depth > 16 || *count > 256 {
            return Err(FormulaError::Limit);
        }
        match f {
            Formula::Literal { value } => scalar(value),
            Formula::Property { key } => {
                if key_valid(key) {
                    Ok(())
                } else {
                    Err(FormulaError::InvalidKey)
                }
            }
            Formula::If {
                condition,
                then,
                otherwise,
            } => {
                visit(condition, depth + 1, count)?;
                visit(then, depth + 1, count)?;
                visit(otherwise, depth + 1, count)
            }
            Formula::Add { left, right }
            | Formula::Subtract { left, right }
            | Formula::Multiply { left, right }
            | Formula::Divide { left, right }
            | Formula::Concat { left, right }
            | Formula::Equal { left, right } => {
                visit(left, depth + 1, count)?;
                visit(right, depth + 1, count)
            }
        }
    }
    visit(formula, 0, &mut 0)
}

pub fn evaluate(
    formula: &Formula,
    properties: &BTreeMap<String, Value>,
) -> Result<Value, FormulaError> {
    validate(formula)?;
    fn run(f: &Formula, p: &BTreeMap<String, Value>) -> Result<Value, FormulaError> {
        match f {
            Formula::Literal { value } => Ok(value.clone()),
            Formula::Property { key } => {
                let value = p
                    .get(key)
                    .ok_or_else(|| FormulaError::MissingProperty(key.clone()))?;
                scalar(value)?;
                Ok(value.clone())
            }
            Formula::If {
                condition,
                then,
                otherwise,
            } => {
                let condition = run(condition, p)?.as_bool().ok_or(FormulaError::Type)?;
                run(if condition { then } else { otherwise }, p)
            }
            Formula::Concat { left, right } => {
                let a = run(left, p)?;
                let b = run(right, p)?;
                let a = a.as_str().ok_or(FormulaError::Type)?;
                let b = b.as_str().ok_or(FormulaError::Type)?;
                if a.len() + b.len() > 16_384 {
                    return Err(FormulaError::Limit);
                }
                Ok(Value::String(format!("{a}{b}")))
            }
            Formula::Equal { left, right } => Ok(Value::Bool(run(left, p)? == run(right, p)?)),
            Formula::Add { left, right }
            | Formula::Subtract { left, right }
            | Formula::Multiply { left, right }
            | Formula::Divide { left, right } => {
                let a = run(left, p)?.as_f64().ok_or(FormulaError::Type)?;
                let b = run(right, p)?.as_f64().ok_or(FormulaError::Type)?;
                if matches!(f, Formula::Divide { .. }) && b == 0.0 {
                    return Err(FormulaError::DivisionByZero);
                }
                let result = match f {
                    Formula::Add { .. } => a + b,
                    Formula::Subtract { .. } => a - b,
                    Formula::Multiply { .. } => a * b,
                    Formula::Divide { .. } => a / b,
                    _ => unreachable!(),
                };
                Number::from_f64(result)
                    .map(Value::Number)
                    .ok_or(FormulaError::NonFinite)
            }
        }
    }
    run(formula, properties)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    fn eval(ast: Value, properties: BTreeMap<String, Value>) -> Result<Value, FormulaError> {
        evaluate(&serde_json::from_value(ast).unwrap(), &properties)
    }
    #[test]
    fn computes_without_mutating_scalar_inputs() {
        let p = BTreeMap::from([
            ("amount".into(), json!(12)),
            ("name".into(), json!("研究😀")),
        ]);
        let before = p.clone();
        assert_eq!(eval(json!({"op":"multiply","left":{"op":"property","key":"amount"},"right":{"op":"literal","value":2}}),p.clone()).unwrap(),json!(24.0));
        assert_eq!(eval(json!({"op":"concat","left":{"op":"property","key":"name"},"right":{"op":"literal","value":" 原文"}}),p.clone()).unwrap(),json!("研究😀 原文"));
        assert_eq!(p, before);
    }
    #[test]
    fn errors_are_not_null_or_success() {
        let divide = json!({"op":"divide","left":{"op":"literal","value":1},"right":{"op":"literal","value":0}});
        assert_eq!(
            eval(divide, BTreeMap::new()),
            Err(FormulaError::DivisionByZero)
        );
        assert_eq!(
            eval(json!({"op":"property","key":"absent"}), BTreeMap::new()),
            Err(FormulaError::MissingProperty("absent".into()))
        );
        assert_eq!(
            eval(json!({"op":"literal","value":{}}), BTreeMap::new()),
            Err(FormulaError::InvalidScalar)
        );
        assert_eq!(
            eval(
                json!({"op":"add","left":{"op":"literal","value":"1"},"right":{"op":"literal","value":2}}),
                BTreeMap::new()
            ),
            Err(FormulaError::Type)
        );
        assert_eq!(
            eval(
                json!({"op":"multiply","left":{"op":"literal","value":1e308},"right":{"op":"literal","value":1e308}}),
                BTreeMap::new()
            ),
            Err(FormulaError::NonFinite)
        );
    }
    #[test]
    fn scripts_unknown_fields_and_ops_rejected() {
        for ast in [
            json!({"op":"eval","code":"fetch(secret)"}),
            json!({"op":"literal","value":1,"code":"execute"}),
        ] {
            assert!(serde_json::from_value::<Formula>(ast).is_err());
        }
    }
    #[test]
    fn bounds_cover_unselected_branches_and_utf8() {
        let mut too_deep = Formula::Literal { value: json!(0) };
        for _ in 0..17 {
            too_deep = Formula::Add {
                left: Box::new(too_deep),
                right: Box::new(Formula::Literal { value: json!(0) }),
            };
        }
        assert_eq!(validate(&too_deep), Err(FormulaError::Limit));
        let f = Formula::If {
            condition: Box::new(Formula::Literal { value: json!(true) }),
            then: Box::new(Formula::Literal { value: json!("ok") }),
            otherwise: Box::new(Formula::Literal {
                value: json!("中".repeat(5462)),
            }),
        };
        assert_eq!(evaluate(&f, &BTreeMap::new()), Err(FormulaError::Limit));
        assert_eq!(
            eval(
                json!({"op":"property","key":"../../secret"}),
                BTreeMap::new()
            ),
            Err(FormulaError::InvalidKey)
        );
    }
    #[test]
    fn conditional_evaluates_only_selected_valid_branch() {
        assert_eq!(eval(json!({"op":"if","condition":{"op":"literal","value":true},"then":{"op":"literal","value":false},"otherwise":{"op":"property","key":"missing"}}),BTreeMap::new()).unwrap(),json!(false));
    }
    #[test]
    fn rejects_integer_precision_loss_and_wide_ast() {
        assert_eq!(
            eval(
                json!({"op":"literal","value":9_007_199_254_740_993_u64}),
                BTreeMap::new()
            ),
            Err(FormulaError::NumberRange)
        );
        fn tree(depth: usize) -> Formula {
            if depth == 0 {
                Formula::Literal { value: json!(0) }
            } else {
                Formula::Add {
                    left: Box::new(tree(depth - 1)),
                    right: Box::new(tree(depth - 1)),
                }
            }
        }
        assert_eq!(validate(&tree(8)), Err(FormulaError::Limit));
        assert!(validate(&tree(7)).is_ok());
    }
}
