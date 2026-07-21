use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RuntimeSpec {
    pub python: PathBuf,
    pub cwd: PathBuf,
    pub data_dir: PathBuf,
    pub isolated: bool,
}

pub fn resolve_runtime(
    manifest_dir: &Path,
    resource_dir: &Path,
    local_data_dir: &Path,
    development: bool,
) -> Result<RuntimeSpec, String> {
    if development {
        let desktop_dir = manifest_dir
            .parent()
            .ok_or_else(|| "desktop manifest has no parent".to_owned())?;
        let root = desktop_dir
            .parent()
            .ok_or_else(|| "desktop directory has no repository parent".to_owned())?;
        let python = root.join(".venv/Scripts/python.exe");
        if !python.is_file() {
            return Err(format!(
                "development Python runtime is missing: {}",
                python.display()
            ));
        }
        return Ok(RuntimeSpec {
            python,
            cwd: root.to_path_buf(),
            data_dir: root.join(".hermes/task-runtime/desktop-dev"),
            isolated: false,
        });
    }

    let python = resource_dir.join("runtime/python/python.exe");
    if !python.is_file() {
        return Err(format!(
            "bundled Python runtime is missing: {}",
            python.display()
        ));
    }
    Ok(RuntimeSpec {
        python,
        cwd: local_data_dir.to_path_buf(),
        data_dir: local_data_dir.to_path_buf(),
        isolated: true,
    })
}

#[cfg(test)]
mod tests {
    use super::{RuntimeSpec, resolve_runtime};
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn development_uses_only_the_repository_virtual_environment() {
        let temp = tempdir().expect("temporary directory");
        let root = temp.path().join("repo");
        let manifest = root.join("desktop/src-tauri");
        let python = root.join(".venv/Scripts/python.exe");
        fs::create_dir_all(python.parent().expect("python parent")).expect("create venv");
        fs::create_dir_all(&manifest).expect("create manifest directory");
        fs::write(&python, b"test").expect("create python marker");

        let resolved = resolve_runtime(
            &manifest,
            &temp.path().join("unused-resources"),
            &temp.path().join("unused-data"),
            true,
        )
        .expect("development runtime");

        assert_eq!(
            resolved,
            RuntimeSpec {
                python,
                cwd: root.clone(),
                data_dir: root.join(".hermes/task-runtime/desktop-dev"),
                isolated: false,
            }
        );
    }

    #[test]
    fn installed_mode_uses_only_bundled_python_and_writable_app_data() {
        let temp = tempdir().expect("temporary directory");
        let resources = temp.path().join("resources");
        let local_data = temp.path().join("local-data");
        let python = resources.join("runtime/python/python.exe");
        fs::create_dir_all(python.parent().expect("python parent")).expect("create runtime");
        fs::write(&python, b"test").expect("create python marker");

        let resolved = resolve_runtime(
            &temp.path().join("irrelevant-manifest"),
            &resources,
            &local_data,
            false,
        )
        .expect("installed runtime");

        assert_eq!(
            resolved,
            RuntimeSpec {
                python,
                cwd: local_data.clone(),
                data_dir: local_data,
                isolated: true,
            }
        );
    }

    #[test]
    fn missing_bundled_runtime_fails_instead_of_falling_back_to_path() {
        let temp = tempdir().expect("temporary directory");
        let error = resolve_runtime(
            &temp.path().join("manifest"),
            &temp.path().join("resources"),
            &temp.path().join("data"),
            false,
        )
        .expect_err("missing runtime must fail closed");

        assert!(error.contains("bundled Python runtime"));
    }
}
