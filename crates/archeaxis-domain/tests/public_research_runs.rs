use archeaxis_domain::public_research::{self as research, Begin, Request};
use archeaxis_store_sqlite::init_workspace;
use base64::{Engine as _, engine::general_purpose::STANDARD};
use serde_json::json;

fn request(conn: &mut rusqlite::Connection) -> Request {
    let state = archeaxis_domain::ui_state::read(conn).unwrap();
    Request {
        request_id: "public_test_1".into(),
        workspace_id: state["workspace_id"].as_str().unwrap().into(),
        restore_epoch: state["restore_epoch"].as_str().unwrap().into(),
        query: "spaced repetition".into(),
        families: vec!["encyclopedia".into(), "community".into(), "research".into()],
        limit: 1,
    }
}

#[test]
fn a_frozen_public_query_cannot_be_replaced_or_silently_reexecuted() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("research.sqlite").to_str().unwrap()).unwrap();
    let mut req = request(&mut conn);
    assert!(matches!(
        research::begin(&mut conn, &req).unwrap(),
        Begin::Started
    ));
    assert!(
        research::begin(&mut conn, &req).is_err(),
        "unfinished request must remain unknown"
    );
    req.query = "different query".into();
    assert!(
        research::begin(&mut conn, &req).is_err(),
        "same identity must not acquire new terms"
    );
    let row = research::read(&conn, "public_test_1").unwrap().unwrap();
    assert_eq!(row["state"], "unknown");
    assert_eq!(row["query"], "spaced repetition");
    assert_eq!(row["knowledge_admission"], "not_executed");
}

#[test]
fn failed_retrieval_is_durable_but_never_a_successful_empty_search() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("research.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let req = request(&mut conn);
    research::begin(&mut conn, &req).unwrap();
    research::fail(&mut conn, &req, "worker_timeout", false).unwrap();
    drop(conn);
    let conn = init_workspace(path.to_str().unwrap()).unwrap();
    let row = research::read(&conn, &req.request_id).unwrap().unwrap();
    assert_eq!(row["state"], "failed");
    assert_eq!(row["reason_code"], "worker_timeout");
    assert_eq!(row["provider_stop_state"], "unknown");
    assert_ne!(
        row["channels"],
        json!([]),
        "failure must not publish an empty complete response"
    );
}

#[test]
fn synthetic_response_bytes_and_derived_content_are_distinct_pinned_sources_after_reopen() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("research.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let mut req = request(&mut conn);
    req.families = vec!["community".into()];
    research::begin(&mut conn, &req).unwrap();
    let original = br#"{"items":[{"question_id":69100,"body":"<p>original</p>"}]}"#;
    let hit = json!({"id":"stackexchange:academia:question:69100","family":"community","provider":"stackexchange","title":"Synthetic question",
        "url":"https://academia.stackexchange.com/questions/69100","retrieved_at":"2026-10-21T00:00:00Z",
        "content":"full_text","excerpt":"original\r\n保留😀","locator":"question_id=69100;body","license":"CC BY-SA 3.0",
        "free_access":"free","upstream_revision":null,"representation":"html_text","truncated":false});
    let response = json!({"schema":"public-research-worker/v1","query":req.query,"families":req.families,
        "channels":[{"family":"community","provider":"stackexchange","status":"complete",
        "retrieved_at":"2026-10-21T00:00:00Z","request_url":"https://api.stackexchange.com/2.3/search/advanced?q=spaced%20repetition&site=academia&pagesize=1&sort=relevance&filter=withbody",
        "retry_after_seconds":null,"error_code":null,"raw_response_base64":STANDARD.encode(original),"hits":[hit]}]});
    let receipt = research::publish(&mut conn, &req, response).unwrap();
    assert_eq!(receipt["state"], "complete");
    assert!(receipt["channels"][0].get("raw_response_base64").is_none());
    let raw = &receipt["channels"][0]["raw_source"];
    assert_eq!(
        archeaxis_store_sqlite::raw_objects::read(&conn, raw["sha256"].as_str().unwrap()).unwrap(),
        original
    );
    let selected = research::materialize(
        &mut conn,
        &req.request_id,
        "community",
        "stackexchange:academia:question:69100",
    )
    .unwrap();
    assert_ne!(selected["reference"], selected["raw_reference"]);
    let bytes = archeaxis_store_sqlite::raw_objects::read(
        &conn,
        selected["reference"]["sha256"].as_str().unwrap(),
    )
    .unwrap();
    let derived = String::from_utf8(bytes).unwrap();
    assert!(derived.contains("派生内容快照"));
    assert!(derived.contains("original\r\n保留😀"));
    assert!(derived.contains(raw["sha256"].as_str().unwrap()));
    let again = research::materialize(
        &mut conn,
        &req.request_id,
        "community",
        "stackexchange:academia:question:69100",
    )
    .unwrap();
    assert_eq!(again, selected);
    drop(conn);
    let conn = init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(
        research::read(&conn, &req.request_id).unwrap().unwrap(),
        receipt
    );
    let count: i64 = conn
        .query_row("SELECT count(*) FROM sources", [], |row| row.get(0))
        .unwrap();
    assert_eq!(count, 2);
}

fn response(req: &Request) -> serde_json::Value {
    json!({"schema":"public-research-worker/v1","query":req.query,"families":req.families,
        "channels":[{"family":"community","provider":"stackexchange","status":"complete",
        "retrieved_at":"2026-10-21T00:00:00Z","request_url":"https://api.stackexchange.com/2.3/search/advanced?q=spaced+repetition&site=academia&pagesize=1&sort=relevance&filter=withbody",
        "retry_after_seconds":null,"error_code":null,"raw_response_base64":STANDARD.encode(b"{\"items\":[]}"),"hits":[]}]})
}

#[test]
fn invalid_or_mismatched_worker_data_never_publishes_a_partial_source_transaction() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("invalid.sqlite").to_str().unwrap()).unwrap();
    let mut req = request(&mut conn);
    req.families = vec!["community".into()];
    research::begin(&mut conn, &req).unwrap();
    for variant in 0..8 {
        let mut value = response(&req);
        match variant {
            0 => value["query"] = json!("changed public terms"),
            1 => value["channels"][0]["raw_response_base64"] = json!(null),
            2 => value["channels"][0]["raw_response_base64"] = json!("invalid base64"),
            3 => {
                value["channels"][0]["raw_response_base64"] =
                    json!(STANDARD.encode(vec![0; 131073]))
            }
            4 => value["channels"][0]["request_url"] = json!("https://evil.example/"),
            5 => value["channels"][0]["provider"] = json!("other-provider"),
            6 => value["channels"][0]["undocumented"] = json!(true),
            _ => value["channels"]
                .as_array_mut()
                .unwrap()
                .push(response(&req)["channels"][0].clone()),
        }
        assert!(
            research::publish(&mut conn, &req, value).is_err(),
            "variant {variant}"
        );
        assert_eq!(
            research::read(&conn, &req.request_id).unwrap().unwrap()["state"],
            "unknown"
        );
        let count: i64 = conn
            .query_row("SELECT count(*) FROM sources", [], |row| row.get(0))
            .unwrap();
        assert_eq!(count, 0, "invalid response must not import even one source");
    }
    let receipt = research::publish(&mut conn, &req, response(&req)).unwrap();
    assert!(matches!(research::begin(&mut conn,&req).unwrap(),Begin::Cached(v) if v==receipt));
    assert!(
        research::publish(&mut conn, &req, response(&req)).is_err(),
        "terminal cannot publish again"
    );
}

#[test]
fn cancellation_and_restore_changes_reject_late_publication() {
    for restored in [false, true] {
        let dir = tempfile::tempdir().unwrap();
        let mut conn = init_workspace(dir.path().join("fence.sqlite").to_str().unwrap()).unwrap();
        let mut req = request(&mut conn);
        req.families = vec!["community".into()];
        research::begin(&mut conn, &req).unwrap();
        if restored {
            conn.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,'different') ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [archeaxis_store_sqlite::authorization_fence::KEY]).unwrap();
        } else {
            research::fail(&mut conn, &req, "public_query_cancelled", true).unwrap();
        }
        assert!(research::publish(&mut conn, &req, response(&req)).is_err());
        let count: i64 = conn
            .query_row("SELECT count(*) FROM sources", [], |row| row.get(0))
            .unwrap();
        assert_eq!(count, 0);
        if !restored {
            assert_eq!(
                research::read(&conn, &req.request_id).unwrap().unwrap()["state"],
                "cancelled"
            );
        }
    }
}

