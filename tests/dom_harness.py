"""SIMULATED DOM evaluation: actual probe JS, no browser/service/model."""
import html
import json
import os
import shutil
import subprocess
from pathlib import Path

REPO = Path(os.environ.get("AAOS_PROBE_SOURCE_REPO", str(Path(__file__).resolve().parents[1])))
HARNESS = r"""
const fs=require('fs');const x=JSON.parse(fs.readFileSync(0,'utf8'));
const {JSDOM}=require(x.jsdom);const w=new JSDOM(x.html).window;
Object.defineProperty(w.HTMLElement.prototype,'innerText',{get(){return this.textContent;}});
w.HTMLElement.prototype.getClientRects=function(){
 for(let n=this;n;n=n.parentElement){const s=w.getComputedStyle(n);
 if(n.hidden||s.display==='none'||s.visibility==='hidden'||s.visibility==='collapse')return [];
 if(n.tagName==='DETAILS'&&!n.open&&n!==this&&!n.querySelector(':scope>summary')?.contains(this))return [];}
 return [{width:100,height:30}];};
const fn=new Function('document','getComputedStyle','XPathResult',x.script);
console.log(JSON.stringify(fn(w.document,w.getComputedStyle,w.XPathResult)));
"""


def evaluate(script, markup):
    value = subprocess.run([shutil.which("node") or "node", "-e", HARNESS], input=json.dumps({
        "script": script, "html": markup, "jsdom": str(REPO / "frontend/node_modules/jsdom")}),
        capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(value.stdout)


def reader_dom(document, *, diagnostic=False, identity=None, hidden="", page="03", title=None, text=None, version=None):
    title = document["title"] if title is None else title
    text = document["text_projection"] if text is None else text
    version = document["version"] if version is None else version
    markup = '<main aria-label="当前页面" data-current-page-id="' + page + '"></main>'
    markup += '<section aria-label="阅读与编辑文档视图" ' + hidden + '><article aria-label="文档正文与编辑"><header><p class="ui-document-meta">关联原件文档 · v' + str(version) + ' · 无需依据即可保存</p><h2>' + html.escape(title) + '</h2></header><section aria-label="版本化草稿编辑器"><div class="ProseMirror">' + html.escape(text) + '</div></section></article></section>'
    if diagnostic:
        identity = identity if identity is not None else {k:document[k] for k in ("document_id", "source_id", "source_revision", "content_sha256")}
        markup += '<div role="dialog"><section aria-label="诊断控制台"><details open><summary>文档身份与来源指纹 · 操作与回执 · synthetic</summary><pre>' + html.escape(json.dumps(identity)) + '</pre></details></section></div>'
    return markup
