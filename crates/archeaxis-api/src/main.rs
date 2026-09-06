//! archeaxis-api standalone server (the process a Supervisor starts).
//!
//! Usage: archeaxis-api <workspace-db-path> [port]
//! Requires a <=4096-byte launch JSON on stdin, closed by the parent within 5s.
//! See packages/contracts/v1/protocol-mapping.md (native launch slice).
//! Port defaults to 47831 (override with ARCHAXIS_VNEXT_PORT).
//! Serves the vNext local HTTP API on 127.0.0.1 — the handshake target for the
//! Avalonia Supervisor (sidecar-protocol versioned envelope is the message
//! contract; /api/v1/system/version is the first exchange).

use std::net::{Ipv4Addr, SocketAddr};

#[tokio::main]
async fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: archeaxis-api <workspace-db-path> [port]");
        std::process::exit(2);
    }
    let db_path = &args[1];
    let port: u16 = args
        .get(2)
        .and_then(|p| p.parse().ok())
        .or_else(|| {
            std::env::var("ARCHAXIS_VNEXT_PORT")
                .ok()
                .and_then(|p| p.parse().ok())
        })
        .unwrap_or(47831);

    let launch=match archeaxis_api::launch::Launch::from_stdin(){
        Ok(launch)=>launch,
        Err(message)=>{eprintln!("{message}");std::process::exit(2);}
    };
    let store = match archeaxis_store_sqlite::writer::Store::open(std::path::Path::new(db_path)) {
        Ok(store) => store,
        Err(e) => {
            eprintln!("failed to open workspace {db_path}: {e}");
            std::process::exit(1);
        }
    };
    let router=match archeaxis_api::launch::protect(archeaxis_api::router(store.clone()),&store,launch).await {
        Ok(router)=>router,Err(_)=>{eprintln!("workspace identity unavailable");std::process::exit(1);}
    };
    let addr = SocketAddr::from((Ipv4Addr::LOCALHOST, port));
    let listener = match tokio::net::TcpListener::bind(addr).await {
        Ok(l) => l,
        Err(e) => {
            eprintln!("cannot bind {addr}: {e}");
            std::process::exit(1);
        }
    };
    let bound_addr = listener.local_addr().expect("bound listener address");
    println!("archeaxis-api ready on http://{bound_addr}");
    axum::serve(listener, router).await.unwrap();
}
