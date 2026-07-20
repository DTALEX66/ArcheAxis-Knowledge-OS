"""Public boundary for the governed Cognitive Workspace."""
from __future__ import annotations

from ipaddress import ip_address
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from app.workspace import service
from shared.storage import DB_PATH

WORKSPACE_PREFIX = "/" + "workspace"
router = APIRouter(prefix=WORKSPACE_PREFIX, tags=["workspace"])


class IntakeURL(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, max_length=2048)


class _Command(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: str = Field(min_length=1, max_length=128)


class PromoteResearchCommand(_Command):
    """Caller intent; reviewer identity is deliberately not a client field."""

    package_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class StartLearningCommand(_Command):
    unit_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class RecordPracticeCommand(_Command):
    artifact_id: str = Field(min_length=1)
    quality: int = Field(ge=0, le=5)


def _local_principal(request: Request) -> dict[str, str]:
    """Trust only direct loopback requests in the local-first workspace."""
    host = request.client.host if request.client else ""
    try:
        is_loopback = ip_address(host).is_loopback
    except ValueError:
        is_loopback = host == "testclient"
    if not is_loopback:
        raise HTTPException(status_code=403, detail="workspace is available only from the local machine")
    return {"subject": "local-workspace", "role": "local"}


def _command_error(action):
    try:
        return action()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("", response_class=HTMLResponse)
def workspace_page() -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>
<title>Cognitive Workspace</title><style>
body{font:16px system-ui;max-width:920px;margin:2rem auto;padding:0 1rem;background:#111;color:#eee}section{border:1px solid #555;border-radius:8px;padding:1rem;margin:1rem 0}input,button{padding:.55rem;margin:.2rem}input{min-width:14rem}button{cursor:pointer}pre{white-space:pre-wrap;background:#222;padding:1rem;border-radius:6px}
</style></head><body><main><h1>Cognitive Workspace</h1><p>Local-first candidate lifecycle. This workspace accepts direct local requests only.</p>
<section><h2>导入内容</h2><p>输入网页地址，或拖入 PDF、Office、图片、文本等文件。系统会自动识别格式并转成可处理文本。</p><form id='url-intake'><input name='url' type='url' placeholder='粘贴网页 URL' required><button>提取网页</button></form><form id='file-intake'><input name='file' type='file' accept='.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.html,.htm,.md,.txt,.csv,.png,.jpg,.jpeg,.webp' required><button>导入文件</button></form></section>
<section><h2>转换结果</h2><p>转换后的内容会显示在这里；后续将自动拆解为知识、学习材料和复习任务。</p><pre id='result' aria-live='polite'>准备就绪。选择网页或文件开始。</pre></section>
</main><script>
const root=location.pathname;const out=document.querySelector('#result');const show=async response=>{const data=await response.json();out.textContent=JSON.stringify(data,null,2);};
document.querySelector('#url-intake').addEventListener('submit',event=>{event.preventDefault();const url=new FormData(event.currentTarget).get('url');show(fetch(root+'/api/intake/url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})}));});
document.querySelector('#file-intake').addEventListener('submit',event=>{event.preventDefault();const data=new FormData(event.currentTarget);show(fetch(root+'/api/intake/upload',{method:'POST',body:data}));});
</script></body></html>"""
    )


@router.get("/api/diagnostics")
def workspace_diagnostics() -> dict[str, object]:
    from app.main import diagnostics

    return diagnostics()


@router.post("/api/intake/url")
def intake_url(payload: IntakeURL, request: Request) -> dict:
    _local_principal(request)
    return _command_error(lambda: service.intake_url(url=payload.url))


@router.post("/api/intake/upload")
async def intake_upload(request: Request, file: UploadFile = File(...)) -> dict:
    _local_principal(request)
    try:
        return service.intake_upload(
            file_name=file.filename or "",
            content=await file.read(),
            db_path=DB_PATH,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/commands/promote-research")
def promote_research(command: PromoteResearchCommand, request: Request) -> dict[str, Any]:
    principal = _local_principal(request)
    return _command_error(
        lambda: service.promote_research(
            command_id=command.command_id, package_id=command.package_id,
            reviewer_id=principal["subject"], rationale=command.rationale, db_path=DB_PATH,
        )
    )


@router.post("/api/commands/start-learning")
def start_learning(command: StartLearningCommand, request: Request) -> dict[str, Any]:
    principal = _local_principal(request)
    return _command_error(
        lambda: service.start_learning(
            command_id=command.command_id, unit_id=command.unit_id,
            reviewer_id=principal["subject"], rationale=command.rationale, db_path=DB_PATH,
        )
    )


@router.post("/api/commands/record-practice")
def record_practice(command: RecordPracticeCommand, request: Request) -> dict[str, Any]:
    _local_principal(request)
    return _command_error(
        lambda: service.record_practice(
            command_id=command.command_id, artifact_id=command.artifact_id,
            quality=command.quality, db_path=DB_PATH,
        )
    )


@router.get("/api/cases/{artifact_id}")
def workspace_case(artifact_id: str, request: Request) -> dict[str, Any]:
    _local_principal(request)
    return _command_error(lambda: service.case_audit(artifact_id=artifact_id, db_path=DB_PATH))