// Captured anonymous public query; local replay is INTEGRATED, not a new network call.
// Original response sha256: 8620d38f642d47482a7aab9b2e4a80d9816d912c5a03c44e030e5693ef9b369b
const CAPTURED_REAL_RESPONSE: &str = r########"{"schema":"public-research-worker/v1","query":"spaced repetition","families":["encyclopedia","community","research"],"channels":[{"family":"encyclopedia","provider":"wikipedia","status":"complete","retrieved_at":"2026-10-20T16:39:07.934899Z","retry_after_seconds":null,"error_code":null,"request_url":"https://en.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch=spaced+repetition&gsrlimit=1&gsrnamespace=0&prop=revisions&rvprop=ids%7Ctimestamp%7Ccontent&rvslots=main&rvsection=0&format=json&formatversion=2","raw_response_base64":"eyJiYXRjaGNvbXBsZXRlIjp0cnVlLCJjb250aW51ZSI6eyJnc3JvZmZzZXQiOjEsImNvbnRpbnVlIjoiZ3Nyb2Zmc2V0fHwifSwicXVlcnkiOnsicGFnZXMiOlt7InBhZ2VpZCI6Mjc4MDUsIm5zIjowLCJ0aXRsZSI6IlNwYWNlZCByZXBldGl0aW9uIiwiaW5kZXgiOjEsInJldmlzaW9ucyI6W3sicmV2aWQiOjEzNzg4NDIxMzAsInBhcmVudGlkIjoxMzc4NzUxODY4LCJ0aW1lc3RhbXAiOiIyMDI2LTEwLTA2VDEyOjM4OjEwWiIsInNsb3RzIjp7Im1haW4iOnsiY29udGVudG1vZGVsIjoid2lraXRleHQiLCJjb250ZW50Zm9ybWF0IjoidGV4dC94LXdpa2kiLCJjb250ZW50Ijoie3tTaG9ydCBkZXNjcmlwdGlvbnxMZWFybmluZyB0ZWNobmlxdWUgcGVyZm9ybWVkIHdpdGggZmxhc2hjYXJkc319XG57e01vcmUgY2l0YXRpb25zIG5lZWRlZHxkYXRlPUZlYnJ1YXJ5IDIwMjB9fVxue3tVc2UgbWR5IGRhdGVzfGRhdGU9SmFudWFyeSAyMDIyfX1cbltbRmlsZTpMZWl0bmVyIHN5c3RlbSBhbHRlcm5hdGl2ZS5zdmd8dGh1bWJ8SW4gdGhlIFtbTGVpdG5lciBzeXN0ZW1dXSwgY29ycmVjdGx5IGFuc3dlcmVkIGNhcmRzIGFyZSBhZHZhbmNlZCB0byB0aGUgbmV4dCwgbGVzcyBmcmVxdWVudCBib3gsIHdoaWxlIGluY29ycmVjdGx5IGFuc3dlcmVkIGNhcmRzIHJldHVybiB0byB0aGUgZmlyc3QgYm94IGZvciBtb3JlIGFnZ3Jlc3NpdmUgcmV2aWV3IGFuZCByZXBldGl0aW9uLl1dXG5cbicnJ1NwYWNlZCByZXBldGl0aW9uJycnIGlzIGFuIFtbZXZpZGVuY2UtYmFzZWQgbGVhcm5pbmddXSB0ZWNobmlxdWUgdGhhdCBpcyB1c3VhbGx5IHBlcmZvcm1lZCB3aXRoIFtbZmxhc2hjYXJkXV1zLiBOZXdseSBpbnRyb2R1Y2VkIGFuZCBtb3JlIGRpZmZpY3VsdCBmbGFzaGNhcmRzIGFyZSBzaG93biBtb3JlIGZyZXF1ZW50bHksIHdoaWxlIG9sZGVyIGFuZCBsZXNzIGRpZmZpY3VsdCBmbGFzaGNhcmRzIGFyZSBzaG93biBsZXNzIGZyZXF1ZW50bHkgaW4gb3JkZXIgdG8gZXhwbG9pdCB0aGUgcHN5Y2hvbG9naWNhbCBbW3NwYWNpbmcgZWZmZWN0XV0uIFRoZSB1c2Ugb2Ygc3BhY2VkIHJlcGV0aXRpb24gaGFzIGJlZW4gcHJvdmVuIHRvIGluY3JlYXNlIHRoZSByYXRlIG9mIGxlYXJuaW5nLjxyZWY+e3tjaXRlIGpvdXJuYWwgfGxhc3QxPVNtb2xlbiB8Zmlyc3QxPVBhdWwgfGxhc3QyPVpoYW5nIHxmaXJzdDI9WWlsaSB8bGFzdDM9QnlybmUgfGZpcnN0Mz1Kb2huIEguIHx0aXRsZT1UaGUgcmlnaHQgdGltZSB0byBsZWFybjogbWVjaGFuaXNtcyBhbmQgb3B0aW1pemF0aW9uIG9mIHNwYWNlZCBsZWFybmluZyB8am91cm5hbD1OYXR1cmUgUmV2aWV3cyBOZXVyb3NjaWVuY2UgfGRhdGU9SmFudWFyeSAyNSwgMjAxNiB8dm9sdW1lPTE3IHxpc3N1ZT0yIHxwYWdlcz03N+KAkzg4IHxkb2k9MTAuMTAzOC9ucm4uMjAxNS4xOCB8cG1pZD0yNjgwNjYyNyB8cG1jPTUxMjY5NzAgfGFyeGl2PTE2MDYuMDgzNzAgfGJpYmNvZGU9MjAxNmFyWGl2MTYwNjA4MzcwUyB9fTwvcmVmPlxuXG5bW0ZpbGU6Rm9yZ2V0dGluZ0N1cnZlLnN2Z3x0aHVtYnxTcGFjZWQgcmVwZXRpdGlvbiB3aXRoIGZvcmdldHRpbmcgY3VydmVzXV1cblxuQWx0aG91Z2ggdGhlIHByaW5jaXBsZSBpcyB1c2VmdWwgaW4gbWFueSBjb250ZXh0cywgc3BhY2VkIHJlcGV0aXRpb24gaXMgY29tbW9ubHkgYXBwbGllZCBpbiBjb250ZXh0cyBpbiB3aGljaCBhIGxlYXJuZXIgbXVzdCBhY3F1aXJlIG1hbnkgaXRlbXMgYW5kIHJldGFpbiB0aGVtIGluZGVmaW5pdGVseSBpbiBtZW1vcnkuIEl0IGlzLCB0aGVyZWZvcmUsIHdlbGwgc3VpdGVkIGZvciB0aGUgcHJvYmxlbSBvZiBbW3ZvY2FidWxhcnldXSBhY3F1aXNpdGlvbiBpbiB0aGUgY291cnNlIG9mIHNlY29uZC1sYW5ndWFnZSBsZWFybmluZy4gQSBudW1iZXIgb2YgW1sjU29mdHdhcmV8c3BhY2VkIHJlcGV0aXRpb24gc29mdHdhcmUgcHJvZ3JhbXNdXSBoYXZlIGJlZW4gZGV2ZWxvcGVkIHRvIGFpZCB0aGUgbGVhcm5pbmcgcHJvY2Vzcy4gSXQgaXMgYWxzbyBwb3NzaWJsZSB0byBwZXJmb3JtIHNwYWNlZCByZXBldGl0aW9uIHdpdGggcGh5c2ljYWwgZmxhc2hjYXJkcyB1c2luZyB0aGUgW1tMZWl0bmVyIHN5c3RlbV1dLiBUaGUgW1t0ZXN0aW5nIGVmZmVjdF1dIGFuZCBzcGFjZWQgcmVwZXRpdGlvbiBjYW4gYmUgY29tYmluZWQgdG8gaW1wcm92ZSBsb25nLXRlcm0gbWVtb3J5LiBUaGVyZWZvcmUsIG1lbW9yaXphdGlvbiBjYW4gYmUgZWFzaWVyIHRvIGRvLiJ9fX1dfV19fQ==","hits":[{"id":"wikipedia:en:27805:1378842130","family":"encyclopedia","provider":"wikipedia","title":"Spaced repetition","url":"https://en.wikipedia.org/w/index.php?oldid=1378842130","retrieved_at":"2026-10-20T16:39:07.934899Z","content":"excerpt","excerpt":"{{Short description|Learning technique performed with flashcards}}\n{{More citations needed|date=February 2020}}\n{{Use mdy dates|date=January 2022}}\n[[File:Leitner system alternative.svg|thumb|In the [[Leitner system]], correctly answered cards are advanced to the next, less frequent box, while incorrectly answered cards return to the first box for more aggressive review and repetition.]]\n\n'''Spaced repetition''' is an [[evidence-based learning]] technique that is usually performed with [[flashcard]]s. Newly introduced and more difficult flashcards are shown more frequently, while older and less difficult flashcards are shown less frequently in order to exploit the psychological [[spacing effect]]. The use of spaced repetition has been proven to increase the rate of learning.<ref>{{cite journal |last1=Smolen |first1=Paul |last2=Zhang |first2=Yili |last3=Byrne |first3=John H. |title=The right time to learn: mechanisms and optimization of spaced learning |journal=Nature Reviews Neuroscience |date=January 25, 2016 |volume=17 |issue=2 |pages=77–88 |doi=10.1038/nrn.2015.18 |pmid=26806627 |pmc=5126970 |arxiv=1606.08370 |bibcode=2016arXiv160608370S }}</ref>\n\n[[File:ForgettingCurve.svg|thumb|Spaced repetition with forgetting curves]]\n\nAlthough the principle is useful in many contexts, spaced repetition is commonly applied in contexts in which a learner must acquire many items and retain them indefinitely in memory. It is, therefore, well suited for the problem of [[vocabulary]] acquisition in the course of second-language learning. A number of [[#Software|spaced repetition software programs]] have been developed to aid the learning process. It is also possible to perform spaced repetition with physical flashcards using the [[Leitner system]]. The [[testing effect]] and spaced repetition can be combined to improve long-term memory. Therefore, memorization can be easier to do.","locator":"pageid=27805;revid=1378842130;section=0","license":"CC BY-SA 4.0","free_access":"free","upstream_revision":"1378842130","representation":"wikitext","truncated":false}]},{"family":"community","provider":"stackexchange","status":"complete","retrieved_at":"2026-10-20T16:39:09.063055Z","retry_after_seconds":null,"error_code":null,"request_url":"https://api.stackexchange.com/2.3/search/advanced?site=academia&q=spaced+repetition&pagesize=1&sort=relevance&filter=withbody","raw_response_base64":"eyJpdGVtcyI6W3sidGFncyI6WyJncmFkdWF0ZS1zY2hvb2wiLCJ0ZWFjaGluZyIsImVkdWNhdGlvbiJdLCJvd25lciI6eyJhY2NvdW50X2lkIjoyOTY4NTc2LCJyZXB1dGF0aW9uIjoxMDkxLCJ1c2VyX2lkIjoyMzI0OCwidXNlcl90eXBlIjoicmVnaXN0ZXJlZCIsInByb2ZpbGVfaW1hZ2UiOiJodHRwczovL2kuc3N0YXRpYy5uZXQvTnB6WmUucG5nP3M9MjU2IiwiZGlzcGxheV9uYW1lIjoidXNlcjI1MjEyMDQiLCJsaW5rIjoiaHR0cHM6Ly9hY2FkZW1pYS5zdGFja2V4Y2hhbmdlLmNvbS91c2Vycy8yMzI0OC91c2VyMjUyMTIwNCJ9LCJpc19hbnN3ZXJlZCI6dHJ1ZSwidmlld19jb3VudCI6MTAyNzgsInByb3RlY3RlZF9kYXRlIjoxNTE1NzA0OTE0LCJhY2NlcHRlZF9hbnN3ZXJfaWQiOjY5MTM5LCJhbnN3ZXJfY291bnQiOjcsInNjb3JlIjo0NCwibGFzdF9hY3Rpdml0eV9kYXRlIjoxNTE1Njc2MzkwLCJjcmVhdGlvbl9kYXRlIjoxNDYzOTE1NTg3LCJsYXN0X2VkaXRfZGF0ZSI6MTQ3OTM4NjQyNiwicXVlc3Rpb25faWQiOjY5MTAwLCJjb250ZW50X2xpY2Vuc2UiOiJDQyBCWS1TQSAzLjAiLCJsaW5rIjoiaHR0cHM6Ly9hY2FkZW1pYS5zdGFja2V4Y2hhbmdlLmNvbS9xdWVzdGlvbnMvNjkxMDAvd2h5LWRvZXNudC1hY2FkZW1pYS1pbmNvcnBvcmF0ZS1zcGFjZWQtcmVwZXRpdGlvbi1pbi1oaWdoZXItZWR1Y2F0aW9uIiwidGl0bGUiOiJXaHkgZG9lc24mIzM5O3QgYWNhZGVtaWEgaW5jb3Jwb3JhdGUgc3BhY2VkIHJlcGV0aXRpb24gaW4gaGlnaGVyIGVkdWNhdGlvbj8iLCJib2R5IjoiPHA+VGhlcmUgYXJlIG1hbnkgcHVibGljYXRpb25zIGV4cGxhaW5pbmcgYWR2YW50YWdlcyBvZiBzcGFjZWQgcmVwZXRpdGlvbi4gSSBmb3VuZCBhIHN1bW1hcnkgb2Ygc29tZSBvZiB0aGVtIDxhIGhyZWY9XCJodHRwOi8vd3d3Lmd3ZXJuLm5ldC9TcGFjZWQlMjByZXBldGl0aW9uXCIgcmVsPVwibm9yZWZlcnJlclwiPmhlcmU8L2E+LjwvcD5cblxuPHA+V2hpbGUgYSBsb3Qgb2Ygc3R1ZGllcyBzaG93IG1hbnkgYWR2YW50YWdlcyBvZiBzcGFjZWQgcmVwZXRpdGlvbiwgaXQgaXMgbm90IGZvcm1hbGx5IGFwcGxpZWQgdG8gaGlnaGVyIGVkdWNhdGlvbi4gV2h5IGlzIHRoYXQ/PC9wPlxuXG48cD48c3Ryb25nPlVQREFURSAxOjwvc3Ryb25nPiBJbiBvcmRlciB0byBjbGFyaWZ5IG15IHF1ZXN0aW9uLCBJIGFkZGVkIGEgcXVvdGUgZm9ybSA8YSBocmVmPVwiaHR0cDovL3d3dy5nd2Vybi5uZXQvZG9jcy9zcGFjZWRyZXBldGl0aW9uLzIwMTItc29uLnBkZlwiIHJlbD1cIm5vcmVmZXJyZXJcIj50aGlzIHB1YmxpY2F0aW9uPC9hPjo8L3A+XG5cbjxibG9ja3F1b3RlPlxuICA8cD5GdXJ0aGVybW9yZSwgZXZlbiBhZnRlciBhY2tub3dsZWRnaW5nIHRoZSBiZW5lZml0cyBvZiBzcGFjaW5nLCBjaGFuZ2luZyB0ZWFjaGluZyBwcmFjdGljZXMgcHJvdmVkIHRvIGJlIGVub3Jtb3VzbHkgZGlmZmljdWx0LiBEZWxhbmV5IGV0IGFsICgyMDEwKSB3cm90ZTog4oCcQW5lY2RvdGFsbHksIGhpZ2ggc2Nob29sIHRlYWNoZXJzIGFuZCBjb2xsZWdlIHByb2Zlc3NvcnMgc2VlbSB0byB0ZWFjaCBpbiBhIGxpbmVhciBmYXNoaW9uIHdpdGhvdXQgcmVwZXRpdGlvbiBhbmQgZ2l2ZSB0aHJlZSBvciBmb3VyIG5vbmN1bXVsYXRpdmUgZXhhbXMu4oCdIChwLiAxMzApLiBGb2N1c2luZyBvbiB0aGUgbWF0aCBkb21haW4sIHdoZXJlIG9uZSBtaWdodCBleHBlY3QgYSB2ZXJ5IGVhc3ktdG8tcmV2aWV3LWFuZC10by1zcGFjZSBzdHJhdGVneSwgUm9ocmVyICgyMDA5KSBwb2ludHMgb3V0IHRoYXQgbWF0aGVtYXRpY3MgdGV4dGJvb2tzIHVzdWFsbHkgcHJlc2VudCB0b3BpY3MgaW4gYSBub24tc3BhY2VkLCBub24tbWl4ZWQgZmFzaGlvbi4gRXZlbiBtdWNoIGVhcmxpZXIsIFZhc2ggKDE5ODkpIGhhZCB3cml0dGVuOiDigJxFZHVjYXRpb24gcG9saWN5IHNldHRlcnMga25vdyBwZXJmZWN0bHkgd2VsbCB0aGF0IFtzcGFjZWQgcHJhY3RpY2VdIHdvcmtzIGJldHRlciBbdGhhbiBtYXNzZWQgcHJhY3RpY2VdLiBUaGV5IGRvbuKAmXQgY2FyZS4gSXQgaXNu4oCZdCB0aWR5LiBJdCBkb2VzbuKAmXQgbGV0IHRlYWNoZXJzIHRlYWNoIGEgdW5pdCBhbmQgZHVzdCBvZmYgdGhlaXIgaGFuZHMgcXVpY2tseSB3aXRoIGEgbmljZSBzZW5zZSBvZiDigJhXZWxsLCB0aGF04oCZcyBkb25lLuKAmeKAnSAocC4gMTU0NykuPC9wPlxuICBcbiAgPHA+Um9ocmVyLCBELiAoMjAwOSkuIFRoZSBlZmZlY3RzIG9mIHNwYWNpbmcgYW5kIG1peGluZyBwcmFjdGljZVxuICBwcm9ibGVtcy4gSm91cm5hbCBmb3IgUmVzZWFyY2ggaW4gTWF0aGVtYXRpY3MgRWR1Y2F0aW9uLCA0MCwgNC0xNzwvcD5cbiAgXG4gIDxwPlZhc2gsIEMuIEwuICgxOTg5KS4g4oCcVGhlIHNwYWNpbmcgZWZmZWN0OiBBIGNhc2Ugc3R1ZHkgaW4gdGhlIGZhaWx1cmVcbiAgdG8gYXBwbHkgdGhlIHJlc3VsdHMgb2YgcHN5Y2hvbG9naWNhbCByZXNlYXJjaOKAnS4gQW1lcmljYW5cbiAgUHN5Y2hvbG9naXN0LCA0NCwgMTU0NyAoYSBjb21tZW50IG9uIERlbXBzdGVy4oCZcyBhcnRpY2xlPyk8L3A+XG48L2Jsb2NrcXVvdGU+XG5cbjxwPkJ5IHRoZSB3YXksIEkgYW0gbm90IHRyeWluZyB0byBkZWZlbmQgdGhpcyBwdWJsaWNhdGlvbiBvciB0aGUgcXVvdGUuIEkganVzdCB3YW50IHRvIGZpZ3VyZSBvdXQgaWYgcGVvcGxlIGJlbGlldmUgdGhpcyBpcyB0cnVlLiBJZiB5ZXMsIHdoeSBwb2xpY3kgbWFrZXJzIGRvIG5vdCBmb3JtYWxseSBpbmNvcnBvcmF0ZSBzcGFjZWQgcmVwZXRpdGlvbiBpbiBlZHVjYXRpb24gc3lzdGVtcy48L3A+XG5cbjxwPjxzdHJvbmc+VVBEQVRFIDI8L3N0cm9uZz46IEkgcmVhbGx5IGFwcHJlY2lhdGUgeW91ciBpbnRlcmVzdCBpbiBhbnN3ZXJpbmcgbXkgcXVlc3Rpb24uIEkgdGhpbmsgdGhlcmUgYXJlIHN0aWxsIHNvbWUgdW5jbGVhciBwb2ludHMgdGhhdCBJIHdhbnQgdG8gbWVudGlvbiBoZXJlOjwvcD5cblxuPHA+UGxlYXNlIHJlYWQgdGhlIGFydGljbGUgaW4gbXkgcXVlc3Rpb24uIFRoZW4geW91J2xsIHNlZSB0aGUgZGlmZmVyZW5jZSBiZXR3ZWVuIFwiYWN0aXZlIHJlY2FsbFwiIGluIHNwYWNlZCByZXBldGl0aW9uIGFuZCBiZWluZyBleHBvc2VkIHRvIGNvbmNlcHRzIGJ5IHJlYWRpbmcgYm9va3Mgb3IgYXR0ZW5kaW5nIGxlY3R1cmVzIGluIG91ciBlZHVjYXRpb24gc3lzdGVtLiBIZXJlIGFyZSBhIGNvdXBsZSBvZiBxdW90ZXM6IDwvcD5cblxuPGJsb2NrcXVvdGU+XG4gIDxwPjxhIGhyZWY9XCJodHRwOi8vZW4ud2lraXBlZGlhLm9yZy93aWtpL2FjdGl2ZSUyMHJlY2FsbFwiIHJlbD1cIm5vcmVmZXJyZXJcIj5hY3RpdmUgcmVjYWxsPC9hPiBpcyBhIGZhciBzdXBlcmlvciBtZXRob2Qgb2YgbGVhcm5pbmcgdGhhbiBzaW1wbHlcbiAgcGFzc2l2ZWx5IGJlaW5nIGV4cG9zZWQgdG8gaW5mb3JtYXRpb24uIC4uLiBUaGVyZSBhcmUgbWFueSBzdHVkaWVzIHRvXG4gIHRoZSBlZmZlY3QgdGhhdCBhY3RpdmUgcmVjYWxsIGlzIGJlc3QuIEhlcmXigJlzIG9uZSByZWNlbnQgc3R1ZHksXG4gIDxhIGhyZWY9XCJodHRwOi8vd3d3LnNjaWVuY2VtYWcub3JnL2NvbnRlbnQvZWFybHkvMjAxMS8wMS8xOS9zY2llbmNlLjExOTkzMjcuYWJzdHJhY3RcIiByZWw9XCJub3JlZmVycmVyXCI+4oCcUmV0cmlldmFsIFByYWN0aWNlIFByb2R1Y2VzIE1vcmUgTGVhcm5pbmcgdGhhbiBFbGFib3JhdGl2ZSBTdHVkeWluZ1xuICB3aXRoIENvbmNlcHQgTWFwcGluZ+KAnSwgS2FycGlja2UgMjAxMSAoY292ZXJlZCBpbiBTY2llbmNlIERhaWx5IGFuZCB0aGVcbiAgTllUKTwvYT4gLi4uIDxhIGhyZWY9XCJodHRwOi8vd3d3Lm55dGltZXMuY29tLzIwMTAvMDkvMDcvaGVhbHRoL3ZpZXdzLzA3bWluZC5odG1sXCIgcmVsPVwibm9yZWZlcnJlclwiPuKAnEZvcmdldCBXaGF0IFlvdSBLbm93IEFib3V0IEdvb2QgU3R1ZHkgSGFiaXRz4oCdLiBOZXcgWW9ya1xuICBUaW1lczwvYT4uPC9wPlxuPC9ibG9ja3F1b3RlPlxuXG48cD5XaGlsZSBcInNwaXJhbCBsZWFybmluZ1wiIGlzIGJhc2ljYWxseSB0aGUgZm91bmRhdGlvbiBvZiBzcGFjaW5nLCBpbiBhZGRpdGlvbiBzcGFjaW5nIGhlYXZpbHkgcmVsaWVzIG9uIGFjdGl2ZSByZWNhbGwuIEZ1cnRoZXJtb3JlLCBzcGFjaW5nIHRha2VzIGFkdmFudGFnZSBvZiA8YSBocmVmPVwiaHR0cHM6Ly9lbi53aWtpcGVkaWEub3JnL3dpa2kvQ2h1bmtpbmdfKHBzeWNob2xvZ3kpXCIgcmVsPVwibm9yZWZlcnJlclwiPmNodW5raW5nPC9hPiBpbiBkZXNpZ25pbmcgZmxhc2ggY2FyZHMuPC9wPlxuXG48cD5Nb3Jlb3ZlciwgdGhlcmUgYXJlIHdlbGwtZGVmaW5lZCBzcGFjaW5nIGFsZ29yaXRobXMsIGRlc2lnbmVkIGJ5IGZhbW91cyBwc3ljaG9sb2dpc3RzIGxpa2UgPGEgaHJlZj1cImh0dHBzOi8vZW4ud2lraXBlZGlhLm9yZy93aWtpL0xlaXRuZXJfc3lzdGVtXCIgcmVsPVwibm9yZWZlcnJlclwiPkRyLiBMZWl0bmVyPC9hPiwgdGhhdCBzaWduaWZpY2FudGx5IGltcHJvdmUgdGhlIGVmZmljaWVuY3kgb2YgbGVhcm5pbmcuIFBsZWFzZSBsb29rIGF0IDxhIGhyZWY9XCJodHRwOi8vd3d3Lm1lbXJpc2UuY29tL3NjaWVuY2UvXCIgcmVsPVwibm9yZWZlcnJlclwiPnN0dWRpZXMgYnkgUHJvZmVzc29yIERhdmlkIFNoYW5rcyBhbmQgRHIuIFJvc2FsaW5kIFBvdHRzPC9hPi48L3A+XG5cbjxwPkZpbmFsbHksIGluIHJlc3BvbnNlIHRvIHRob3NlIHdobyB0aGluayBzcGFjaW5nIG9ubHkgaW1wcm92ZXMgbWVtb3JpemluZywgcGxlYXNlIHJlYWQgYWJvdXQgdGhlIHJlc3VsdHMgb2YgUHJvZmVzc29yIEJqb3JrJ3MgbWFueSB5ZWFycyBvZiBleHBlcmltZW50cywgc3BlY2lmaWNhbGx5IFwiS29ybmVsbCwgTi4sIENhc3RlbCwgQS4gRC4sIEVpY2gsIFQuIFMuLCAmYW1wOyBCam9yaywgUi4gQS4gKDIwMTApLiDigJxTcGFjaW5nIGFzIHRoZSBmcmllbmQgb2YgYm90aCBtZW1vcnkgYW5kIGluZHVjdGlvbiBpbiB5b3VuZ2VyIGFuZCBvbGRlciBhZHVsdHPigJ0uIFBzeWNob2xvZ3kgYW5kIEFnaW5nLCAyNSwgNDk4LTUwMy5cIjwvcD5cblxuPHA+Tm93LCBkbyB5b3UgYmVsaWV2ZSBzY2hvb2xzIHNob3VsZCBsZWF2ZSBzdHVkZW50cyBvbiB0aGVpciBvd24gdG8gZGlzY292ZXIgZWZmaWNpZW50IHdheXMgb2YgbGVhcm5pbmcsIG9yIGRvIHlvdSBiZWxpZXZlIGl0J3MgYmV0dGVyIHRvIGluY29ycG9yYXRlIHRoZXNlIHdlbGwtc3R1ZGllZCBtZXRob2RvbG9naWVzIGludG8gdGhlIGVkdWNhdGlvbiBzeXN0ZW0/IEFzIGEgc3R1ZGVudCwgSSBwYXkgbXkgc2Nob29sIHRvIHByb3ZpZGUgbWUgd2l0aCBtb3RpdmF0aW9uLCBwYXRod2F5cywgYW5kIGVmZmljaWVudCB3YXlzIG9mIGxlYXJuaW5nLCByYXRoZXIgdGhhbiBtZXJlbHkgcHJvdmlkaW5nIG1lIHdpdGggYSBjb21wZXRpdGl2ZSBlbnZpcm9ubWVudCB0byBwcm92ZSBteXNlbGYgZm9yIGEgYmV0dGVyIGpvYiBpbiB0aGUgZnV0dXJlLjwvcD5cblxuPHA+TGV0IG1lIGNsYXJpZnkgdGhpczogSSBsb3ZlIGVkdWNhdGlvbiwgcmVzZWFyY2gsIGFuZCBldmVuIGp1c3QgYmVpbmcgYXQgc2Nob29sLiBIb3dldmVyLCBJIGJlbGlldmUgaW4gY29uc2lkZXJpbmcgYWxsIGltcHJvdmVtZW50cyB0aGF0IHRlY2hub2xvZ3kgaGFzIHByb3ZpZGVkIGZvciB1cyBpbiBkaWZmZXJlbnQgYXNwZWN0cyBvZiBvdXIgbGl2ZXMsIGFuZCBJIGJlbGlldmUgb3VyIGVkdWNhdGlvbiBzeXN0ZW0gaXMgdG9vIG9sZC4gSSBiZWxpZXZlIHdlIGNhbiBhcHBseSB3ZWxsLXN0dWRpZWQgdGhlb3JpZXMgb2YgbGVhcm5pbmcsIGtub3dsZWRnZSwgbmV1cm9zY2llbmNlLCBhbmQgcHN5Y2hvbG9neSB0byBvdXIgZWR1Y2F0aW9uIHN5c3RlbSwgdGhyb3VnaCB0aGUgdXNlIG9mIHRlY2hub2xvZ3ksIGFuZCByZWFsbHkgaW1wcm92ZSBvdXIgZWR1Y2F0aW9uIHN5c3RlbS4gSSBhbSB0cnlpbmcgbXkgYmVzdCB0byBwbGF5IG15IHNtYWxsIHJvbGUgaW4gdGhpcyByZWdhcmQuIE15IG1haW4gcHVycG9zZSBvZiBhc2tpbmcgdGhpcyBxdWVzdGlvbiBpbiB0aGlzIGZvcnVtIGlzIHRvIGJyYWluc3Rvcm0gd2l0aCB5b3UgdG8gY29sbGFib3JhdGl2ZWx5IGFuZCBsZWFybiBob3cgdG8gaW1wcm92ZSBvdXIgZWR1Y2F0aW9uIHN5c3RlbS48L3A+XG4ifV0sImhhc19tb3JlIjp0cnVlLCJxdW90YV9tYXgiOjMwMCwicXVvdGFfcmVtYWluaW5nIjoyOTd9","hits":[{"id":"stackexchange:academia:question:69100","family":"community","provider":"stackexchange","title":"Why doesn't academia incorporate spaced repetition in higher education?","url":"https://academia.stackexchange.com/questions/69100/why-doesnt-academia-incorporate-spaced-repetition-in-higher-education","retrieved_at":"2026-10-20T16:39:09.063055Z","content":"full_text","excerpt":"There are many publications explaining advantages of spaced repetition. I found a summary of some of them here.\nWhile a lot of studies show many advantages of spaced repetition, it is not formally applied to higher education. Why is that?\nUPDATE 1: In order to clarify my question, I added a quote form this publication:\nFurthermore, even after acknowledging the benefits of spacing, changing teaching practices proved to be enormously difficult. Delaney et al (2010) wrote: “Anecdotally, high school teachers and college professors seem to teach in a linear fashion without repetition and give three or four noncumulative exams.” (p. 130). Focusing on the math domain, where one might expect a very easy-to-review-and-to-space strategy, Rohrer (2009) points out that mathematics textbooks usually present topics in a non-spaced, non-mixed fashion. Even much earlier, Vash (1989) had written: “Education policy setters know perfectly well that [spaced practice] works better [than massed practice]. They don’t care. It isn’t tidy. It doesn’t let teachers teach a unit and dust off their hands quickly with a nice sense of ‘Well, that’s done.’” (p. 1547).\nRohrer, D. (2009). The effects of spacing and mixing practice\nproblems. Journal for Research in Mathematics Education, 40, 4-17\nVash, C. L. (1989). “The spacing effect: A case study in the failure\nto apply the results of psychological research”. American\nPsychologist, 44, 1547 (a comment on Dempster’s article?)\nBy the way, I am not trying to defend this publication or the quote. I just want to figure out if people believe this is true. If yes, why policy makers do not formally incorporate spaced repetition in education systems.\nUPDATE 2: I really appreciate your interest in answering my question. I think there are still some unclear points that I want to mention here:\nPlease read the article in my question. Then you'll see the difference between \"active recall\" in spaced repetition and being exposed to concepts by reading books or attending lectures in our education system. Here are a couple of quotes:\nactive recall is a far superior method of learning than simply\npassively being exposed to information. ... There are many studies to\nthe effect that active recall is best. Here’s one recent study,\n“Retrieval Practice Produces More Learning than Elaborative Studying\nwith Concept Mapping”, Karpicke 2011 (covered in Science Daily and the\nNYT) ... “Forget What You Know About Good Study Habits”. New York\nTimes.\nWhile \"spiral learning\" is basically the foundation of spacing, in addition spacing heavily relies on active recall. Furthermore, spacing takes advantage of chunking in designing flash cards.\nMoreover, there are well-defined spacing algorithms, designed by famous psychologists like Dr. Leitner, that significantly improve the efficiency of learning. Please look at studies by Professor David Shanks and Dr. Rosalind Potts.\nFinally, in response to those who think spacing only improves memorizing, please read about the results of Professor Bjork's many years of experiments, specifically \"Kornell, N., Castel, A. D., Eich, T. S., & Bjork, R. A. (2010). “Spacing as the friend of both memory and induction in younger and older adults”. Psychology and Aging, 25, 498-503.\"\nNow, do you believe schools should leave students on their own to discover efficient ways of learning, or do you believe it's better to incorporate these well-studied methodologies into the education system? As a student, I pay my school to provide me with motivation, pathways, and efficient ways of learning, rather than merely providing me with a competitive environment to prove myself for a better job in the future.\nLet me clarify this: I love education, research, and even just being at school. However, I believe in considering all improvements that technology has provided for us in different aspects of our lives, and I believe our education system is too old. I believe we can apply well-studied theories of learning, knowledge, neuroscience, and psychology to our education system, through the use of technology, and really improve our education system. I am trying my best to play my small role in this regard. My main purpose of asking this question in this forum is to brainstorm with you to collaboratively and learn how to improve our education system.","locator":"question_id=69100;body","license":"CC BY-SA 3.0","free_access":"free","upstream_revision":"last_edit_date:1479386426","representation":"html_text","truncated":false}]},{"family":"research","provider":"openalex","status":"complete","retrieved_at":"2026-10-20T16:39:10.631107Z","retry_after_seconds":null,"error_code":null,"request_url":"https://api.openalex.org/works?search=spaced+repetition&per_page=1","raw_response_base64":"eyJtZXRhIjogeyJub3RpY2UiOiAiTm8gQVBJIGtleSwgc28gdGhpcyByZXF1ZXN0IHNoYXJlcyBvbmUgZnJlZSBkYWlseSBidWRnZXQgKCQwLjEwKSB3aXRoIGV2ZXJ5b25lIG9uIHlvdXIgbmV0d29yaydzIElQIGFkZHJlc3MuIEdldCBhIGZyZWUga2V5IHdpdGggaXRzIG93biAkMS9kYXkgYXQgaHR0cHM6Ly9vcGVuYWxleC5vcmcvc2V0dGluZ3MvYXBpIGFuZCBhZGQgYXBpX2tleT1ZT1VSX0tFWSB0byB5b3VyIHJlcXVlc3RzLiBBbiBBSSBhZ2VudCBjYW4gZ2V0IG9uZSBmb3IgaXRzIHVzZXIgaW4gb25lIGNhbGw6IFBPU1QgaHR0cHM6Ly9hcGkub3BlbmFsZXgub3JnL2FwaS1rZXlzIHdpdGgge1wiZW1haWxcIjogXCI8eW91ciB1c2VyJ3MgZW1haWw+XCJ9OyB3ZSBlbWFpbCB0aGVtIGEgbGluaywgYW5kIHRoZSBrZXkgd29ya3Mgb25jZSB0aGV5IGNsaWNrIGl0LiBEb2NzIGZvciBhZ2VudHM6IGh0dHBzOi8vaGVscC5vcGVuYWxleC5vcmcvbGxtcy50eHQiLCAiY291bnQiOiAxMTY0NzE3LCAiZGJfcmVzcG9uc2VfdGltZV9tcyI6IDEzMSwgInBhZ2UiOiAxLCAicGVyX3BhZ2UiOiAxLCAiZ3JvdXBzX2NvdW50IjogbnVsbCwgInhfcXVlcnkiOiB7Im9xbCI6ICJnZXQgd29ya3Mgd2hlcmUgZnVsbCB0ZXh0IGhhcyAoc3BhY2VkIHJlcGV0aXRpb24pIiwgInhfbmV3X29xbCI6ICJnZXQgd29ya3Mgd2l0aCAoc3BhY2VkIHJlcGV0aXRpb24pIGluIHRoZSBmdWxsIHRleHQiLCAib3FvIjogeyJnZXRfcm93cyI6ICJ3b3JrcyIsICJmaWx0ZXJfcm93cyI6IFt7ImNvbHVtbl9pZCI6ICJmdWxsdGV4dC5zZWFyY2giLCAidmFsdWUiOiAic3BhY2VkIHJlcGV0aXRpb24iLCAib3BlcmF0b3IiOiAiaGFzIn1dfSwgInVybCI6ICIvd29ya3M/ZmlsdGVyPWZ1bGx0ZXh0LnNlYXJjaDpzcGFjZWQgcmVwZXRpdGlvbiZwZXJfcGFnZT0xIn0sICJjb3N0X3VzZCI6IDAuMDAxfSwgInJlc3VsdHMiOiBbeyJpZCI6ICJodHRwczovL29wZW5hbGV4Lm9yZy9XMjUxNDg5Nzk1OSIsICJkb2kiOiAiaHR0cHM6Ly9kb2kub3JnLzEwLjE4NjUzL3YxL3AxNi0xMTc0IiwgInRpdGxlIjogIkEgVHJhaW5hYmxlIFNwYWNlZCBSZXBldGl0aW9uIE1vZGVsIGZvciBMYW5ndWFnZSBMZWFybmluZyIsICJkaXNwbGF5X25hbWUiOiAiQSBUcmFpbmFibGUgU3BhY2VkIFJlcGV0aXRpb24gTW9kZWwgZm9yIExhbmd1YWdlIExlYXJuaW5nIiwgInJlbGV2YW5jZV9zY29yZSI6IDE1OS41MjIsICJwdWJsaWNhdGlvbl95ZWFyIjogMjAxNiwgInB1YmxpY2F0aW9uX2RhdGUiOiAiMjAxNi0wMS0wMSIsICJpZHMiOiB7Im9wZW5hbGV4IjogImh0dHBzOi8vb3BlbmFsZXgub3JnL1cyNTE0ODk3OTU5IiwgImRvaSI6ICJodHRwczovL2RvaS5vcmcvMTAuMTg2NTMvdjEvcDE2LTExNzQiLCAibWFnIjogIjI1MTQ4OTc5NTkifSwgImxhbmd1YWdlIjogImVuIiwgInByaW1hcnlfbG9jYXRpb24iOiB7ImlkIjogImRvaToxMC4xODY1My92MS9wMTYtMTE3NCIsICJkb2kiOiAiaHR0cHM6Ly9kb2kub3JnLzEwLjE4NjUzL3YxL3AxNi0xMTc0IiwgImlzX29hIjogdHJ1ZSwgImxhbmRpbmdfcGFnZV91cmwiOiAiaHR0cHM6Ly9kb2kub3JnLzEwLjE4NjUzL3YxL3AxNi0xMTc0IiwgInBkZl91cmwiOiAiaHR0cHM6Ly93d3cuYWNsd2ViLm9yZy9hbnRob2xvZ3kvUDE2LTExNzQucGRmIiwgInNvdXJjZSI6IHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvUzQzNjM2MDg2NTIiLCAiZGlzcGxheV9uYW1lIjogIkFubnVhbCBNZWV0aW5nIG9mIHRoZSBBc3NvY2lhdGlvbiBmb3IgQ29tcHV0YXRpb25hbCBMaW5ndWlzdGljcyAoQUNMKSIsICJpc3NuX2wiOiBudWxsLCAiaXNzbiI6IG51bGwsICJpc19vYSI6IGZhbHNlLCAiaXNfaW5fZG9haiI6IGZhbHNlLCAiaXNfY29yZSI6IGZhbHNlLCAibGlzdGVkX2luIjogW10sICJob3N0X29yZ2FuaXphdGlvbiI6IG51bGwsICJob3N0X29yZ2FuaXphdGlvbl9uYW1lIjogbnVsbCwgImhvc3Rfb3JnYW5pemF0aW9uX2xpbmVhZ2UiOiBbXSwgImhvc3Rfb3JnYW5pemF0aW9uX2xpbmVhZ2VfbmFtZXMiOiBbXSwgInR5cGUiOiAiY29uZmVyZW5jZSJ9LCAibGljZW5zZSI6ICJjYy1ieSIsICJsaWNlbnNlX2lkIjogImh0dHBzOi8vb3BlbmFsZXgub3JnL2xpY2Vuc2VzL2NjLWJ5IiwgInZlcnNpb24iOiAicHVibGlzaGVkVmVyc2lvbiIsICJpc19hY2NlcHRlZCI6IHRydWUsICJpc19wdWJsaXNoZWQiOiB0cnVlLCAicmF3X3NvdXJjZV9uYW1lIjogIlByb2NlZWRpbmdzIG9mIHRoZSA1NHRoIEFubnVhbCBNZWV0aW5nIG9mIHRoZSBBc3NvY2lhdGlvbiBmb3IgQ29tcHV0YXRpb25hbCBMaW5ndWlzdGljcyAoVm9sdW1lIDE6IExvbmcgUGFwZXJzKSIsICJyYXdfdHlwZSI6ICJwcm9jZWVkaW5ncy1hcnRpY2xlIn0sICJ2b2x1bWUiOiBudWxsLCAidHlwZSI6ICJjb25mZXJlbmNlLXBhcGVyIiwgImluZGV4ZWRfaW4iOiBbImNyb3NzcmVmIl0sICJvcGVuX2FjY2VzcyI6IHsiaXNfb2EiOiB0cnVlLCAib2Ffc3RhdHVzIjogImh5YnJpZCIsICJvYV91cmwiOiAiaHR0cHM6Ly93d3cuYWNsd2ViLm9yZy9hbnRob2xvZ3kvUDE2LTExNzQucGRmIiwgImFueV9yZXBvc2l0b3J5X2hhc19mdWxsdGV4dCI6IGZhbHNlfSwgImF1dGhvcnNoaXBzIjogW3siYXV0aG9yX3Bvc2l0aW9uIjogImZpcnN0IiwgImF1dGhvciI6IHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvQTUwMjg2ODM3MjIiLCAiZGlzcGxheV9uYW1lIjogIkJ1cnIgU2V0dGxlcyIsICJvcmNpZCI6IG51bGwsICJvYnNlcnZlZF9vcmNpZHMiOiBbXX0sICJpbnN0aXR1dGlvbnMiOiBbXSwgImNvdW50cmllcyI6IFtdLCAiaXNfY29ycmVzcG9uZGluZyI6IGZhbHNlLCAicmF3X2F1dGhvcl9uYW1lIjogIkJ1cnIgU2V0dGxlcyIsICJyYXdfYWZmaWxpYXRpb25fc3RyaW5ncyI6IFsiUGl0dHNidXJnaCAsIFBBIFVTQSIsICJQaXR0c2J1cmdoLCBQQSBVU0EiLCAiVWJlciBBZHZhbmNlZCBUZWNobm9sb2dpZXMgQ2VudGVyIFBpdHRzYnVyZ2gsIFBBIFVTQSJdLCAicmF3X29yY2lkIjogbnVsbCwgImFmZmlsaWF0aW9ucyI6IFt7InJhd19hZmZpbGlhdGlvbl9zdHJpbmciOiAiUGl0dHNidXJnaCAsIFBBIFVTQSIsICJpbnN0aXR1dGlvbl9pZHMiOiBbXX0sIHsicmF3X2FmZmlsaWF0aW9uX3N0cmluZyI6ICJQaXR0c2J1cmdoLCBQQSBVU0EiLCAiaW5zdGl0dXRpb25faWRzIjogW119LCB7InJhd19hZmZpbGlhdGlvbl9zdHJpbmciOiAiVWJlciBBZHZhbmNlZCBUZWNobm9sb2dpZXMgQ2VudGVyIFBpdHRzYnVyZ2gsIFBBIFVTQSIsICJpbnN0aXR1dGlvbl9pZHMiOiBbXX1dfSwgeyJhdXRob3JfcG9zaXRpb24iOiAibGFzdCIsICJhdXRob3IiOiB7ImlkIjogImh0dHBzOi8vb3BlbmFsZXgub3JnL0E1MDM1NjA0MDgxIiwgImRpc3BsYXlfbmFtZSI6ICJCcmVuZGFuIE1lZWRlciIsICJvcmNpZCI6IG51bGwsICJvYnNlcnZlZF9vcmNpZHMiOiBbXX0sICJpbnN0aXR1dGlvbnMiOiBbeyJpZCI6ICJodHRwczovL29wZW5hbGV4Lm9yZy9JNDQwMTcyNjk5NCIsICJkaXNwbGF5X25hbWUiOiAiRHVvbGluZ28gKFVuaXRlZCBTdGF0ZXMpIiwgInJvciI6ICJodHRwczovL3Jvci5vcmcvMDJiOTJ4djIyIiwgImNvdW50cnlfY29kZSI6IG51bGwsICJ0eXBlIjogImNvbXBhbnkiLCAibGluZWFnZSI6IFsiaHR0cHM6Ly9vcGVuYWxleC5vcmcvSTQ0MDE3MjY5OTQiXX1dLCAiY291bnRyaWVzIjogW10sICJpc19jb3JyZXNwb25kaW5nIjogdHJ1ZSwgInJhd19hdXRob3JfbmFtZSI6ICJCcmVuZGFuIE1lZWRlciIsICJyYXdfYWZmaWxpYXRpb25fc3RyaW5ncyI6IFsiUmVzZWFyY2ggY29uZHVjdGVkIGF0IER1b2xpbmdvIiwgIlViZXIgQWR2YW5jZWQgVGVjaG5vbG9naWVzIENlbnRlciBQaXR0c2J1cmdoICwgUEEgVVNBIl0sICJyYXdfb3JjaWQiOiBudWxsLCAiYWZmaWxpYXRpb25zIjogW3sicmF3X2FmZmlsaWF0aW9uX3N0cmluZyI6ICJSZXNlYXJjaCBjb25kdWN0ZWQgYXQgRHVvbGluZ28iLCAiaW5zdGl0dXRpb25faWRzIjogWyJodHRwczovL29wZW5hbGV4Lm9yZy9JNDQwMTcyNjk5NCJdfSwgeyJyYXdfYWZmaWxpYXRpb25fc3RyaW5nIjogIlViZXIgQWR2YW5jZWQgVGVjaG5vbG9naWVzIENlbnRlciBQaXR0c2J1cmdoICwgUEEgVVNBIiwgImluc3RpdHV0aW9uX2lkcyI6IFtdfV19XSwgImluc3RpdHV0aW9ucyI6IFtdLCAiY291bnRyaWVzX2Rpc3RpbmN0X2NvdW50IjogMCwgImluc3RpdHV0aW9uc19kaXN0aW5jdF9jb3VudCI6IDEsICJjb3JyZXNwb25kaW5nX2F1dGhvcl9pZHMiOiBbImh0dHBzOi8vb3BlbmFsZXgub3JnL0E1MDM1NjA0MDgxIl0sICJjb3JyZXNwb25kaW5nX2luc3RpdHV0aW9uX2lkcyI6IFsiaHR0cHM6Ly9vcGVuYWxleC5vcmcvSTQ0MDE3MjY5OTQiXSwgImFwY19saXN0IjogbnVsbCwgImFwY19wYWlkIjogbnVsbCwgImZ3Y2kiOiA0OC4xMzA2LCAiaGFzX2Z1bGx0ZXh0IjogdHJ1ZSwgImNpdGVkX2J5X2NvdW50IjogMjE3LCAiY2l0YXRpb25fbm9ybWFsaXplZF9wZXJjZW50aWxlIjogeyJ2YWx1ZSI6IDAuOTk5NTQzMDcsICJpc19pbl90b3BfMV9wZXJjZW50IjogdHJ1ZSwgImlzX2luX3RvcF8xMF9wZXJjZW50IjogdHJ1ZX0sICJjaXRlZF9ieV9wZXJjZW50aWxlX3llYXIiOiB7Im1pbiI6IDk4LCAibWF4IjogMTAwfSwgImJpYmxpbyI6IHsidm9sdW1lIjogbnVsbCwgImlzc3VlIjogbnVsbCwgImZpcnN0X3BhZ2UiOiAiMTg0OCIsICJsYXN0X3BhZ2UiOiAiMTg1OCJ9LCAiaXNfcmV0cmFjdGVkIjogZmFsc2UsICJpc19wYXJhdGV4dCI6IGZhbHNlLCAiaXNfeHBhYyI6IGZhbHNlLCAicHJpbWFyeV90b3BpYyI6IHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVDExNTg3IiwgImRpc3BsYXlfbmFtZSI6ICJTZWNvbmQgTGFuZ3VhZ2UgQWNxdWlzaXRpb24gYW5kIExlYXJuaW5nIiwgInNjb3JlIjogMC40NDAyMDAwMDEwMDEzNTgwMywgInN1YmZpZWxkIjogeyJpZCI6ICJodHRwczovL29wZW5hbGV4Lm9yZy9zdWJmaWVsZHMvMzIwNCIsICJkaXNwbGF5X25hbWUiOiAiRGV2ZWxvcG1lbnRhbCBhbmQgRWR1Y2F0aW9uYWwgUHN5Y2hvbG9neSJ9LCAiZmllbGQiOiB7ImlkIjogImh0dHBzOi8vb3BlbmFsZXgub3JnL2ZpZWxkcy8zMiIsICJkaXNwbGF5X25hbWUiOiAiUHN5Y2hvbG9neSJ9LCAiZG9tYWluIjogeyJpZCI6ICJodHRwczovL29wZW5hbGV4Lm9yZy9kb21haW5zLzIiLCAiZGlzcGxheV9uYW1lIjogIlNvY2lhbCBTY2llbmNlcyJ9fSwgInRvcGljcyI6IFt7ImlkIjogImh0dHBzOi8vb3BlbmFsZXgub3JnL1QxMTU4NyIsICJkaXNwbGF5X25hbWUiOiAiU2Vjb25kIExhbmd1YWdlIEFjcXVpc2l0aW9uIGFuZCBMZWFybmluZyIsICJzY29yZSI6IDAuNDQwMjAwMDAxMDAxMzU4MDMsICJzdWJmaWVsZCI6IHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvc3ViZmllbGRzLzMyMDQiLCAiZGlzcGxheV9uYW1lIjogIkRldmVsb3BtZW50YWwgYW5kIEVkdWNhdGlvbmFsIFBzeWNob2xvZ3kifSwgImZpZWxkIjogeyJpZCI6ICJodHRwczovL29wZW5hbGV4Lm9yZy9maWVsZHMvMzIiLCAiZGlzcGxheV9uYW1lIjogIlBzeWNob2xvZ3kifSwgImRvbWFpbiI6IHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvZG9tYWlucy8yIiwgImRpc3BsYXlfbmFtZSI6ICJTb2NpYWwgU2NpZW5jZXMifX0sIHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVDExOTAyIiwgImRpc3BsYXlfbmFtZSI6ICJJbnRlbGxpZ2VudCBUdXRvcmluZyBTeXN0ZW1zIGFuZCBBZGFwdGl2ZSBMZWFybmluZyIsICJzY29yZSI6IDAuMjQzNDk5OTk0Mjc3OTU0MSwgInN1YmZpZWxkIjogeyJpZCI6ICJodHRwczovL29wZW5hbGV4Lm9yZy9zdWJmaWVsZHMvMTcwMiIsICJkaXNwbGF5X25hbWUiOiAiQXJ0aWZpY2lhbCBJbnRlbGxpZ2VuY2UifSwgImZpZWxkIjogeyJpZCI6ICJodHRwczovL29wZW5hbGV4Lm9yZy9maWVsZHMvMTciLCAiZGlzcGxheV9uYW1lIjogIkNvbXB1dGVyIFNjaWVuY2UifSwgImRvbWFpbiI6IHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvZG9tYWlucy8zIiwgImRpc3BsYXlfbmFtZSI6ICJQaHlzaWNhbCBTY2llbmNlcyJ9fSwgeyJpZCI6ICJodHRwczovL29wZW5hbGV4Lm9yZy9UMTExMjIiLCAiZGlzcGxheV9uYW1lIjogIk9ubGluZSBMZWFybmluZyBhbmQgQW5hbHl0aWNzIiwgInNjb3JlIjogMC4xMDA5MDAwMDE4MjM5MDIxMywgInN1YmZpZWxkIjogeyJpZCI6ICJodHRwczovL29wZW5hbGV4Lm9yZy9zdWJmaWVsZHMvMTcwNiIsICJkaXNwbGF5X25hbWUiOiAiQ29tcHV0ZXIgU2NpZW5jZSBBcHBsaWNhdGlvbnMifSwgImZpZWxkIjogeyJpZCI6ICJodHRwczovL29wZW5hbGV4Lm9yZy9maWVsZHMvMTciLCAiZGlzcGxheV9uYW1lIjogIkNvbXB1dGVyIFNjaWVuY2UifSwgImRvbWFpbiI6IHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvZG9tYWlucy8zIiwgImRpc3BsYXlfbmFtZSI6ICJQaHlzaWNhbCBTY2llbmNlcyJ9fV0sICJrZXl3b3JkcyI6IFt7ImlkIjogImh0dHBzOi8vb3BlbmFsZXgub3JnL2tleXdvcmRzL3NwYWNlZC1yZXBldGl0aW9uIiwgImRpc3BsYXlfbmFtZSI6ICJzcGFjZWQgcmVwZXRpdGlvbiIsICJzY29yZSI6IDAuOTg3OTk5OTc1NjgxMzA0OX0sIHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcva2V5d29yZHMvc2Vjb25kLWxhbmd1YWdlLWFjcXVpc2l0aW9uIiwgImRpc3BsYXlfbmFtZSI6ICJzZWNvbmQgbGFuZ3VhZ2UgYWNxdWlzaXRpb24iLCAic2NvcmUiOiAwLjk4NTAwMDAxNDMwNTExNDd9LCB7ImlkIjogImh0dHBzOi8vb3BlbmFsZXgub3JnL2tleXdvcmRzL2xhbmd1YWdlLWxlYXJuaW5nIiwgImRpc3BsYXlfbmFtZSI6ICJsYW5ndWFnZSBsZWFybmluZyIsICJzY29yZSI6IDAuNjk4MDAwMDEzODI4Mjc3Nn0sIHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcva2V5d29yZHMvbG9uZy10ZXJtLW1lbW9yeSIsICJkaXNwbGF5X25hbWUiOiAibG9uZy10ZXJtIG1lbW9yeSIsICJzY29yZSI6IDAuNjk5OTk5OTg4MDc5MDcxfSwgeyJpZCI6ICJodHRwczovL29wZW5hbGV4Lm9yZy9rZXl3b3Jkcy9yZWNhbGwtcHJlZGljdGlvbiIsICJkaXNwbGF5X25hbWUiOiAicmVjYWxsIHByZWRpY3Rpb24iLCAic2NvcmUiOiAwLjgzMDk5OTk3MDQzNjA5NjJ9LCB7ImlkIjogImh0dHBzOi8vb3BlbmFsZXgub3JnL2tleXdvcmRzL2R1b2xpbmdvIiwgImRpc3BsYXlfbmFtZSI6ICJEdW9saW5nbyIsICJzY29yZSI6IDAuOTMwMDAwMDA3MTUyNTU3NH0sIHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcva2V5d29yZHMvc3R1ZGVudC1lbmdhZ2VtZW50IiwgImRpc3BsYXlfbmFtZSI6ICJzdHVkZW50IGVuZ2FnZW1lbnQiLCAic2NvcmUiOiAwLjY5MDk5OTk4NDc0MTIxMDl9LCB7ImlkIjogImh0dHBzOi8vb3BlbmFsZXgub3JnL2tleXdvcmRzL3BzeWNob2xpbmd1aXN0aWNzIiwgImRpc3BsYXlfbmFtZSI6ICJwc3ljaG9saW5ndWlzdGljcyIsICJzY29yZSI6IDAuNjM0MDAwMDAzMzM3ODYwMX0sIHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcva2V5d29yZHMvb25saW5lLWxhbmd1YWdlLWxlYXJuaW5nIiwgImRpc3BsYXlfbmFtZSI6ICJvbmxpbmUgbGFuZ3VhZ2UgbGVhcm5pbmciLCAic2NvcmUiOiAwLjU0MTk5OTk5NTcwODQ2NTZ9XSwgImNvbmNlcHRzIjogW3siaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvQzI3NzYxNDE1MTUiLCAid2lraWRhdGEiOiAiaHR0cHM6Ly93d3cud2lraWRhdGEub3JnL3dpa2kvUTEyNzQ0NzkiLCAiZGlzcGxheV9uYW1lIjogIlJlcGV0aXRpb24gKHJoZXRvcmljYWwgZGV2aWNlKSIsICJsZXZlbCI6IDIsICJzY29yZSI6IDAuODI3MTc0NjAzOTM5MDU2NH0sIHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvQzQxMDA4MTQ4IiwgIndpa2lkYXRhIjogImh0dHBzOi8vd3d3Lndpa2lkYXRhLm9yZy93aWtpL1EyMTE5OCIsICJkaXNwbGF5X25hbWUiOiAiQ29tcHV0ZXIgc2NpZW5jZSIsICJsZXZlbCI6IDAsICJzY29yZSI6IDAuNzAwOTExOTk4NzQ4Nzc5M30sIHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvQzEzNzI5Mzc2MCIsICJ3aWtpZGF0YSI6ICJodHRwczovL3d3dy53aWtpZGF0YS5vcmcvd2lraS9RMzYyMTY5NiIsICJkaXNwbGF5X25hbWUiOiAiTGFuZ3VhZ2UgbW9kZWwiLCAibGV2ZWwiOiAyLCAic2NvcmUiOiAwLjQ1ODQwMjQ1NDg1MzA1Nzg2fSwgeyJpZCI6ICJodHRwczovL29wZW5hbGV4Lm9yZy9DMjg0OTAzMTQiLCAid2lraWRhdGEiOiAiaHR0cHM6Ly93d3cud2lraWRhdGEub3JnL3dpa2kvUTE4OTQzNiIsICJkaXNwbGF5X25hbWUiOiAiU3BlZWNoIHJlY29nbml0aW9uIiwgImxldmVsIjogMSwgInNjb3JlIjogMC4zNjU4OTY5MTA0MjkwMDA4NX0sIHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvQzIwNDMyMTQ0NyIsICJ3aWtpZGF0YSI6ICJodHRwczovL3d3dy53aWtpZGF0YS5vcmcvd2lraS9RMzA2NDIiLCAiZGlzcGxheV9uYW1lIjogIk5hdHVyYWwgbGFuZ3VhZ2UgcHJvY2Vzc2luZyIsICJsZXZlbCI6IDEsICJzY29yZSI6IDAuMzYwMzE1NjIwODk5MjAwNDR9LCB7ImlkIjogImh0dHBzOi8vb3BlbmFsZXgub3JnL0MxNTQ5NDUzMDIiLCAid2lraWRhdGEiOiAiaHR0cHM6Ly93d3cud2lraWRhdGEub3JnL3dpa2kvUTExNjYwIiwgImRpc3BsYXlfbmFtZSI6ICJBcnRpZmljaWFsIGludGVsbGlnZW5jZSIsICJsZXZlbCI6IDEsICJzY29yZSI6IDAuMzIxNzIwODk4MTUxMzk3N30sIHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvQzQxODk1MjAyIiwgIndpa2lkYXRhIjogImh0dHBzOi8vd3d3Lndpa2lkYXRhLm9yZy93aWtpL1E4MTYyIiwgImRpc3BsYXlfbmFtZSI6ICJMaW5ndWlzdGljcyIsICJsZXZlbCI6IDEsICJzY29yZSI6IDAuMjExOTMwODQxMjA3NTA0Mjd9LCB7ImlkIjogImh0dHBzOi8vb3BlbmFsZXgub3JnL0MxMzg4ODU2NjIiLCAid2lraWRhdGEiOiAiaHR0cHM6Ly93d3cud2lraWRhdGEub3JnL3dpa2kvUTU4OTEiLCAiZGlzcGxheV9uYW1lIjogIlBoaWxvc29waHkiLCAibGV2ZWwiOiAwLCAic2NvcmUiOiAwLjB9XSwgIm1lc2giOiBbXSwgImxvY2F0aW9uc19jb3VudCI6IDEsICJsb2NhdGlvbnMiOiBbeyJpZCI6ICJkb2k6MTAuMTg2NTMvdjEvcDE2LTExNzQiLCAiZG9pIjogImh0dHBzOi8vZG9pLm9yZy8xMC4xODY1My92MS9wMTYtMTE3NCIsICJpc19vYSI6IHRydWUsICJsYW5kaW5nX3BhZ2VfdXJsIjogImh0dHBzOi8vZG9pLm9yZy8xMC4xODY1My92MS9wMTYtMTE3NCIsICJwZGZfdXJsIjogImh0dHBzOi8vd3d3LmFjbHdlYi5vcmcvYW50aG9sb2d5L1AxNi0xMTc0LnBkZiIsICJzb3VyY2UiOiB7ImlkIjogImh0dHBzOi8vb3BlbmFsZXgub3JnL1M0MzYzNjA4NjUyIiwgImRpc3BsYXlfbmFtZSI6ICJBbm51YWwgTWVldGluZyBvZiB0aGUgQXNzb2NpYXRpb24gZm9yIENvbXB1dGF0aW9uYWwgTGluZ3Vpc3RpY3MgKEFDTCkiLCAiaXNzbl9sIjogbnVsbCwgImlzc24iOiBudWxsLCAiaXNfb2EiOiBmYWxzZSwgImlzX2luX2RvYWoiOiBmYWxzZSwgImlzX2NvcmUiOiBmYWxzZSwgImxpc3RlZF9pbiI6IFtdLCAiaG9zdF9vcmdhbml6YXRpb24iOiBudWxsLCAiaG9zdF9vcmdhbml6YXRpb25fbmFtZSI6IG51bGwsICJob3N0X29yZ2FuaXphdGlvbl9saW5lYWdlIjogW10sICJob3N0X29yZ2FuaXphdGlvbl9saW5lYWdlX25hbWVzIjogW10sICJ0eXBlIjogImNvbmZlcmVuY2UifSwgImxpY2Vuc2UiOiAiY2MtYnkiLCAibGljZW5zZV9pZCI6ICJodHRwczovL29wZW5hbGV4Lm9yZy9saWNlbnNlcy9jYy1ieSIsICJ2ZXJzaW9uIjogInB1Ymxpc2hlZFZlcnNpb24iLCAiaXNfYWNjZXB0ZWQiOiB0cnVlLCAiaXNfcHVibGlzaGVkIjogdHJ1ZSwgInJhd19zb3VyY2VfbmFtZSI6ICJQcm9jZWVkaW5ncyBvZiB0aGUgNTR0aCBBbm51YWwgTWVldGluZyBvZiB0aGUgQXNzb2NpYXRpb24gZm9yIENvbXB1dGF0aW9uYWwgTGluZ3Vpc3RpY3MgKFZvbHVtZSAxOiBMb25nIFBhcGVycykiLCAicmF3X3R5cGUiOiAicHJvY2VlZGluZ3MtYXJ0aWNsZSJ9XSwgImJlc3Rfb2FfbG9jYXRpb24iOiB7ImlkIjogImRvaToxMC4xODY1My92MS9wMTYtMTE3NCIsICJkb2kiOiAiaHR0cHM6Ly9kb2kub3JnLzEwLjE4NjUzL3YxL3AxNi0xMTc0IiwgImlzX29hIjogdHJ1ZSwgImxhbmRpbmdfcGFnZV91cmwiOiAiaHR0cHM6Ly9kb2kub3JnLzEwLjE4NjUzL3YxL3AxNi0xMTc0IiwgInBkZl91cmwiOiAiaHR0cHM6Ly93d3cuYWNsd2ViLm9yZy9hbnRob2xvZ3kvUDE2LTExNzQucGRmIiwgInNvdXJjZSI6IHsiaWQiOiAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvUzQzNjM2MDg2NTIiLCAiZGlzcGxheV9uYW1lIjogIkFubnVhbCBNZWV0aW5nIG9mIHRoZSBBc3NvY2lhdGlvbiBmb3IgQ29tcHV0YXRpb25hbCBMaW5ndWlzdGljcyAoQUNMKSIsICJpc3NuX2wiOiBudWxsLCAiaXNzbiI6IG51bGwsICJpc19vYSI6IGZhbHNlLCAiaXNfaW5fZG9haiI6IGZhbHNlLCAiaXNfY29yZSI6IGZhbHNlLCAibGlzdGVkX2luIjogW10sICJob3N0X29yZ2FuaXphdGlvbiI6IG51bGwsICJob3N0X29yZ2FuaXphdGlvbl9uYW1lIjogbnVsbCwgImhvc3Rfb3JnYW5pemF0aW9uX2xpbmVhZ2UiOiBbXSwgImhvc3Rfb3JnYW5pemF0aW9uX2xpbmVhZ2VfbmFtZXMiOiBbXSwgInR5cGUiOiAiY29uZmVyZW5jZSJ9LCAibGljZW5zZSI6ICJjYy1ieSIsICJsaWNlbnNlX2lkIjogImh0dHBzOi8vb3BlbmFsZXgub3JnL2xpY2Vuc2VzL2NjLWJ5IiwgInZlcnNpb24iOiAicHVibGlzaGVkVmVyc2lvbiIsICJpc19hY2NlcHRlZCI6IHRydWUsICJpc19wdWJsaXNoZWQiOiB0cnVlLCAicmF3X3NvdXJjZV9uYW1lIjogIlByb2NlZWRpbmdzIG9mIHRoZSA1NHRoIEFubnVhbCBNZWV0aW5nIG9mIHRoZSBBc3NvY2lhdGlvbiBmb3IgQ29tcHV0YXRpb25hbCBMaW5ndWlzdGljcyAoVm9sdW1lIDE6IExvbmcgUGFwZXJzKSIsICJyYXdfdHlwZSI6ICJwcm9jZWVkaW5ncy1hcnRpY2xlIn0sICJzdXN0YWluYWJsZV9kZXZlbG9wbWVudF9nb2FscyI6IFt7InNjb3JlIjogMC42MTY0MDAwMDM0MzMyMjc1LCAiaWQiOiAiaHR0cHM6Ly9tZXRhZGF0YS51bi5vcmcvc2RnLzQiLCAiZGlzcGxheV9uYW1lIjogIlF1YWxpdHkgZWR1Y2F0aW9uIn1dLCAic3VzdGFpbmFibGVfZGV2ZWxvcG1lbnRfZ29hbHNfYXVyb3JhIjogW3sic2NvcmUiOiAwLjU2OTk5OTk5Mjg0NzQ0MjYsICJpZCI6ICJodHRwczovL21ldGFkYXRhLnVuLm9yZy9zZGcvNCIsICJkaXNwbGF5X25hbWUiOiAiUXVhbGl0eSBlZHVjYXRpb24ifV0sICJzdHVkeV9kZXNpZ25zIjogW10sICJhd2FyZHMiOiBbXSwgImZ1bmRlcnMiOiBbXSwgImhhc19jb250ZW50IjogeyJwZGYiOiB0cnVlLCAiZ3JvYmlkX3htbCI6IHRydWV9LCAiY29udGVudF91cmxzIjogeyJwZGYiOiAiaHR0cHM6Ly9jb250ZW50Lm9wZW5hbGV4Lm9yZy93b3Jrcy9XMjUxNDg5Nzk1OS5wZGYiLCAiZ3JvYmlkX3htbCI6ICJodHRwczovL2NvbnRlbnQub3BlbmFsZXgub3JnL3dvcmtzL1cyNTE0ODk3OTU5Lmdyb2JpZC14bWwifSwgInJlZmVyZW5jZWRfd29ya3NfY291bnQiOiAyMiwgInJlZmVyZW5jZWRfd29ya3MiOiBbImh0dHBzOi8vb3BlbmFsZXgub3JnL1cyMzQ5MzU2NTAiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzE1MDQyNjQ3MjAiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzE5ODg3MzcwMTciLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIwMjY0ODA4OTkiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIwMjk1MDc3NjQiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIwMzAwMDc4NTAiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIwNDkyNjA3MTgiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIwNDk0Mjg0NjQiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIwNTY1MTM0NDYiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIwNTgxNjYwNDMiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIwODQxMjk1ODgiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIwODkzNjUzMzMiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIxMTkzMzUyNTUiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIxMjY4MDcwNjgiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIxMzAwMDA5NTciLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIxMzk0NDg0NjkiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIxNDY1MDI2MzUiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIxNTg2OTg2OTEiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzIzMDQxMjc0ODYiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzI0NjE4OTIwNDMiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzI3NDg3NTUyNTYiLCAiaHR0cHM6Ly9vcGVuYWxleC5vcmcvVzQyMzk4MTM1MjgiXSwgInJlbGF0ZWRfd29ya3MiOiBbImh0dHBzOi8vb3BlbmFsZXgub3JnL1cxOTg5NzA1MTUzIiwgImh0dHBzOi8vb3BlbmFsZXgub3JnL1cyNzg5OTE5NjE5IiwgImh0dHBzOi8vb3BlbmFsZXgub3JnL1cyNDk2MjI4ODQ2IiwgImh0dHBzOi8vb3BlbmFsZXgub3JnL1cyMjkzNDU3MDE2IiwgImh0dHBzOi8vb3BlbmFsZXgub3JnL1cyODk2NDExOTMyIiwgImh0dHBzOi8vb3BlbmFsZXgub3JnL1cxNTUxNDA2NzM4IiwgImh0dHBzOi8vb3BlbmFsZXgub3JnL1cyNjEwMzg3NzE0IiwgImh0dHBzOi8vb3BlbmFsZXgub3JnL1cyMzY5MzA4NDI2IiwgImh0dHBzOi8vb3BlbmFsZXgub3JnL1cxNTY5ODQxMjg3IiwgImh0dHBzOi8vb3BlbmFsZXgub3JnL1cyMzU5MDAxODcxIl0sICJhYnN0cmFjdF9pbnZlcnRlZF9pbmRleCI6IHsiV2UiOiBbMF0sICJwcmVzZW50IjogWzFdLCAiaGFsZi1saWZlIjogWzJdLCAicmVncmVzc2lvbiI6IFszXSwgIihITFIpLCI6IFs0XSwgImEiOiBbNSwgMzEsIDM2XSwgIm5vdmVsIjogWzZdLCAibW9kZWwiOiBbNywgNjddLCAiZm9yIjogWzgsIDc5XSwgInNwYWNlZCI6IFs5XSwgInJlcGV0aXRpb24iOiBbMTBdLCAicHJhY3RpY2UiOiBbMTFdLCAid2l0aCI6IFsxMiwgMjFdLCAiYXBwbGljYXRpb25zIjogWzEzXSwgInRvIjogWzE0LCA1OSwgODZdLCAic2Vjb25kIjogWzE1LCA4MF0sICJsYW5ndWFnZSI6IFsxNiwgNDcsIDgxXSwgImFjcXVpc2l0aW9uLkhMUiI6IFsxN10sICJjb21iaW5lcyI6IFsxOF0sICJwc3ljaG9saW5ndWlzdGljIjogWzE5XSwgInRoZW9yeSI6IFsyMF0sICJtb2Rlcm4iOiBbMjJdLCAibWFjaGluZSI6IFsyM10sICJsZWFybmluZyI6IFsyNCwgNDhdLCAidGVjaG5pcXVlcywiOiBbMjVdLCAiaW5kaXJlY3RseSI6IFsyNl0sICJlc3RpbWF0aW5nIjogWzI3XSwgInRoZSI6IFsyOF0sICJcImhhbGZsaWZlXCIiOiBbMjldLCAib2YiOiBbMzBdLCAid29yZCI6IFszMl0sICJvciI6IFszM10sICJjb25jZXB0IjogWzM0XSwgImluIjogWzM1LCA5NF0sICJzdHVkZW50J3MiOiBbMzddLCAibG9uZy10ZXJtIjogWzM4XSwgIm1lbW9yeS5XZSI6IFszOV0sICJ1c2UiOiBbNDBdLCAiZGF0YSI6IFs0MV0sICJmcm9tIjogWzQyXSwgIkR1b2xpbmdvIjogWzQzLCA4OF0sICItYSI6IFs0NF0sICJwb3B1bGFyIjogWzQ1XSwgIm9ubGluZSI6IFs0Nl0sICJhcHBsaWNhdGlvbiI6IFs0OV0sICItdG8iOiBbNTBdLCAiZml0IjogWzUxXSwgIkhMUiI6IFs1MiwgODNdLCAibW9kZWxzLCI6IFs1M10sICJyZWR1Y2luZyI6IFs1NF0sICJlcnJvciI6IFs1NV0sICJieSI6IFs1NiwgOTJdLCAiNDUlKyI6IFs1N10sICJjb21wYXJlZCI6IFs1OF0sICJzZXZlcmFsIjogWzYwXSwgImJhc2VsaW5lcyI6IFs2MV0sICJhdCI6IFs2Ml0sICJwcmVkaWN0aW5nIjogWzYzXSwgInN0dWRlbnQiOiBbNjQsIDkwXSwgInJlY2FsbCI6IFs2NV0sICJyYXRlcy5ITFIiOiBbNjZdLCAid2VpZ2h0cyI6IFs2OF0sICJhbHNvIjogWzY5XSwgInNoZWQiOiBbNzBdLCAibGlnaHQiOiBbNzFdLCAib24iOiBbNzJdLCAid2hpY2giOiBbNzNdLCAibGluZ3Vpc3RpYyI6IFs3NF0sICJjb25jZXB0cyI6IFs3NV0sICJhcmUiOiBbNzZdLCAic3lzdGVtYXRpY2FsbHkiOiBbNzddLCAiY2hhbGxlbmdpbmciOiBbNzhdLCAibGVhcm5lcnMuRmluYWxseSwiOiBbODJdLCAid2FzIjogWzg0XSwgImFibGUiOiBbODVdLCAiaW1wcm92ZSI6IFs4N10sICJkYWlseSI6IFs4OV0sICJlbmdhZ2VtZW50IjogWzkxXSwgIjEyJSI6IFs5M10sICJhbiI6IFs5NV0sICJvcGVyYXRpb25hbCI6IFs5Nl0sICJ1c2VyIjogWzk3XSwgInN0dWR5LiI6IFs5OF19LCAiY291bnRzX2J5X3llYXIiOiBbeyJ5ZWFyIjogMjAyNiwgImNpdGVkX2J5X2NvdW50IjogMzR9LCB7InllYXIiOiAyMDI1LCAiY2l0ZWRfYnlfY291bnQiOiAzM30sIHsieWVhciI6IDIwMjQsICJjaXRlZF9ieV9jb3VudCI6IDEzfSwgeyJ5ZWFyIjogMjAyMywgImNpdGVkX2J5X2NvdW50IjogMjF9LCB7InllYXIiOiAyMDIyLCAiY2l0ZWRfYnlfY291bnQiOiAxOH0sIHsieWVhciI6IDIwMjEsICJjaXRlZF9ieV9jb3VudCI6IDI3fSwgeyJ5ZWFyIjogMjAyMCwgImNpdGVkX2J5X2NvdW50IjogMjB9LCB7InllYXIiOiAyMDE5LCAiY2l0ZWRfYnlfY291bnQiOiAyNH0sIHsieWVhciI6IDIwMTgsICJjaXRlZF9ieV9jb3VudCI6IDIxfSwgeyJ5ZWFyIjogMjAxNywgImNpdGVkX2J5X2NvdW50IjogNn1dLCAidXBkYXRlZF9kYXRlIjogIjIwMjYtMTAtMTZUMDk6NTk6MjIuMjM1MTczIiwgImNyZWF0ZWRfZGF0ZSI6ICIyMDI1LTEwLTEwVDAwOjAwOjAwIn1dLCAiZ3JvdXBfYnkiOiBbXX0=","hits":[{"id":"https://openalex.org/W2514897959","family":"research","provider":"openalex","title":"A Trainable Spaced Repetition Model for Language Learning","url":"https://openalex.org/W2514897959","retrieved_at":"2026-10-20T16:39:10.631107Z","content":"excerpt","excerpt":"We present half-life regression (HLR), a novel model for spaced repetition practice with applications to second language acquisition.HLR combines psycholinguistic theory with modern machine learning techniques, indirectly estimating the \"halflife\" of a word or concept in a student's long-term memory.We use data from Duolingo -a popular online language learning application -to fit HLR models, reducing error by 45%+ compared to several baselines at predicting student recall rates.HLR model weights also shed light on which linguistic concepts are systematically challenging for second language learners.Finally, HLR was able to improve Duolingo daily student engagement by 12% in an operational user study.","locator":"https://openalex.org/W2514897959#/abstract_inverted_index","license":"CC0","free_access":"free","upstream_revision":"2026-10-16T09:59:22.235173","representation":"abstract","truncated":false}]}]}"########;
fn captured_response() -> serde_json::Value {
    serde_json::from_str(CAPTURED_REAL_RESPONSE).unwrap()
}

