use archeaxis_sidecar_protocol::worker::{Request, decode_hello, decode_response};
use serde_json::{Value, json};

fn request() -> Request {
    Request::text("request-1", "job-1", 2, &"a".repeat(64), "text/plain", 5000).unwrap()
}
fn hello() -> Value {
    json!({"schema":"archeaxis.worker-hello/v1","type":"hello",
        "protocol":{"major":1,"min_minor":0,"max_minor":0},
        "worker":{"name":"python-worker-text","version":"0.1.0"},
        "capabilities":["text.extract"],
        "schemas":["archeaxis.text/v1","archeaxis.document-structure/v1","archeaxis.loss-receipt/v1"]})
}
fn response() -> Value {
    let outputs: Vec<Value> = [ ("text", "archeaxis.text/v1", "text/plain; charset=utf-8"),
        ("document_structure", "archeaxis.document-structure/v1", "application/json"),
        ("loss_report", "archeaxis.loss-receipt/v1", "application/json") ].into_iter().map(|(kind,schema,media)|
        json!({"kind":kind,"uri":format!("job://output/{}", "b".repeat(64)),"sha256":"b".repeat(64),
            "media_type":media,"byte_length":12,"schema":schema,"authority_effect":"candidate_or_measurement_only"})
    ).collect();
    json!({"schema":"archeaxis.worker-response/v1","type":"job_result","request_id":"request-1",
        "job_id":"job-1","attempt":2,"protocol_minor":0,"status":"succeeded", "outputs":outputs,
        "measurements":{},"warnings":[],"error":null})
}

#[test]
fn handshake_requires_supported_versions_and_actual_text_capability() {
    assert!(decode_hello(&hello().to_string()).is_ok());
    for pointer in ["/protocol/major", "/protocol/min_minor"] {
        let mut frame=hello(); *frame.pointer_mut(pointer).unwrap()=json!(9);
        assert!(decode_hello(&frame.to_string()).is_err(), "{pointer}");
    }
    for field in ["capabilities", "schemas"] {
        let mut frame=hello(); frame[field]=json!([]);
        assert!(decode_hello(&frame.to_string()).is_err(), "{field}");
    }
    let mut frame=hello(); frame["protocol"]["unknown"]=json!(true);
    assert!(decode_hello(&frame.to_string()).is_err());
}

#[test]
fn result_identity_and_full_output_set_cannot_be_forged_or_dropped() {
    let req=request();
    let decoded=decode_response(&response().to_string(), &req).unwrap();
    assert_eq!(decoded.outputs.len(), 3);
    for (pointer,value) in [("/attempt",json!(1)),("/request_id",json!("other")),
        ("/job_id",json!("other")),("/protocol_minor",json!(1)),
        ("/outputs/0/uri",json!("job://output/../../outside")),
        ("/outputs/0/sha256",json!("a".repeat(64))),
        ("/outputs/0/authority_effect",json!("accepted")),
        ("/outputs/0/schema",json!("archeaxis.text/v2")),
        ("/outputs/0/byte_length",json!(-1)),
        ("/error",json!({"code":"X","message":"bad","retryable":false}))] {
        let mut frame=response(); *frame.pointer_mut(pointer).unwrap()=value;
        assert!(decode_response(&frame.to_string(),&req).is_err(), "{pointer}");
    }
    let mut frame=response(); frame["outputs"].as_array_mut().unwrap().pop();
    assert!(decode_response(&frame.to_string(),&req).is_err());
    frame=response(); frame["outputs"][1]=frame["outputs"][0].clone();
    assert!(decode_response(&frame.to_string(),&req).is_err());
    frame=response(); frame.as_object_mut().unwrap().remove("error");
    assert!(decode_response(&frame.to_string(),&req).is_err());
}

#[test]
fn errors_are_explicit_and_unknown_duplicate_or_oversized_frames_fail() {
    let req=request();
    let mut frame=response(); frame["status"]=json!("rejected"); frame["outputs"]=json!([]);
    frame["error"]=json!({"code":"AAK-VAL-001","message":"bad request","retryable":false});
    assert!(decode_response(&frame.to_string(),&req).is_ok());
    frame["error"]["retryable"]=json!(true);
    assert!(decode_response(&frame.to_string(),&req).is_err());
    frame=response(); frame["unknown"]=json!(0);
    assert!(decode_response(&frame.to_string(),&req).is_err());
    let text=response().to_string().replacen("{", "{\"attempt\":2,", 1);
    assert!(decode_response(&text,&req).is_err());
    assert!(decode_response(&" ".repeat(1024*1024+1),&req).is_err());
    assert!(Request::text("r","j",0,&"a".repeat(64),"text/plain",1).is_err());
    assert!(Request::text("r","j",1,"../path","text/plain",1).is_err());
}

#[test]
fn schema_integer_spellings_and_failed_terminal_shape_are_checked() {
    let hello=hello().to_string().replace("\"major\":1", "\"major\":1.0").replace("\"min_minor\":0", "\"min_minor\":0e0");
    assert!(decode_hello(&hello).is_ok());
    let req=request();
    let wire=response().to_string().replace("\"attempt\":2", "\"attempt\":2.0").replace("\"byte_length\":12", "\"byte_length\":12e0");
    assert!(decode_response(&wire,&req).is_ok());
    for value in [json!(1.5),json!(null),json!(9_007_199_254_740_992_u64)] {
        let mut frame=response(); frame["outputs"][0]["byte_length"]=value;
        assert!(decode_response(&frame.to_string(),&req).is_err());
    }
    let mut frame=response(); frame["status"]=json!("failed");
    assert!(decode_response(&frame.to_string(),&req).is_err());
    frame["error"]=json!({"code":"AAK-WORKER-003","message":"parser failed","retryable":true});
    assert!(decode_response(&frame.to_string(),&req).is_err());
    frame["outputs"]=json!([]);
    assert!(decode_response(&frame.to_string(),&req).is_ok());
}
