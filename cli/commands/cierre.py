"""Comandos `toolkit cierre` — RF-37 (§27).

Mensaje final uniforme de 7 puntos desde artefactos reales
(checkpoints, journal, tareas, tablero, navegación). Solo lectura:
no ejecuta fases ni muta estado.
"""

from __future__ import annotations

import pathlib

from cli.commands import context as mod_context
from cli.commands import plan as mod_plan
from cli.commands import tablero as mod_tablero
from cli.commands import tasks as mod_tasks
from core import checkpoints as mod_cp
from core.cierre import bloque
from core.journal import historial
from core.navigation import sugerir
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def _pills(raiz) -> tuple[str, list[str]]:
    try:
        estado = mod_tablero.recopilar(raiz)
    except Exception:  # noqa: BLE001 — sin tablero, se declara
        return "tablero", []
    nav = sugerir(estado)
    rec = (nav.get("recomendada") or {}).get("comando", "")
    pills = [p["comando"] for p in nav.get("pills", []) if p.get("comando")]
    return rec, pills


def _cierre_tarea(raiz, task_id: str) -> int:
    try:
        plan, tarea = mod_context._localizar(raiz, task_id)
    except store.StoreError as error:
        print(f"⛔ {error}")
        return 1
    punto = mod_cp.cargar(raiz, tarea.id)
    eventos = [e for e in historial(raiz, plan.plan_id)
               if e.get("tarea") == tarea.id]
    pruebas = ["%s [%s] %s: %s" % (
        e.get("fecha", "?"), e.get("evento", "?"), e.get("tarea", "?"),
        ("verdes" if e.get("pruebas_ok") else "con rojo")
        if e.get("evento") == "tests" else (e.get("nota") or "—"))
        for e in eventos[-8:]]
    archivos = list((punto or {}).get("archivos", []) or list(tarea.archivos))
    if punto:
        resumen = "%s %s; pruebas: %s." % (
            tarea.id, tarea.estado, punto.get("pruebas", "—"))
        estado = ("checkpoint .specify/checkpoints/%s.json + journal "
                  "(proxima: %s)." % (tarea.id, punto.get("proxima") or "—"))
        proxima = punto.get("proxima") or "ninguna (era la última)"
    else:
        resumen = "%s %s (sin checkpoint todavía)." % (
            tarea.id, tarea.estado)
        estado = "journal (.specify/memory/) sin checkpoint de la tarea."
        proxima = "test %s" % tarea.id
    pendientes = (["%s: %s" % (e.get("tarea", "?"), e.get("nota") or "fallida")
                   for e in eventos if e.get("evento") == "fallida"] or
                  (["tarea sin completar: %s" % tarea.estado]
                   if tarea.estado != "completada" else []))
    rec, pills = _pills(raiz)
    print(bloque("%s (%s)" % (tarea.id, plan.plan_id), resumen,
                 archivos, pruebas, pendientes, estado, rec or proxima,
                 pills))
    return 0


def _cierre_plan(raiz, plan_id: str) -> int:
    try:
        plan = mod_plan._cargar_plan(raiz, plan_id)
        _info, tareas = mod_tasks._cargar_tareas(raiz, plan_id)
    except Exception as error:  # noqa: BLE001 — TasksError/StoreError
        print(f"⛔ {error}")
        return 1
    puntos = mod_cp.listar(raiz, plan_id)
    eventos = historial(raiz, plan_id)
    hechas = [t for t in tareas if t.estado == "completada"]
    tests = [e for e in eventos if e.get("evento") == "tests"]
    resumen = ("%s: %d/%d tareas completadas; %d checkpoint(s), "
               "%d corrida(s) de pruebas." % (
                   plan_id, len(hechas), len(tareas), len(puntos), len(tests)))
    archivos = sorted({a for p in puntos for a in p.get("archivos", [])} |
                      {a for t in hechas for a in t.archivos})
    validaciones = [
        "%s %s: %s" % (e.get("fecha", "?"), e.get("tarea", "?"),
                       "✅ verdes" if e.get("pruebas_ok") else "❌ con rojo")
        for e in tests[-8:]]
    pendientes = (["%s pendiente (%s)" % (t.id, t.estado) for t in tareas
                   if t.estado != "completada"] +
                  ["%s: %s" % (e.get("tarea", "?"), e.get("nota") or "fallida")
                   for e in eventos if e.get("evento") == "fallida"][-8:])
    estado = ("journal (%d evento(s)) + %d checkpoint(s) en "
              ".specify/checkpoints/." % (len(eventos), len(puntos)))
    rec, pills = _pills(raiz)
    print(bloque("%s (%s)" % (plan_id, plan.spec_id), resumen, archivos,
                 validaciones, pendientes, estado,
                 rec or ("traza %s" % plan.spec_id), pills))
    return 0


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        texto = (args.texto or "").strip()
    except store.StoreError as error:
        print(f"⛔ {error}")
        return 1
    if not texto:
        rec, pills = _pills(raiz)
        try:
            estado = mod_tablero.recopilar(raiz)
            fase = "proyecto «%s» — %s" % (
                estado.get("proyecto", "?"), estado.get("fase", "sin SPEC"))
        except Exception:  # noqa: BLE001 — sin tablero, se declara
            fase = "proyecto (sin estado legible)"
        print(bloque(fase, "Foto actual sin cerrar una fase concreta: "
                           "use `cierre TASK-ID` o `cierre PLAN-ID`.",
                     [], [], [], "solo lectura, nada se ejecutó.",
                     rec or "—", pills))
        return 0
    if texto.startswith("TASK-"):
        return _cierre_tarea(raiz, texto)
    if texto.startswith("PLAN-"):
        return _cierre_plan(raiz, texto)
    print("⛔ indique un TASK-ID o un PLAN-ID")
    return 1
