//! Slide narration and focus actions: Core captures the donor slide-action
//! prompt over the normalized slide, replays the declared local model text
//! through the same branch and admits only inert speech, spotlight and laser
//! actions. Nothing is executed or rendered; every other named verb is refused.
use crate::document::Error;
use crate::openmaic_quiz::{bounded_text, hex_digest, token};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::HashSet;

pub const OPENMAIC_SLIDE_ACTIONS_PROMPT_SCHEMA: &str = "archeaxis.openmaic-slide-actions-prompt/v1";
pub const OPENMAIC_SLIDE_ACTIONS_PROMPT_RESULT_SCHEMA: &str =
    "archeaxis.openmaic-slide-actions-prompt-result/v1";
pub const OPENMAIC_SLIDE_ACTIONS_PROMPT_BINDING_SCHEMA: &str =
    "archeaxis.openmaic-slide-actions-prompt-binding/v1";
pub const OPENMAIC_SLIDE_ACTIONS_RECORD_SCHEMA: &str = "archeaxis.openmaic-slide-actions-record/v1";
pub const OPENMAIC_SLIDE_ACTIONS_GENERATION_ROUTE: &str = "outline_slide_actions_local_model";
/// The donor reply budget the Node adapter accepts.
const MAX_REPLY_BYTES: usize = 120_000;
/// The scene builder accepts up to 100 actions; the prompt asks for 5-10.
const MAX_ACTIONS: usize = 30;
const MAX_ACTION_TEXT: usize = 8_000;
const BINDING_FIELDS: [&str; 11] = [
    "schema",
    "request_id",
    "input_sha256",
    "outline_manifest_sha256",
    "scene_actions_manifest_sha256",
    "npm_members_sha256",
    "worker_sha256",
    "system",
    "user",
    "system_sha256",
    "user_sha256",
];
const BINDING_HASHES: [&str; 7] = [
    "input_sha256",
    "outline_manifest_sha256",
    "scene_actions_manifest_sha256",
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

/// The bounded slide-action prompt receives the **normalized** slide so every
/// focus target it can name is a real mounted element.
fn action_content(normalized: &Value) -> Result<Value, Error> {
    let elements = normalized["content"]["canvas"]["elements"]
        .as_array()
        .filter(|items| (1..=200).contains(&items.len()))
        .ok_or(invalid("SLIDE_ACTIONS_ELEMENTS_OUT_OF_BOUNDS"))?;
    let mut seen = HashSet::new();
    for element in elements {
        if !element.is_object()
            || !token(element["id"].as_str().unwrap_or(""))
            || !element["type"]
                .as_str()
                .is_some_and(|kind| !kind.trim().is_empty() && kind.len() <= 32)
            || !seen.insert(element["id"].as_str().unwrap_or("").to_owned())
        {
            return Err(invalid("SLIDE_ACTIONS_ELEMENTS_UNSUPPORTED"));
        }
    }
    let mut content = json!({"elements":elements});
    if let Some(background) = normalized["content"]["canvas"].get("background") {
        if background.is_object() {
            content["background"] = background.clone();
        }
    }
    Ok(content)
}

fn slide_outline(selection: &Value) -> Result<Value, Error> {
    let outline = &selection["outline"];
    if outline["type"].as_str() != Some("slide") || !token(outline["id"].as_str().unwrap_or("")) {
        return Err(invalid("UNSUPPORTED_OUTLINE_TYPE"));
    }
    let title = outline["title"]
        .as_str()
        .filter(|value| !value.trim().is_empty() && value.chars().count() <= 240)
        .ok_or(invalid("OUTLINE_TITLE_OUT_OF_PROMPT_BOUNDS"))?;
    let description = outline["description"]
        .as_str()
        .filter(|value| value.chars().count() <= 16_000)
        .ok_or(invalid("OUTLINE_DESCRIPTION_OUT_OF_PROMPT_BOUNDS"))?;
    let key_points = outline["keyPoints"]
        .as_array()
        .filter(|points| {
            points.len() <= 200 && points.iter().all(|point| bounded_text(point, 2_000))
        })
        .ok_or(invalid("OUTLINE_KEY_POINTS_OUT_OF_PROMPT_BOUNDS"))?;
    let order = outline["order"]
        .as_u64()
        .ok_or(invalid("OUTLINE_ORDER_OUT_OF_PROMPT_BOUNDS"))?;
    Ok(json!({"id":outline["id"],"type":"slide","title":title,
        "description":description,"keyPoints":key_points,"order":order}))
}

fn language_directive(selection: &Value) -> Result<String, Error> {
    let directive = selection["language_directive"].as_str().unwrap_or("");
    if directive.chars().count() > 2_000 || directive.contains('\0') {
        return Err(invalid("OUTLINE_LANGUAGE_DIRECTIVE_OUT_OF_BOUNDS"));
    }
    Ok(directive.to_owned())
}

fn binding_shape(binding: &Value, create_request_id: &str) -> bool {
    binding.as_object().is_some_and(|object| {
        object.len() == BINDING_FIELDS.len()
            && BINDING_FIELDS.iter().all(|key| object.contains_key(*key))
            && binding["schema"] == OPENMAIC_SLIDE_ACTIONS_PROMPT_BINDING_SCHEMA
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

/// The capture frame: the slide outline, the normalized elements and the
/// language directive. It carries no reply, so only a binding can come back.
pub fn openmaic_slide_actions_capture_request(
    create_request_id: &str,
    selection: &Value,
    normalized: &Value,
) -> Result<Value, Error> {
    if !token(create_request_id) {
        return Err(invalid("OUTLINE_DOCUMENT_ID_INVALID"));
    }
    let outline = slide_outline(selection)?;
    let content = action_content(normalized)?;
    let language_directive = language_directive(selection)?;
    Ok(
        json!({"schema":OPENMAIC_SLIDE_ACTIONS_PROMPT_SCHEMA,"stage":"capture",
        "request_id":create_request_id,"outline":outline,"content":content,
        "language_directive":language_directive}),
    )
}

/// The prompt binding a `PROMPT_CAPTURED` result carries, or a named refusal.
pub fn openmaic_slide_actions_capture_binding(
    create_request_id: &str,
    capture: &Value,
) -> Result<Value, Error> {
    if capture["schema"] != OPENMAIC_SLIDE_ACTIONS_PROMPT_RESULT_SCHEMA
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
        return Err(invalid("SLIDE_ACTIONS_PROMPT_RECEIPT_INVALID"));
    }
    if !binding_shape(&capture["binding"], create_request_id) {
        return Err(invalid("SLIDE_ACTIONS_PROMPT_BINDING_UNSUPPORTED"));
    }
    Ok(capture["binding"].clone())
}

/// The prompt binding without the prompt text, as stored beside the candidate.
pub fn openmaic_slide_actions_prompt_record(binding: &Value) -> Value {
    let bytes = |key: &str| {
        binding[key]
            .as_str()
            .map(|text| text.as_bytes().len())
            .map_or(Value::Null, |len| json!(len))
    };
    json!({
        "schema":OPENMAIC_SLIDE_ACTIONS_PROMPT_BINDING_SCHEMA,
        "request_id":binding["request_id"],
        "input_sha256":binding["input_sha256"],
        "outline_manifest_sha256":binding["outline_manifest_sha256"],
        "scene_actions_manifest_sha256":binding["scene_actions_manifest_sha256"],
        "npm_members_sha256":binding["npm_members_sha256"],
        "worker_sha256":binding["worker_sha256"],
        "system_sha256":binding["system_sha256"],
        "user_sha256":binding["user_sha256"],
        "system_bytes":bytes("system"),
        "user_bytes":bytes("user"),
    })
}

/// The replay frame: the captured binding plus the model's final text.
pub fn openmaic_slide_actions_replay_request(
    create_request_id: &str,
    selection: &Value,
    normalized: &Value,
    binding: &Value,
    content: &str,
) -> Result<Value, Error> {
    if !binding_shape(binding, create_request_id) {
        return Err(invalid("SLIDE_ACTIONS_PROMPT_BINDING_UNSUPPORTED"));
    }
    if content.as_bytes().len() > MAX_REPLY_BYTES {
        return Err(invalid("MODEL_REPLY_EXCEEDS_BOUND"));
    }
    let outline = slide_outline(selection)?;
    let content_frame = action_content(normalized)?;
    let language_directive = language_directive(selection)?;
    Ok(
        json!({"schema":OPENMAIC_SLIDE_ACTIONS_PROMPT_SCHEMA,"stage":"replay",
        "request_id":create_request_id,"outline":outline,"content":content_frame,
        "language_directive":language_directive,"binding":binding,
        "reply":{"kind":"caller_supplied","value":content}}),
    )
}

/// The admitted inert actions, or `Ok(None)` for the worker's named refusal.
/// `element_ids` are the real mounted element ids a focus action may name.
pub fn openmaic_slide_actions_candidate(
    replay: &Value,
    element_ids: &HashSet<String>,
) -> Result<Option<Value>, Error> {
    if replay["schema"] != OPENMAIC_SLIDE_ACTIONS_PROMPT_RESULT_SCHEMA {
        return Err(invalid("SLIDE_ACTIONS_REPLAY_RECEIPT_INVALID"));
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
        return Err(invalid("SLIDE_ACTIONS_REPLAY_RECEIPT_INVALID"));
    }
    let actions = replay["data"]["actions"]
        .as_array()
        .filter(|items| (1..=MAX_ACTIONS).contains(&items.len()))
        .ok_or(invalid("SLIDE_ACTIONS_REPLAY_ACTIONS_INVALID"))?;
    let mut ids = HashSet::new();
    for action in actions {
        if !action.is_object()
            || !token(action["id"].as_str().unwrap_or(""))
            || !ids.insert(action["id"].as_str().unwrap_or("").to_owned())
        {
            return Err(invalid("SLIDE_ACTIONS_REPLAY_ACTIONS_INVALID"));
        }
        let shaped = action.as_object().is_some_and(|object| {
            object.len() == 3
                && object.contains_key("id")
                && object.contains_key("type")
                && match action["type"].as_str() {
                    Some("speech") => {
                        object.contains_key("text")
                            && bounded_text(&action["text"], MAX_ACTION_TEXT)
                    }
                    Some("spotlight" | "laser") => {
                        object.contains_key("elementId")
                            && token(action["elementId"].as_str().unwrap_or(""))
                            && element_ids.contains(action["elementId"].as_str().unwrap_or(""))
                    }
                    _ => false,
                }
        });
        if !shaped {
            return Err(invalid("SLIDE_ACTIONS_REPLAY_ACTIONS_INVALID"));
        }
    }
    Ok(Some(json!({"actions":actions})))
}

/// The Core-derived stage record stored beside the scene chain. `binding` and
/// `replay` are present only for a stage that actually ran; `action_count` is
/// the number of admitted actions (zero for every refusal).
pub fn openmaic_slide_actions_stage(
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
        "schema":OPENMAIC_SLIDE_ACTIONS_RECORD_SCHEMA,
        "status":status,
        "reason":reason,
        "generation_route":OPENMAIC_SLIDE_ACTIONS_GENERATION_ROUTE,
        "prompt_binding":binding.map(openmaic_slide_actions_prompt_record).unwrap_or(Value::Null),
        "replay":replay_record.unwrap_or(Value::Null),
        "action_count":action_count,
        "action_execution":"NOT_PERFORMED",
        "rendering_authorized":false,
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
            "outline":{"id":"o1","type":"slide","title":"Slide","description":"Body",
                "keyPoints":["One"],"order":1},
            "language_directive":"Use Chinese."})
    }

    fn normalized() -> Value {
        json!({"content":{"canvas":{"id":"canvas_1","viewportSize":1000,
            "elements":[{"id":"text_1","type":"text","content":"Point"},
                {"id":"image_1","type":"image"}],
            "background":{"type":"solid","color":"#ffffff"}}}})
    }

    fn binding() -> Value {
        let system = "SYSTEM prompt";
        let user = "USER prompt";
        json!({"schema":OPENMAIC_SLIDE_ACTIONS_PROMPT_BINDING_SCHEMA,"request_id":"req_1",
            "input_sha256":digest(b"identity"),
            "outline_manifest_sha256":digest(b"outline"),
            "scene_actions_manifest_sha256":digest(b"scene"),
            "npm_members_sha256":digest(b"npm"),
            "worker_sha256":digest(b"worker"),
            "system":system,"user":user,
            "system_sha256":digest(system.as_bytes()),"user_sha256":digest(user.as_bytes())})
    }

    fn candidate(actions: Value) -> Value {
        json!({"schema":OPENMAIC_SLIDE_ACTIONS_PROMPT_RESULT_SCHEMA,"status":"CANDIDATE",
            "reason":null,"request_id":"req_1","stage":"replay",
            "response_origin":"CALLER_SUPPLIED_UNVERIFIED","model_call":"NOT_INVOKED",
            "network_performed":false,"core_task":"NOT_CONNECTED",
            "core_authorization":"NOT_ESTABLISHED","canonical_bindings_verified":false,
            "persisted":false,"active_content_executed":false,"rendering_authorized":false,
            "action_execution":"NOT_PERFORMED","human_review_required":true,
            "callback_count":1,"exact_json_output":true,
            "transformations":["UNSTABLE_GENERATED_ACTION_IDS"],
            "data":{"actions":actions}})
    }

    fn element_ids() -> HashSet<String> {
        HashSet::from(["text_1".to_owned(), "image_1".to_owned()])
    }

    #[test]
    fn a_capture_frame_carries_the_normalized_elements() {
        let frame =
            openmaic_slide_actions_capture_request("req_1", &selection(), &normalized()).unwrap();
        assert_eq!(frame["stage"], "capture");
        assert_eq!(frame["outline"]["type"], "slide");
        assert_eq!(frame["content"]["elements"][0]["id"], "text_1");
        assert_eq!(frame["content"]["background"]["color"], "#ffffff");
        assert!(frame.get("reply").is_none());
    }

    #[test]
    fn only_speech_and_focus_actions_that_name_real_elements_are_admitted() {
        let admitted = openmaic_slide_actions_candidate(
            &candidate(json!([
                {"id":"a1","type":"spotlight","elementId":"text_1"},
                {"id":"a2","type":"speech","text":"Opening"},
                {"id":"a3","type":"laser","elementId":"image_1"}])),
            &element_ids(),
        )
        .unwrap()
        .unwrap();
        assert_eq!(admitted["actions"].as_array().unwrap().len(), 3);
        // A focus target that is not a real element is refused.
        assert!(
            openmaic_slide_actions_candidate(
                &candidate(json!([{"id":"a1","type":"spotlight","elementId":"missing_9"}])),
                &element_ids()
            )
            .is_err()
        );
        // Every other named verb is refused by name.
        assert!(
            openmaic_slide_actions_candidate(
                &candidate(json!([{"id":"a1","type":"play_video","elementId":"image_1"}])),
                &element_ids()
            )
            .is_err()
        );
        assert!(
            openmaic_slide_actions_candidate(
                &candidate(json!([{"id":"a1","type":"discussion","topic":"Talk"}])),
                &element_ids()
            )
            .is_err()
        );
    }

    #[test]
    fn the_stage_record_names_what_ran_without_copying_prompt_text() {
        let stage = openmaic_slide_actions_stage(
            "CANDIDATE",
            &Value::Null,
            Some(&binding()),
            Some(&candidate(
                json!([{"id":"a1","type":"speech","text":"Opening"}]),
            )),
            1,
            true,
        );
        assert_eq!(stage["schema"], OPENMAIC_SLIDE_ACTIONS_RECORD_SCHEMA);
        assert_eq!(stage["action_count"], 1);
        assert!(stage["prompt_binding"].get("system").is_none());
        assert_eq!(stage["action_execution"], "NOT_PERFORMED");
        let refused = openmaic_slide_actions_stage(
            "NOT_ADMITTED",
            &json!("NO_MODEL_REPLY"),
            None,
            None,
            0,
            false,
        );
        assert_eq!(refused["action_count"], 0);
        assert_eq!(refused["model_call"], "NOT_INVOKED");
    }
}
