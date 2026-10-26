//! Measure Rust-owned CAS payload allocations in a dedicated single-test process.
//! SQLite C allocations / process RSS are not measured by this allocator.
use archeaxis_domain::{backup, source};
use archeaxis_store_sqlite::init_workspace;
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicUsize, Ordering};

struct Measured;
static LIVE: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);
fn acquired(bytes: usize) {
    let current = LIVE.fetch_add(bytes, Ordering::SeqCst) + bytes;
    PEAK.fetch_max(current, Ordering::SeqCst);
}
unsafe impl GlobalAlloc for Measured {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let value = unsafe { System.alloc(layout) };
        if !value.is_null() {
            acquired(layout.size());
        }
        value
    }
    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        LIVE.fetch_sub(layout.size(), Ordering::SeqCst);
        unsafe { System.dealloc(ptr, layout) }
    }
    unsafe fn realloc(&self, ptr: *mut u8, old: Layout, size: usize) -> *mut u8 {
        let value = unsafe { System.realloc(ptr, old, size) };
        if !value.is_null() {
            LIVE.fetch_sub(old.size(), Ordering::SeqCst);
            acquired(size);
        }
        value
    }
}
#[global_allocator]
static ALLOCATOR: Measured = Measured;

#[test]
fn restore_payload_peak_tracks_one_object_instead_of_the_total_library() {
    const SIZE: usize = 4 * 1024 * 1024;
    const OBJECTS: usize = 12;
    let dir = tempfile::tempdir().unwrap();
    let mut source_db = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    for index in 0..OBJECTS {
        let mut bytes = vec![b'x'; SIZE];
        bytes[0] = index as u8;
        source::import_source(&mut source_db, &bytes, "synthetic.bin", None).unwrap();
    }
    let snapshot = dir.path().join("snapshot.sqlite");
    backup::backup(&source_db, snapshot.to_str().unwrap()).unwrap();
    let mut target = init_workspace(dir.path().join("target.sqlite").to_str().unwrap()).unwrap();
    let baseline = LIVE.load(Ordering::SeqCst);
    PEAK.store(baseline, Ordering::SeqCst);
    backup::restore(snapshot.to_str().unwrap(), &mut target).unwrap();
    let extra_peak = PEAK.load(Ordering::SeqCst).saturating_sub(baseline);
    eprintln!(
        "RESTORE_RUST_ALLOCATION_PEAK_BYTES={extra_peak}; largest_object={SIZE}; total_original_bytes={}; excludes_SQLite_C_and_process_RSS",
        SIZE * OBJECTS
    );
    assert!(
        extra_peak < 2 * SIZE + 8 * 1024 * 1024,
        "restoration retained the aggregate CAS payload: {extra_peak}"
    );
    assert!(backup::verify_counts(&source_db, &target).unwrap());
}
