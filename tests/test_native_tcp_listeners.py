"""IP Helper ABI/error regressions plus real, self-owned loopback sockets."""

import ast
import ctypes
import os
from pathlib import Path
import socket
import time
from unittest.mock import Mock

import pytest

from scripts.probes import native_tcp_listeners as tcp


def row(family, address, port, pid, *, state=2, scope=0):
    item = (tcp._Tcp4Row if family == tcp.AF_INET else tcp._Tcp6Row)()
    item.state, item.pid, item.local_port = state, pid, socket.htons(port)
    packed = socket.inet_pton(socket.AF_INET if family == tcp.AF_INET else socket.AF_INET6, address)
    if family == tcp.AF_INET:
        item.local_address = tcp.DWORD.from_buffer_copy(packed).value
    else:
        item.local_address[:] = packed
        item.local_scope = socket.htonl(scope)
    return bytes(item)


def table(*rows, count=None):
    return bytes(tcp.DWORD(len(rows) if count is None else count)) + b"".join(rows)


class Api:
    def __init__(self, tables=None):
        self.tables = tables or {tcp.AF_INET: table(), tcp.AF_INET6: table()}
        self.calls = []

    def __call__(self, buffer, size_pointer, ordered, family, table_class, reserved):
        assert ordered is False and table_class == 3 and reserved == 0
        self.calls.append(family)
        size = ctypes.cast(size_pointer, ctypes.POINTER(tcp.DWORD)).contents
        payload = self.tables[family]
        capacity, size.value = size.value, len(payload)
        if buffer is None or capacity < len(payload):
            return 122
        ctypes.memmove(buffer, payload, len(payload))
        return 0


def test_abi_fixed_width_layout():
    assert ctypes.sizeof(tcp.DWORD) == 4
    assert ctypes.sizeof(tcp._Tcp4Row) == 24
    assert ctypes.sizeof(tcp._Tcp6Row) == 56
    assert tcp._Tcp4Table.rows.offset == tcp._Tcp6Table.rows.offset == 4
    assert tcp._Tcp6Row.pid.offset == 52


def test_two_families_exact_address_port_pid_and_or_filter():
    api = Api({tcp.AF_INET: table(row(2, "127.0.0.1", 54410, 120),
                                 row(2, "0.0.0.0", 43210, 121),
                                 row(2, "127.0.0.1", 443, 999)),
               tcp.AF_INET6: table(row(23, "::1", 54410, 120),
                                   row(23, "fe80::1234", 12345, 121, scope=7))})
    result = tcp.tcp_listener_rows(ports=[54410], pids=[121], query=api)
    assert result == [
        {"LocalAddress": "fe80::1234%7", "LocalPort": 12345, "OwningProcess": 121},
        {"LocalAddress": "0.0.0.0", "LocalPort": 43210, "OwningProcess": 121},
        {"LocalAddress": "127.0.0.1", "LocalPort": 54410, "OwningProcess": 120},
        {"LocalAddress": "::1", "LocalPort": 54410, "OwningProcess": 120}]
    assert api.calls == [2, 2, 23, 23]


def test_only_two_successful_tables_can_mean_empty():
    assert tcp.tcp_listener_rows(ports=[54410], query=Api()) == []


@pytest.mark.parametrize("family", [2, 23])
@pytest.mark.parametrize("status", [5, 50, 87])
def test_api_error_is_not_free_port_even_after_other_family_succeeds(family, status):
    api = Api()
    def error(*args):
        return status if args[3] == family else api(*args)
    with pytest.raises(OSError, match=f"family {family} failed"):
        tcp.tcp_listener_rows(ports=[54410], query=error)


