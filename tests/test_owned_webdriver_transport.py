"""Synthetic real-loopback checks of the production native probe transport."""
import ast
import http.client
import io
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request
import pytest

ROOT = Path(__file__).resolve().parents[1]
node = next(n for n in ast.parse((ROOT / 'scripts/probes/aaos01_tauri_webdriver_loop.py').read_text(encoding='utf-8')).body if isinstance(n, ast.ClassDef) and n.name == 'OwnedWebDriverTransport')
namespace = {'http': http, 'io': io, 'urlsplit': urlsplit, 'HTTPError': HTTPError}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / 'scripts/probes/aaos01_tauri_webdriver_loop.py'), 'exec'), namespace)
Transport = namespace['OwnedWebDriverTransport']

@contextmanager
def server():
    events = []
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'
        def log_message(self, *args): pass
        def do_POST(self):
            self.rfile.read(int(self.headers.get('Content-Length', 0)))
            events.append((self.path, self.client_address[1]))
            if self.path == '/lost':
                self.send_response(200); self.send_header('Content-Length', '20'); self.end_headers()
                self.wfile.write(b'{'); self.wfile.flush(); self.close_connection = True
            elif self.path == '/redirect':
                self.send_response(302); self.send_header('Location', 'https://example.invalid/'); self.send_header('Content-Length', '0'); self.end_headers()
            else:
                body=b'{"value":true}'
                self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    listener=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=listener.serve_forever,daemon=True);thread.start()
    transport=Transport(listener.server_port)
    try: yield transport, listener.server_port, events
    finally: transport.close();listener.shutdown();listener.server_close();thread.join(3)

def command(port, path): return Request(f'http://127.0.0.1:{port}{path}',data=b'{}',method='POST')

def test_repeated_commands_use_one_connection():
    with server() as (transport,port,events):
        for _ in range(25):
            with transport.open(command(port,'/command'),timeout=3) as response:
                assert response.read()==b'{"value":true}'
        assert len(events)==25
        assert len({client for _,client in events})==1

def test_redirect_is_not_followed():
    with server() as (transport,port,events):
        with pytest.raises(HTTPError) as error: transport.open(command(port,'/redirect'),timeout=3)
        assert error.value.code==302
        assert len(events)==1

def test_applied_command_with_lost_response_is_not_replayed():
    with server() as (transport,port,events):
        with pytest.raises(http.client.IncompleteRead): transport.open(command(port,'/lost'),timeout=3)
        assert len(events)==1
        assert transport.connection.sock is None

def test_destination_must_match_owned_port():
    with server() as (transport,port,events):
        with pytest.raises(ValueError): transport.open(command(port+1,'/command'),timeout=3)
        assert events==[]