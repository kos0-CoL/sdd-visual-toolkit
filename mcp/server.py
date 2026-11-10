"""RF-40 — Servidor MCP (§30, entornos vía APIs/MCP).

Expone el mismo estado central que la CLI por JSON-RPC 2.0 sobre stdio
(NDJSON, sin dependencias): initialize, tools/list, tools/call, ping.
Herramientas de solo lectura: exportar_estado, siguiente, tablero.
Herramientas operativas: asignar_tarea, registrar_resultado, marcar_completada
sobre el motor central (asignación, resultado y cierre con gate de pruebas).
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
from cli.commands import tasks as mod_tasks  # noqa: E402
from core import board as mod_board  # noqa: E402
from core import build as mod_build  # noqa: E402
from core import navigation as mod_nav  # noqa: E402
from core import export as mod_export  # noqa: E402
from core.tasks import TasksError  # noqa: E402
from state import store  # noqa: E402
from core.version import version as version_herramienta  # noqa: E402

NOMBRE = "sdd-visual-toolkit"
VERSION = version_herramienta()

HERRAMIENTAS_OPERATIVAS = ("asignar_tarea", "registrar_resultado",
                           "marcar_completada")


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
        {"name": "asignar_tarea",
         "description": ("Marca una tarea pendiente como en curso; respeta "
                         "dependencias y la regla de una sola tarea activa."),
         "inputSchema": {"type": "object",
                         "properties": {"root": {"type": "string"},
                                        "task_id": {"type": "string"}},
                         "required": ["task_id"],
                         "additionalProperties": False}},
        {"name": "registrar_resultado",
         "description": ("Registra el resultado de una tarea en curso: "
                         "«completada» verifica archivos y pruebas; "
                         "«fallida» exige una nota."),
         "inputSchema": {"type": "object",
                         "properties": {"root": {"type": "string"},
                                        "task_id": {"type": "string"},
                                        "resultado": {"type": "string",
                                                      "enum": ["completada",
                                                               "fallida"]},
                                        "nota": {"type": "string"}},
                         "required": ["task_id", "resultado"],
                         "additionalProperties": False}},
        {"name": "marcar_completada",
         "description": ("Cierra una tarea en curso tras verificar archivos y "
                         "pruebas ejecutables (gate NOT_VERIFIED)."),
         "inputSchema": {"type": "object",
                         "properties": {"root": {"type": "string"},
                                        "task_id": {"type": "string"},
                                        "nota": {"type": "string"}},
                         "required": ["task_id"],
                         "additionalProperties": False}},
    ]


def _texto(texto: str, es_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": texto}],
            "isError": es_error}


def _cargar_tarea(raiz, task_id: str):
    """Localiza una tarea por id en el índice de tareas (§9)."""
    indice = mod_tasks._indice(raiz)
    if not indice:
        raise TasksError("sin tareas indexadas; ejecute `tasks <plan>` primero")
    for plan_id in sorted(indice):
        info, tareas = mod_tasks._cargar_tareas(raiz, plan_id)
        tarea = next((t for t in tareas if t.id == task_id), None)
        if tarea is not None:
            return info, tareas, tarea
    raise TasksError(f"tarea inexistente: {task_id}")


def _operar(nombre: str, argumentos: dict) -> dict:
    """Herramientas operativas sobre el motor central (§11, §30)."""
    raiz = _raiz(argumentos)
    task_id = str((argumentos or {}).get("task_id") or "").strip()
    if not task_id:
        return _texto(f"⛔ falta task_id para {nombre}", es_error=True)
    info, tareas, tarea = _cargar_tarea(raiz, task_id)
    nota = str((argumentos or {}).get("nota") or "")
    if nombre == "asignar_tarea":
        mod_build.marcar_en_curso(tarea, tareas)
        evento = {"evento": "en_curso", "tarea": tarea.id}
    elif nombre == "marcar_completada":
        evento = mod_build.registrar_done(tarea, tareas, raiz, nota=nota)
    else:
        resultado = str((argumentos or {}).get("resultado") or "").strip()
        if resultado == "fallida":
            evento = mod_build.registrar_fail(tarea, nota)
        elif resultado == "completada":
            evento = mod_build.registrar_done(tarea, tareas, raiz, nota=nota)
        else:
            return _texto("⛔ resultado debe ser «completada» o «fallida»",
                          es_error=True)
    mod_tasks._persistir(raiz, info["plan_id"], info["spec_id"], tareas)
    return _texto(json.dumps({"tarea": tarea.to_dict(), "evento": evento},
                             ensure_ascii=False))


def _llamar(nombre: str, argumentos: dict) -> dict:
    try:
        if nombre in HERRAMIENTAS_OPERATIVAS:
            return _operar(nombre, argumentos)
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