def test_table_growth_retries_then_succeeds():
    api, calls = Api(), 0
    def growing(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            ctypes.cast(args[1], ctypes.POINTER(tcp.DWORD)).contents.value = 128
            return 122
        return api(*args)
    assert tcp.tcp_listener_rows(ports=[54410], query=growing) == []
    assert calls == 5


def test_continuous_growth_has_finite_call_budget():
    calls = 0
    def growing(buffer, size_pointer, *_):
        nonlocal calls
        calls += 1
        ctypes.cast(size_pointer, ctypes.POINTER(tcp.DWORD)).contents.value += 4
        return 122
    with pytest.raises(RuntimeError, match="kept growing"):
        tcp.tcp_listener_rows(ports=[54410], query=growing)
    assert calls == tcp.MAX_TABLE_CALLS


@pytest.mark.parametrize("size", [0, tcp.MAX_TABLE_BYTES + 1])
def test_invalid_growth_is_rejected_before_allocation(size):
    def invalid(buffer, size_pointer, *_):
        ctypes.cast(size_pointer, ctypes.POINTER(tcp.DWORD)).contents.value = size
        return 122
    with pytest.raises(RuntimeError, match="Invalid TCP table growth"):
        tcp.tcp_listener_rows(ports=[54410], query=invalid)


@pytest.mark.parametrize("payload", [b"\x00", table(count=1),
    table(row(2, "127.0.0.1", 1234, 7))[:-1], table(count=0xffffffff),
    table(row(2, "127.0.0.1", 1234, 7, state=5))])
def test_bad_table_boundaries_or_state_never_mean_empty(payload):
    with pytest.raises(RuntimeError):
        tcp.tcp_listener_rows(ports=[1234], query=Api({2: payload, 23: table()}))


def test_success_size_outside_allocated_buffer_is_rejected():
    api = Api()
    def invalid(*args):
        code = api(*args)
        if code == 0:
            ctypes.cast(args[1], ctypes.POINTER(tcp.DWORD)).contents.value += 1
        return code
    with pytest.raises(RuntimeError, match="Invalid TCP table size"):
        tcp.tcp_listener_rows(ports=[1234], query=invalid)


@pytest.mark.parametrize("options", [{}, {"ports": [0]}, {"ports": [65536]},
    {"pids": [-1]}, {"ports": [True]}, {"pids": [2**32]}])
def test_invalid_targets_do_not_query_system(options):
    api = Mock()
    with pytest.raises(ValueError):
        tcp.tcp_listener_rows(query=api, **options)
    api.assert_not_called()


def test_observer_exception_is_never_suppressed():
    with pytest.raises(TimeoutError, match="unavailable"):
        tcp.tcp_listener_rows(ports=[1234], query=Mock(side_effect=TimeoutError("unavailable")))


SOURCE = Path(__file__).resolve().parents[1] / "scripts/probes/aaos01_tauri_webdriver_loop.py"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
scope = {}
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "owned_cdp_listener_rows")
exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE), "exec"), scope)
owned_cdp = scope["owned_cdp_listener_rows"]


def test_cdp_success_rechecks_listener_creation():
    owned = [{"pid": 12, "created": 77}]
    listeners = [{"LocalAddress": "::1", "LocalPort": 54410, "OwningProcess": 12}]
    observe, snapshot = Mock(return_value=listeners), Mock(return_value=owned)
    assert owned_cdp(54410, owned, observe=observe, snapshot=snapshot) == listeners
    observe.assert_called_once_with(ports=(54410,))
    snapshot.assert_called_once_with()


@pytest.mark.parametrize("address,pid,after", [("0.0.0.0",12,77), ("::",12,77),
    ("127.0.0.1",13,77), ("127.0.0.1",12,78), ("::1",12,None)])
def test_cdp_unowned_wildcard_recycled_or_missing_owner_rejected(address, pid, after):
    observe = Mock(return_value=[{"LocalAddress":address, "LocalPort":54410, "OwningProcess":pid}])
    with pytest.raises(RuntimeError):
        owned_cdp(54410, [{"pid":12,"created":77}], observe=observe,
                  snapshot=lambda: [{"pid":12,"created":after}] if after else [])


def test_cdp_absent_or_unknown_observation_never_qualifies():
    for observe in [Mock(return_value=[]), Mock(side_effect=OSError("unavailable"))]:
        with pytest.raises((RuntimeError, OSError)):
            owned_cdp(54410, [{"pid":12,"created":77}], observe=observe, snapshot=lambda: [])


@pytest.mark.skipif(os.name != "nt", reason="Real IP Helper ABI requires Windows")
@pytest.mark.parametrize("family,address", [(socket.AF_INET,"127.0.0.1"), (socket.AF_INET6,"::1")])
def test_real_owned_listener_appears_and_disappears(family, address):
    # No product launch, connections, shared process termination or system changes.
    with socket.socket(family, socket.SOCK_STREAM) as owned:
        if family == socket.AF_INET6:
            owned.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        owned.bind((address, 0))
        owned.listen(1)
        port = owned.getsockname()[1]
        expected = {"LocalAddress": address, "LocalPort": port, "OwningProcess": os.getpid()}
        assert expected in tcp.tcp_listener_rows(ports=[port])
    deadline = time.monotonic() + 2
    while expected in tcp.tcp_listener_rows(ports=[port]):
        assert time.monotonic() < deadline, "Closed self-owned socket remained listening"
        time.sleep(.02)
