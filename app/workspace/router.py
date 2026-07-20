"""Public boundary for the governed Cognitive Workspace."""
from __future__ import annotations

from ipaddress import ip_address
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from app.workspace import service
from shared.storage import DB_PATH

WORKSPACE_PREFIX = "/" + "workspace"
router = APIRouter(prefix=WORKSPACE_PREFIX, tags=["workspace"])


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
<section><h2>Research → Knowledge</h2><form data-action='promote-research'><input name='command_id' placeholder='command id' required><input name='package_id' placeholder='persisted package id' required><input name='rationale' placeholder='rationale' required><button>Promote</button></form></section>
<section><h2>Knowledge → Learning</h2><form data-action='start-learning'><input name='command_id' placeholder='command id' required><input name='unit_id' placeholder='candidate unit id' required><input name='rationale' placeholder='rationale' required><button>Create learning material</button></form></section>
<section><h2>Practice → Mastery</h2><form data-action='record-practice'><input name='command_id' placeholder='command id' required><input name='artifact_id' placeholder='artifact id' required><input name='quality' type='number' min='0' max='5' value='5' required><button>Record practice</button></form></section>
<section><h2>Audit timeline</h2><input id='case-id' placeholder='artifact id'><button id='load-case'>Load case</button><pre id='result' aria-live='polite'>Ready.</pre></section>
</main><script>
const root=location.pathname;const out=document.querySelector('#result');const call=async(path,options={})=>{const r=await fetch(path,{...options,headers:{'Content-Type':'application/json',...(options.headers||{})}});const p=await r.json();out.textContent=JSON.stringify(p,null,2);};
document.querySelectorAll('form[data-action]').forEach(form=>form.addEventListener('submit',event=>{event.preventDefault();const data=Object.fromEntries(new FormData(form));if('quality'in data)data.quality=Number(data.quality);call(root+'/api/commands/'+form.dataset.action,{method:'POST',body:JSON.stringify(data)});}));
document.querySelector('#load-case').addEventListener('click',()=>call(root+'/api/cases/'+encodeURIComponent(document.querySelector('#case-id').value)));
</script></body></html>"""
    )


@router.get("/api/diagnostics")
def workspace_diagnostics() -> dict[str, object]:
    from app.main import diagnostics

    return diagnostics()


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