fn reject_mutations(variants: Vec<serde_json::Value>) {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("negative.sqlite").to_str().unwrap()).unwrap();
    let req = request(&mut conn);
    research::begin(&mut conn, &req).unwrap();
    for (index, value) in variants.into_iter().enumerate() {
        assert!(
            research::publish(&mut conn, &req, value).is_err(),
            "mutation {index} was accepted"
        );
        assert_eq!(
            research::read(&conn, &req.request_id).unwrap().unwrap()["state"],
            "unknown"
        );
        let count: i64 = conn
            .query_row("SELECT count(*) FROM sources", [], |row| row.get(0))
            .unwrap();
        assert_eq!(count, 0, "mutation {index} published source rows");
    }
}

#[test]
fn channel_url_must_bind_every_fixed_parameter_and_decoded_public_query() {
    let original = captured_response();
    let mut variants = Vec::new();
    for (channel, old, new) in [
        (0, "gsrsearch=spaced+repetition", "gsrsearch=different"),
        (0, "gsrlimit=1", "gsrlimit=3"),
        (0, "rvsection=0", "rvsection=1"),
        (0, "generator=search", "generator=allpages"),
        (1, "site=academia", "site=stackoverflow"),
        (1, "q=spaced+repetition", "q=different"),
        (1, "pagesize=1", "pagesize=99"),
        (1, "filter=withbody", "filter=default"),
        (1, "sort=relevance", "sort=activity"),
        (2, "search=spaced+repetition", "search=different"),
        (2, "per_page=1", "per_page=3"),
    ] {
        let mut value = original.clone();
        value["channels"][channel]["request_url"] = json!(
            value["channels"][channel]["request_url"]
                .as_str()
                .unwrap()
                .replace(old, new)
        );
        variants.push(value);
    }
    for suffix in [
        "&search=other",
        "&api_key=unexpected",
        "&extra=x",
        "#fragment",
        "&bad=%GG",
        "&%73earch=spaced+repetition",
    ] {
        let mut value = original.clone();
        value["channels"][2]["request_url"] = json!(format!(
            "{}{}",
            value["channels"][2]["request_url"].as_str().unwrap(),
            suffix
        ));
        variants.push(value);
    }
    reject_mutations(variants);
}

