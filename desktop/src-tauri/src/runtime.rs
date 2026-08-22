use std::path::{Component, Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RuntimeSpec {
    pub python: PathBuf,
    pub cwd: PathBuf,
    pub data_dir: PathBuf,
    pub isolated: bool,
}

/// Resolve the data root for a portable distribution.  An explicitly supplied
/// root remains the compatibility and automation override; a release archive
/// can otherwise be launched directly when its executable sits beside the
/// `portable.flag` marker.
fn portable_root_from_marker(executable: &Path) -> Option<PathBuf> {
    let distribution_root = executable.parent()?;
    distribution_root
        .join("portable.flag")
        .is_file()
        .then(|| distribution_root.join("data"))
}

pub fn portable_root_for_executable(executable: &Path) -> Option<PathBuf> {
    std::env::var_os("ARCHEAXIS_PORTABLE_ROOT")
        // AXW-RUN-205 compatibility window for the prior portable launcher.
        .or_else(|| std::env::var_os("COGNITIVE_PORTABLE_ROOT"))
        .map(PathBuf::from)
        .or_else(|| portable_root_from_marker(executable))
}

fn project_root_for_resource(resource_dir: &Path) -> Option<PathBuf> {
    resource_dir
        .ancestors()
        .find(|candidate| {
            if !candidate.join("pyproject.toml").is_file() || !candidate.join(".hermes").is_dir() {
                return false;
            }
            let Ok(relative) = resource_dir.strip_prefix(candidate.join(".hermes")) else {
                return false;
            };
            !matches!(
                relative.components().next(),
                Some(Component::Normal(name)) if name == "task-runtime"
            )
        })
        .map(Path::to_path_buf)
}

pub fn resolve_runtime(
    manifest_dir: &Path,
    resource_dir: &Path,
    local_data_dir: &Path,
    development: bool,
) -> Result<RuntimeSpec, String> {
    resolve_runtime_with_portable_root(
        manifest_dir,
        resource_dir,
        local_data_dir,
        development,
        None,
    )
}

pub fn resolve_runtime_with_portable_root(
    manifest_dir: &Path,
    resource_dir: &Path,
    local_data_dir: &Path,
    development: bool,
    portable_root: Option<&Path>,
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
    if let Some(portable_root) = portable_root {
        if !portable_root.is_absolute() {
            return Err(format!(
                "portable data root must be absolute: {}",
                portable_root.display()
            ));
        }
        return Ok(RuntimeSpec {
            python,
            cwd: portable_root.to_path_buf(),
            data_dir: portable_root.to_path_buf(),
            isolated: true,
        });
    }
    let data_dir = project_root_for_resource(resource_dir)
        .map(|root| root.join(".hermes/task-runtime/desktop-installed"))
        .unwrap_or_else(|| local_data_dir.to_path_buf());
    Ok(RuntimeSpec {
        python,
        cwd: data_dir.clone(),
        data_dir,
        isolated: true,
    })
}

#[cfg(test)]
mod tests {
    use super::{
        portable_root_from_marker, resolve_runtime, resolve_runtime_with_portable_root, RuntimeSpec,
    };
    use std::fs;
    use std::path::Path;
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
    fn development_data_root_is_under_project_task_runtime_boundary() {
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

        let expected_prefix = root.join(".hermes/task-runtime/");
        assert!(
            resolved.data_dir.starts_with(&expected_prefix),
            "dev data root must be under .hermes/task-runtime/: {}",
            resolved.data_dir.display(),
        );
    }

    #[test]
    fn installed_data_root_is_writable_and_outside_repository_checkout() {
        let temp = tempdir().expect("temporary directory");
        let resources = temp.path().join("resources");
        let local_data = temp.path().join("local-data");
        let python = resources.join("runtime/python/python.exe");
        fs::create_dir_all(python.parent().expect("python parent")).expect("create runtime");
        fs::write(&python, b"test").expect("create python marker");
        let checkout_root = temp.path().join("repo");
        fs::create_dir_all(&checkout_root).expect("create checkout marker");

        let resolved = resolve_runtime(
            &checkout_root.join("irrelevant-manifest"),
            &resources,
            &local_data,
            false,
        )
        .expect("installed runtime");

        assert!(
            !resolved.data_dir.starts_with(&checkout_root),
            "installed data root must not be inside the repository checkout: {}",
            resolved.data_dir.display(),
        );
        assert!(resolved.isolated, "installed runtime must be isolated");
        assert_ne!(
            resolved.cwd,
            resolved.data_dir.parent().unwrap_or(&resolved.cwd)
        );
    }

    #[test]
    fn project_bundle_installed_mode_uses_project_task_runtime_boundary() {
        let temp = tempdir().expect("temporary directory");
        let repository = temp.path().join("repo");
        let resources = repository.join(".hermes/portable-archeaxis/resources");
        let local_data = temp.path().join("user-local-data");
        let python = resources.join("runtime/python/python.exe");
        fs::create_dir_all(python.parent().expect("python parent")).expect("create runtime");
        fs::create_dir_all(repository.join(".hermes")).expect("create project boundary");
        fs::write(
            repository.join("pyproject.toml"),
            b"[project]\nname = 'fixture'\n",
        )
        .expect("create project marker");
        fs::write(&python, b"test").expect("create python marker");

        let resolved = resolve_runtime(&resources, &resources, &local_data, false)
            .expect("project bundle runtime");

        assert_eq!(
            resolved.data_dir,
            repository.join(".hermes/task-runtime/desktop-installed")
        );
        assert_eq!(resolved.cwd, resolved.data_dir);
        assert_ne!(resolved.data_dir, local_data);
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

    #[test]
    fn explicit_portable_root_overrides_installed_user_data_root() {
        let temp = tempdir().expect("temporary directory");
        let resources = temp.path().join("resources");
        let local_data = temp.path().join("user-local-data");
        let portable_root = temp.path().join("portable-data");
        let python = resources.join("runtime/python/python.exe");
        fs::create_dir_all(python.parent().expect("python parent")).expect("create runtime");
        fs::write(&python, b"test").expect("create python marker");

        let resolved = resolve_runtime_with_portable_root(
            &temp.path().join("manifest"),
            &resources,
            &local_data,
            false,
            Some(&portable_root),
        )
        .expect("portable runtime");

        assert_eq!(resolved.data_dir, portable_root);
        assert_eq!(resolved.cwd, resolved.data_dir);
        assert_ne!(resolved.data_dir, local_data);
        assert!(resolved.isolated);
    }

    #[test]
    fn portable_root_must_be_absolute() {
        let temp = tempdir().expect("temporary directory");
        let resources = temp.path().join("resources");
        let python = resources.join("runtime/python/python.exe");
        fs::create_dir_all(python.parent().expect("python parent")).expect("create runtime");
        fs::write(&python, b"test").expect("create python marker");

        let error = resolve_runtime_with_portable_root(
            &temp.path().join("manifest"),
            &resources,
            &temp.path().join("user-local-data"),
            false,
            Some(Path::new("portable-data")),
        )
        .expect_err("relative portable root must fail closed");

        assert!(error.contains("portable data root must be absolute"));
    }

    #[test]
    fn portable_flag_beside_executable_selects_distribution_data_root() {
        let temp = tempdir().expect("temporary directory");
        let executable = temp.path().join("portable/ArcheAxis.exe");
        fs::create_dir_all(executable.parent().expect("distribution root"))
            .expect("create distribution root");
        fs::write(
            executable
                .parent()
                .expect("distribution root")
                .join("portable.flag"),
            b"",
        )
        .expect("create portable marker");

        assert_eq!(
            portable_root_from_marker(&executable),
            Some(temp.path().join("portable/data"))
        );
    }
}
