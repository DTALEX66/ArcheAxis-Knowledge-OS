//! Finite directory-only loopback read; no Core token, credentials, model load or inference.
use serde::{Deserialize, Serialize};
use std::{io::Read, time::Duration};

const MAX_BYTES: u64 = 1024 * 1024;

#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Protocol {
    Openai,
    Ollama,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Request {
    pub endpoint: String,
    pub protocol: Protocol,
}

#[derive(Debug, Serialize)]
pub struct Failure {
    pub code: &'static str,
    pub status: Option<u16>,
}

pub fn failure(code: &'static str) -> Failure {
    Failure { code, status: None }
}

#[derive(Debug, Serialize)]
pub struct Inventory {
    pub schema: &'static str,
    pub models: Vec<String>,
    pub inference_status: &'static str,
    pub loaded_status: &'static str,
}

fn directory_url(request: &Request) -> Result<url::Url, Failure> {
    let mut url = url::Url::parse(&request.endpoint).map_err(|_| failure("INVALID_DESTINATION"))?;
    let loopback = matches!(url.host(), Some(url::Host::Ipv4(ip)) if ip.octets()==[127,0,0,1])
        || matches!(url.host(), Some(url::Host::Ipv6(ip)) if ip.is_loopback());
    if url.scheme() != "http"
        || !loopback
        || !url.username().is_empty()
        || url.password().is_some()
        || url.query().is_some()
        || url.fragment().is_some()
        || url.port() == Some(0)
    {
        return Err(failure("INVALID_DESTINATION"));
    }
    let base = url.path().trim_end_matches('/');
    let path = match request.protocol {
        Protocol::Openai => format!(
            "{}/models",
            if base.ends_with("/v1") {
                base.to_owned()
            } else {
                format!("{base}/v1")
            }
        ),
        Protocol::Ollama => format!("{base}/api/tags"),
    };
    url.set_path(&path);
    Ok(url)
}

fn parse(bytes: &[u8], protocol: &Protocol) -> Result<Inventory, Failure> {
    let value: serde_json::Value =
        serde_json::from_slice(bytes).map_err(|_| failure("INVALID_INVENTORY"))?;
    let (key, identity) = match protocol {
        Protocol::Openai => ("data", "id"),
        Protocol::Ollama => ("models", "name"),
    };
    let rows = value[key]
        .as_array()
        .filter(|rows| rows.len() <= 256)
        .ok_or_else(|| failure("INVALID_INVENTORY"))?;
    let mut models = Vec::with_capacity(rows.len());
    for row in rows {
        let name = row[identity]
            .as_str()
            .filter(|s| !s.trim().is_empty() && s.len() <= 256 && !s.chars().any(char::is_control))
            .ok_or_else(|| failure("INVALID_INVENTORY"))?;
        models.push(name.to_owned());
    }
    Ok(Inventory {
        schema: "archeaxis.local-model-inventory/v1",
        models,
        inference_status: "NOT_EXECUTED",
        loaded_status: "UNKNOWN",
    })
}

