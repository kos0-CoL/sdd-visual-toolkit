"""Comandos `toolkit tablero` — RF-31 (§20).

Lee SPEC, planes, tareas y journal reales y presenta el panel de
estado general. La fase y la próxima acción se derivan de los gates
reales superados (§26); nada se inventa.
"""

from __future__ import annotations

import pathlib

from cli.commands import clarify as mod_clarify
from cli.commands import plan as mod_plan
from cli.commands import specify as mod_specify
from cli.commands import tasks as mod_tasks
from core.board import render
from core.build import EN_CURSO
from core.journal import historial
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def _pendientes_clarify(raiz, spec_id: str) -> int | None:
    try:
        preguntas, _hist = mod_clarify._preguntas_de(raiz, spec_id)
    except Exception:  # noqa: BLE001 — sin clarify, se declara
        return None
    return len(mod_clarify.pendientes(preguntas))


def recopilar(raiz) -> dict:
    """Estado del tablero desde artefactos reales."""
    estado: dict = {"proyecto": raiz.name,
                    "proxima": "enrich «idea»"}
    specs = mod_specify._indice(raiz)
    if not specs:
        return estado
    spec_id = sorted(specs)[-1]
    spec = mod_specify._cargar_spec(raiz, spec_id)
    estado["spec_id"] = spec_id
    estado["spec_status"] = spec.status
    estado["fase"] = "📝 Especificación"
    estado["proxima"] = "clarify %s" % spec_id

    pendientes = _pendientes_clarify(raiz, spec_id)
    if pendientes is not None:
        estado["fase"] = "🔍 Aclaraciones"
        if pendientes:
            estado["proxima"] = (
                "clarify %s --answer … (%d pendiente(s))" % (
                    spec_id, pendientes))
            estado["pendientes"] = pendientes
            return estado
        estado["proxima"] = "plan %s" % spec_id

    planes = [(pid, info) for pid, info in mod_plan._indice(raiz).items()
              if info.get("spec_id") == spec_id]
    if not planes:
        estado["pendientes"] = pendientes or 0
        return estado
    plan_id = sorted(p for p, _i in planes)[-1]
    plan = mod_plan._cargar_plan(raiz, plan_id)
    estado["fase"] = "📐 Arquitectura"
    estado["proxima"] = "plan --gate %s" % plan_id
    if plan.status != "validado":
        estado["pendientes"] = pendientes or 0
        return estado

    try:
        _info, tareas = mod_tasks._cargar_tareas(raiz, plan_id)
    except Exception:  # noqa: BLE001 — sin tareas, se declara
        estado["proxima"] = "tasks %s" % plan_id
        estado["pendientes"] = pendientes or 0
        return estado
    estado["fase"] = "💾 Tareas"
    hechas = [t for t in tareas if t.estado == "completada"]
    en_curso = [t for t in tareas if t.estado == EN_CURSO]
    estado["hechas"] = len(hechas)
    estado["total"] = len(tareas)
    estado["pendientes"] = len(tareas) - len(hechas)
    estado["tarea_actual"] = en_curso[0].id if en_curso else None
    estado["ultima_completada"] = hechas[-1].id if hechas else None
    estado["proxima"] = "build %s" % plan_id
    if en_curso:
        estado["proxima"] = "build %s (continuar %s)" % (
            plan_id, en_curso[0].id)

    eventos = historial(raiz, plan_id)
    if eventos:
        estado["fase"] = "⚡ Implementación"
    pruebas = [e for e in eventos if e.get("evento") == "tests"]
    if pruebas:
        ult = pruebas[-1]
        estado["fase"] = "🧪 Pruebas"
        estado["pruebas"] = "%s P=%s F=%s cob=%s (%s)" % (
            "✅" if ult.get("pruebas_ok") else "❌",
            ult.get("pasadas", "?"), ult.get("fallidas", "?"),
            "—" if ult.get("cobertura_pct") is None
            else "%s%%" % ult.get("cobertura_pct"),
            ult.get("tarea", "?"))
        estado["pruebas_ok"] = bool(ult.get("pruebas_ok"))
        estado["pruebas_tarea"] = ult.get("tarea")
        if not ult.get("pruebas_ok"):
            estado["proxima"] = "test %s" % ult.get("tarea")
    else:
        estado["pruebas"] = "sin corridas"
    fallos = [e for e in eventos if e.get("evento") == "fallida"]
    estado["errores"] = [
        "%s: %s" % (e.get("tarea", "?"), e.get("nota", "—") or "—")
        for e in fallos[-5:]]
    if len(hechas) == len(tareas) and tareas:
        estado["fase"] = "✅ Completado"
        estado["proxima"] = "traza %s + historia de cada tarea" % spec_id
    return estado


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        print(render(recopilar(raiz)))
    except store.StoreError as error:
        print(f"⛔ {error}")
        return 1
    return 0
