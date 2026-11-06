//! Quiz narration actions: Core captures the donor quiz-action prompt from the
//! original excerpt, replays the declared local model text through the same
//! branch and admits only inert speech actions. Nothing here executes, renders
//! or authorises an action; the admitted list travels beside the quiz candidate.
use crate::document::Error;
use crate::openmaic_quiz::{
    self, bounded_text, hex_digest, quiz_language_directive, quiz_question_shape, token,
};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::HashSet;

pub const OPENMAIC_QUIZ_ACTIONS_PROMPT_SCHEMA: &str = "archeaxis.openmaic-quiz-actions-prompt/v1";
pub const OPENMAIC_QUIZ_ACTIONS_PROMPT_RESULT_SCHEMA: &str =
    "archeaxis.openmaic-quiz-actions-prompt-result/v1";
pub const OPENMAIC_QUIZ_ACTIONS_PROMPT_BINDING_SCHEMA: &str =
    "archeaxis.openmaic-quiz-actions-prompt-binding/v1";
pub const OPENMAIC_QUIZ_ACTIONS_RECORD_SCHEMA: &str = "archeaxis.openmaic-quiz-actions-record/v1";
pub const OPENMAIC_QUIZ_ACTIONS_GENERATION_ROUTE: &str = "outline_quiz_actions_local_model";
/// The donor reply budget the Node adapter accepts.
const MAX_REPLY_BYTES: usize = 120_000;
/// The prompt template asks for one or two short segments; more is refused.
const MAX_ACTIONS: usize = 2;
const BINDING_FIELDS: [&str; 13] = [
    "schema",
    "request_id",
    "input_sha256",
    "outline_manifest_sha256",
    "quiz_manifest_sha256",
    "actions_manifest_sha256",
    "dsl_manifest_sha256",
    "npm_members_sha256",
    "worker_sha256",
    "system",
    "user",
    "system_sha256",
    "user_sha256",
];
const BINDING_HASHES: [&str; 9] = [
    "input_sha256",
    "outline_manifest_sha256",
    "quiz_manifest_sha256",
    "actions_manifest_sha256",
    "dsl_manifest_sha256",
    "npm_members_sha256",
    "worker_sha256",
    "system_sha256",
    "user_sha256",
];

fn invalid(reason: &'static str) -> Error {
    Error::Invalid(reason)
}

fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn sha_matches(text: &Value, expected: &Value) -> bool {
    text.as_str()
        .is_some_and(|text| expected.as_str() == Some(&digest(text.as_bytes())))
}

fn questions_list(questions: &Value) -> Result<&Vec<Value>, Error> {
    let list = questions["questions"]
        .as_array()
        .filter(|items| (1..=30).contains(&items.len()))
        .ok_or(invalid("QUIZ_ACTIONS_QUESTIONS_INVALID"))?;
    let mut ids = HashSet::new();
    for question in list {
        if !quiz_question_shape(question)
            || !ids.insert(question["id"].as_str().unwrap_or("").to_owned())
        {
            return Err(invalid("QUIZ_ACTIONS_QUESTIONS_INVALID"));
        }
    }
    Ok(list)
}

fn action_shape(action: &Value) -> bool {
    action.as_object().is_some_and(|object| {
        object.len() == 3
            && object.contains_key("id")
            && object.contains_key("type")
            && object.contains_key("text")
            && token(action["id"].as_str().unwrap_or(""))
            && action["type"].as_str() == Some("speech")
            && bounded_text(&action["text"], 8_000)
    })
}

fn binding_shape(binding: &Value, create_request_id: &str) -> bool {
    binding.as_object().is_some_and(|object| {
        object.len() == BINDING_FIELDS.len()
            && BINDING_FIELDS.iter().all(|key| object.contains_key(*key))
            && binding["schema"] == OPENMAIC_QUIZ_ACTIONS_PROMPT_BINDING_SCHEMA
            && binding["request_id"].as_str() == Some(create_request_id)
            && BINDING_HASHES.iter().all(|key| hex_digest(&binding[*key]))
            && binding["system"]
                .as_str()
                .is_some_and(|text| text.as_bytes().len() <= 200_000 && !text.contains('\0'))
            && binding["user"]
                .as_str()
                .is_some_and(|text| text.as_bytes().len() <= 200_000 && !text.contains('\0'))
            && sha_matches(&binding["system"], &binding["system_sha256"])
            && sha_matches(&binding["user"], &binding["user_sha256"])
    })
}

