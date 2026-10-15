"""Read-only Windows TCP listeners without PowerShell/CIM startup.

ABI: Microsoft Learn GetExtendedTcpTable, MIB_TCP{,6}ROW_OWNER_PID and
MIB_TCP{,6}TABLE_OWNER_PID (tcpmib.h). DWORD stays 32 bits on x64 Windows.
Only requested ports/PIDs leave this module; an unavailable family is an error,
never an empty table. Retries and allocation are capped if the table grows.
"""

from __future__ import annotations

import ctypes
import os
import socket

DWORD = ctypes.c_uint32
AF_INET = 2
AF_INET6 = 23  # Windows ABI value, including when synthetic tests run elsewhere.
TCP_TABLE_OWNER_PID_LISTENER = 3
ERROR_INSUFFICIENT_BUFFER = 122
MAX_TABLE_BYTES = 16 * 1024 * 1024
MAX_TABLE_CALLS = 4


class _Tcp4Row(ctypes.Structure):
    _fields_ = [(name, DWORD) for name in (
        "state", "local_address", "local_port", "remote_address", "remote_port", "pid")]


class _Tcp6Row(ctypes.Structure):
    _fields_ = [
        ("local_address", ctypes.c_ubyte * 16), ("local_scope", DWORD),
        ("local_port", DWORD), ("remote_address", ctypes.c_ubyte * 16),
        ("remote_scope", DWORD), ("remote_port", DWORD), ("state", DWORD), ("pid", DWORD)]


class _Tcp4Table(ctypes.Structure):
    _fields_ = [("count", DWORD), ("rows", _Tcp4Row * 1)]


class _Tcp6Table(ctypes.Structure):
    _fields_ = [("count", DWORD), ("rows", _Tcp6Row * 1)]


def _api():
    if os.name != "nt":
        raise OSError("Native TCP listener observation requires Windows")
    call = ctypes.WinDLL("iphlpapi.dll").GetExtendedTcpTable
    call.argtypes = [ctypes.c_void_p, ctypes.POINTER(DWORD), ctypes.c_int,
                     DWORD, ctypes.c_int, DWORD]
    call.restype = DWORD
    return call


def _family_rows(call, family):
    row_type, table_type = ((_Tcp4Row, _Tcp4Table) if family == AF_INET
                            else (_Tcp6Row, _Tcp6Table))
    capacity = 0
    for _ in range(MAX_TABLE_CALLS):
        buffer = ctypes.create_string_buffer(capacity) if capacity else None
        size = DWORD(capacity)
        status = call(buffer, ctypes.byref(size), False, family,
                      TCP_TABLE_OWNER_PID_LISTENER, 0)
        if status == ERROR_INSUFFICIENT_BUFFER:
            if size.value <= capacity or size.value > MAX_TABLE_BYTES:
                raise RuntimeError(f"Invalid TCP table growth for family {family}: {size.value}")
            capacity = size.value
            continue
        if status:
            raise OSError(status, f"GetExtendedTcpTable family {family} failed ({status})")
        offset, stride = table_type.rows.offset, ctypes.sizeof(row_type)
        if buffer is None or not offset <= size.value <= capacity:
            raise RuntimeError(f"Invalid TCP table size for family {family}: {size.value}")
        count = DWORD.from_buffer_copy(buffer).value
        if count > (size.value - offset) // stride:
            raise RuntimeError(f"Truncated TCP table for family {family}: {count} rows")
        result = []
        for index in range(count):
            row = row_type.from_buffer_copy(buffer, offset + index * stride)
            if row.state != 2:
                raise RuntimeError(f"Non-listener in TCP listener table for family {family}")
            if family == AF_INET:
                address = socket.inet_ntop(socket.AF_INET, bytes(DWORD(row.local_address)))
            else:
                address = socket.inet_ntop(socket.AF_INET6, bytes(row.local_address))
                if row.local_scope:
                    address += f"%{socket.ntohl(row.local_scope)}"
            result.append({"LocalAddress": address,
                           "LocalPort": socket.ntohs(row.local_port & 0xffff),
                           "OwningProcess": row.pid})
        return result
    raise RuntimeError(f"TCP table kept growing for family {family} after {MAX_TABLE_CALLS} calls")


def tcp_listener_rows(*, ports=(), pids=(), query=None):
    """Return exact address/port/PID for requested ports OR owning PIDs.

    Both families must succeed. Errors propagate even after successful IPv4
    observation, so cleanup cannot mistake UNKNOWN for a released port.
    """
    ports, pids = set(ports), set(pids)
    if not ports and not pids:
        raise ValueError("At least one target port or PID is required")
    if any(type(port) is not int or not 1 <= port <= 65535 for port in ports):
        raise ValueError("Invalid target TCP port")
    if any(type(pid) is not int or not 0 < pid <= 0xffffffff for pid in pids):
        raise ValueError("Invalid target PID")
    call = query if query is not None else _api()
    result = []
    for family in (AF_INET, AF_INET6):
        result.extend(row for row in _family_rows(call, family)
                      if row["LocalPort"] in ports or row["OwningProcess"] in pids)
    return sorted(result, key=lambda row: (row["LocalPort"], row["LocalAddress"], row["OwningProcess"]))
