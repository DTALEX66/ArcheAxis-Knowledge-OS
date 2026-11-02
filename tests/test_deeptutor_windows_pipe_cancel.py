"""Windows-only synthetic synchronous pipe cancellation experiment.

This does not execute a product worker, read user material, or prove the Rust
Executor, authorization, provider, or cross-platform behavior. An outer owned
Job Object contains only this experiment's two fixed Python processes.
"""

import json
import os
import secrets
import subprocess
import sys
import time

import pytest


INNER_EXPERIMENT = r'''
import ctypes
from ctypes import wintypes
import json
import msvcrt
import os
import subprocess
import sys
import threading
import time

if sys.stdin.buffer.readline() != b"GO\n":
    raise SystemExit(3)

k = ctypes.WinDLL("kernel32", use_last_error=True)
HANDLE = wintypes.HANDLE
DWORD = wintypes.DWORD
BOOL = wintypes.BOOL
k.CreatePipe.argtypes = [ctypes.POINTER(HANDLE), ctypes.POINTER(HANDLE), ctypes.c_void_p, DWORD]
k.CreatePipe.restype = BOOL
k.PeekNamedPipe.argtypes = [HANDLE, ctypes.c_void_p, DWORD, ctypes.POINTER(DWORD), ctypes.POINTER(DWORD), ctypes.POINTER(DWORD)]
k.PeekNamedPipe.restype = BOOL
k.WriteFile.argtypes = [HANDLE, ctypes.c_void_p, DWORD, ctypes.POINTER(DWORD), ctypes.c_void_p]
k.WriteFile.restype = BOOL
k.GetCurrentThreadId.restype = DWORD
k.OpenThread.argtypes = [DWORD, BOOL, DWORD]
k.OpenThread.restype = HANDLE
k.CancelSynchronousIo.argtypes = [HANDLE]
k.CancelSynchronousIo.restype = BOOL
k.CloseHandle.argtypes = [HANDLE]
k.CloseHandle.restype = BOOL
k.OpenJobObjectW.argtypes = [DWORD, BOOL, wintypes.LPCWSTR]
k.OpenJobObjectW.restype = HANDLE
k.IsProcessInJob.argtypes = [HANDLE, HANDLE, ctypes.POINTER(BOOL)]
k.IsProcessInJob.restype = BOOL

out = {"status": "UNKNOWN", "reason": "not_started", "blocked": False, "cancel_called": False,
       "cancel_returned_success": False, "writer_joined": False, "child_exit_confirmed": False,
       "pipe_created": False, "child_started": False, "child_ready": False,
       "same_job_confirmed": False, "buffer_stable_after_join": False,
       "buffer_before_cancel": None, "buffer_after_join": None, "buffer_final": None,
       "buffer_changed_across_cancel": None}
reader = None
write_handle = HANDLE()
writer = None
child = None
write_result = {}
started = threading.Event()

def available(handle):
    count = DWORD()
    if not k.PeekNamedPipe(handle, None, 0, None, ctypes.byref(count), None):
        return None
    return int(count.value)

try:
    read_handle = HANDLE()
    if not k.CreatePipe(ctypes.byref(read_handle), ctypes.byref(write_handle), None, 4096):
        raise RuntimeError("pipe")
    out["pipe_created"] = True
    reader = os.fdopen(msvcrt.open_osfhandle(int(read_handle.value), os.O_RDONLY), "rb", buffering=0)
    # Write binary bytes so Windows text-mode CRLF translation cannot affect
    # the fixture handshake. The previous UNKNOWN did not establish its cause.
    child_code = "import sys,time; sys.stdout.buffer.write(b'READY\\n'); sys.stdout.buffer.flush(); time.sleep(12)"
    child = subprocess.Popen([sys.executable, "-I", "-B", "-S", "-u", "-c", child_code],
                             stdin=reader, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             close_fds=True, creationflags=0x08000000)
    out["child_started"] = True
    if child.stdout.readline() != b"READY\n" or child.poll() is not None:
        raise RuntimeError("child_not_ready")
    out["child_ready"] = True
    query_job = k.OpenJobObjectW(0x0004, False, sys.argv[1])
    if not query_job:
        raise RuntimeError("job_query")
    try:
        in_job = BOOL()
        if not k.IsProcessInJob(HANDLE(int(child._handle)), query_job, ctypes.byref(in_job)):
            raise RuntimeError("job_membership_query")
        out["same_job_confirmed"] = bool(in_job.value)
    finally:
        k.CloseHandle(query_job)
    if not out["same_job_confirmed"]:
        raise RuntimeError("child_not_in_job")

    # The child never reads; the parent deliberately keeps a separate read end
    # open, so cancelling the write is tested while a reader still exists.
    read_native = HANDLE(msvcrt.get_osfhandle(reader.fileno()))
    payload = ctypes.create_string_buffer(b"X" * (2 * 1024 * 1024))

    def write_all_once():
        write_result["thread_id"] = int(k.GetCurrentThreadId())
        started.set()
        written = DWORD()
        ok = k.WriteFile(write_handle, payload, 2 * 1024 * 1024, ctypes.byref(written), None)
        write_result["ok"] = bool(ok)
        write_result["error"] = 0 if ok else int(ctypes.get_last_error())
        write_result["written"] = int(written.value)

    writer = threading.Thread(target=write_all_once, daemon=True)
    writer.start()
    if not started.wait(2):
        raise RuntimeError("writer_not_started")
    end = time.monotonic() + 3
    first = None
    while time.monotonic() < end:
        count = available(read_native)
        if count is not None and count > 0 and writer.is_alive() and child.poll() is None:
            time.sleep(0.1)
            if available(read_native) == count and writer.is_alive() and child.poll() is None:
                first = count
                break
        time.sleep(0.005)
    out["blocked"] = first is not None
    if not out["blocked"]:
        raise RuntimeError("blocking_not_confirmed")
    out["buffer_before_cancel"] = first
    thread_handle = k.OpenThread(0x0001, False, write_result["thread_id"])
    if not thread_handle:
        raise RuntimeError("thread_handle")
    try:
        out["cancel_called"] = True
        ok = k.CancelSynchronousIo(thread_handle)
        out["cancel_returned_success"] = bool(ok)
        out["cancel_error"] = 0 if ok else int(ctypes.get_last_error())
    finally:
        k.CloseHandle(thread_handle)
    writer.join(2)
    out["writer_joined"] = not writer.is_alive()
    out["write_success"] = write_result.get("ok")
    out["write_error"] = write_result.get("error")
    out["bytes_written"] = write_result.get("written")
    after = available(read_native)
    time.sleep(0.1)
    final = available(read_native)
    out["buffer_after_join"] = after
    out["buffer_final"] = final
    out["buffer_changed_across_cancel"] = None if after is None else after != first
    out["buffer_stable_after_join"] = (out["writer_joined"] and after is not None and final == after)
    child.terminate()
    child.wait(timeout=2)
    out["child_exit_confirmed"] = child.poll() is not None
    if (out["same_job_confirmed"] and out["blocked"] and out["cancel_returned_success"]
            and out["writer_joined"] and out["write_success"] is False
            and out["write_error"] == 995 and out["buffer_stable_after_join"]
            and out["child_exit_confirmed"]):
        out["status"] = "PASS"
        out["reason"] = "synthetic_windows_synchronous_pipe_only"
    else:
        out["reason"] = "cancellation_or_cleanup_unconfirmed"
except RuntimeError as error:
    allowed = {"pipe", "child_not_ready", "job_query", "job_membership_query", "child_not_in_job",
               "writer_not_started", "blocking_not_confirmed", "thread_handle"}
    reason = error.args[0] if len(error.args) == 1 and isinstance(error.args[0], str) and error.args[0] in allowed else "other"
    out["reason"] = "runtime_" + reason
except BaseException as error:
    out["reason"] = {"OSError": "os_error", "TimeoutExpired": "wait_timeout"}.get(type(error).__name__, "unexpected")
finally:
    if child is not None and child.poll() is None:
        try:
            child.kill()
            child.wait(timeout=2)
        except BaseException:
            out["status"] = "UNKNOWN"
            out["reason"] = "child_exit_unconfirmed"
    if child is not None and child.poll() is not None:
        out["child_exit_confirmed"] = True
    if reader is not None:
        try:
            reader.close()
        except BaseException:
            out["status"] = "UNKNOWN"
            out["reason"] = "reader_close_unconfirmed"
    if writer is not None and writer.is_alive():
        thread_handle = k.OpenThread(0x0001, False, write_result.get("thread_id", 0))
        if thread_handle:
            k.CancelSynchronousIo(thread_handle)
            k.CloseHandle(thread_handle)
        writer.join(1)
    if writer is not None and writer.is_alive():
        out["status"] = "UNKNOWN"
        out["reason"] = "writer_exit_unconfirmed"
    if write_handle:
        k.CloseHandle(write_handle)
print(json.dumps(out, separators=(",", ":")))
'''


