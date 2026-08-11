"""Tests for shared.schemas (unified API response envelope models)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from shared.schemas import (
    APIResponse,
    CardCreate,
    DateRangeParams,
    DocumentCreate,
    ErrorResponse,
    IDParam,
    ListResponse,
    MKUCreate,
    PaginationParams,
    PipelineRequest,
    ReviewCreate,
    SearchRequest,
    TranslateRequest,
)


def test_api_response_defaults() -> None:
    r = APIResponse()
    assert r.status == "ok"
    assert r.data is None
    assert r.message == ""


def test_api_response_with_data() -> None:
    r = APIResponse(data={"key": "value"})
    assert r.data == {"key": "value"}
    assert r.status == "ok"


def test_list_response_defaults() -> None:
    r = ListResponse()
    assert r.status == "ok"
    assert r.data == []
    assert r.count == 0
    assert r.total == 0
    assert r.limit == 100


def test_list_response_with_items() -> None:
    r = ListResponse(data=[1, 2, 3], count=3, total=10)
    assert r.count == 3
    assert r.total == 10


def test_error_response_defaults() -> None:
    r = ErrorResponse()
    assert r.status == "error"
    assert r.error == ""
    assert r.code == 400


def test_error_response_fields() -> None:
    r = ErrorResponse(error="not found", detail="doc missing", code=404)
    assert r.error == "not found"
    assert r.code == 404


def test_search_request_required_query() -> None:
    r = SearchRequest(query="neural networks")
    assert r.top_k == 5
    assert r.mode == "hybrid"


def test_search_request_requires_query() -> None:
    with pytest.raises(ValidationError):
        SearchRequest()  # type: ignore[call-arg]


def test_pipeline_request_defaults() -> None:
    r = PipelineRequest(input="text here")
    assert r.source == "text"
    assert r.auto_ingest is True


def test_pagination_and_id() -> None:
    p = PaginationParams(limit=20)
    assert p.offset == 0
    assert p.limit == 20
    i = IDParam(id="doc_1")
    assert i.id == "doc_1"


def test_date_range_defaults() -> None:
    d = DateRangeParams()
    assert d.start_date is None
    assert d.end_date is None
    assert d.days == 7


def test_document_create_required() -> None:
    doc = DocumentCreate(title="T", content="C")
    assert doc.source == "unknown"
    assert doc.tags == []


def test_review_create_quality_required() -> None:
    with pytest.raises(ValidationError):
        ReviewCreate(card_id="c1")  # quality missing


def test_review_create_quality_type() -> None:
    r = ReviewCreate(card_id="c1", quality=4)
    assert r.quality == 4


def test_mku_create_defaults() -> None:
    m = MKUCreate(title="Rule")
    assert m.unit_type == "rule"
    assert m.confidence == 0.5


def test_translate_request() -> None:
    t = TranslateRequest(card_id="c1")
    assert t.unit_type == "rule"


def test_card_create() -> None:
    c = CardCreate(title="Card", content="Body")
    assert c.source_ids == []
    assert c.tags == []
