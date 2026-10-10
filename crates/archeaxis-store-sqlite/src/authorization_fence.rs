//! Restore-owned authorization fence in existing workspace_meta; no second DB/table.
use rusqlite::{Connection, OptionalExtension};
pub const KEY: &str = "authorization_restore_fence";
pub const SCHEMA: &str = "archeaxis.authorization-restore-fence/v1";

/// Call exactly once under the staged archive restore transaction, after all rows
/// are restored and checked, before publication. Never inherit a backup's epoch.
/// Document/history and archive bytes are untouched; only this Core-owned meta key changes.
pub fn install_after_restore(conn:&Connection)->rusqlite::Result<()> {
    if conn.is_autocommit() {
        return Err(rusqlite::Error::InvalidParameterName("restore fence requires active restore transaction".into()));
    }
    conn.execute(
        "INSERT INTO workspace_meta(key,value)
         SELECT ?1,json_object('schema',?2,'epoch',lower(hex(randomblob(16))),
           'blocked_grant_ids',json(COALESCE((SELECT json_group_array(document_id) FROM (
             SELECT DISTINCT document_id FROM document_versions
             WHERE json_type(editor_json,'$.attrs.archeaxis_context_grant') IS NOT NULL
                OR json_type(editor_json,'$.attrs.archeaxis_asset_context_grant') IS NOT NULL
             ORDER BY document_id)), '[]')))
         ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        rusqlite::params![KEY,SCHEMA],
    )?;
    Ok(())
}

/// Before every grant admission AND post-worker publication check. New grant IDs
/// created by an explicit trusted human action after restore may authorize anew.
/// Removing a namespace, modifying state or restoring old versions cannot clear this fence.
pub fn assert_grant_not_fenced(conn:&Connection,document_id:&str)->rusqlite::Result<()> {
    let raw:Option<String>=conn.query_row("SELECT value FROM workspace_meta WHERE key=?1",[KEY],|r|r.get(0)).optional()?;
    let Some(raw)=raw else {return Ok(());}; // Existing ordinary workspace compatibility.
    let valid:bool=conn.query_row(
        "SELECT CASE WHEN json_valid(?1) THEN
           json_extract(?1,'$.schema')=?2 AND json_type(?1,'$.blocked_grant_ids')='array'
           AND json_type(?1,'$.epoch')='text' AND length(json_extract(?1,'$.epoch'))=32
           AND NOT EXISTS(SELECT 1 FROM json_each(?1,'$.blocked_grant_ids') WHERE type!='text' OR length(value)=0)
         ELSE 0 END",rusqlite::params![raw,SCHEMA],|r|r.get(0),
    )?;
    if !valid {return Err(rusqlite::Error::InvalidParameterName("unknown or corrupt restore authorization fence; deny consumption".into()));}
    let blocked:bool=conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM json_each(?1,'$.blocked_grant_ids') WHERE value=?2)",
        rusqlite::params![raw,document_id],|r|r.get(0),
    )?;
    if blocked {return Err(rusqlite::Error::InvalidParameterName("restored grant requires a new explicit human authorization object".into()));}
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture()->Connection {
        let c=Connection::open_in_memory().unwrap();
        c.execute_batch("CREATE TABLE workspace_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE document_versions(document_id TEXT,version INTEGER,editor_json TEXT);").unwrap();c
    }
    fn grant(c:&Connection,id:&str,version:i64,namespace:&str,state:&str) {
        c.execute("INSERT INTO document_versions VALUES(?1,?2,json_object('attrs',json_object(?3,json_object('state',?4))))",
            rusqlite::params![id,version,namespace,state]).unwrap();
    }
    #[test]
    fn restored_historical_grants_are_fenced_and_new_identity_is_allowed_until_next_restore() {
        let mut c=fixture();
        grant(&c,"old",1,"archeaxis_context_grant","granted");
        grant(&c,"old",2,"archeaxis_context_grant","revoked");
        grant(&c,"asset-old",1,"archeaxis_asset_context_grant","granted");
        let history:String=c.query_row("SELECT editor_json FROM document_versions WHERE document_id='old' AND version=1",[],|r|r.get(0)).unwrap();
        assert_grant_not_fenced(&c,"old").unwrap();
        let tx=c.transaction().unwrap();install_after_restore(&tx).unwrap();tx.commit().unwrap();
        assert!(assert_grant_not_fenced(&c,"old").is_err());assert!(assert_grant_not_fenced(&c,"asset-old").is_err());
        grant(&c,"old",3,"archeaxis_context_grant","granted");
        assert!(assert_grant_not_fenced(&c,"old").is_err());
        grant(&c,"new-human-object",1,"archeaxis_context_grant","granted");
        assert_grant_not_fenced(&c,"new-human-object").unwrap();
        let first:String=c.query_row("SELECT value FROM workspace_meta WHERE key=?1",[KEY],|r|r.get(0)).unwrap();
        let tx=c.transaction().unwrap();install_after_restore(&tx).unwrap();tx.commit().unwrap();
        let second:String=c.query_row("SELECT value FROM workspace_meta WHERE key=?1",[KEY],|r|r.get(0)).unwrap();
        assert_ne!(first,second);assert!(assert_grant_not_fenced(&c,"new-human-object").is_err());
        assert_eq!(history,c.query_row::<String,_,_>("SELECT editor_json FROM document_versions WHERE document_id='old' AND version=1",[],|r|r.get(0)).unwrap());
    }
    #[test]
    fn unknown_corrupt_fence_denies_and_nontransaction_install_refuses() {
        let c=fixture();assert!(install_after_restore(&c).is_err());
        for raw in ["broken",r#"{"schema":"future","epoch":"00000000000000000000000000000000","blocked_grant_ids":[]}"#] {
            c.execute("INSERT OR REPLACE INTO workspace_meta VALUES(?1,?2)",rusqlite::params![KEY,raw]).unwrap();
            assert!(assert_grant_not_fenced(&c,"new").is_err());
        }
    }
}
