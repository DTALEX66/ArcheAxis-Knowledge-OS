//! Rebuildable relation/backlink projection. Graph and list share one snapshot DTO.
use crate::{collection::{self,PropertyKind}, document::{self,Error}, object_reference::{self,Reference}, research::{Relations,Relation,RELATION_SCHEMA}};
use rusqlite::{Connection,params};
use serde_json::{Value,json};
use sha2::{Digest,Sha256};
use std::collections::{BTreeMap,BTreeSet};

fn reference(document_id:&str,version:i64)->Reference {
    Reference::Document{document_id:document_id.into(),version,block_id:None}
}
fn key(reference:&Reference)->String {serde_json::to_string(reference).expect("scalar reference serialization")}
fn add_node(conn:&Connection,reference:&Reference,nodes:&mut BTreeMap<String,Value>) {
    let key=key(reference);
    if nodes.contains_key(&key) {return;}
    let value=match object_reference::resolve(conn,reference) {
        Ok(value)=>json!({"key":key,"reference":reference,"status":"resolved","object":value}),
        Err(_)=>json!({"key":key,"reference":reference,"status":"unavailable","object":null}),
    };nodes.insert(key,value);
}
fn relation_metadata_valid(r:&Relations)->bool {
    if r.schema!=RELATION_SCHEMA || r.relations.len()>256 {return false;}
    let mut ids=BTreeSet::new();
    let token=|s:&str|!s.is_empty() && s.len()<=256 && s!="." && s!=".." && s.bytes().all(|b|b.is_ascii_alphanumeric() || matches!(b,b'_'|b'-'|b'.'));
    r.relations.iter().all(|relation| {
        let id=&relation.id;
        if id.is_empty() || id.len()>128 || !id.bytes().all(|b|b.is_ascii_alphanumeric() || matches!(b,b'_'|b'-')) || !ids.insert(id) || relation.label.len()>1024 {return false;}
        match &relation.target {
            Reference::Document{document_id,version,block_id}=>token(document_id) && *version>0 && block_id.as_ref().is_none_or(|b|token(b)),
            Reference::Source{source_id,sha256}=>token(source_id) && sha256.len()==64 && sha256.bytes().all(|b|b.is_ascii_digit() || (b'a'..=b'f').contains(&b)),
            Reference::Knowledge{knowledge_id}=>token(knowledge_id),
        }
    })
}
fn relations(editor:&Value)->Option<Result<Relations,()>> {
    let raw=editor["attrs"].get("archeaxis_relations")?;
    Some(serde_json::from_value::<Relations>(raw.clone()).map_err(|_|()).and_then(|r|if relation_metadata_valid(&r) {Ok(r)}else{Err(())}))
}
struct DerivedEdge { from:Reference, relation:Relation, record_id:String, property_id:String }
fn collection_edges(editor:&Value)->Option<Result<Vec<DerivedEdge>,()>> {
    let raw=editor["attrs"].get("archeaxis_collection")?;
    Some((|| {
        let c=collection::parse(raw).map_err(|_|())?;
        collection::validate_shape(&c).map_err(|_|())?;
        let mut edges=Vec::new();
        for record in &c.records {
            for p in c.properties.iter().filter(|p|p.kind==PropertyKind::Relation) {
                if let Some(values)=record.values.get(&p.property_id).and_then(Value::as_array) {
                    for (index,value) in values.iter().enumerate() {
                        let target=serde_json::from_value(value.clone()).map_err(|_|())?;
                        edges.push(DerivedEdge{from:record.reference.clone(),relation:Relation{id:format!("collection:{}:{}:{}",record.record_id,p.property_id,index),kind:crate::research::RelationKind::Related,label:p.name.clone(),target},record_id:record.record_id.clone(),property_id:p.property_id.clone()});
                    }
                }
            }
        }
        Ok(edges)
    })())
}
struct Projection<'a> {conn:&'a Connection,nodes:BTreeMap<String,Value>,edges:Vec<Value>,omitted:usize}
impl Projection<'_> {
    fn append(&mut self,source:&Value,from:&Reference,relation:&Relation,direction:&str,collection:Option<(&str,&str)>) {
        // Bounded transport/visual projection. Omission is explicit; original
        // canonical definitions and paged collection queries remain available.
        if self.edges.len()>=1000 {self.omitted+=1;return;}
        add_node(self.conn,from,&mut self.nodes);add_node(self.conn,&relation.target,&mut self.nodes);
        let mut edge=json!({"id":format!("{}:{}:{}",source["document_id"].as_str().unwrap(),source["version"],relation.id),"from":key(from),"to":key(&relation.target),"relation":relation,"source_snapshot":{"document_id":source["document_id"],"version":source["version"],"content_sha256":source["content_sha256"]},"direction":direction,"origin":if collection.is_some(){"collection_property"}else{"document_relation"}});
        if let Some((record,property))=collection {edge["record_id"]=json!(record);edge["property_id"]=json!(property);}
        self.edges.push(edge);
    }
}
fn matches_center(r:&Reference,id:&str,version:i64)->bool {matches!(r,Reference::Document{document_id,version:v,..} if document_id==id && *v==version)}
fn project_source(p:&mut Projection<'_>,unsupported:&mut Vec<Value>,source:&Value,id:&str,version:i64,own_center:bool) {
    let source_ref=reference(source["document_id"].as_str().unwrap(),source["version"].as_i64().unwrap());
    match relations(&source["editor_json"]) {
        Some(Ok(r))=>for relation in &r.relations {if own_center || matches_center(&relation.target,id,version) {p.append(source,&source_ref,relation,if own_center{"outgoing"}else{"backlink"},None);}},
        Some(Err(()))=>unsupported.push(json!({"document_id":source["document_id"],"version":source["version"],"status":"unsupported_relation_metadata"})),
        None=>{},
    }
    match collection_edges(&source["editor_json"]) {
        Some(Ok(edges))=>for edge in edges {
            let outgoing=own_center || matches_center(&edge.from,id,version);
            if outgoing || matches_center(&edge.relation.target,id,version) {
                p.append(source,&edge.from,&edge.relation,if outgoing{"outgoing"}else{"backlink"},Some((&edge.record_id,&edge.property_id)));
            }
        },
        Some(Err(()))=>unsupported.push(json!({"document_id":source["document_id"],"version":source["version"],"status":"unsupported_collection_metadata"})),
        None=>{},
    }
}
/// Backlinks come from current source versions and point to the exact requested
/// center version. The scan cursor is explicit even when a page has zero matches.
pub fn query(conn:&Connection,id:&str,version:Option<i64>,cursor:Option<&str>)->Result<Value,Error> {
    let tx=conn.unchecked_transaction()?;
    let result=query_snapshot(&tx,id,version,cursor)?;
    tx.commit()?;
    Ok(result)
}
fn query_snapshot(conn:&Connection,id:&str,version:Option<i64>,cursor:Option<&str>)->Result<Value,Error> {
    if cursor.is_some_and(|s|s.len()>256 || !s.bytes().all(|b|b.is_ascii_alphanumeric() || matches!(b,b'_'|b'-'|b'.'))) {
        return Err(Error::Invalid("relation scan cursor is invalid"));
    }
    let center=document::read(conn,id,version)?;let version=center["version"].as_i64().ok_or(Error::Invalid("document version is invalid"))?;
    let center_ref=reference(id,version);let mut nodes=BTreeMap::new();add_node(conn,&center_ref,&mut nodes);
    let mut projection=Projection{conn,nodes,edges:Vec::new(),omitted:0};let mut unsupported=Vec::new();
    project_source(&mut projection,&mut unsupported,&center,id,version,true);
    let mut statement=conn.prepare("SELECT document_id,current_version FROM documents WHERE document_id>?1 ORDER BY document_id LIMIT 21")?;
    let mut scanned:Vec<(String,i64)>=statement.query_map(params![cursor.unwrap_or("")],|row|Ok((row.get(0)?,row.get(1)?)))?.collect::<Result<_,_>>()?;
    let has_more=scanned.len()>20;if has_more {scanned.truncate(20);}
    let next=if has_more {scanned.last().map(|(id,_)|id.clone())}else{None};
    let mut page_bindings=Vec::new();
    for (source_id,source_version) in &scanned {
        let source=document::read(conn,source_id,Some(*source_version))?;
        page_bindings.push(json!({"document_id":source_id,"version":source_version,"content_sha256":source["content_sha256"]}));
        if source_id==id && *source_version==version {continue;}
        project_source(&mut projection,&mut unsupported,&source,id,version,false);
    }
    let snapshot_sha256=hex::encode(Sha256::digest(serde_json::to_vec(&json!({"center_hash":center["content_sha256"],"scan":page_bindings})).unwrap()));
    Ok(json!({"schema":"archeaxis.relation-projection/v1","snapshot_sha256":snapshot_sha256,"center":{"document_id":id,"version":version,"content_sha256":center["content_sha256"]},"scope":"current_source_versions_to_pinned_center","nodes":projection.nodes.into_values().collect::<Vec<_>>(),"edges":projection.edges,"omitted_edges":projection.omitted,"projection_truncated":projection.omitted>0,"unsupported_sources":unsupported,"scan":{"scanned":scanned.len(),"next_cursor":next,"complete":!has_more},"derived_only":true}))
}
