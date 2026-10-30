"""Finite desktop semantic transport contract; no API/model execution."""
import copy
import json
from pathlib import Path
from jsonschema import Draft202012Validator
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "packages/contracts/v1/core-document.schema.json").read_bytes())

def test_strict_query_and_operation_scope():
    validator = Draft202012Validator({"$ref":"#/$defs/SemanticSearchInput", "$defs":SCHEMA["$defs"]})
    assert validator.is_valid({"q":"🛰" * 2048})
    for invalid in [{}, {"q":""}, {"q":"  "}, {"q":True}, {"q":"x" * 2049}, {"q":"query", "model":"override"}, {"q":"query", "candidates":[]}]:
        assert not validator.is_valid(invalid)
    commands=json.loads((ROOT / "packages/contracts/v1/core-command.schema.json").read_bytes())
    operations=commands["properties"]["operation"]["enum"]
    assert operations.count("semantic_search")==1
    assert not set(operations) & {"vault_links", "vault_members", "vault_links_record"}

def test_schema_and_openapi_bind_existing_bounds():
    Draft202012Validator.check_schema(copy.deepcopy(SCHEMA))
    document=yaml.safe_load((ROOT / "packages/contracts/v1/openapi-outline.yaml").read_text(encoding="utf-8"))
    operation=document["paths"]["/api/v1/search/semantic"]["post"]
    assert operation["x-core-deadline-seconds"]==90
    assert operation["x-desktop-transport-seconds"]==135
    assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith("/SemanticSearchInput")
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/SemanticSearchDto")
    assert {"401","403","409","422","500","502","503","504"} <= operation["responses"].keys()

def test_empty_response_and_bounded_rank_types():
    check=Draft202012Validator({"$ref":"#/$defs/SemanticSearchDto", "$defs":SCHEMA["$defs"]})
    result={"schema":"archeaxis.semantic-search/v1","q":"fixture","status":"EMPTY","complete":False,"candidate_count":0,"candidates":[],"embedding":{"complete":False,"rank":[]},"reranker":{"complete":False,"rank":[]},"index_persisted":False}
    assert check.is_valid(result)
    for name,value in [("status","PASS"),("index_persisted",True),("candidate_count",-1),("complete","true")]:
        changed={**result,name:value}
        assert not check.is_valid(changed)
    for name in ["SemanticEmbeddingRankDto","SemanticRerankDto"]:
        validator=Draft202012Validator({"$ref":"#/$defs/"+name,"$defs":SCHEMA["$defs"]})
        row={"knowledge_id":"k","knowledge_version":"k","score":0.5,"anchor_id":None,"source_id":None,"source_revision":None}
        if name=="SemanticRerankDto": row.update(yes_logprob=-1.0,no_logprob=-1.0,reasoning_tokens=0)
        assert validator.is_valid(row)
        assert not validator.is_valid({**row,"score":2})
