//! 只对 owned loopback stub 注入恶意响应，核验实际 Rust HTTP adapter 拒绝能力。
use archeaxis_api::project_observer::{
    client::{ClientAdmission, ObserverClient, ReadError},
    now_ms,
};
use serde_json::{Value, json};
use std::{
    io::{Read, Write},
    net::{Ipv4Addr, TcpListener},
    time::{Duration, Instant},
};
fn valid_response() -> Value {
    let now = now_ms();
    json!({"schema":"archeaxis.project-observer-response/v1","protocol":"archeaxis.project-observer/v1","producer":{"namespace":"archeaxis","workspace_id":"a".repeat(32),"restore_epoch":"initial"},"consumer":{"namespace":"work-lab","instance_id":"b".repeat(32)},"checked_at_ms":now,"expires_at_ms":now+30_000,"payload":{"kind":"handshake","operations":["handshake","objects.read","object.status"],"authority":"REFERENCE_ONLY","grants_execution":false,"grants_knowledge_acceptance":false}})
}
fn roundtrip(body: &str, status: u16, extra: &str, length: usize) -> Result<(), ReadError> {
    let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0)).unwrap();
    let port = listener.local_addr().unwrap().port();
    listener.set_nonblocking(true).unwrap();
    let response = format!(
        "HTTP/1.1 {status} SYNTHETIC\r\nContent-Type: application/json\r\nContent-Length: {length}\r\nConnection: close\r\n{extra}\r\n{body}"
    );
    let worker = std::thread::spawn(move || {
        let deadline = Instant::now() + Duration::from_secs(5);
        let mut socket = loop {
            match listener.accept() {
                Ok((socket, _)) => break socket,
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    assert!(Instant::now() < deadline, "owned stub received no request");
                    std::thread::sleep(Duration::from_millis(5));
                }
                Err(error) => panic!("owned stub: {error}"),
            }
        };
        socket.set_nonblocking(false).unwrap();
        socket
            .set_read_timeout(Some(Duration::from_secs(2)))
            .unwrap();
        let mut read = Vec::new();
        while !read.windows(4).any(|w| w == b"\r\n\r\n") {
            let mut buffer = [0; 1024];
            let n = socket.read(&mut buffer).unwrap();
            assert!(n > 0);
            read.extend_from_slice(&buffer[..n]);
            assert!(read.len() < 8192);
        }
        assert!(
            std::str::from_utf8(&read)
                .unwrap()
                .starts_with("GET /api/v1/project-observer/handshake HTTP/1.1\r\n")
        );
        socket.write_all(response.as_bytes()).unwrap();
    });
    let admission:ClientAdmission=serde_json::from_value(json!({"port":port,"token":"c".repeat(64),"producer":{"namespace":"archeaxis","workspace_id":"a".repeat(32),"restore_epoch":"initial"},"consumer":{"namespace":"work-lab","instance_id":"b".repeat(32)}})).unwrap();
    let result = ObserverClient::connect(admission).map(|_| ());
    worker.join().unwrap();
    result
}
#[test]
fn actual_adapter_rejects_forged_expired_future_or_wrong_operation_responses() {
    let control = valid_response().to_string();
    assert_eq!(roundtrip(&control, 200, "", control.len()), Ok(()));
    let mut cases = Vec::new();
    for (field, value) in [
        ("schema", json!("unknown")),
        ("protocol", json!("v999")),
        ("token", json!("SYNTHETIC_FORBIDDEN")),
        ("editor_json", json!({})),
        ("checked_at_ms", json!(now_ms() + 600_000)),
        ("expires_at_ms", json!(now_ms() - 1)),
    ] {
        let mut value_case = valid_response();
        value_case[field] = value;
        cases.push(value_case);
    }
    let mut wrong = valid_response();
    wrong["producer"]["workspace_id"] = json!("f".repeat(32));
    cases.push(wrong);
    let mut wrong = valid_response();
    wrong["consumer"]["namespace"] = json!("design-lab");
    cases.push(wrong);
    let mut wrong = valid_response();
    wrong["payload"]["grants_execution"] = json!(true);
    cases.push(wrong);
    let mut wrong = valid_response();
    wrong["payload"]["grants_knowledge_acceptance"] = json!(true);
    cases.push(wrong);
    let mut wrong = valid_response();
    wrong["payload"] = json!({"kind":"objects","objects":[],"navigation":"UNAVAILABLE"});
    cases.push(wrong);
    for value in cases {
        let raw = value.to_string();
        assert!(
            roundtrip(&raw, 200, "", raw.len()).is_err(),
            "forged metadata was admitted"
        );
    }
}
#[test]
fn actual_adapter_does_not_follow_redirects_or_accept_ambiguous_http_frames() {
    let body = valid_response().to_string();
    for (status, extra, length) in [
        (302, "Location: http://127.0.0.1:1/private\r\n", body.len()),
        (200, "Location: http://127.0.0.1:1/private\r\n", body.len()),
        (200, "Transfer-Encoding: chunked\r\n", body.len()),
        (200, "Content-Length: 1\r\n", body.len()),
        (200, "Content-Type: text/plain\r\n", body.len()),
        (200, "", body.len() + 1),
    ] {
        assert!(roundtrip(&body, status, extra, length).is_err());
    }
    assert!(roundtrip("{", 200, "", 1).is_err());
    let oversize = "x".repeat(73_729);
    assert!(roundtrip(&oversize, 200, "", oversize.len()).is_err());
}