pub fn read(request: Request) -> Result<Inventory, Failure> {
    let url = directory_url(&request)?;
    let client = reqwest::blocking::Client::builder()
        .no_proxy()
        .redirect(reqwest::redirect::Policy::none())
        .timeout(Duration::from_secs(5))
        .build()
        .map_err(|_| failure("NETWORK_FAILURE"))?;
    let response = client
        .get(url)
        .send()
        .map_err(|_| failure("NETWORK_FAILURE"))?;
    if !response.status().is_success() {
        return Err(Failure {
            code: "HTTP_FAILURE",
            status: Some(response.status().as_u16()),
        });
    }
    if response.content_length().is_some_and(|n| n > MAX_BYTES) {
        return Err(failure("INVENTORY_TOO_LARGE"));
    }
    let mut bytes = Vec::new();
    response
        .take(MAX_BYTES + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| failure("NETWORK_FAILURE"))?;
    if bytes.len() as u64 > MAX_BYTES {
        return Err(failure("INVENTORY_TOO_LARGE"));
    }
    parse(&bytes, &request.protocol)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{io::Write, net::TcpListener, sync::mpsc, thread};

    #[test]
    fn finite_destinations_and_protocol_paths() {
        for endpoint in [
            "https://example.com/v1",
            "http://localhost:1234",
            "http://127.0.0.2:1234",
            "http://user:secret@127.0.0.1:1234",
            "http://127.0.0.1:1234?token=hidden",
            "http://127.0.0.1:1234/#x",
        ] {
            assert!(directory_url(&Request {
                endpoint: endpoint.into(),
                protocol: Protocol::Openai
            })
            .is_err());
        }
        for (endpoint, path) in [
            ("http://127.0.0.1:1234", "/v1/models"),
            ("http://[::1]:1234/v1/", "/v1/models"),
        ] {
            assert_eq!(
                directory_url(&Request {
                    endpoint: endpoint.into(),
                    protocol: Protocol::Openai
                })
                .unwrap()
                .path(),
                path
            );
        }
        assert_eq!(
            directory_url(&Request {
                endpoint: "http://127.0.0.1:1234/".into(),
                protocol: Protocol::Ollama
            })
            .unwrap()
            .path(),
            "/api/tags"
        );
        assert!(serde_json::from_str::<Request>(
            r#"{"endpoint":"http://127.0.0.1:1234","protocol":"openai","headers":{}}"#
        )
        .is_err());
    }

    fn server(response: Vec<u8>) -> (String, mpsc::Receiver<String>, thread::JoinHandle<()>) {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        let (tx, rx) = mpsc::channel();
        let handle = thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            let mut buf = [0; 4096];
            let n = stream.read(&mut buf).unwrap();
            let _ = tx.send(String::from_utf8_lossy(&buf[..n]).into_owned());
            let _ = stream.write_all(&response);
        });
        (format!("http://{address}/v1"), rx, handle)
    }

    #[test]
    fn reads_without_cors_and_never_sends_credentials_or_inference() {
        let body = r#"{"data":[{"id":"selected","private":"ignored"}]}"#;
        let (endpoint, request, handle) = server(
            format!(
                "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
                body.len()
            )
            .into_bytes(),
        );
        let result = read(Request {
            endpoint,
            protocol: Protocol::Openai,
        })
        .unwrap();
        handle.join().unwrap();
        let raw = request.recv().unwrap().to_lowercase();
        assert!(raw.starts_with("get /v1/models http/1.1"));
        assert!(
            !raw.contains("authorization:")
                && !raw.contains("cookie:")
                && !raw.contains("x-archeaxis")
        );
        assert_eq!(result.models, vec!["selected"]);
        assert_eq!(result.inference_status, "NOT_EXECUTED");
        assert!(!serde_json::to_string(&result).unwrap().contains("private"));
    }

    #[test]
    fn refuses_redirects_without_visiting_the_target() {
        let target = TcpListener::bind("127.0.0.1:0").unwrap();
        target.set_nonblocking(true).unwrap();
        let (endpoint,_,handle)=server(format!("HTTP/1.1 302 Found\r\nLocation: http://{}/private\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",target.local_addr().unwrap()).into_bytes());
        let error = read(Request {
            endpoint,
            protocol: Protocol::Openai,
        })
        .unwrap_err();
        handle.join().unwrap();
        assert_eq!(error.status, Some(302));
        assert!(target.accept().is_err());
    }

    #[test]
    fn bounds_unframed_body_and_directory_shape() {
        let mut response = b"HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n".to_vec();
        response.extend(vec![b' '; MAX_BYTES as usize + 1]);
        let (endpoint, _, handle) = server(response);
        let error = read(Request {
            endpoint,
            protocol: Protocol::Openai,
        })
        .unwrap_err();
        handle.join().unwrap();
        assert_eq!(error.code, "INVENTORY_TOO_LARGE");
        for value in [
            serde_json::json!({"data":[{"id":""}]}),
            serde_json::json!({"data":[{"id":"bad\nname"}]}),
            serde_json::json!({"models":[]}),
            serde_json::json!({"data":vec![serde_json::json!({"id":"x"});257]}),
        ] {
            assert!(parse(&serde_json::to_vec(&value).unwrap(), &Protocol::Openai).is_err());
        }
    }

    #[test]
    fn stalled_directory_read_is_bounded_and_does_not_return_response_body() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let endpoint = format!("http://{}/v1", listener.local_addr().unwrap());
        let handle = thread::spawn(move || {
            let (_stream, _) = listener.accept().unwrap();
            thread::sleep(Duration::from_secs(6));
        });
        let start = std::time::Instant::now();
        let error = read(Request {
            endpoint,
            protocol: Protocol::Openai,
        })
        .unwrap_err();
        assert_eq!(error.code, "NETWORK_FAILURE");
        assert!(start.elapsed() < Duration::from_secs(15));
        handle.join().unwrap();
        assert_eq!(
            serde_json::to_value(error).unwrap(),
            serde_json::json!({"code":"NETWORK_FAILURE","status":null})
        );
    }
}