/// The capture frame: the bounded outline, the admitted question list and the
/// language directive. It carries no reply, so only a binding can come back.
pub fn openmaic_quiz_actions_capture_request(
    create_request_id: &str,
    selection: &Value,
    questions: &Value,
) -> Result<Value, Error> {
    if !token(create_request_id) {
        return Err(invalid("OUTLINE_DOCUMENT_ID_INVALID"));
    }
    questions_list(questions)?;
    let outline = openmaic_quiz::openmaic_quiz_outline(selection)?;
    let language_directive = quiz_language_directive(selection)?;
    Ok(
        json!({"schema":OPENMAIC_QUIZ_ACTIONS_PROMPT_SCHEMA,"stage":"capture",
        "request_id":create_request_id,"outline":outline,
        "content":{"questions":questions["questions"]},
        "language_directive":language_directive}),
    )
}

/// The prompt binding a `PROMPT_CAPTURED` result carries, or a named refusal.
pub fn openmaic_quiz_actions_capture_binding(
    create_request_id: &str,
    capture: &Value,
) -> Result<Value, Error> {
    if capture["schema"] != OPENMAIC_QUIZ_ACTIONS_PROMPT_RESULT_SCHEMA
        || capture["status"] != "PROMPT_CAPTURED"
        || capture["stage"] != "capture"
        || capture["request_id"].as_str() != Some(create_request_id)
        || capture["model_call"] != "NOT_INVOKED"
        || capture["network_performed"] != false
        || capture["core_task"] != "NOT_CONNECTED"
        || capture["core_authorization"] != "NOT_ESTABLISHED"
        || capture["canonical_bindings_verified"] != false
        || capture["persisted"] != false
        || capture["active_content_executed"] != false
        || capture["binding"].is_null()
    {
        return Err(invalid("QUIZ_ACTIONS_PROMPT_RECEIPT_INVALID"));
    }
    if !binding_shape(&capture["binding"], create_request_id) {
        return Err(invalid("QUIZ_ACTIONS_PROMPT_BINDING_UNSUPPORTED"));
    }
    Ok(capture["binding"].clone())
}

/// The prompt binding without the prompt text, as stored beside the candidate.
pub fn openmaic_quiz_actions_prompt_record(binding: &Value) -> Value {
    let bytes = |key: &str| {
        binding[key]
            .as_str()
            .map(|text| text.as_bytes().len())
            .map_or(Value::Null, |len| json!(len))
    };
    json!({
        "schema":OPENMAIC_QUIZ_ACTIONS_PROMPT_BINDING_SCHEMA,
        "request_id":binding["request_id"],
        "input_sha256":binding["input_sha256"],
        "outline_manifest_sha256":binding["outline_manifest_sha256"],
        "quiz_manifest_sha256":binding["quiz_manifest_sha256"],
        "actions_manifest_sha256":binding["actions_manifest_sha256"],
        "dsl_manifest_sha256":binding["dsl_manifest_sha256"],
        "npm_members_sha256":binding["npm_members_sha256"],
        "worker_sha256":binding["worker_sha256"],
        "system_sha256":binding["system_sha256"],
        "user_sha256":binding["user_sha256"],
        "system_bytes":bytes("system"),
        "user_bytes":bytes("user"),
    })
}

/// The replay frame: the captured binding plus the model's final text.
pub fn openmaic_quiz_actions_replay_request(
    create_request_id: &str,
    selection: &Value,
    questions: &Value,
    binding: &Value,
    content: &str,
) -> Result<Value, Error> {
    if !binding_shape(binding, create_request_id) {
        return Err(invalid("QUIZ_ACTIONS_PROMPT_BINDING_UNSUPPORTED"));
    }
    if content.as_bytes().len() > MAX_REPLY_BYTES {
        return Err(invalid("MODEL_REPLY_EXCEEDS_BOUND"));
    }
    questions_list(questions)?;
    let outline = openmaic_quiz::openmaic_quiz_outline(selection)?;
    let language_directive = quiz_language_directive(selection)?;
    Ok(
        json!({"schema":OPENMAIC_QUIZ_ACTIONS_PROMPT_SCHEMA,"stage":"replay",
        "request_id":create_request_id,"outline":outline,
        "content":{"questions":questions["questions"]},
        "language_directive":language_directive,"binding":binding,
        "reply":{"kind":"caller_supplied","value":content}}),
    )
}