#[test]
fn production_three_second_deadline_rejects_silent_owned_http_peer() {
    let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0)).unwrap();
    let port = listener.local_addr().unwrap().port();
    listener.set_nonblocking(true).unwrap();
    let worker = std::thread::spawn(move || {
        let accept_deadline = Instant::now() + Duration::from_secs(5);
        let mut socket = loop {
            match listener.accept() {
                Ok((socket, _)) => break socket,
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    assert!(
                        Instant::now() < accept_deadline,
                        "owned stub received no request"
                    );
                    std::thread::sleep(Duration::from_millis(2));
                }
                Err(error) => panic!("owned stub: {error}"),
            }
        };
        socket.set_nonblocking(false).unwrap();
        socket
            .set_read_timeout(Some(Duration::from_secs(2)))
            .unwrap();
        let mut request = Vec::new();
        while !request.windows(4).any(|w| w == b"\r\n\r\n") {
            let mut buffer = [0; 1024];
            let count = socket.read(&mut buffer).unwrap();
            assert!(count > 0 && request.len() + count < 8192);
            request.extend_from_slice(&buffer[..count]);
        }
        assert!(request.starts_with(b"GET /api/v1/project-observer/handshake HTTP/1.1\r\n"));
        // 持有 owned socket 4.2 秒；生产客户端必须在对端关闭前自行截止。
        std::thread::sleep(Duration::from_millis(4200));
    });
    let admission: ClientAdmission = serde_json::from_value(json!({"port":port,"token":"c".repeat(64),"producer":{"namespace":"archeaxis","workspace_id":"a".repeat(32),"restore_epoch":"initial"},"consumer":{"namespace":"work-lab","instance_id":"b".repeat(32)}})).unwrap();
    let started = Instant::now();
    let result = ObserverClient::connect(admission);
    let elapsed = started.elapsed();
    worker.join().unwrap();
    assert!(matches!(result, Err(ReadError::Unavailable)));
    assert!(
        elapsed >= Duration::from_millis(2500),
        "production budget unexpectedly shortened: {elapsed:?}"
    );
    assert!(
        elapsed < Duration::from_millis(4000),
        "waited for peer EOF: {elapsed:?}"
    );
    eprintln!(
        "production deadline silent peer elapsed_ms={}",
        elapsed.as_millis()
    );
}
