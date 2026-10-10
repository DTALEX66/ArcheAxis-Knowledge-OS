use archeaxis_domain::{document,relation_projection};
use archeaxis_store_sqlite::init_workspace;
use serde_json::{Value,json};
fn envelope(relations:Value)->Value {json!({"type":"doc","content":[],"attrs":{"archeaxis_relations":{"schema":"archeaxis.relations/v1","relations":relations}}})}
#[test]
fn graph_and_list_share_pinned_versions_after_relation_removal_and_restart() {
 let dir=tempfile::tempdir().unwrap();let db=dir.path().join("workspace.sqlite");let mut c=init_workspace(db.to_str().unwrap()).unwrap();
 let target=document::create_optional(&mut c,None,None,"依据",json!({"type":"doc","content":[]})).unwrap();let tid=target["document_id"].as_str().unwrap();
 let ref1=json!({"kind":"document","document_id":tid,"version":1,"block_id":null});
 let source=document::create_optional(&mut c,None,None,"研究关系",envelope(json!([{"id":"rel","kind":"supports","label":"支持","target":ref1}])),).unwrap();let sid=source["document_id"].as_str().unwrap();
 let graph=relation_projection::query(&c,tid,Some(1),None).unwrap();assert_eq!(graph["edges"].as_array().unwrap().len(),1);assert_eq!(graph["edges"][0]["direction"],"backlink");assert_eq!(graph["edges"][0]["source_snapshot"]["content_sha256"],source["content_sha256"]);
 document::save(&mut c,tid,1,json!({"type":"doc","content":[]})).unwrap();
 assert!(relation_projection::query(&c,tid,None,None).unwrap()["edges"].as_array().unwrap().is_empty());
 assert_eq!(relation_projection::query(&c,tid,Some(1),None).unwrap()["edges"],graph["edges"]);
 document::save(&mut c,sid,1,envelope(json!([]))).unwrap();drop(c);
 let c=init_workspace(db.to_str().unwrap()).unwrap();
 assert!(relation_projection::query(&c,tid,Some(1),None).unwrap()["edges"].as_array().unwrap().is_empty());
 let historical=relation_projection::query(&c,sid,Some(1),None).unwrap();assert_eq!(historical["edges"][0]["direction"],"outgoing");assert_eq!(historical["edges"][0]["relation"]["target"]["version"],1);
 assert_eq!(document::read(&c,sid,Some(1)).unwrap(),source);
}
#[test]
fn backlink_scan_does_not_claim_complete_when_page_has_no_matches() {
 let dir=tempfile::tempdir().unwrap();let mut c=init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
 let target=document::create_optional(&mut c,None,None,"target",json!({"type":"doc","content":[]})).unwrap();
 for i in 0..21 {document::create_optional_with_request(&mut c,None,None,"other",json!({"type":"doc","content":[]}),Some(&format!("other-{i}"))).unwrap();}
 let tid=target["document_id"].as_str().unwrap();let page=relation_projection::query(&c,tid,None,None).unwrap();assert_eq!(page["scan"]["scanned"],20);assert_eq!(page["scan"]["complete"],false);assert!(page["edges"].as_array().unwrap().is_empty());
 let next=page["scan"]["next_cursor"].as_str().unwrap();assert_eq!(relation_projection::query(&c,tid,None,Some(next)).unwrap()["scan"]["complete"],true);
 assert!(relation_projection::query(&c,tid,None,Some("../path")).is_err());
}