/// The admitted inert speech actions, or `Ok(None)` for the worker's refusal.
pub fn openmaic_quiz_actions_candidate(replay: &Value) -> Result<Option<Value>, Error> {
    if replay["schema"] != OPENMAIC_QUIZ_ACTIONS_PROMPT_RESULT_SCHEMA {
        return Err(invalid("QUIZ_ACTIONS_REPLAY_RECEIPT_INVALID"));
    }
    if replay["status"] != "CANDIDATE" {
        return Ok(None);
    }
    if replay["stage"] != "replay"
        || replay["response_origin"] != "CALLER_SUPPLIED_UNVERIFIED"
        || replay["model_call"] != "NOT_INVOKED"
        || replay["network_performed"] != false
        || replay["core_task"] != "NOT_CONNECTED"
        || replay["core_authorization"] != "NOT_ESTABLISHED"
        || replay["canonical_bindings_verified"] != false
        || replay["persisted"] != false
        || replay["active_content_executed"] != false
        || replay["rendering_authorized"] != false
        || replay["action_execution"] != "NOT_PERFORMED"
        || replay["human_review_required"] != true
        || replay["data"].is_null()
    {
        return Err(invalid("QUIZ_ACTIONS_REPLAY_RECEIPT_INVALID"));
    }
    let actions = replay["data"]["actions"]
        .as_array()
        .filter(|items| (1..=MAX_ACTIONS).contains(&items.len()))
        .ok_or(invalid("QUIZ_ACTIONS_REPLAY_ACTIONS_INVALID"))?;
    let mut ids = HashSet::new();
    for action in actions {
        if !action_shape(action) || !ids.insert(action["id"].as_str().unwrap_or("").to_owned()) {
            return Err(invalid("QUIZ_ACTIONS_REPLAY_ACTIONS_INVALID"));
        }
    }
    Ok(Some(json!({"actions":actions})))
}