#[test]
fn nullable_fields_are_required_but_explicit_null_is_valid() {
    let original = captured_response();
    let mut variants = Vec::new();
    for name in ["retry_after_seconds", "error_code", "raw_response_base64"] {
        let mut value = original.clone();
        value["channels"][0].as_object_mut().unwrap().remove(name);
        variants.push(value);
    }
    for name in ["locator", "license", "upstream_revision"] {
        let mut value = original.clone();
        value["channels"][1]["hits"][0]
            .as_object_mut()
            .unwrap()
            .remove(name);
        variants.push(value);
    }
    // Missing raw bytes on failure must not silently deserialize as a null receipt.
    let mut failed = original.clone();
    failed["channels"][0]["status"] = json!("failed");
    failed["channels"][0]["error_code"] = json!("network_unavailable");
    failed["channels"][0]["hits"] = json!([]);
    failed["channels"][0]
        .as_object_mut()
        .unwrap()
        .remove("raw_response_base64");
    variants.push(failed);
    reject_mutations(variants);
}

#[test]
fn timestamps_family_representations_and_stable_source_identities_are_bound() {
    let original = captured_response();
    let mut variants = Vec::new();
    for timestamp in [
        "x",
        "2026-02-30T00:00:00Z",
        "2026-10-20T25:00:00Z",
        "2026-10-20T16:39:07+00:00",
        "2026-10-20T16:39:07.Z",
    ] {
        let mut value = original.clone();
        value["channels"][0]["retrieved_at"] = json!(timestamp);
        value["channels"][0]["hits"][0]["retrieved_at"] = json!(timestamp);
        variants.push(value);
    }
    for (channel, field, change) in [
        (0, "retrieved_at", json!("2026-10-21T00:00:00Z")),
        (0, "id", json!("wikipedia:en:27805:1")),
        (0, "upstream_revision", json!("0001378842130")),
        (0, "locator", json!("pageid=999;revid=1378842130;section=0")),
        (0, "content", json!("full_text")),
        (0, "representation", json!("abstract")),
        (1, "id", json!("stackexchange:academia:question:69101")),
        (
            1,
            "url",
            json!("https://academia.stackexchange.com/questions/69100evil"),
        ),
        (
            1,
            "url",
            json!("https://academia.stackexchange.com/questions/69100/../../private"),
        ),
        (1, "upstream_revision", json!("invented-revision")),
        (1, "locator", json!("unbound")),
        (1, "representation", json!("wikitext")),
        (1, "truncated", json!(true)),
        (2, "id", json!("https://openalex.org/W999")),
        (
            2,
            "url",
            json!("https://openalex.org/W2514897959?api_key=private"),
        ),
        (2, "content", json!("full_text")),
        (2, "representation", json!("html_text")),
        (2, "license", json!("CC BY-SA 4.0")),
        (2, "excerpt", json!("")),
    ] {
        let mut value = original.clone();
        value["channels"][channel]["hits"][0][field] = change;
        variants.push(value);
    }
    reject_mutations(variants);
}