// SYNTHETIC pre-contract persisted metadata, not a supported current write path.
fn legacy_editor(c:&rusqlite::Connection,id:&str,editor:Value) {
 use sha2::{Digest,Sha256};let encoded=editor.to_string();let digest=hex::encode(Sha256::digest(encoded.as_bytes()));
 c.execute("UPDATE document_versions SET editor_json=?1,content_sha256=?2 WHERE document_id=?3 AND version=1",rusqlite::params![encoded,digest,id]).unwrap();
}
#[test]
fn malformed_legacy_relations_are_reported_without_breaking_other_projection_data() {
 let dir=tempfile::tempdir().unwrap();let mut c=init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
 let d=document::create_optional(&mut c,None,None,"legacy",json!({"type":"doc","content":[]})).unwrap();let id=d["document_id"].as_str().unwrap();
 let valid=json!({"id":"r","kind":"related","label":"ok","target":{"kind":"document","document_id":"missing_document","version":1}});
 for list in [json!([valid.clone(),valid.clone()]),json!([{ "id":"bad/id","kind":"related","label":"ok","target":{"kind":"document","document_id":"missing_document","version":1}}]),json!([{ "id":"r","kind":"related","label":"x".repeat(1025),"target":{"kind":"document","document_id":"missing_document","version":1}}]),json!([{ "id":"r","kind":"related","label":"ok","target":{"kind":"document","document_id":"missing_document","version":0}}])] {
  legacy_editor(&c,id,envelope(list));let p=relation_projection::query(&c,id,Some(1),None).unwrap();assert_eq!(p["unsupported_sources"][0]["document_id"],id);assert!(p["edges"].as_array().unwrap().is_empty());assert_eq!(p["center"]["version"],1);
 }
}
#[test]
fn valid_legacy_reference_to_missing_object_remains_unavailable_not_unsupported() {
 let dir=tempfile::tempdir().unwrap();let mut c=init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
 let d=document::create_optional(&mut c,None,None,"legacy",json!({"type":"doc","content":[]})).unwrap();let id=d["document_id"].as_str().unwrap();
 legacy_editor(&c,id,envelope(json!([{ "id":"r","kind":"related","label":"missing target","target":{"kind":"document","document_id":"missing_document","version":1}}])));
 let p=relation_projection::query(&c,id,Some(1),None).unwrap();assert!(p["unsupported_sources"].as_array().unwrap().is_empty());assert_eq!(p["edges"].as_array().unwrap().len(),1);assert!(p["nodes"].as_array().unwrap().iter().any(|n|n["status"]=="unavailable" && n["reference"]["document_id"]=="missing_document"));
}
fn collection_editor(from:&str,to:&str,rows:usize,links:usize)->Value {
 let records:Vec<_>=(0..rows).map(|i|json!({"record_id":format!("row_{i}"),"reference":{"kind":"document","document_id":from,"version":1},"values":{"related":(0..links).map(|_|json!({"kind":"document","document_id":to,"version":1})).collect::<Vec<_>>()}})).collect();
 json!({"type":"doc","content":[],"attrs":{"archeaxis_collection":{"schema":"archeaxis.collection/v1","properties":[{"property_id":"related","name":"关联文档","kind":"relation"}],"records":records,"views":[{"view_id":"all","name":"全部","kind":"table"}]},"foreign":{"preserve":true}}})
}
#[test]
fn collection_relations_are_bidirectional_and_keep_record_identity_and_definition_version() {
 let dir=tempfile::tempdir().unwrap();let path=dir.path().join("workspace.sqlite");let mut c=init_workspace(path.to_str().unwrap()).unwrap();
 let a=document::create_optional(&mut c,None,None,"记录 A",json!({"type":"doc","content":[]})).unwrap();let aid=a["document_id"].as_str().unwrap();
 let b=document::create_optional(&mut c,None,None,"目标 B",json!({"type":"doc","content":[]})).unwrap();let bid=b["document_id"].as_str().unwrap();
 let collection=document::create_optional(&mut c,None,None,"集合",collection_editor(aid,bid,1,1)).unwrap();let cid=collection["document_id"].as_str().unwrap();
 let out=relation_projection::query(&c,aid,Some(1),None).unwrap();let back=relation_projection::query(&c,bid,Some(1),None).unwrap();
 assert_eq!(out["edges"].as_array().unwrap().len(),1);assert_eq!(back["edges"].as_array().unwrap().len(),1);
 let e=&back["edges"][0];assert_eq!(e["direction"],"backlink");assert_eq!(e["origin"],"collection_property");assert_eq!(e["record_id"],"row_0");assert_eq!(e["property_id"],"related");assert_eq!(e["source_snapshot"]["content_sha256"],collection["content_sha256"]);
 assert!(e["from"].as_str().unwrap().contains(aid));assert_eq!(e["to"],out["edges"][0]["to"]);
 document::save(&mut c,bid,1,json!({"type":"doc","content":[]})).unwrap();assert!(relation_projection::query(&c,bid,None,None).unwrap()["edges"].as_array().unwrap().is_empty());
 document::save(&mut c,cid,1,collection_editor(aid,bid,1,0)).unwrap();drop(c);let c=init_workspace(path.to_str().unwrap()).unwrap();
 assert!(relation_projection::query(&c,bid,Some(1),None).unwrap()["edges"].as_array().unwrap().is_empty());
 assert_eq!(relation_projection::query(&c,cid,Some(1),None).unwrap()["edges"][0]["source_snapshot"]["version"],1);
 assert_eq!(document::read(&c,cid,Some(1)).unwrap(),collection);assert_eq!(document::read(&c,aid,None).unwrap(),a);
}
#[test]
fn collection_projection_bounds_are_explicit_and_never_rewrite_canonical_records() {
 let dir=tempfile::tempdir().unwrap();let mut c=init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();let a=document::create_optional(&mut c,None,None,"A",json!({"type":"doc","content":[]})).unwrap();let id=a["document_id"].as_str().unwrap();
 let saved=document::create_optional(&mut c,None,None,"many links",collection_editor(id,id,100,11)).unwrap();let cid=saved["document_id"].as_str().unwrap();
 let p=relation_projection::query(&c,cid,None,None).unwrap();assert_eq!(p["edges"].as_array().unwrap().len(),1000);assert_eq!(p["omitted_edges"],100);assert_eq!(p["projection_truncated"],true);assert_eq!(document::read(&c,cid,None).unwrap(),saved);
 let invalid=collection_editor(id,id,22,100);assert!(document::create_optional(&mut c,None,None,"over budget",invalid).is_err());
}
#[test]
fn legacy_collection_missing_targets_and_malformed_definitions_are_distinct() {
 let dir=tempfile::tempdir().unwrap();let mut c=init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();let a=document::create_optional(&mut c,None,None,"legacy",json!({"type":"doc","content":[]})).unwrap();let id=a["document_id"].as_str().unwrap();
 let raw=collection_editor(id,"missing_document",1,1);legacy_editor(&c,id,raw.clone());let p=relation_projection::query(&c,id,None,None).unwrap();assert_eq!(p["edges"].as_array().unwrap().len(),1);assert!(p["unsupported_sources"].as_array().unwrap().is_empty());assert!(p["nodes"].as_array().unwrap().iter().any(|n|n["status"]=="unavailable"));
 let mut bad=raw;bad["attrs"]["archeaxis_collection"]["records"][0]["values"]["related"][0]["version"]=json!(0);legacy_editor(&c,id,bad);let p=relation_projection::query(&c,id,None,None).unwrap();assert_eq!(p["unsupported_sources"][0]["status"],"unsupported_collection_metadata");assert!(p["edges"].as_array().unwrap().is_empty());
}
