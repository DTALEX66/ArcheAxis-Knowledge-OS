"""Local model transport: numeric loopback, no proxies or redirects."""
import ipaddress
import urllib.parse
import urllib.request


class NoLocalRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Local model redirects are refused")


def local_urlopen(request, timeout):
    url = request.full_url if isinstance(request, urllib.request.Request) else request
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "http" or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Invalid local model endpoint")
    host = "127.0.0.1" if parsed.hostname == "localhost" else parsed.hostname
    try:
        if not ipaddress.ip_address(host).is_loopback:
            raise ValueError("Remote model endpoint refused")
    except (ValueError, TypeError) as error:
        raise ValueError("Numeric loopback model endpoint required") from error
    port = parsed.port
    netloc = (f"[{host}]" if ":" in host else host) + (f":{port}" if port is not None else "")
    canonical = urllib.parse.urlunsplit(("http", netloc, parsed.path, parsed.query, ""))
    if isinstance(request, urllib.request.Request):
        request = urllib.request.Request(canonical, data=request.data, headers=dict(request.header_items()), method=request.get_method())
    else:
        request = canonical
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoLocalRedirect()).open(request, timeout=timeout)