#[test]
fn request_character_bounds_match_worker_without_conflating_utf8_bytes() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("bounds.sqlite").to_str().unwrap()).unwrap();
    let mut req = request(&mut conn);
    req.query = "a".repeat(1001);
    assert!(req.validate().is_err());
    req.query = "汉".repeat(1000);
    assert!(req.validate().is_ok());
    req.query = "😀".repeat(1000);
    assert_eq!(req.query.len(), 4000);
    assert!(req.validate().is_ok());
    req.query.push('a');
    assert!(req.validate().is_err());
}

#[test]
fn captured_three_provider_response_replays_exact_raw_bytes_and_derives_after_restart() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("captured.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let req = request(&mut conn);
    let captured = captured_response();
    research::begin(&mut conn, &req).unwrap();
    let receipt = research::publish(&mut conn, &req, captured.clone()).unwrap();
    assert_eq!(receipt["state"], "complete");
    for (stored, original) in receipt["channels"]
        .as_array()
        .unwrap()
        .iter()
        .zip(captured["channels"].as_array().unwrap())
    {
        let raw = STANDARD
            .decode(original["raw_response_base64"].as_str().unwrap())
            .unwrap();
        let read = archeaxis_store_sqlite::raw_objects::read(
            &conn,
            stored["raw_source"]["sha256"].as_str().unwrap(),
        )
        .unwrap();
        assert_eq!(read, raw);
        assert_eq!(stored["hits"], original["hits"]);
    }
    drop(conn);
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(
        research::read(&conn, &req.request_id).unwrap().unwrap(),
        receipt
    );
    assert_eq!(research::list(&conn).unwrap()["receipts"][0], receipt);
    for channel in receipt["channels"].as_array().unwrap() {
        let hit = &channel["hits"][0];
        let selected = research::materialize(
            &mut conn,
            &req.request_id,
            channel["family"].as_str().unwrap(),
            hit["id"].as_str().unwrap(),
        )
        .unwrap();
        assert_ne!(selected["reference"], selected["raw_reference"]);
        assert_eq!(selected["knowledge_admission"], "not_executed");
    }
    let count: i64 = conn
        .query_row("SELECT count(*) FROM sources", [], |r| r.get(0))
        .unwrap();
    assert_eq!(count, 6);
}
