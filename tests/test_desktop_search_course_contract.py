from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
import pytest

ROOT=Path(__file__).resolve().parents[1]
DESKTOP=ROOT/'apps/ArcheAxis.Desktop'

def test_semantic_is_explicit_authenticated_and_keeps_fts():
    xaml=(DESKTOP/'MainWindow.axaml').read_text(encoding='utf-8')
    code=(DESKTOP/'MainWindow.SemanticSearch.cs').read_text(encoding='utf-8')
    main=(DESKTOP/'MainWindow.axaml.cs').read_text(encoding='utf-8')
    supervisor=(DESKTOP/'CoreSupervisor.cs').read_text(encoding='utf-8')
    assert 'Click="OnSemanticSearchClick"' in xaml
    assert '_supervisor.SendAsync(HttpMethod.Post, "/api/v1/search/semantic"' in code
    assert 'new { q = query }' in code
    assert 'SendMachineAsync' not in code and 'HttpClient' not in code
    assert 'or "/api/v1/search/semantic"' in supervisor
    assert 'TimeSpan.FromSeconds(125)' in supervisor
    assert '/api/v1/search?q=' in main
    assert 'version == _librarySearchRequestVersion' in code
    assert '_activeSection == "search"' in code
    assert '"PARTIAL" =>' in code and '排序尚未完整完成' in code
    assert 'Body = hit.Body' in code

def test_semantic_receipts_are_collapsed_but_body_is_readable():
    root=ET.parse(DESKTOP/'MainWindow.axaml').getroot()
    parents={c:p for p in root.iter() for c in p}
    names={node.get('{http://schemas.microsoft.com/winfx/2006/xaml}Name'):node for node in root.iter()}
    assert parents[names['SearchPageDiagnosticsText']].get('IsExpanded')=='False'
    assert any(node.get('Text')=='{Binding Body}' for node in root.iter())

def test_semantic_readback_behaviour():
    powershell=shutil.which('pwsh')
    if powershell is None: pytest.skip('PowerShell 7 is required for C# readback behaviour')
    result=subprocess.run([powershell,'-NoProfile','-File',str(ROOT/'tests/desktop/SemanticSearchReadback.Tests.ps1')],cwd=ROOT,text=True,encoding='utf-8',capture_output=True,timeout=45)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'SEMANTIC READBACK PASS' in result.stdout

def test_course_actions_use_core_bindings_and_separate_human_learning():
    code=(DESKTOP/'MainWindow.CourseLearning.cs').read_text(encoding='utf-8')
    main=(DESKTOP/'MainWindow.axaml.cs').read_text(encoding='utf-8')
    generation=code.split('private async void OnGenerateCourseClick',1)[1].split('private async void OnReadCourseClick',1)[0]
    start=code.split('private async void OnStartCourseLearningClick',1)[1]
    assert '"/api/v1/courses/from-knowledge", new { knowledge_id = knowledgeId }' in generation
    assert 'lesson.ReadStored(stored.RootElement)' in generation
    assert 'lesson.ReadRendered(rendered.RootElement)' in generation
    assert 'EnrollKnowledgeAsync' not in generation
    assert 'await EnrollKnowledgeAsync(lesson.KnowledgeId, lesson.ItemKey, Current, lesson.KnowledgeVersion)' in start
    assert start.index('lesson.ReadStored') < start.index('await EnrollKnowledgeAsync')
    assert 'await EnrollKnowledgeAsync(knowledgeId, itemKey, IsCurrentRequest)' in main
    assert 'Uri.EscapeDataString(itemKey)' in code
    assert 'CourseLessonReadback.ValidateAssessment' in code
    assert 'SendMachineAsync' not in code and 'HttpClient' not in code
    assert '/accept' not in code and '/api/v1/learning/reviews' not in code
    assert 'mastery' not in code.lower()

def test_course_technical_fields_default_collapsed():
    root=ET.parse(DESKTOP/'MainWindow.axaml').getroot()
    names={node.get('{http://schemas.microsoft.com/winfx/2006/xaml}Name'):node for node in root.iter()}
    diagnostics=names['CourseDiagnostics']
    assert diagnostics.get('IsExpanded')=='False'
    assert names['CourseIdReadbackBox'] in list(diagnostics.iter())
    assert names['CourseDiagnosticsText'] in list(diagnostics.iter())
    assert names['CourseStartLearningButton'].get('Click')=='OnStartCourseLearningClick'
    assert names['GenerateCourseButton'].get('Click')=='OnGenerateCourseClick'

def test_course_persisted_identity_and_actual_render_behaviour():
    powershell=shutil.which('pwsh')
    if powershell is None: pytest.skip('PowerShell 7 is required for C# readback behaviour')
    result=subprocess.run([powershell,'-NoProfile','-File',str(ROOT/'tests/desktop/CourseLessonReadback.Tests.ps1')],cwd=ROOT,text=True,encoding='utf-8',capture_output=True,timeout=45)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'COURSE READBACK PASS' in result.stdout
