//! Product-owned Windows Credential Manager adapter. Secret values never serialize.
pub trait Vault {
    fn write(&self, reference: &str, value: &[u8]) -> Result<(), &'static str>;
    fn read(&self, reference: &str) -> Result<Vec<u8>, &'static str>;
    fn remove(&self, reference: &str) -> Result<(), &'static str>;
}
fn target(reference: &str) -> Result<String, &'static str> {
    let suffix = reference
        .strip_prefix("aak_cred_")
        .ok_or("CREDENTIAL_REFERENCE_INVALID")?;
    if suffix.len() != 32
        || !suffix
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("CREDENTIAL_REFERENCE_INVALID");
    }
    Ok(format!("ArcheAxis.Knowledge/product-model/{reference}"))
}
pub fn create(vault: &impl Vault, mut secret: Vec<u8>) -> Result<String, &'static str> {
    if secret.is_empty() || secret.len() > 2560 {
        secret.fill(0);
        return Err("CREDENTIAL_SIZE_INVALID");
    }
    let mut nonce = [0u8; 16];
    getrandom::fill(&mut nonce).map_err(|_| "CREDENTIAL_RANDOM_UNAVAILABLE")?;
    let reference = format!(
        "aak_cred_{}",
        nonce.iter().map(|b| format!("{b:02x}")).collect::<String>()
    );
    let result = vault.write(&reference, &secret);
    secret.fill(0);
    result?;
    Ok(reference)
}
pub struct NativeVault;
#[cfg(windows)]
mod native {
    use super::*;
    use std::ffi::c_void;
    #[repr(C)]
    struct Credential {
        flags: u32,
        kind: u32,
        target: *mut u16,
        comment: *mut u16,
        last_written: [u32; 2],
        size: u32,
        blob: *mut u8,
        persist: u32,
        attribute_count: u32,
        attributes: *mut c_void,
        alias: *mut u16,
        username: *mut u16,
    }
    #[link(name = "Advapi32")]
    unsafe extern "system" {
        fn CredWriteW(credential: *const Credential, flags: u32) -> i32;
        fn CredReadW(
            target: *const u16,
            kind: u32,
            flags: u32,
            credential: *mut *mut Credential,
        ) -> i32;
        fn CredDeleteW(target: *const u16, kind: u32, flags: u32) -> i32;
        fn CredFree(buffer: *mut c_void);
    }
    fn wide(reference: &str) -> Result<Vec<u16>, &'static str> {
        Ok(target(reference)?.encode_utf16().chain([0]).collect())
    }
    impl Vault for NativeVault {
        fn write(&self, reference: &str, value: &[u8]) -> Result<(), &'static str> {
            if value.is_empty() || value.len() > 2560 {
                return Err("CREDENTIAL_SIZE_INVALID");
            }
            let mut name = wide(reference)?;
            let c = Credential {
                flags: 0,
                kind: 1,
                target: name.as_mut_ptr(),
                comment: std::ptr::null_mut(),
                last_written: [0; 2],
                size: value.len() as u32,
                blob: value.as_ptr() as *mut u8,
                persist: 2,
                attribute_count: 0,
                attributes: std::ptr::null_mut(),
                alias: std::ptr::null_mut(),
                username: std::ptr::null_mut(),
            };
            if unsafe { CredWriteW(&c, 0) } == 0 {
                return Err("CREDENTIAL_WRITE_FAILED");
            }
            Ok(())
        }
        fn read(&self, reference: &str) -> Result<Vec<u8>, &'static str> {
            let name = wide(reference)?;
            let mut c = std::ptr::null_mut();
            if unsafe { CredReadW(name.as_ptr(), 1, 0, &mut c) } == 0 {
                return Err("CREDENTIAL_UNAVAILABLE");
            }
            // Only exact product target reads; never enumerate the native store.
            let result = unsafe {
                if c.is_null() || (*c).size == 0 || (*c).size > 2560 || (*c).blob.is_null() {
                    Err("CREDENTIAL_INVALID")
                } else {
                    Ok(std::slice::from_raw_parts((*c).blob, (*c).size as usize).to_vec())
                }
            };
            unsafe { CredFree(c as *mut c_void) };
            result
        }
        fn remove(&self, reference: &str) -> Result<(), &'static str> {
            let name = wide(reference)?;
            if unsafe { CredDeleteW(name.as_ptr(), 1, 0) } == 0 {
                return Err("CREDENTIAL_DELETE_FAILED");
            }
            Ok(())
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use std::{cell::RefCell, collections::BTreeMap};
    #[derive(Default)]
    struct Mock(RefCell<BTreeMap<String, Vec<u8>>>);
    impl Vault for Mock {
        fn write(&self, r: &str, v: &[u8]) -> Result<(), &'static str> {
            target(r)?;
            self.0.borrow_mut().insert(r.into(), v.into());
            Ok(())
        }
        fn read(&self, r: &str) -> Result<Vec<u8>, &'static str> {
            target(r)?;
            self.0
                .borrow()
                .get(r)
                .cloned()
                .ok_or("CREDENTIAL_UNAVAILABLE")
        }
        fn remove(&self, r: &str) -> Result<(), &'static str> {
            target(r)?;
            self.0.borrow_mut().remove(r);
            Ok(())
        }
    }
    #[test]
    fn mock_lifecycle_is_product_scoped() {
        let vault = Mock::default();
        let r = create(&vault, b"synthetic-secret".to_vec()).unwrap();
        assert_eq!(vault.read(&r).unwrap(), b"synthetic-secret");
        vault.remove(&r).unwrap();
        assert!(vault.read(&r).is_err());
        assert!(target("other-product").is_err());
        assert!(create(&vault, vec![]).is_err());
    }
}