/// The Core-derived stage record stored beside the quiz chain. `binding` and
/// `replay` are present only for a stage that actually ran; `action_count` is
/// the number of admitted actions (zero for every refusal).
pub fn openmaic_quiz_actions_stage(
    status: &str,
    reason: &Value,
    binding: Option<&Value>,
    replay: Option<&Value>,
    action_count: usize,
    model_invoked: bool,
) -> Value {
    let replay_record = replay.map(|replay| {
        json!({
            "status":replay["status"],
            "reason":replay["reason"],
            "callback_count":replay["callback_count"],
            "exact_json_output":replay["exact_json_output"],
            "transformations":replay["transformations"],
        })
    });
    json!({
        "schema":OPENMAIC_QUIZ_ACTIONS_RECORD_SCHEMA,
        "status":status,
        "reason":reason,
        "generation_route":OPENMAIC_QUIZ_ACTIONS_GENERATION_ROUTE,
        "prompt_binding":binding.map(openmaic_quiz_actions_prompt_record).unwrap_or(Value::Null),
        "replay":replay_record.unwrap_or(Value::Null),
        "action_count":action_count,
        "action_execution":"NOT_PERFORMED",
        "rendering_authorized":false,
        "answer_non_disclosure_verified":false,
        "human_review_required":true,
        "model_call":if model_invoked { "INVOKED" } else { "NOT_INVOKED" },
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn selection() -> Value {
        json!({"document_id":"doc_req_1","version":1,"content_sha256":"0".repeat(64),
            "index":0,
            "outline":{"id":"o1","type":"quiz","title":"Quiz","description":"Body",
                "keyPoints":["One"],"order":1,
                "quizConfig":{"questionCount":1,"difficulty":"easy",
                    "questionTypes":["single"]}},
            "language_directive":"Use Chinese."})
    }

    fn questions() -> Value {
        json!({"questions":[{"id":"q1","type":"single","question":"Pick one",
            "options":[{"label":"Alpha","value":"A"},{"label":"Beta","value":"B"}],
            "answer":["A"],"hasAnswer":true}]})
    }

    fn binding() -> Value {
        let system = "SYSTEM prompt";
        let user = "USER prompt";
        json!({"schema":OPENMAIC_QUIZ_ACTIONS_PROMPT_BINDING_SCHEMA,"request_id":"req_1",
            "input_sha256":digest(b"identity"),
            "outline_manifest_sha256":digest(b"outline"),
            "quiz_manifest_sha256":digest(b"quiz"),
            "actions_manifest_sha256":digest(b"actions"),
            "dsl_manifest_sha256":digest(b"dsl"),
            "npm_members_sha256":digest(b"npm"),
            "worker_sha256":digest(b"worker"),
            "system":system,"user":user,
            "system_sha256":digest(system.as_bytes()),"user_sha256":digest(user.as_bytes())})
    }

    fn candidate() -> Value {
        json!({"schema":OPENMAIC_QUIZ_ACTIONS_PROMPT_RESULT_SCHEMA,"status":"CANDIDATE",
            "reason":null,"request_id":"req_1","stage":"replay",
            "response_origin":"CALLER_SUPPLIED_UNVERIFIED","model_call":"NOT_INVOKED",
            "network_performed":false,"core_task":"NOT_CONNECTED",
            "core_authorization":"NOT_ESTABLISHED","canonical_bindings_verified":false,
            "persisted":false,"active_content_executed":false,"rendering_authorized":false,
            "action_execution":"NOT_PERFORMED","human_review_required":true,
            "callback_count":1,"exact_json_output":true,
            "transformations":["UNSTABLE_GENERATED_ACTION_IDS"],
            "data":{"actions":[{"id":"action_1","type":"speech","text":"Opening"}]}})
    }

    #[test]
    fn a_capture_frame_carries_the_questions_but_no_reply() {
        let frame =
            openmaic_quiz_actions_capture_request("req_1", &selection(), &questions()).unwrap();
        assert_eq!(frame["stage"], "capture");
        assert_eq!(frame["content"]["questions"], questions()["questions"]);
        assert!(frame.get("reply").is_none());
        assert_eq!(frame["language_directive"], "Use Chinese.");
        // The answer key is still in the admitted question list; only the donor
        // prompt formatter's projection drops it, and that is the worker's view.
        assert_eq!(questions()["questions"][0]["answer"], json!(["A"]));
    }

    #[test]
    fn a_binding_with_a_wrong_schema_or_missing_field_is_refused() {
        let mut broken = binding();
        broken["source_manifest_sha256"] = broken["actions_manifest_sha256"].clone();
        assert!(
            openmaic_quiz_actions_replay_request("req_1", &selection(), &questions(), &broken, "x")
                .is_err()
        );
        let mut broken = binding();
        broken["system_sha256"] = json!("0".repeat(64));
        assert!(
            openmaic_quiz_actions_capture_binding(
                "req_1",
                &json!({
            "schema":OPENMAIC_QUIZ_ACTIONS_PROMPT_RESULT_SCHEMA,"status":"PROMPT_CAPTURED",
            "stage":"capture","request_id":"req_1","model_call":"NOT_INVOKED",
            "network_performed":false,"core_task":"NOT_CONNECTED",
            "core_authorization":"NOT_ESTABLISHED","canonical_bindings_verified":false,
            "persisted":false,"active_content_executed":false,"binding":broken})
            )
            .is_err()
        );
    }

    #[test]
    fn only_bounded_speech_actions_are_admitted() {
        let admitted = openmaic_quiz_actions_candidate(&candidate())
            .unwrap()
            .unwrap();
        assert_eq!(admitted["actions"][0]["type"], "speech");
        let mut unsupported = candidate();
        unsupported["data"]["actions"][0]["type"] = json!("discussion");
        assert!(openmaic_quiz_actions_candidate(&unsupported).is_err());
        let mut too_many = candidate();
        too_many["data"]["actions"] = json!([
            {"id":"a1","type":"speech","text":"one"},
            {"id":"a2","type":"speech","text":"two"},
            {"id":"a3","type":"speech","text":"three"}]);
        assert!(openmaic_quiz_actions_candidate(&too_many).is_err());
        let mut non_candidate = candidate();
        non_candidate["status"] = json!("UNSUPPORTED_OUTPUT");
        assert!(
            openmaic_quiz_actions_candidate(&non_candidate)
                .unwrap()
                .is_none()
        );
    }

    #[test]
    fn the_stage_record_names_what_ran_without_copying_prompt_text() {
        let stage = openmaic_quiz_actions_stage(
            "CANDIDATE",
            &Value::Null,
            Some(&binding()),
            Some(&candidate()),
            1,
            true,
        );
        assert_eq!(stage["schema"], OPENMAIC_QUIZ_ACTIONS_RECORD_SCHEMA);
        assert_eq!(stage["action_count"], 1);
        assert!(stage["prompt_binding"].get("system").is_none());
        assert_eq!(stage["prompt_binding"]["system_bytes"], 13);
        assert_eq!(stage["replay"]["status"], "CANDIDATE");
        assert_eq!(stage["action_execution"], "NOT_PERFORMED");
        let refused = openmaic_quiz_actions_stage(
            "NOT_ADMITTED",
            &json!("NO_MODEL_REPLY"),
            None,
            None,
            0,
            false,
        );
        assert_eq!(refused["action_count"], 0);
        assert_eq!(refused["model_call"], "NOT_INVOKED");
        assert!(refused["prompt_binding"].is_null());
    }
}
