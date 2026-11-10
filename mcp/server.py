"""RF-40 — Servidor MCP (§30, entornos vía APIs/MCP).

Expone el mismo estado central que la CLI por JSON-RPC 2.0 sobre stdio
(NDJSON, sin dependencias): initialize, tools/list, tools/call, ping.
Herramientas de solo lectura: exportar_estado, siguiente, tablero.
Sin proyecto inicializado se declara en vez de inventar.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli.commands import arbol as mod_arbol  # noqa: E402
from cli.commands import plan as mod_plan  # noqa: E402
from cli.commands import tablero as mod_tablero  # noqa: E402
from core import board as mod_board  # noqa: E402
from core import navigation as mod_nav  # noqa: E402
from core import export as mod_export  # noqa: E402
from state import store  # noqa: E402

NOMBRE = "sdd-visual-toolkit"
VERSION = "0.1.0"


def _foto(raiz):
    """Mismo estado central que tablero/árbol/siguiente/export."""
    estado = mod_tablero.recopilar(raiz)
    spec_id = estado.get("spec_id")
    if spec_id and "PLAN-" not in str(estado.get("proxima") or ""):
        try:
            planes = [(pid, info)
                      for pid, info in mod_plan._indice(raiz).items()
                      if info.get("spec_id") == spec_id]
            if planes:
                estado["plan_id"] = sorted(p for p, _i in planes)[-1]
        except Exception:  # noqa: BLE001 — sin índice, se declara
            pass
    nodos, transiciones = mod_arbol.nodos(raiz)
    nav = mod_nav.sugerir(estado)
    return estado, nodos, transiciones, nav


def _raiz(argumentos: dict):
    base = (argumentos or {}).get("root") or os.getcwd()
    return store.descubrir_raiz(Path(base))


def _herramientas() -> list:
    return [
        {"name": "exportar_estado",
         "description": ("Foto JSON del proyecto: fase, progreso, tarea, "
                         "pruebas, árbol, navegación y píldoras. Solo lectura."),
         "inputSchema": {"type": "object",
                         "properties": {"root": {"type": "string"}},
                         "additionalProperties": False}},
        {"name": "siguiente",
         "description": ("Qué sigue y cómo ir: píldoras, bloqueos y "
                         "aprobaciones. Solo lectura."),
         "inputSchema": {"type": "object",
                         "properties": {"root": {"type": "string"}},
                         "additionalProperties": False}},
        {"name": "tablero",
         "description": "Panel de estado general del proyecto. Solo lectura.",
         "inputSchema": {"type": "object",
                         "properties": {"root": {"type": "string"}},
                         "additionalProperties": False}},
    ]


def _texto(texto: str, es_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": texto}],
            "isError": es_error}


def _llamar(nombre: str, argumentos: dict) -> dict:
    try:
        raiz = _raiz(argumentos)
        estado, nodos, transiciones, nav = _foto(raiz)
    except Exception as error:  # noqa: BLE001 — se declara, no se rompe
        return _texto("⛔ %s" % error, es_error=True)
    if nombre == "exportar_estado":
        doc = mod_export.documento(estado, nodos, transiciones, nav)
        return {"content": [{"type": "text",
                             "text": mod_export.render(doc)}]}
    if nombre == "siguiente":
        return _texto(mod_nav.render(nav))
    if nombre == "tablero":
        return _texto(mod_board.render(estado))
    return _texto("⛔ herramienta desconocida: %s" % nombre, es_error=True)


def _responder(ident, resultado=None, error=None) -> None:
    mensaje: dict = {"jsonrpc": "2.0", "id": ident}
    if error is not None:
        mensaje["error"] = error
    else:
        mensaje["result"] = resultado if resultado is not None else {}
    sys.stdout.write(json.dumps(mensaje, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def atender(pedido: dict):
    ident = pedido.get("id")
    metodo = pedido.get("method", "")
    params = pedido.get("params") or {}
    if metodo == "initialize":
        return _responder(ident, {
            "protocolVersion": params.get("protocolVersion", "2024-11-05"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": NOMBRE, "version": VERSION}})
    if metodo in ("notifications/initialized", "notifications/cancelled"):
        return
    if metodo == "ping":
        return _responder(ident, {})
    if metodo == "tools/list":
        return _responder(ident, {"tools": _herramientas()})
    if metodo == "tools/call":
        return _responder(ident, _llamar(params.get("name", ""),
                                         params.get("arguments") or {}))
    if ident is None:
        return
    return _responder(ident, error={"code": -32601,
                                    "message": "método desconocido: %s" % metodo})


def main() -> int:
    for linea in sys.stdin:
        linea = linea.strip()
        if not linea:
            continue
        try:
            pedido = json.loads(linea)
        except json.JSONDecodeError:
            continue
        atender(pedido if isinstance(pedido, dict) else {})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
