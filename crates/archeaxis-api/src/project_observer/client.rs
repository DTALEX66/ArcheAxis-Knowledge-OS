//! 实际 Rust HTTP 消费者：仅固定 IPv4 loopback；不接收 URL、文件路径或任意命令。
use super::now_ms;
use archeaxis_contracts::project_observer::{
    self as contract, ConsumerIdentity, ObjectReference, Payload, ProducerIdentity, ReadResponse,
};
use serde::Deserialize;
use std::{
    io::{Read, Write},
    net::{Ipv4Addr, SocketAddr, TcpStream},
    time::{Duration, Instant},
};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ClientAdmission {
    pub port: u16,
    token: String,
    pub producer: ProducerIdentity,
    pub consumer: ConsumerIdentity,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ReadError {
    InvalidAdmission,
    Unavailable,
    Rejected,
    Incompatible,
    InvalidResponse,
    Expired,
}
impl ReadError {
    pub fn code(self) -> &'static str {
        match self {
            Self::InvalidAdmission => "OBSERVER_INVALID_ADMISSION",
            Self::Unavailable => "OBSERVER_UNAVAILABLE",
            Self::Rejected => "OBSERVER_REJECTED",
            Self::Incompatible => "OBSERVER_INCOMPATIBLE",
            Self::InvalidResponse => "OBSERVER_INVALID_RESPONSE",
            Self::Expired => "OBSERVER_EXPIRED",
        }
    }
}
// 单次请求共用同一个单调时钟截止；每次 I/O 只可使用尚余预算。
struct RequestDeadline(Instant);
impl RequestDeadline {
    fn new(timeout: Duration) -> Result<Self, ReadError> {
        Instant::now()
            .checked_add(timeout)
            .map(Self)
            .ok_or(ReadError::Unavailable)
    }
    fn remaining(&self) -> Result<Duration, ReadError> {
        self.0
            .checked_duration_since(Instant::now())
            .filter(|remaining| !remaining.is_zero())
            .ok_or(ReadError::Unavailable)
    }
    fn finish<T>(&self, value: T) -> Result<T, ReadError> {
        self.remaining()?;
        Ok(value)
    }
}
pub struct ObserverClient {
    admission: ClientAdmission,
}
impl ObserverClient {
    pub fn connect(admission: ClientAdmission) -> Result<Self, ReadError> {
        if admission.port == 0
            || !contract::hex(&admission.token, 64)
            || !admission.producer.valid()
            || !contract::hex(&admission.consumer.instance_id, 32)
        {
            return Err(ReadError::InvalidAdmission);
        }
        let client = Self { admission };
        client.handshake()?;
        Ok(client)
    }
    pub fn handshake(&self) -> Result<ReadResponse, ReadError> {
        let response = self.request("/api/v1/project-observer/handshake")?;
        if !matches!(response.payload, Payload::Handshake { .. }) {
            return Err(ReadError::InvalidResponse);
        }
        Ok(response)
    }
    pub fn objects(&self) -> Result<ReadResponse, ReadError> {
        let response = self.request("/api/v1/project-observer/objects")?;
        if !matches!(response.payload, Payload::Objects { .. }) {
            return Err(ReadError::InvalidResponse);
        }
        Ok(response)
    }
    pub fn status(&self, reference: &ObjectReference) -> Result<ReadResponse, ReadError> {
        if !reference.valid() {
            return Err(ReadError::InvalidAdmission);
        }
        let response = self.request(&format!(
            "/api/v1/project-observer/objects/{}?version={}&content_sha256={}",
            reference.document_id, reference.version, reference.content_sha256
        ))?;
        if !matches!(&response.payload, Payload::ObjectStatus { reference: echoed, .. } if echoed == reference)
        {
            return Err(ReadError::InvalidResponse);
        }
        Ok(response)
    }
    fn request(&self, path: &str) -> Result<ReadResponse, ReadError> {
        self.request_with_timeout(path, Duration::from_secs(3))
    }
    // 生产唯一入口固定 3 秒；较短预算仅供本模块真实 loopback 回归使用。
    fn request_with_timeout(
        &self,
        path: &str,
        timeout: Duration,
    ) -> Result<ReadResponse, ReadError> {
        let deadline = RequestDeadline::new(timeout)?;
        let address = SocketAddr::from((Ipv4Addr::LOCALHOST, self.admission.port));
        let mut socket = TcpStream::connect_timeout(&address, deadline.remaining()?)
            .map_err(|_| ReadError::Unavailable)?;
        deadline.remaining()?;
        let request = format!(
            "GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{}\r\nConnection: close\r\nx-archeaxis-launch-token: {}\r\nx-archeaxis-observer-protocol: {}\r\nx-archeaxis-observer-namespace: {}\r\nx-archeaxis-observer-instance: {}\r\n\r\n",
            self.admission.port,
            self.admission.token,
            contract::PROTOCOL,
            self.admission.consumer.namespace.as_str(),
            self.admission.consumer.instance_id
        );
        let mut sent = 0;
        while sent < request.len() {
            socket
                .set_write_timeout(Some(deadline.remaining()?))
                .map_err(|_| ReadError::Unavailable)?;
            let written = socket.write(&request.as_bytes()[sent..]);
            deadline.remaining()?;
            match written {
                Ok(0) => return Err(ReadError::Unavailable),
                Ok(n) => sent += n,
                Err(error) if error.kind() == std::io::ErrorKind::Interrupted => continue,
                Err(_) => return Err(ReadError::Unavailable),
            }
        }
        let mut raw = Vec::new();
        loop {
            let remaining = deadline.remaining()?;
            socket
                .set_read_timeout(Some(remaining))
                .map_err(|_| ReadError::Unavailable)?;
            let mut buffer = [0; 4096];
            let n = socket
                .read(&mut buffer)
                .map_err(|_| ReadError::Unavailable)?;
            // 包括 EOF 在内，内核调用返回后再次检查，不能将迟到数据判为成功。
            deadline.remaining()?;
            if n == 0 {
                break;
            }
            if raw.len() + n > contract::MAX_RESPONSE_BYTES + 8192 {
                return Err(ReadError::InvalidResponse);
            }
            raw.extend_from_slice(&buffer[..n]);
        }
        deadline.remaining()?;
        let split = raw
            .windows(4)
            .position(|w| w == b"\r\n\r\n")
            .filter(|n| *n <= 8192)
            .ok_or(ReadError::InvalidResponse)?;
        let headers = std::str::from_utf8(&raw[..split]).map_err(|_| ReadError::InvalidResponse)?;
        let mut lines = headers.split("\r\n");
        let status_line = lines.next().ok_or(ReadError::InvalidResponse)?;
        let fields: Vec<_> = status_line.split_whitespace().collect();
        if fields.len() < 2 || fields[0] != "HTTP/1.1" {
            return Err(ReadError::InvalidResponse);
        }
        let status: u16 = fields[1].parse().map_err(|_| ReadError::InvalidResponse)?;
        if status != 200 {
            return Err(match status {
                401 | 403 | 404 => ReadError::Rejected,
                409 => ReadError::Incompatible,
                _ => ReadError::Unavailable,
            });
        }
        let mut content_length = None;
        let mut content_type = None;
        for line in lines {
            let (key, value) = line.split_once(':').ok_or(ReadError::InvalidResponse)?;
            match key.to_ascii_lowercase().as_str() {
                "content-length" if content_length.is_none() => {
                    content_length = Some(
                        value
                            .trim()
                            .parse::<usize>()
                            .map_err(|_| ReadError::InvalidResponse)?,
                    )
                }
                "content-type" if content_type.is_none() => content_type = Some(value.trim()),
                "content-length" | "content-type" | "transfer-encoding" | "location" => {
                    return Err(ReadError::InvalidResponse);
                }
                _ => {}
            }
        }
        let body = &raw[split + 4..];
        if content_length != Some(body.len())
            || body.len() > contract::MAX_RESPONSE_BYTES
            || content_type != Some("application/json")
        {
            return Err(ReadError::InvalidResponse);
        }
        let response: ReadResponse =
            serde_json::from_slice(body).map_err(|_| ReadError::InvalidResponse)?;
        deadline.remaining()?;
        if response.producer != self.admission.producer
            || response.consumer != self.admission.consumer
        {
            return Err(ReadError::InvalidResponse);
        }
        let now = now_ms();
        if response.expires_at_ms <= now {
            return Err(ReadError::Expired);
        }
        if !response.valid(now) {
            return Err(ReadError::InvalidResponse);
        }
        // DTO 解析和身份/新鲜度核验同样计入总预算。
        deadline.finish(response)
    }
}

