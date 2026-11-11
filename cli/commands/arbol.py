"""Comandos `toolkit arbol` — RF-32 (§21).

Cada fase es un nodo; el estado se deriva de los artefactos y gates
reales. Las transiciones salen del journal; si no hay, se dice.
"""

from __future__ import annotations

import pathlib

from cli.commands import analyze as mod_analyze
from cli.commands import clarify as mod_clarify
from cli.commands import enrich as mod_enrich
from cli.commands import plan as mod_plan
from cli.commands import specify as mod_specify
from cli.commands import tablero as mod_tablero
from cli.commands import tasks as mod_tasks
from core.journal import historial
from core.states import NODOS, render
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def _criticas(raiz, plan_id: str) -> int | None:
    try:
        indice = mod_analyze._indice(raiz)
    except Exception:  # noqa: BLE001 — sin informes, se declara
        return None
    if plan_id not in indice:
        return None
    try:
        datos = store.leer_json(raiz / indice[plan_id]["archivo"])
    except (OSError, ValueError, KeyError):
        return None
    incs = datos.get("incidencias", datos if isinstance(datos, list) else [])
    if not isinstance(incs, list):
        return None
    return sum(1 for i in incs
               if isinstance(i, dict) and i.get("severidad") == "crítica")


def _en_orden(nod: dict[str, str]) -> list[tuple[str, str]]:
    """§21: las fases en el orden del árbol, no en el de inserción del dict."""
    return [(fase, nod[fase]) for _icono, fase in NODOS if fase in nod]


def nodos(raiz) -> tuple[list[tuple[str, str]], list[str]]:
    """(nodos, transiciones) desde artefactos reales."""
    estado = mod_tablero.recopilar(raiz)
    spec_id = estado.get("spec_id")
    if not spec_id:
        pendientes_enr = len(mod_enrich._registro(raiz).listar())
        enr = ("en progreso" if pendientes_enr else "pendiente",
               "%d enriquecimiento(s)" % pendientes_enr
               if pendientes_enr else "sin enriquecimientos")
        resto = [("Enriquecimiento", enr[0])]
        resto += [(fase, "pendiente") for _icono, fase in NODOS[1:]]
        return resto, []
    spec = mod_specify._cargar_spec(raiz, spec_id)
    nod: dict[str, str] = {}
    nod["Enriquecimiento"] = "completado"
    nod["Especificación"] = ("completado" if spec.status == "approved"
                             else "requiere intervención")
    pendientes = mod_tablero._pendientes_clarify(raiz, spec_id)
    nod["Aclaraciones"] = ("pendiente" if pendientes is None
                           else "completado" if pendientes == 0
                           else "en progreso")
    planes = [(pid, info) for pid, info in mod_plan._indice(raiz).items()
              if info.get("spec_id") == spec_id]
    if not planes:
        nod.update({f: "pendiente" for f in
                    ("Arquitectura", "Tareas", "Análisis",
                     "Implementación", "Pruebas", "Recuperación")})
        return (_en_orden(nod), [])
    plan_id = sorted(p for p, _i in planes)[-1]
    plan = mod_plan._cargar_plan(raiz, plan_id)
    nod["Arquitectura"] = ("completado" if plan.status == "validado"
                           else "en progreso")
    try:
        _info, tareas = mod_tasks._cargar_tareas(raiz, plan_id)
    except Exception:  # noqa: BLE001 — sin tareas, se declara
        tareas = []
    if not tareas:
        nod.update({f: "pendiente" for f in
                    ("Tareas", "Análisis", "Implementación", "Pruebas",
                     "Recuperación")})
        return (_en_orden(nod), [])
    hechas = sum(1 for t in tareas if t.estado == "completada")
    nod["Tareas"] = ("completado" if hechas == len(tareas)
                     else "en progreso")
    criticas = _criticas(raiz, plan_id)
    nod["Análisis"] = ("pendiente" if criticas is None
                       else "requiere intervención" if criticas
                       else "completado")
    eventos = historial(raiz, plan_id)
    if not eventos:
        nod.update({f: "pendiente" for f in
                    ("Implementación", "Pruebas", "Recuperación")})
        return (_en_orden(nod), [])
    tipos = {e.get("evento") for e in eventos}
    nod["Recuperación"] = ("recuperado" if "rollback" in tipos
                           else "pendiente")
    ult_cierre = [e for e in eventos
                  if e.get("evento") in ("completada", "fallida")]
    if hechas == len(tareas):
        nod["Implementación"] = "completado"
    elif ult_cierre and ult_cierre[-1].get("evento") == "fallida":
        nod["Implementación"] = "fallido"
    else:
        nod["Implementación"] = "en progreso"
    pruebas = [e for e in eventos if e.get("evento") == "tests"]
    nod["Pruebas"] = ("pendiente" if not pruebas
                      else "completado" if pruebas[-1].get("pruebas_ok")
                      else "fallido")
    transiciones = []
    for e in eventos:
        tipo = e.get("evento")
        if tipo == "en_curso":
            transiciones.append("%s → ⚡ Implementación: %s en curso" % (
                e.get("fecha", "?"), e.get("tarea", "?")))
        elif tipo == "tests":
            transiciones.append("%s → 🧪 Pruebas: %s %s" % (
                e.get("fecha", "?"), e.get("tarea", "?"),
                "verdes" if e.get("pruebas_ok") else "con rojo"))
        elif tipo in ("completada", "fallida"):
            transiciones.append("%s → ⚡ Implementación: %s %s" % (
                e.get("fecha", "?"), e.get("tarea", "?"), tipo))
        elif tipo == "rollback":
            transiciones.append("%s → ♻️ Recuperación: %s" % (
                e.get("fecha", "?"), e.get("nota") or "rollback"))
        elif tipo == "checkpoint":
            transiciones.append("%s → 🔖 hito: %s" % (
                e.get("fecha", "?"), e.get("tarea", "?")))
    return (_en_orden(nod), transiciones)


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        nodos_lista, transiciones = nodos(raiz)
        print(render(nodos_lista, transiciones))
    except store.StoreError as error:
        print(f"⛔ {error}")
        return 1
    return 0
