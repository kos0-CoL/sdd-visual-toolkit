"""Comandos `toolkit diff` — RF-34 (§24).

Compara el snapshot previo de la tarea contra el árbol actual:
vista estructural (AST) + vista comparativa (diff) + cambios fuera
de alcance + resultado de validación (por qué se acepta o rechaza).
"""

from __future__ import annotations

import pathlib

from cli.commands import context as mod_context
from cli.commands import plan as mod_plan
from cli.commands import specify as mod_specify
from core.diffview import (analizar_fuente, comparativa,
                           comparar_estructural, fuera_de_alcance, vista)
from core.context import ContextError
from core.journal import historial
from core.plan import PlanError
from core.pin import _cargar_pin
from core.spec import SpecError
from core.validate import validar
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def _leer(ruta: pathlib.Path) -> str | None:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _snapshots(raiz, task_id: str) -> list[int]:
    base = raiz / store.SPECIFY_DIR / "snapshots" / task_id
    if not base.is_dir():
        return []
    return sorted(int(p.name) for p in base.iterdir()
                  if p.name.isdigit() and p.is_dir())


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        if not args.texto:
            print("⛔ indique el TASK-ID")
            return 1
        plan, tarea = mod_context._localizar(raiz, args.texto)
        spec = mod_specify._cargar_spec(raiz, plan.spec_id)
        nums = _snapshots(raiz, tarea.id)
        numero = args.n if args.n is not None else (0 if 0 in nums else None)
        if numero is None or numero not in nums:
            print("⛔ %s sin snapshot previo "
                  "(se toman al poner la tarea en curso)" % tarea.id)
            return 1
        snap = raiz / store.SPECIFY_DIR / "snapshots" / tarea.id / str(numero)
        print("🔍 Diff %s: snapshot %d ↔ árbol actual." % (tarea.id, numero))
        for rel in sorted(set(tarea.archivos)):
            antes = _leer(snap / rel)
            despues = _leer(raiz / rel)
            if antes is None and despues is None:
                print(vista(rel, "inexistente en ambos", {}, [],
                            sin_antes=True))
                continue
            if antes is None:
                estado = "nuevo en la tarea"
            elif despues is None:
                estado = "eliminado de la tarea"
            elif antes == despues:
                estado = "sin cambios"
            else:
                estado = "modificado"
            est = comparar_estructural(
                analizar_fuente(antes or ""),
                analizar_fuente(despues or ""))
            diff = (comparativa(antes or "", despues or "", rel)
                    if antes != despues else [])
            print(vista(rel, estado, est, diff, sin_antes=antes is None))
        resultado = validar(raiz, tarea, plan, spec,
                            historial(raiz, plan.plan_id))
        pin = _cargar_pin(raiz, tarea.id) or {}
        arbol = set((pin.get("baseline") or {}).get("__arbol__", {}).keys()
                    if isinstance((pin.get("baseline") or {}).get("__arbol__"),
                                 dict)
                    else [])
        actuales = set()
        for carpeta in ("src", "tests"):
            base = raiz / carpeta
            if base.is_dir():
                actuales.update(
                    str(p.relative_to(raiz))
                    for p in base.rglob("*.py") if p.is_file())
        if arbol:
            fuera = fuera_de_alcance(arbol, actuales, set(tarea.archivos))
            if fuera:
                print("⚠️ Cambios fuera de alcance (%d): %s." % (
                    len(fuera), ", ".join(fuera)))
            else:
                print("✅ Sin cambios fuera de alcance.")
        else:
            print("(sin línea base: alcance no verificable)")
        print("Validación: %s (%d rechazo(s), %d observación(es))." % (
            resultado.get("veredicto", "?"),
            len(resultado.get("rechazos", [])),
            len(resultado.get("observaciones", []))))
        for r in resultado.get("rechazos", [])[:5]:
            print("   🔴 %s" % r)
        for o in resultado.get("observaciones", [])[:5]:
            print("   🟡 %s" % o)
    except (ContextError, PlanError, SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0
