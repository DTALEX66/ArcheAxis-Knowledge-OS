'''The review queue status must describe the queue that is on screen.

The line above the queue was a static default that no code ever assigned, so the page claimed the
queue had not been read while the queue itself was listed underneath it. These assertions keep the
status tied to the same state the empty title already uses.
'''

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / 'apps/ArcheAxis.Desktop/MainWindow.axaml'
CODE = ROOT / 'apps/ArcheAxis.Desktop/MainWindow.axaml.cs'


def _update_block() -> str:
    code = CODE.read_text(encoding='utf-8')
    return code.split('private void UpdateReviewQueueEmptyState()', 1)[1].split(chr(10) + '    }', 1)[0]


def test_the_status_line_is_assigned_by_code():
    xaml = XAML.read_text(encoding='utf-8')
    assert 'x:Name="ReviewPageStatusText"' in xaml, 'the status line lost its name'
    block = _update_block()
    assert 'ReviewPageStatusText.Text' in block, (
        'nothing assigns the review status, so it can only ever show its XAML default')


def test_the_status_line_reports_the_state_it_is_given():
    block = _update_block()
    assert '_reviewQueueLoadedFromCore' in block, 'the status ignores whether the read happened'
    assert '尚未读取 Core 复习队列。' in block, 'the not-read case must stay reachable'
    assert '已读取 Core 复习队列' in block, 'the read case must be stated, not left implied'
    assert 'ReviewQueueList.Items.Count' in block, (
        'the read case counts what is listed rather than asserting a number')


def test_title_description_and_status_read_the_same_flag():
    block = _update_block()
    assert 'ReviewPageStatusText.Text = !_reviewQueueLoadedFromCore' in block, (
        'the status must be derived from the same flag as the empty title')