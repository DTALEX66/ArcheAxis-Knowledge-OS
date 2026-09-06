//! Real Python transport + Rust consumer. This is not a persisted executor test.
use archeaxis_sidecar_protocol::worker::{Request, decode_hello, decode_response, MAX_FRAME_BYTES};
use std::{io::{Read, Write}, path::PathBuf, process::{Child, Command, Stdio}, time::{Duration, Instant}};
use sha2::{Digest, Sha256};

struct OwnedChild(Child);
impl Drop for OwnedChild { fn drop(&mut self) { let _=self.0.kill(); let _=self.0.wait(); } }

#[test]
fn real_python_text_outputs_are_accepted_without_discarding_structure_or_loss() {
    let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let staging=tempfile::tempdir().unwrap();
    std::fs::create_dir(staging.path().join("input")).unwrap();
    let digest="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
    std::fs::write(staging.path().join("input").join(digest),b"abc").unwrap();
    let request=Request::text("real-request", "real-job", 1, digest, "text/plain", 5000).unwrap();
    let python=std::env::var_os("ARCHEAXIS_PYTHON").expect("run via scripts/runtime/dev.py to select project Python");
    let mut command=Command::new(python);
    command.arg("-B").arg("-S").arg(root.join("services/python-workers/transport/text_ndjson.py"))
        .arg("--staging-root").arg(staging.path()).current_dir(&root)
        .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null());
    #[cfg(windows)] {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child=OwnedChild(command.spawn().unwrap());
    let stdout=child.0.stdout.take().unwrap();
    let (send, receive)=std::sync::mpsc::channel();
    let reader=std::thread::spawn(move || {
        let mut bytes=Vec::new();
        let result=stdout.take((2*MAX_FRAME_BYTES+1) as u64).read_to_end(&mut bytes);
        let _=send.send((result,bytes));
    });
    let mut input=child.0.stdin.take().unwrap();
    writeln!(input,"{}",serde_json::to_string(&request).unwrap()).unwrap();
    drop(input);
    let deadline=Instant::now()+Duration::from_secs(15);
    let status=loop {
        if let Some(status)=child.0.try_wait().unwrap() { break status; }
        assert!(Instant::now()<deadline,"worker exceeded owned test deadline");
        std::thread::sleep(Duration::from_millis(10));
    };
    let (read,bytes)=receive.recv_timeout(Duration::from_secs(2)).unwrap();
    read.unwrap(); reader.join().unwrap();
    assert!(status.success(),"worker failed: {}",String::from_utf8_lossy(&bytes));
    assert!(bytes.len()<=2*MAX_FRAME_BYTES);
    let text=String::from_utf8(bytes).unwrap();
    let lines: Vec<&str>=text.lines().collect();
    assert_eq!(lines.len(),2,"one hello and one terminal response");
    decode_hello(lines[0]).unwrap();
    let result=decode_response(lines[1],&request).unwrap();
    assert_eq!(result.status,"succeeded");
    for output in result.outputs {
        let bytes=std::fs::read(staging.path().join("output").join(&output.sha256)).unwrap();
        assert_eq!(bytes.len() as u64,output.byte_length);
        assert_eq!(hex::encode(Sha256::digest(&bytes)),output.sha256);
        match output.kind.as_str() {
            "text" => assert_eq!(bytes,b"abc"),
            "document_structure" => assert_eq!(serde_json::from_slice::<serde_json::Value>(&bytes).unwrap(),
                serde_json::json!([{"kind":"line","path":["line-1"],"char_start":0,"char_end":3}])),
            "loss_report" => {
                let loss:serde_json::Value=serde_json::from_slice(&bytes).unwrap();
                assert_eq!(loss["covered"],1); assert_eq!(loss["total"],1);
                assert_eq!(loss["losses"],serde_json::json!([]));
            }
            other => panic!("unexpected output {other}"),
        }
    }
}
