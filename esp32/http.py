# A minimal HTTP implementation since the latest stable
# Only supports HTTP since I use local network. Please don't hack.

import re
import socket


def _parse_url(url):
    m = re.match(r"^http://([a-zA-Z0-9_-\.]+(:[0-9]+)?)(/?|(/[a-zA-Z0-9_-\.]+)*)$", url)
    if not m:
        raise RuntimeError(f"invalid URL: {url}")
    host = m.group(1)
    path = m.group(3) or "/"
    return host, path


def _parse_host(host):
    parts = host.rsplit(":", 1)
    hostname = parts[0]
    port = int(parts[1]) if len(parts) > 1 else 80
    return hostname, port


def _initiate_get_request(sock, host, path):
    sock.sendall(f"GET {path} HTTP/1.0\r\nHost: {host}\r\n\r\n".encode())
    status = sock.readline()
    parts = status.split(b" ")
    if parts[1] != b"200":
        raise RuntimeError("unsuccessful or unsupported GET request")
    while True:
        line = sock.readline().strip()
        if not line:
            break
        parts = line.split(b":", 1)
        header = parts[0].lower()
        value = parts[1]
        if header == b"content-encoding":
            raise RuntimeError(f"content encoding not supported, got: {value}")
        elif header == b"transfer-encoding":
            raise RuntimeError(f"transfer encoding not supported, got: {value}")


def open_get_request(url):
    host, path = _parse_url(url)
    hostname, port = _parse_host(host)
    addrinfo = socket.getaddrinfo(hostname, port)[0]
    sock = socket.socket()
    try:
        sock.connect(addrinfo[-1])
        _initiate_get_request(sock, host, path)
    except:
        sock.close()
        raise
    else:
        return sock
