"""Single owned Material cloud process; no argv/env secrets or secret files."""
import ctypes
import importlib.util
import json
import re
import sys
from ctypes import wintypes
from pathlib import Path

spec = importlib.util.spec_from_file_location("owned_material_cloud", Path(__file__).with_name("material_cloud.py"))
cloud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cloud)


def credential_target(reference):
    if not isinstance(reference, str) or re.fullmatch(r"aak_cred_[a-f0-9]{32}", reference) is None:
        raise cloud.CloudFailure("CREDENTIAL_REFERENCE_INVALID")
    return "ArcheAxis.Knowledge/product-model/" + reference


def read_product_credential(reference):
    target = credential_target(reference)
    if sys.platform != "win32":
        raise cloud.CloudFailure("CREDENTIAL_UNAVAILABLE")

    class Credential(ctypes.Structure):
        _fields_ = [("flags", wintypes.DWORD), ("kind", wintypes.DWORD),
                    ("target", wintypes.LPWSTR), ("comment", wintypes.LPWSTR),
                    ("written", wintypes.FILETIME), ("size", wintypes.DWORD),
                    ("blob", ctypes.POINTER(ctypes.c_ubyte)), ("persist", wintypes.DWORD),
                    ("count", wintypes.DWORD), ("attributes", ctypes.c_void_p),
                    ("alias", wintypes.LPWSTR), ("username", wintypes.LPWSTR)]

    api = ctypes.WinDLL("Advapi32", use_last_error=True)
    pointer = ctypes.POINTER(Credential)()
    api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(Credential))]
    api.CredReadW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    if not api.CredReadW(target, 1, 0, ctypes.byref(pointer)):
        raise cloud.CloudFailure("CREDENTIAL_UNAVAILABLE")
    try:
        value = pointer.contents
        if not value.blob or not 0 < value.size <= 2560:
            raise cloud.CloudFailure("CREDENTIAL_INVALID")
        return bytearray(value.blob[:value.size])
    finally:
        api.CredFree(pointer)


def run(stream, *, resolver=read_product_credential, transport=cloud.http.fetch):
    raw = stream.read(200001)
    if len(raw) > 200000:
        raise cloud.CloudFailure("MATERIAL_CLOUD_FRAME_LIMIT")
    frame = json.loads(raw)
    return cloud.execute(frame, resolve_credential=resolver, transport=transport)


if __name__ == "__main__":
    try:
        result = run(sys.stdin.buffer)
        print(json.dumps(result, ensure_ascii=False))
    except Exception:
        # No exception repr, URL, HTTP headers, secret or provider body in diagnostics.
        print('{"schema":"archeaxis.machine-worker-failure/v1","reason_code":"MODEL_CALL_FAILED"}')
        sys.exit(1)
