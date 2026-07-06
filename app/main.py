from fastapi import FastAPI, HTTPException

from app.api.ingest import ingest
from app.core.router import route
from app.rag.retriever import retrieve
from app.core.compiler import compile_task
from app.agent.executor import execute
from app.memory.store import list_lessons, save_lesson, save_memory, search_memory
from app.core.trace import log_trace, list_traces
from app.evaluation.evaluator import evaluate
from app.evaluation.feedback import compile_lesson
from app.core.permissions import check_permission
from app.ingestion.file import IngestionError, ingest_directory, ingest_file
from app.ingestion.multi_format import convert_file, convert_url, convert_directory as multi_convert_directory
from app.tools.registry import list_tools

app = FastAPI(title='Cognitive OS v2', version='0.2.0')


@app.get('/health')
def health():
    return {'status': 'ok', 'system': 'cognitive-os-v2'}


@app.get('/tools')
def tools():
    return {'items': list_tools()}


@app.post('/ingest')
def ingest_api(input_data: dict):
    doc = ingest(input_data)
    save_memory(doc)
    return doc


@app.post('/ingest/file')
def ingest_file_api(payload: dict):
    try:
        doc = ingest_file(
            str(payload.get('path', '')),
            source=payload.get('source'),
            metadata=payload.get('metadata'),
        )
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    decision = route(doc)
    doc.attention_score = decision.score
    doc.route = decision.route
    if decision.route != 'DROP':
        save_memory(doc)
    return {'document': doc, 'route': decision}


@app.post('/ingest/directory')
def ingest_directory_api(payload: dict):
    try:
        docs = ingest_directory(
            str(payload.get('path', '')),
            pattern=str(payload.get('pattern', '*.md')),
            limit=int(payload.get('limit', 50)),
            source=payload.get('source'),
            metadata=payload.get('metadata'),
        )
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    items = []
    for doc in docs:
        decision = route(doc)
        doc.attention_score = decision.score
        doc.route = decision.route
        if decision.route != 'DROP':
            save_memory(doc)
        items.append({'document': doc, 'route': decision})

    return {'count': len(items), 'items': items}


@app.post('/route')
def route_api(input_data: dict):
    doc = ingest(input_data)
    return route(doc)


@app.post('/run')
def run(input_data: dict):
    doc = ingest(input_data)
    decision = route(doc)
    doc.attention_score = decision.score
    doc.route = decision.route

    if decision.route == 'DROP':
        return {'status': 'ignored', 'document': doc, 'route': decision}

    if decision.route == 'REVIEW':
        save_memory(doc)
        return {'status': 'needs_review', 'document': doc, 'route': decision}

    save_memory(doc)
    context = retrieve(doc.content)
    task = compile_task(context)
    perm = check_permission(task, doc.content)
    if perm.requires_human_review:
        return {
            'status': 'blocked',
            'document': doc,
            'route': decision,
            'task': task,
            'permission': perm.model_dump(),
        }
    trace = execute(task, perm)
    log_trace(trace)
    eval_result = evaluate(trace)
    lesson = compile_lesson(eval_result, trace)
    save_lesson(lesson)

    return {
        'status': 'done',
        'document': doc,
        'route': decision,
        'context': context,
        'task': task,
        'trace': trace,
        'eval': eval_result,
        'lesson': lesson,
    }


@app.post('/convert/file')
def convert_file_api(payload: dict):
    """Convert any supported file (PDF/DOCX/PPTX/XLSX/HTML/image) to Markdown."""
    path = str(payload.get('path', ''))
    fmt = payload.get('format')
    try:
        content, engine = convert_file(path, fmt)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'path': path, 'format': fmt or 'auto', 'engine': engine,
            'content': content, 'char_count': len(content)}


@app.post('/convert/url')
def convert_url_api(payload: dict):
    """Fetch a URL and convert to Markdown."""
    url = str(payload.get('url', ''))
    try:
        content, engine = convert_url(url)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'url': url, 'engine': engine, 'content': content,
            'char_count': len(content)}


@app.post('/convert/directory')
def convert_directory_api(payload: dict):
    """Batch-convert all files in a directory."""
    directory = str(payload.get('path', ''))
    pattern = str(payload.get('pattern', '*.*'))
    limit = int(payload.get('limit', 50))
    results = multi_convert_directory(directory, pattern, limit)
    return {'path': directory, 'count': len(results), 'items': results}


@app.post('/memory/search')
def memory_search(payload: dict):
    query = str(payload.get('query', ''))
    top_k = int(payload.get('top_k', 5))
    return {'query': query, 'items': search_memory(query, top_k=top_k)}


@app.get('/traces')
def traces():
    return {'items': list_traces()}


@app.get('/memory/lessons')
def lessons():
    return {'items': list_lessons()}
