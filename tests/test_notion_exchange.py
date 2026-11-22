import copy
import csv
import io

from scripts.ingest.notion_exchange import csv_bytes, page_relations, table_groups


def test_equivalent_view_and_full_csv_share_only_the_matching_paths_and_bytes():
    base = "Folder/Projects " + "a" * 32
    native = {"sha256": "snapshot"}
    other = "Folder/Projects " + "b" * 32 + ".csv"
    files = {base + ".csv": native, base + "_all.csv": native, other: native, "attachment.csv": native}
    assert table_groups(files) == [[base + ".csv", base + "_all.csv"], [other]]
    files[base + "_all.csv"] = {"sha256": "full database"}
    assert table_groups(files) == [[base + ".csv"], [base + "_all.csv"], [other]]


def test_cell_writeback_preserves_duplicate_headers_and_rows_and_embedded_record_separators():
    raw = b"\xef\xbb\xbfLabel,Label\nsame,\nsame,"
    initial = {"properties": [{"property_id": "a"}, {"property_id": "b"}], "records": [
        {"record_id": i, "reference": {"block_id": i}, "values": {"a": "same", "b": ""}}
        for i in ("first", "second")]}
    current = copy.deepcopy(initial)
    assert csv_bytes(raw, initial, current) == raw
    current["records"][1]["values"]["b"] = 'A,\rB\n"C"'
    returned = csv_bytes(raw, initial, current)
    assert returned.startswith(b"\xef\xbb\xbfLabel,Label\n") and not returned.endswith(b"\n")
    assert list(csv.reader(io.StringIO(returned.decode("utf-8-sig"), newline=""))) == [
        ["Label", "Label"], ["same", ""], ["same", 'A,\rB\n"C"']]


def test_relative_page_and_file_properties_bind_to_the_named_sources():
    parent = "Projects " + "0" * 32
    page = parent + "/Row " + "1" * 32 + ".md"
    sources = {name: {"source_id": name, "sha256": "d" * 64}
               for name in (parent + "_all.csv", "a b.png", parent + "/B 2.md", "shared.md")}
    md = "# Row\n\nFiles: ../a%20b.png\nPeer: B (B%202.md)\n\n[quote](../shared.md#p)\n\n[missing](absent.md)"
    relations, losses = page_relations(page, md, sources)
    assert [link["target"]["source_id"] for link in relations["relations"]] == list(sources)
    assert [loss["target"] for loss in losses] == ["../shared.md#p", "absent.md"]
