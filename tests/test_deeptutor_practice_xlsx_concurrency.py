"""Bounded concurrency for private XLSX preview; inputs are synthetic."""

import importlib.util
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "services" / "learning-providers" / "deeptutor" / "practice_import.py"


@pytest.fixture
def adapter():
    name = "deeptutor_xlsx_concurrency_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(name, None)


def test_second_preview_does_not_start_while_first_launch_is_in_flight(adapter, monkeypatch):
    real_popen = subprocess.Popen
    opened, proceed = threading.Event(), threading.Event()
    children, attempts, outcomes = [], [], []

    def controlled_popen(_command, **kwargs):
        attempts.append(1)
        if len(attempts) != 1:
            raise OSError("second synthetic child would have started")
        # This owned child exits on input and has its own finite deadline even
        # if its test launcher fails before releasing the parent-side barrier.
        program = ("import os,sys,threading; "
                   "threading.Timer(5,lambda:os._exit(3)).start(); "
                   "sys.stdin.buffer.readline(); print('invalid synthetic reply'); os._exit(0)")
        child = real_popen([sys.executable, "-I", "-B", "-c", program], **kwargs)
        children.append(child)
        opened.set()
        proceed.wait(4)
        return child

    def first_call():
        try:
            adapter._isolated_xlsx_preview(b"synthetic")
        except Exception as error:
            outcomes.append(type(error))

    monkeypatch.setattr(adapter.subprocess, "Popen", controlled_popen)
    first = threading.Thread(target=first_call, daemon=True)
    first.start()
    try:
        assert opened.wait(4), "first owned child did not start"
        with pytest.raises(adapter.UpstreamUnavailable):
            adapter._isolated_xlsx_preview(b"synthetic")
        assert len(attempts) == 1
    finally:
        proceed.set()
        first.join(timeout=7)
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
        first.join(timeout=2)
    assert not first.is_alive()
    assert outcomes == [adapter.UpstreamUnavailable]
    monkeypatch.setattr(adapter.subprocess, "Popen", real_popen)
    # A confirmed direct-child/pipe cleanup allows another attempt even when
    # the previous child returned an invalid result.
    with pytest.raises(adapter.InvalidInput):
        adapter._isolated_xlsx_preview(b"synthetic-not-a-workbook")


def test_failed_launch_keeps_the_instance_closed_when_state_is_unknown(adapter, monkeypatch):
    attempts = []

    def unavailable(*_args, **_kwargs):
        attempts.append(1)
        raise OSError("synthetic launch failure")

    monkeypatch.setattr(adapter.subprocess, "Popen", unavailable)
    for _ in range(2):
        with pytest.raises(adapter.UpstreamUnavailable):
            adapter._isolated_xlsx_preview(b"synthetic")
    assert len(attempts) == 1


def test_launch_error_after_child_creation_does_not_allow_a_second_launch(adapter, monkeypatch):
    real_popen = subprocess.Popen
    attempts, children = [], []

    def failed_after_creation(_command, **kwargs):
        attempts.append(1)
        if len(attempts) != 1:
            raise OSError("second synthetic child would have started")
        # The test retains this original handle for cleanup. The code under
        # test receives only an exception, as can happen after OS creation.
        program = ("import os,sys,threading; "
                   "threading.Timer(15,lambda:os._exit(3)).start(); "
                   "sys.stdin.buffer.read(); os._exit(0)")
        child = real_popen([sys.executable, "-I", "-B", "-c", program], **kwargs)
        children.append(child)
        raise OSError("synthetic failure after child creation")

    monkeypatch.setattr(adapter.subprocess, "Popen", failed_after_creation)
    try:
        with pytest.raises(adapter.UpstreamUnavailable):
            adapter._isolated_xlsx_preview(b"synthetic")
        assert len(children) == 1 and children[0].poll() is None
        with pytest.raises(adapter.UpstreamUnavailable):
            adapter._isolated_xlsx_preview(b"synthetic")
        assert len(attempts) == 1
    finally:
        for child in children:
            if child.stdin and not child.stdin.closed:
                child.stdin.close()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
            if child.stdout:
                child.stdout.close()
            if child.stderr:
                child.stderr.close()


