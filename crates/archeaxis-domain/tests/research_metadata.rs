use archeaxis_domain::document;
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;
use serde_json::{Value,json};
fn research(reference:Value)->Value {
 json!({"schema":"archeaxis.research/v1","question":"问题😀 保留原文",
 "materials":[{"id":"material","note":"原件材料","reference":reference}],
 "hypotheses":[],"methods":[{"id":"method","text":"方法独立于结论","references":[]}],
 "experiments":[],"counterevidence":[{"id":"counter","text":"反证尚未解决","references":[reference]}],
 "conclusions":[{"id":"conclusion","text":"暂定结论 <script>inert</script>","sources":[reference],"basis":[]}],
 "unresolved":[{"id":"open","text":"未决问题","references":[]}]})
}
fn editor(value:Value)->Value {json!({"type":"doc","attrs":{"archeaxis_research":value,"future_payload":{"opaque":[true,null,123]}},"content":[]})}
fn count(conn:&Connection)->i64 {conn.query_row("SELECT COUNT(*) FROM document_versions",[],|r|r.get(0)).unwrap()}
#[test]
fn authored_research_relations_restart_history_and_reference_separation() {
 let dir=tempfile::tempdir().unwrap();let db=dir.path().join("workspace.sqlite");let mut c=init_workspace(db.to_str().unwrap()).unwrap();
 let material=document::create_optional(&mut c,None,None,"原件文档",json!({"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"evidence"},"content":[{"type":"text","text":"原始依据"}]}]})).unwrap();
 let reference=json!({"kind":"document","document_id":material["document_id"],"version":1,"block_id":"evidence"});
 let mut e=editor(research(reference.clone()));e["attrs"]["archeaxis_relations"]=json!({"schema":"archeaxis.relations/v1","relations":[{"id":"related","kind":"contradicts","label":"反证关联","target":reference}]});
 let first=document::create_optional_with_request(&mut c,None,None,"研究",e.clone(),Some("research-create")).unwrap();
 let id=first["document_id"].as_str().unwrap().to_owned();
 assert_eq!(document::create_optional_with_request(&mut c,None,None,"研究",e.clone(),Some("research-create")).unwrap(),first);
 e["attrs"]["archeaxis_research"]["conclusions"][0]["basis"]=json!([reference]);
 e["attrs"]["archeaxis_relations"]["relations"]=json!([]);
 let second=document::save(&mut c,&id,1,e.clone()).unwrap();
 assert!(document::save(&mut c,&id,1,e).is_err());
 drop(c);let c=init_workspace(db.to_str().unwrap()).unwrap();
 assert_eq!(document::read(&c,&id,None).unwrap(),second);
 assert_eq!(document::read(&c,&id,Some(1)).unwrap(),first);
 assert_eq!(document::read(&c,material["document_id"].as_str().unwrap(),None).unwrap(),material);
 assert!(second["text_projection"].as_str().unwrap().contains("反证尚未解决"));
 assert_eq!(first["editor_json"]["attrs"]["archeaxis_research"]["conclusions"][0]["basis"],json!([]));
 assert_eq!(second["editor_json"]["attrs"]["future_payload"],first["editor_json"]["attrs"]["future_payload"]);
}
#[test]
fn malformed_references_and_unknown_new_schemas_leave_no_partial_versions() {
 let dir=tempfile::tempdir().unwrap();let mut c=init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
 let material=document::create_optional(&mut c,None,None,"材料",json!({"type":"doc","content":[]})).unwrap();
 let valid=editor(research(json!({"kind":"document","document_id":material["document_id"],"version":1,"block_id":null})));
 let mutations:Vec<Box<dyn Fn(&mut Value)>>=vec![
 Box::new(|e|e["attrs"]["archeaxis_research"]["schema"]=json!("archeaxis.research/v999")),
 Box::new(|e|e["attrs"]["archeaxis_research"]["question"]=json!("中".repeat(5462))),
 Box::new(|e|e["attrs"]["archeaxis_research"]["materials"][0]["reference"]["version"]=json!(99)),
 Box::new(|e|e["attrs"]["archeaxis_research"]["materials"][0]["reference"]["block_id"]=json!("missing")),
 Box::new(|e|e["attrs"]["archeaxis_research"]["methods"][0]["id"]=json!("material")),
 Box::new(|e|e["attrs"]["archeaxis_research"]["search_results"]=json!(["invented"])),
 Box::new(|e|e["attrs"]["archeaxis_relations"]=json!({"schema":"archeaxis.relations/v1","relations":[{"id":"link","kind":"related","label":"missing","target":{"kind":"knowledge","knowledge_id":"missing"}}]})),
 ];
 for mutate in mutations {let before=count(&c);let mut e=valid.clone();mutate(&mut e);assert!(document::create_optional(&mut c,None,None,"非法研究",e).is_err());assert_eq!(count(&c),before);}
}
#[test]
fn empty_nonlinear_research_and_ordinary_documents_remain_valid() {
 let dir=tempfile::tempdir().unwrap();let mut c=init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
 let empty=json!({"schema":"archeaxis.research/v1","question":"","materials":[],"hypotheses":[],"methods":[],"experiments":[],"counterevidence":[],"conclusions":[],"unresolved":[]});
 let d=document::create_optional(&mut c,None,None,"待研究",editor(empty)).unwrap();assert_eq!(d["text_projection"],"");
 let ordinary=json!({"type":"doc","attrs":{"future":{"archeaxis_research":"unknown opaque"}},"content":[]});
 assert_eq!(document::create_optional(&mut c,None,None,"普通文档",ordinary.clone()).unwrap()["editor_json"],ordinary);
}
