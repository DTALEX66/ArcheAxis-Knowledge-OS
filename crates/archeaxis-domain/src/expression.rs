//! Bounded authored expression metadata on existing immutable Document versions.
//! Read paths do not validate or rewrite historical unknown attrs. No engine execution.
use crate::document::Error;
use rusqlite::{Connection, OptionalExtension};
use serde::Deserialize;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use sha2::{Digest, Sha256};

pub const SCHEMA: &str = "archeaxis.expression/v1";
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Expression { schema: String, nodes: Vec<Node>, edges: Vec<Edge>, context: Option<Context>, capability_metadata: Option<Value> }
#[derive(Debug, Deserialize, PartialEq)]
#[serde(rename_all="snake_case")]
enum NodeType { Text, Media }
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Node { id:String, #[serde(rename="type")] kind:NodeType, x:f64,y:f64,width:f64,height:f64,text:String,media:Option<Media> }
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Media {source_id:String,sha256:String,media_type:String}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Edge {id:String,#[serde(rename="fromNode")]from_node:String,#[serde(rename="toNode")]to_node:String,label:String}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Context {knowledge_id:Option<String>,course_id:Option<String>,teaching_record_id:Option<String>}
fn bad(message:&'static str)->Error {Error::Invalid(message)}
fn token(s:&str,max:usize)->Result<(),Error>{if s.is_empty()||s.len()>max||s=="."||s==".."||!s.bytes().all(|b|b.is_ascii_alphanumeric()||matches!(b,b'_'|b'-'|b'.')){return Err(bad("expression ID must be a bounded ASCII token"));}Ok(())}
fn descriptor(v:&Value,depth:usize)->Result<(),Error>{
 if depth>4{return Err(bad("capability metadata depth exceeds limit"));}
 match v {Value::String(s) if s.len()>4096=>return Err(bad("capability descriptor string exceeds limit")),Value::Array(a)=>{if a.len()>32{return Err(bad("capability descriptor array exceeds limit"));}for x in a{descriptor(x,depth+1)?;}},Value::Object(o)=>{if o.len()>32{return Err(bad("capability descriptor object exceeds limit"));}for(k,x)in o{token(k,128)?;descriptor(x,depth+1)?;}},_=>{}}Ok(())
}
/// Header MIME recognition from CAS bytes, never filename/extension or user declaration.
/// This is type admission, not a decoder or a promise that a renderer can play the asset.
fn actual_mime(b:&[u8])->Option<&'static str>{
 if b.len()>=24&&b.starts_with(b"\x89PNG\r\n\x1a\n")&&&b[12..16]==b"IHDR"{return Some("image/png");}
 if b.len()>=4&&b.starts_with(b"\xff\xd8\xff"){return Some("image/jpeg");}
 if b.len()>=10&&(b.starts_with(b"GIF87a")||b.starts_with(b"GIF89a")){return Some("image/gif");}
 if b.len()>=12&&b.starts_with(b"RIFF") {let size=u32::from_le_bytes(b[4..8].try_into().ok()?) as usize;if size.checked_add(8)?!=b.len(){return None;}if &b[8..12]==b"WEBP"{return Some("image/webp");}if &b[8..12]==b"WAVE"{return Some("audio/wav");}}
 if b.len()>=10&&b.starts_with(b"ID3"){return Some("audio/mpeg");}
 if b.len()>=4&&b[0]==0xff&&(b[1]&0xe0)==0xe0&&(b[1]&0x18)!=0x08&&(b[1]&0x06)!=0&&(b[2]&0xf0)!=0xf0&&(b[2]&0x0c)!=0x0c{return Some("audio/mpeg");}
 if b.len()>=16&&&b[4..8]==b"ftyp" {let size=u32::from_be_bytes(b[..4].try_into().ok()?) as usize;if size>=16&&size<=b.len()&&size<=4096&&[b"isom",b"iso2",b"mp41",b"mp42",b"avc1",b"M4V "].iter().any(|brand|b[8..size].windows(4).any(|x|x==*brand)){return Some("video/mp4");}}
 if b.starts_with(b"\x1a\x45\xdf\xa3")&&b[..b.len().min(4096)].windows(4).any(|x|x==b"webm"){return Some("video/webm");}None
}
fn context(conn:&Connection,c:&Context)->Result<(),Error>{
 for id in [&c.knowledge_id,&c.course_id,&c.teaching_record_id].into_iter().flatten(){token(id,256)?;}
 if let Some(id)=&c.knowledge_id {let exists:bool=conn.query_row("SELECT EXISTS(SELECT 1 FROM knowledge WHERE knowledge_id=?1)",[id],|r|r.get(0))?;if !exists{return Err(bad("expression knowledge reference missing"));}}
 let course=if let Some(id)=&c.course_id {Some(crate::course::read_candidate(conn,id)?.ok_or_else(||bad("expression course reference missing"))?)}else{None};
 if let(Some(k),Some(course))=(&c.knowledge_id,&course){if !course["bindings"].as_array().is_some_and(|a|a.iter().any(|b|b["knowledge_id"]==k.as_str()&&b["knowledge_version"]==k.as_str())){return Err(bad("expression course and knowledge mismatch"));}}
 if let Some(id)=&c.teaching_record_id {
 let item=crate::teaching::get(conn,id).map_err(|_|bad("expression teaching reference invalid"))?.ok_or_else(||bad("expression teaching reference missing"))?;
 if item.withdrawn{return Err(bad("expression teaching reference withdrawn"));}
 if !matches!(item.record.kind,crate::teaching::RecordKind::Proposal|crate::teaching::RecordKind::Revision|crate::teaching::RecordKind::Delivery){return Err(bad("expression teaching reference must be proposal revision or delivery"));}
 if c.knowledge_id.as_ref().is_some_and(|k|k!=&item.record.knowledge_id){return Err(bad("expression teaching and knowledge mismatch"));}
 if let Some(id)=&c.course_id {if item.record.course_id.as_ref().is_some_and(|bound|bound!=id){return Err(bad("expression teaching and course mismatch"));}}
 // Even when knowledge_id is omitted, the selected course must bind the teaching record knowledge.
 if let Some(course)=&course {if !course["bindings"].as_array().is_some_and(|a|a.iter().any(|b|b["knowledge_id"]==item.record.knowledge_id&&b["knowledge_version"]==item.record.knowledge_version)){return Err(bad("expression course and teaching knowledge mismatch"));}}
 }Ok(())
}
/// Invoked only inside Document append's transaction before any version/block insert.
/// Payload is validated in place, never normalized: null/absent and unknown unrelated attrs persist.
pub fn validate_editor(conn:&Connection,editor:&Value)->Result<(),Error>{
 let Some(raw)=editor.get("attrs").and_then(|v|v.get("archeaxis_expression"))else{return Ok(());};
 let e:Expression=serde_json::from_value(raw.clone()).map_err(|_|bad("invalid expression DTO or unknown fields"))?;
 if e.schema!=SCHEMA{return Err(bad("unsupported expression schema"));}
 if e.nodes.len()>500||e.edges.len()>1000{return Err(bad("expression node or edge limit exceeded"));}
 let mut ids=BTreeSet::new();
 let mut media_cache=BTreeMap::<String,String>::new(); let mut media_total=0usize;
 for n in &e.nodes {token(&n.id,128)?;if !ids.insert(n.id.clone()){return Err(bad("duplicate expression node ID"));}
 if !n.x.is_finite()||!n.y.is_finite()||n.x.abs()>100000.0||n.y.abs()>100000.0||!n.width.is_finite()||!n.height.is_finite()||!(1.0..=10000.0).contains(&n.width)||!(1.0..=10000.0).contains(&n.height){return Err(bad("expression geometry is outside finite bounds"));}
 if n.text.len()>16384{return Err(bad("expression node text exceeds UTF8 byte limit"));}
 match(&n.kind,&n.media){(NodeType::Text,None)=>{},(NodeType::Media,Some(m))=>{
 token(&m.source_id,256)?;if m.sha256.len()!=64||!m.sha256.bytes().all(|b|b.is_ascii_digit()||(b'a'..=b'f').contains(&b)){return Err(bad("invalid expression media hash"));}
 let digest:Option<String>=conn.query_row("SELECT sha256 FROM sources WHERE source_id=?1",[&m.source_id],|r|r.get(0)).optional()?;
 if digest.as_ref()!=Some(&m.sha256){return Err(bad("expression media source hash mismatch or missing"));}
 let mime=if let Some(mime)=media_cache.get(&m.sha256){mime.clone()}else{
 let bytes=archeaxis_store_sqlite::raw_objects::read_bounded(conn,&m.sha256,32*1024*1024)?;
 if hex::encode(Sha256::digest(&bytes))!=m.sha256{return Err(bad("expression CAS content hash mismatch"));}
 media_total=media_total.checked_add(bytes.len()).ok_or_else(||bad("expression media byte budget"))?;
 if media_total>64*1024*1024{return Err(bad("expression media total byte budget"));}
 let mime=actual_mime(&bytes).ok_or_else(||bad("expression CAS media header unsupported"))?.to_owned();media_cache.insert(m.sha256.clone(),mime.clone());mime};
 if mime!=m.media_type{return Err(bad("expression media MIME does not match supported CAS header"));}
 },_=>return Err(bad("expression media/text node mismatch"))}
 }
 let mut edges=BTreeSet::new();for e in &e.edges {token(&e.id,128)?;token(&e.from_node,128)?;token(&e.to_node,128)?;if !edges.insert(e.id.clone()){return Err(bad("duplicate expression edge ID"));}if !ids.contains(&e.from_node)||!ids.contains(&e.to_node){return Err(bad("expression edge endpoint missing"));}if e.label.len()>1024{return Err(bad("expression edge label exceeds UTF8 byte limit"));}}
 if let Some(c)=&e.context{context(conn,c)?;}
 if let Some(v)=&e.capability_metadata {if !v.is_object()||v.to_string().len()>16384{return Err(bad("capability metadata must be a bounded inert object"));}descriptor(v,0)?;}
 Ok(())
}



/// Deterministic pure-text projection for recognized expression nodes/captions and labels.
/// Unknown historical attrs never acquire invented text semantics. No lookup or normalization.
pub fn text_projection(editor:&Value)->Option<String>{
 let raw=editor.get("attrs")?.get("archeaxis_expression")?;
 let e:Expression=serde_json::from_value(raw.clone()).ok()?;if e.schema!=SCHEMA{return None;}
 let text=e.nodes.iter().map(|n|n.text.as_str()).chain(e.edges.iter().map(|e|e.label.as_str())).filter(|s|!s.trim().is_empty()).collect::<Vec<_>>().join("\n");
 if text.is_empty(){None}else{Some(text)}
}