def test_failed_child_closes_its_owned_pipes_before_reuse(adapter, monkeypatch):
    real_popen = subprocess.Popen
    children = []

    def diagnostic_child(_command, **kwargs):
        child = real_popen([sys.executable, "-I", "-B", "-c",
                            "import sys;sys.stdin.buffer.readline();sys.stderr.write('synthetic')"], **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(adapter.subprocess, "Popen", diagnostic_child)
    with pytest.raises(adapter.UpstreamUnavailable):
        adapter._isolated_xlsx_preview(b"synthetic")
    assert len(children) == 1 and children[0].poll() is not None
    assert children[0].stdin.closed
    assert children[0].stdout.closed
    assert children[0].stderr.closed


def test_pipe_close_error_keeps_the_instance_closed(adapter, monkeypatch):
    real_popen = subprocess.Popen
    attempts, children = [], []

    class FailedClose:
        def __init__(self, raw):
            self.raw = raw

        def read(self, size):
            return self.raw.read(size)

        def close(self):
            self.raw.close()  # Keep the synthetic test's own descriptor safe.
            raise OSError("synthetic close error")

    def controlled_popen(_command, **kwargs):
        attempts.append(1)
        if len(attempts) != 1:
            raise OSError("second synthetic child would have started")
        child = real_popen([sys.executable, "-I", "-B", "-c",
                            "import sys;sys.stdin.buffer.readline()"], **kwargs)
        children.append(child)
        child.stdout = FailedClose(child.stdout)
        return child

    monkeypatch.setattr(adapter.subprocess, "Popen", controlled_popen)
    for _ in range(2):
        with pytest.raises(adapter.UpstreamUnavailable):
            adapter._isolated_xlsx_preview(b"synthetic")
    assert len(attempts) == 1
    assert children[0].poll() is not None and children[0].stdout.raw.closed


@pytest.mark.parametrize("failure", ["construct", "start"])
def test_thread_startup_failure_reaps_child_and_closes_unowned_pipes(adapter, monkeypatch, failure):
    real_popen, real_thread = subprocess.Popen, threading.Thread
    children, thread_count = [], []

    def controlled_popen(_command, **kwargs):
        program = ("import os,sys,threading; "
                   "threading.Timer(15,lambda:os._exit(3)).start(); "
                   "sys.stdin.buffer.readline(); threading.Event().wait(10)")
        child = real_popen([sys.executable, "-I", "-B", "-c", program], **kwargs)
        children.append(child)
        return child

    def controlled_thread(*args, **kwargs):
        thread_count.append(1)
        if len(thread_count) == 2 and failure == "construct":
            raise RuntimeError("synthetic thread construction failure")
        thread = real_thread(*args, **kwargs)
        if len(thread_count) == 2 and failure == "start":
            def failed_start():
                raise RuntimeError("synthetic thread start failure")
            monkeypatch.setattr(thread, "start", failed_start)
        return thread

    monkeypatch.setattr(adapter.subprocess, "Popen", controlled_popen)
    monkeypatch.setattr(adapter.threading, "Thread", controlled_thread)
    try:
        with pytest.raises(adapter.UpstreamUnavailable):
            adapter._isolated_xlsx_preview(b"synthetic")
        assert len(children) == 1 and children[0].poll() is not None
        assert children[0].stdin.closed and children[0].stderr.closed
        # The instance must stay closed even if the synthetic cleanup succeeds.
        with pytest.raises(adapter.UpstreamUnavailable):
            adapter._isolated_xlsx_preview(b"synthetic")
        assert len(children) == 1
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
            for stream in (child.stdin, child.stdout, child.stderr):
                if stream and not stream.closed:
                    stream.close()


def test_unconfirmed_pipe_cleanup_blocks_another_preview(adapter, monkeypatch, tmp_path):
    real_popen = subprocess.Popen
    read_fd, write_fd = os.pipe()
    state = {"read_fd": read_fd, "write_fd": write_fd, "worker": None}
    attempts = []
    reader_done = threading.Event()
    holder = None

    class ObservedReader:
        def __init__(self, raw):
            self.raw = raw

        def read(self, size):
            return self.raw.read(size)

        def close(self):
            try:
                self.raw.close()
            finally:
                reader_done.set()
    try:
        # The holder is a test-owned sibling of the worker. It first proves it
        # can write to the shared anonymous pipe, then keeps that pipe open.
        program = ("import os,sys,threading; "
                   "threading.Timer(15,lambda:os._exit(3)).start(); "
                   "sys.stdout.buffer.write(b'H'); sys.stdout.buffer.flush(); "
                   "from pathlib import Path; Path(sys.argv[1]).write_bytes(b'READY'); "
                   "sys.stdin.buffer.read(); os._exit(0)")
        ready = tmp_path / "synthetic-holder-ready"
        holder = real_popen([sys.executable, "-I", "-B", "-c", program, str(ready)],
                            stdin=subprocess.PIPE, stdout=write_fd, stderr=subprocess.DEVNULL,
                            close_fds=True)
        deadline = time.monotonic() + 8
        while not ready.exists():
            assert holder.poll() is None, "test-owned holder exited before writing"
            assert time.monotonic() < deadline, "test-owned holder did not become ready"
            time.sleep(0.01)
        assert ready.read_bytes() == b"READY"
        assert os.read(read_fd, 1) == b"H"
        assert holder.poll() is None

        def controlled_popen(_command, **kwargs):
            attempts.append(1)
            if len(attempts) != 1:
                raise OSError("second synthetic child would have started")
            kwargs["stdout"] = state["write_fd"]
            try:
                worker = real_popen([sys.executable, "-I", "-B", "-c",
                                     "import sys;sys.stdin.buffer.readline()"], **kwargs)
                state["worker"] = worker
                worker.stdout = ObservedReader(os.fdopen(state["read_fd"], "rb"))
                state["read_fd"] = None
                return worker
            finally:
                os.close(state["write_fd"])
                state["write_fd"] = None

        monkeypatch.setattr(adapter.subprocess, "Popen", controlled_popen)
        with pytest.raises(adapter.UpstreamUnavailable):
            adapter._isolated_xlsx_preview(b"synthetic")
        assert state["worker"].poll() is not None
        assert holder.poll() is None
        with pytest.raises(adapter.UpstreamUnavailable):
            adapter._isolated_xlsx_preview(b"synthetic")
        assert len(attempts) == 1
        # Even after this test-owned holder exits, the instance conservatively
        # remains closed: the earlier return could not confirm cleanup.
        holder.stdin.close()
        assert holder.wait(timeout=5) == 0
        assert reader_done.wait(5)
        with pytest.raises(adapter.UpstreamUnavailable):
            adapter._isolated_xlsx_preview(b"synthetic")
        assert len(attempts) == 1
    finally:
        if holder is not None:
            if holder.stdin is not None and not holder.stdin.closed:
                holder.stdin.close()
            try:
                holder.wait(timeout=5)
            except subprocess.TimeoutExpired:
                holder.kill()
                holder.wait(timeout=5)
        worker = state["worker"]
        if worker is not None:
            if worker.poll() is None:
                worker.kill()
            worker.wait(timeout=5)
            assert reader_done.wait(5), "test-owned pipe reader did not stop"
            worker.stdout.close()
        for name in ("read_fd", "write_fd"):
            if state[name] is not None:
                os.close(state[name])
