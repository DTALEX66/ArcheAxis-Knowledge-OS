//! Single owned desktop session. Credentials arrive on inherited stdin only.
//! This is not a multi-user role service or protection against same-user memory access.
use archeaxis_store_sqlite::writer::{Store,StoreError};
use axum::{Router,Json,extract::{Request,State},http::{StatusCode,Method},middleware::{self,Next},response::{Response,IntoResponse}};
use serde::Deserialize;
use std::{io::Read,sync::mpsc,time::Duration};

#[derive(Clone,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Launch {launch_token:String,session_id:String}
impl Launch {
    pub fn from_stdin()->Result<Self,&'static str> {
        // A std thread (not the async blocking pool) lets main exit on a parent
        // that holds stdin open. Never include input or parse details in errors.
        let (send,receive)=mpsc::channel();
        std::thread::spawn(move||{
            let mut bytes=Vec::new();
            let result=std::io::stdin().take(4097).read_to_end(&mut bytes);
            let _=send.send(result.map(|_|bytes));
        });
        let bytes=receive.recv_timeout(Duration::from_secs(5)).map_err(|_|"launch input timed out")?
            .map_err(|_|"launch input failed")?;
        if bytes.len()>4096{return Err("launch input exceeds limit");}
        let launch:Self=serde_json::from_slice(&bytes).map_err(|_|"invalid launch input")?;
        if !hex(&launch.launch_token,64)||!hex(&launch.session_id,32){return Err("invalid launch identity");}
        Ok(launch)
    }
}
fn hex(s:&str,n:usize)->bool{s.len()==n&&s.bytes().all(|b|b.is_ascii_hexdigit())}
#[derive(Clone)]
struct Session {launch:Launch,workspace_db:String}

/// Wrap every route, including fallbacks, before binding the production listener.
pub async fn protect(router:Router,store:&Store,launch:Launch)->Result<Router,StoreError> {
    let workspace_db=store.submit(|conn|conn.query_row("SELECT file FROM pragma_database_list WHERE name='main'",[],|r|r.get::<_,String>(0))).await??;
    Ok(router.layer(middleware::from_fn_with_state(Session{launch,workspace_db},authenticate)))
}
fn error(status:StatusCode,code:&str,message:&str)->Response {
    (status,Json(serde_json::json!({"code":code,"message":message,"retryable":false}))).into_response()
}
async fn authenticate(State(session):State<Session>,request:Request,next:Next)->Response {
    let values=request.headers().get_all("x-archeaxis-launch-token");
    let mut values=values.iter();
    let value=values.next().map(|v|v.as_bytes()).unwrap_or_default();
    let expected=session.launch.launch_token.as_bytes();
    let valid=value.len()==expected.len()&&value.iter().zip(expected).fold(0u8,|diff,(a,b)|diff|(a^b))==0;
    if !valid||values.next().is_some(){return error(StatusCode::UNAUTHORIZED,"AAK-AUTH-001","invalid launch credentials");}
    // Formal desktop is a native client. Do not allow browser origins to turn
    // this localhost API into a credentialed cross-origin write surface.
    if request.headers().contains_key("origin") {return error(StatusCode::FORBIDDEN,"AAK-AUTH-002","browser origin not allowed");}
    if request.method()==Method::GET&&request.uri().path()=="/api/v1/system/version" {
        return Json(serde_json::json!({"runtime":"archeaxis-api","contract":"0.1.0-outline",
            "schema_version":archeaxis_store_sqlite::SCHEMA_VERSION,
            "session_id":session.launch.session_id,"workspace_db":session.workspace_db})).into_response();
    }
    next.run(request).await
}
