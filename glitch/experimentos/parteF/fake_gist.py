"""Doble de prueba de la API de Gists (en memoria, sin red). Compartido por las pruebas de la Parte F."""
import json


class HTTPError(Exception):
    pass


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code, self._body = status, body or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError(f"{self.status_code} Client Error")


class FakeGist:
    """files: {nombre: contenido-texto}. mode='ok' | '401' (todo falla con 401) | 'write401' (lee bien, escribir falla) |
    'write_lost' (el PATCH responde 200 pero NO guarda: caso de verificacion por lectura posterior)."""

    def __init__(self, files=None, mode="ok"):
        self.files = {k: (v if isinstance(v, str) else json.dumps(v)) for k, v in (files or {}).items()}
        self.mode, self.gets, self.patches = mode, 0, []

    def get(self, url, headers=None, timeout=None, **kw):
        self.gets += 1
        if self.mode == "401":
            return FakeResponse(401)
        return FakeResponse(200, {"files": {k: {"content": v} for k, v in self.files.items()}})

    def patch(self, url, headers=None, json=None, timeout=None, **kw):
        self.patches.append(json)
        if self.mode in ("401", "write401"):
            return FakeResponse(401)
        if self.mode == "write_lost":
            return FakeResponse(200, {})
        for name, obj in json["files"].items():
            self.files[name] = obj["content"]
        return FakeResponse(200, {})

    def read(self, name):
        import json as _j
        return _j.loads(self.files[name]) if name in self.files and self.files[name].strip() else None
