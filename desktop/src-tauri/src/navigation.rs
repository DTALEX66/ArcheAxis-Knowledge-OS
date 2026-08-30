use std::path::Path;

use url::Url;

pub fn navigation_allowed(url: &Url, backend_port: u16, bootstrap_dir: Option<&Path>) -> bool {
    // AXW-RUN-201: the Recovery Shell lives in the packaged frontendDist
    // (app:// scheme, local-only assets). Everything else must be the exact
    // loopback workspace origin.
    if url.scheme() == "app" {
        return true;
    }
    // Green distribution: allow file:// navigation only for assets inside
    // the bootstrap/ directory beside the executable.
    if url.scheme() == "file" {
        let Some(root) = bootstrap_dir else {
            return false;
        };
        let Ok(canonical_root) = root.canonicalize() else {
            return false;
        };
        let Ok(canonical_path) = url.to_file_path() else {
            return false;
        };
        let Ok(canonical_path) = canonical_path.canonicalize() else {
            return false;
        };
        return canonical_path.starts_with(&canonical_root);
    }
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
    use std::path::Path;
    use url::Url;

    fn bootstrap() -> Option<&'static Path> {
        Some(Path::new("C:/green/bootstrap"))
    }

    fn allowed(value: &str, port: u16) -> bool {
        navigation_allowed(&Url::parse(value).expect("valid test URL"), port, bootstrap())
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

    #[test]
    fn accepts_packaged_recovery_shell_assets() {
        assert!(allowed("app://index.html", 43123));
        assert!(allowed("app://assets/app.js", 43123));
        assert!(allowed("app://assets/style.css", 43123));
        assert!(allowed("app://localhost/index.html", 43123));
    }

    #[test]
    fn accepts_green_bootstrap_file_navigation_inside_bootstrap_dir() {
        // Build a real temp bootstrap dir so canonicalize() succeeds.
        let tmp = std::env::temp_dir().join("ax-green-bootstrap-test");
        let bootstrap = tmp.join("bootstrap");
        std::fs::create_dir_all(&bootstrap).expect("create temp bootstrap dir");
        let index = bootstrap.join("index.html");
        std::fs::write(&index, "<html></html>").expect("write temp index");
        let assets = bootstrap.join("assets");
        std::fs::create_dir_all(&assets).expect("create temp assets dir");
        let app_js = assets.join("app.js");
        std::fs::write(&app_js, "// app").expect("write temp app.js");

        let allowed_in = |value: &str| {
            navigation_allowed(
                &Url::parse(value).expect("valid test URL"),
                43123,
                Some(&bootstrap),
            )
        };
        let file_url = |path: &std::path::Path| {
            Url::from_file_path(path).expect("valid file URL")
        };

        // file:// inside the bootstrap dir is allowed.
        assert!(allowed_in(file_url(&index).as_str()));
        assert!(allowed_in(file_url(&app_js).as_str()));
        // file:// outside the bootstrap dir stays rejected.
        let outside = tmp.join("other.html");
        std::fs::write(&outside, "<html></html>").expect("write temp outside");
        assert!(!allowed_in(file_url(&outside).as_str()));
        // Without a bootstrap dir, file:// is always rejected.
        assert!(!navigation_allowed(&file_url(&index), 43123, None));

        let _ = std::fs::remove_dir_all(&tmp);
    }
}
