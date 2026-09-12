use archeaxis_store_sqlite::raw_objects::read_staged;

#[test]
fn staging_reads_are_bounded_and_reject_nonregular_or_aliased_objects() {
    let dir=tempfile::tempdir().unwrap();let file=dir.path().join("object");
    std::fs::write(&file,b"abc").unwrap();
    assert_eq!(read_staged(&file,3).unwrap(),b"abc");
    assert!(read_staged(&file,2).is_err());
    assert!(read_staged(dir.path(),3).is_err());
    assert!(read_staged(&dir.path().join("sub/../object"),3).is_err());
    std::fs::hard_link(&file,dir.path().join("alias")).unwrap();
    assert!(read_staged(&file,3).is_err());
    assert_eq!(std::fs::read(file).unwrap(),b"abc");
}

#[cfg(unix)]
#[test]
fn fifo_is_rejected_before_a_blocking_open() {
    let dir=tempfile::tempdir().unwrap();let file=dir.path().join("fifo");
    let python=std::env::var_os("ARCHEAXIS_PYTHON").expect("use dev.py");
    assert!(std::process::Command::new(python).args(["-B","-S","-c","import os,sys; os.mkfifo(sys.argv[1])"]).arg(&file).status().unwrap().success());
    let (send,receive)=std::sync::mpsc::channel();
    let reader=std::thread::spawn(move||{let _=send.send(read_staged(&file,1024).is_err());});
    assert!(receive.recv_timeout(std::time::Duration::from_secs(1)).expect("FIFO open blocked"));
    reader.join().unwrap();
}
