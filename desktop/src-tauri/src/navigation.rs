use url::Url;

pub fn navigation_allowed(url: &Url, backend_port: u16) -> bool {
    let path = url.path();
    url.scheme() == "http"
        && url.host_str() == Some("127.0.0.1")
        && url.port() == Some(backend_port)
        && url.username().is_empty()
        && url.password().is_none()
        && (path == "/workspace" || path.starts_with("/workspace/"))
}

#[cfg(test)]
mod tests {
    use super::navigation_allowed;
    use url::Url;

    fn allowed(value: &str, port: u16) -> bool {
        navigation_allowed(&Url::parse(value).expect("valid test URL"), port)
    }

    #[test]
    fn accepts_only_the_current_workspace_origin() {
        assert!(allowed("http://127.0.0.1:43123/workspace", 43123));
        assert!(allowed("http://127.0.0.1:43123/workspace/", 43123));
        assert!(allowed(
            "http://127.0.0.1:43123/workspace#diagnostics",
            43123
        ));
    }

    #[test]
    fn rejects_external_and_ambiguous_navigation() {
        for value in [
            "https://example.com/workspace",
            "file:///C:/Windows/System32/drivers/etc/hosts",
            "data:text/html,unsafe",
            "blob:http://127.0.0.1:43123/unsafe",
            "http://localhost:43123/workspace",
            "http://[::1]:43123/workspace",
            "http://127.0.0.1:43124/workspace",
            "http://127.0.0.1:43123/",
            "http://127.0.0.1:43123/workspace-evil",
            "http://127.0.0.1:43123@evil.example/workspace",
        ] {
            assert!(!allowed(value, 43123), "unexpectedly allowed {value}");
        }
    }
}