@pytest.mark.skipif(sys.platform != "win32", reason="Windows synchronous pipe experiment")
def test_owned_blocked_stdin_cancel_has_bounded_cleanup(tmp_path):
    import ctypes
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in
                    ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                     "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BasicLimits), ("IoInfo", IoCounters),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    class Accounting(ctypes.Structure):
        _fields_ = [("TotalUserTime", ctypes.c_int64), ("TotalKernelTime", ctypes.c_int64),
                    ("ThisPeriodTotalUserTime", ctypes.c_int64), ("ThisPeriodTotalKernelTime", ctypes.c_int64),
                    ("TotalPageFaultCount", wintypes.DWORD), ("TotalProcesses", wintypes.DWORD),
                    ("ActiveProcesses", wintypes.DWORD), ("TotalTerminatedProcesses", wintypes.DWORD)]

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    k.CreateJobObjectW.restype = wintypes.HANDLE
    k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k.SetInformationJobObject.restype = wintypes.BOOL
    k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    k.AssignProcessToJobObject.restype = wintypes.BOOL
    k.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                           wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    k.QueryInformationJobObject.restype = wintypes.BOOL
    k.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    k.TerminateJobObject.restype = wintypes.BOOL
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.CloseHandle.restype = wintypes.BOOL

    name = "Local\\AAOS-pipe-fixture-" + secrets.token_hex(16)
    ctypes.set_last_error(0)
    job = k.CreateJobObjectW(None, name)
    if not job:
        pytest.skip("UNKNOWN: experiment Job Object unavailable")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS: never touch another job.
        k.CloseHandle(job)
        pytest.skip("UNKNOWN: experiment Job identity collision")
    process = None
    assigned = False
    result = None
    try:
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        if not k.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            pytest.skip("UNKNOWN: experiment Job cleanup policy unavailable")
        home = tmp_path / "home"
        temporary = tmp_path / "temp"
        home.mkdir()
        temporary.mkdir()
        env = {"SystemRoot": os.environ["SystemRoot"], "HOME": str(home), "USERPROFILE": str(home),
               "TEMP": str(temporary), "TMP": str(temporary), "APPDATA": str(home), "LOCALAPPDATA": str(home)}
        process = subprocess.Popen([sys.executable, "-I", "-B", "-S", "-u", "-X", "utf8", "-c", INNER_EXPERIMENT, name],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=env, close_fds=True, creationflags=0x08000000)
        # The harness is blocked on GO and cannot create its fixture until
        # successful assignment to this experiment's Job Object.
        assigned = bool(k.AssignProcessToJobObject(job, wintypes.HANDLE(int(process._handle))))
        if not assigned:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            pytest.skip("UNKNOWN: experiment process could not be assigned to its Job")
        try:
            stdout, stderr = process.communicate(input=b"GO\n", timeout=18)
        except subprocess.TimeoutExpired:
            terminated = bool(k.TerminateJobObject(job, 91))
            if not terminated and process.poll() is None:
                process.kill()
            try:
                process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                pass
            pytest.skip("UNKNOWN: experiment exceeded its owned-process deadline")
        if process.returncode != 0 or stderr or len(stdout) > 4096:
            pytest.skip("UNKNOWN: experiment process result unavailable")
        try:
            result = json.loads(stdout)
        except (ValueError, UnicodeDecodeError):
            pytest.skip("UNKNOWN: experiment receipt unavailable")
        if not isinstance(result, dict):
            pytest.skip("UNKNOWN: experiment receipt shape unavailable")

        accounting = Accounting()
        deadline = time.monotonic() + 2
        count_confirmed = False
        while time.monotonic() < deadline:
            queried = k.QueryInformationJobObject(job, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None)
            if queried and accounting.ActiveProcesses == 0:
                count_confirmed = True
                break
            time.sleep(0.01)
        if not count_confirmed:
            k.TerminateJobObject(job, 92)
            pytest.skip("UNKNOWN: experiment Job still has unconfirmed processes")
    finally:
        if process is not None and process.poll() is None:
            if assigned:
                if not k.TerminateJobObject(job, 93):
                    process.kill()
            else:
                process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
        k.CloseHandle(job)

    safe_fields = ("status", "reason", "pipe_created", "child_started", "child_ready", "blocked", "cancel_called", "cancel_returned_success", "cancel_error",
                   "writer_joined", "write_success", "write_error", "bytes_written", "child_exit_confirmed",
                   "same_job_confirmed", "buffer_stable_after_join", "buffer_before_cancel", "buffer_after_join",
                   "buffer_final", "buffer_changed_across_cancel")
    evidence = {key: result.get(key) for key in safe_fields}
    evidence["outer_job_assignment_confirmed"] = assigned
    evidence["outer_job_zero_active_confirmed"] = count_confirmed
    # With pytest -s the project receipt records only these synthetic statuses,
    # not input bytes, environment, paths, or account configuration.
    print("SYNTHETIC_WINDOWS_PIPE_RESULT " + json.dumps(evidence, sort_keys=True), flush=True)
    if result.get("status") != "PASS":
        pytest.skip("UNKNOWN: " + str(result.get("reason", "fixture_unconfirmed")))
    assert result["same_job_confirmed"] and result["blocked"] and result["cancel_called"]
    assert result["cancel_returned_success"] and result["writer_joined"]
    assert result["write_success"] is False and result["write_error"] == 995
    assert result["buffer_stable_after_join"] and result["child_exit_confirmed"]