#[cfg(test)]
mod deadline_tests {
    use super::*;
    use serde_json::json;
    use std::{net::TcpListener, thread};

    fn fixture() -> String {
        let now = now_ms();
        let body = json!({"schema":"archeaxis.project-observer-response/v1","protocol":"archeaxis.project-observer/v1","producer":{"namespace":"archeaxis","workspace_id":"a".repeat(32),"restore_epoch":"initial"},"consumer":{"namespace":"work-lab","instance_id":"b".repeat(32)},"checked_at_ms":now,"expires_at_ms":now+30_000,"payload":{"kind":"handshake","operations":["handshake","objects.read","object.status"],"authority":"REFERENCE_ONLY","grants_execution":false,"grants_knowledge_acceptance":false}}).to_string();
        format!(
            "HTTP/1.1 200 SYNTHETIC\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
            body.len()
        )
    }

    // 每次测试独占临时端口与连接，无共享服务、真实数据或任意 URL。
    fn owned_request(
        budget: Duration,
        serve: impl FnOnce(&mut TcpStream, &str) + Send + 'static,
    ) -> (Result<ReadResponse, ReadError>, Duration) {
        let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0)).unwrap();
        let port = listener.local_addr().unwrap().port();
        listener.set_nonblocking(true).unwrap();
        let worker = thread::spawn(move || {
            let accept_deadline = Instant::now() + Duration::from_secs(5);
            let mut socket = loop {
                match listener.accept() {
                    Ok((socket, _)) => break socket,
                    Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                        assert!(
                            Instant::now() < accept_deadline,
                            "owned stub received no request"
                        );
                        thread::sleep(Duration::from_millis(2));
                    }
                    Err(error) => panic!("owned stub: {error}"),
                }
            };
            socket.set_nonblocking(false).unwrap();
            socket
                .set_read_timeout(Some(Duration::from_secs(2)))
                .unwrap();
            socket
                .set_write_timeout(Some(Duration::from_secs(2)))
                .unwrap();
            let mut request = Vec::new();
            while !request.windows(4).any(|w| w == b"\r\n\r\n") {
                let mut buffer = [0; 1024];
                let count = socket.read(&mut buffer).unwrap();
                assert!(count > 0 && request.len() + count < 8192);
                request.extend_from_slice(&buffer[..count]);
            }
            assert!(request.starts_with(b"GET /api/v1/project-observer/handshake HTTP/1.1\r\n"));
            serve(&mut socket, &fixture());
        });
        let admission = serde_json::from_value(json!({"port":port,"token":"c".repeat(64),"producer":{"namespace":"archeaxis","workspace_id":"a".repeat(32),"restore_epoch":"initial"},"consumer":{"namespace":"work-lab","instance_id":"b".repeat(32)}})).unwrap();
        let client = ObserverClient { admission };
        let started = Instant::now();
        let result = client.request_with_timeout("/api/v1/project-observer/handshake", budget);
        let elapsed = started.elapsed();
        worker.join().unwrap();
        (result, elapsed)
    }

    #[test]
    fn timely_valid_http_response_remains_usable() {
        let (result, elapsed) = owned_request(Duration::from_secs(1), |socket, response| {
            socket.write_all(response.as_bytes()).unwrap();
        });
        assert!(result.is_ok());
        assert!(elapsed < Duration::from_secs(1));
        eprintln!(
            "deadline timely positive elapsed_ms={}",
            elapsed.as_millis()
        );
    }

    #[test]
    fn continuously_arriving_bytes_do_not_renew_total_budget() {
        let (result, elapsed) = owned_request(Duration::from_millis(250), |socket, response| {
            for byte in response.bytes().take(30) {
                if socket.write_all(&[byte]).is_err() {
                    break;
                }
                thread::sleep(Duration::from_millis(35));
            }
        });
        assert!(matches!(result, Err(ReadError::Unavailable)));
        assert!(
            elapsed < Duration::from_millis(750),
            "stream renewed deadline: {elapsed:?}"
        );
        eprintln!("deadline slow stream elapsed_ms={}", elapsed.as_millis());
    }

    #[test]
    fn complete_valid_response_with_late_eof_is_unavailable() {
        let (result, elapsed) = owned_request(Duration::from_millis(250), |socket, response| {
            socket.write_all(response.as_bytes()).unwrap();
            // 早到的完整合法正文不能绕过总截止，EOF 必须在预算内。
            thread::sleep(Duration::from_millis(900));
        });
        assert!(matches!(result, Err(ReadError::Unavailable)));
        assert!(
            elapsed < Duration::from_millis(750),
            "late EOF admitted: {elapsed:?}"
        );
        eprintln!("deadline delayed EOF elapsed_ms={}", elapsed.as_millis());
    }

    #[test]
    fn expired_final_gate_rejects_even_valid_dto() {
        let response = fixture();
        let body = response.split_once("\r\n\r\n").unwrap().1;
        let dto: ReadResponse = serde_json::from_str(body).unwrap();
        assert!(dto.valid(now_ms()));
        let deadline = RequestDeadline(Instant::now() - Duration::from_millis(1));
        assert!(matches!(deadline.finish(dto), Err(ReadError::Unavailable)));
        assert_eq!(deadline.remaining(), Err(ReadError::Unavailable));
    }
}
