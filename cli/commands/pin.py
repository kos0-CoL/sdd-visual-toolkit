"""Comandos `toolkit pin` — RF-10 (§11.1, §12)."""

from __future__ import annotations

import pathlib

from cli.commands import clarify as mod_clarify
from cli.commands import plan as mod_plan
from cli.commands import specify as mod_specify
from cli.commands import tasks as mod_tasks
from core.pin import (
    Desviacion,
    PinError,
    asegurar_baseline,
    chequear,
    decisiones_aprobadas,
    generar_pin,
)
from core.plan import PlanError
from core.spec import SpecError
from core.tasks import TasksError
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def cmd_pin(args) -> int:
    raiz = _raiz(args)
    try:
        plan = mod_plan._cargar_plan(raiz, args.texto)
        spec = mod_specify._cargar_spec(raiz, plan.spec_id)
        _info, tareas = mod_tasks._cargar_tareas(raiz, plan.plan_id)
        tarea = next((t for t in tareas if t.id == args.task), None)
        if tarea is None:
            print(f"⛔ tarea inexistente: {args.task}")
            return 1
        _preguntas, historial = mod_clarify._preguntas_de(raiz, spec.spec_id)
        baseline, _parcial = asegurar_baseline(raiz, tarea)
        print(generar_pin(plan, spec, tarea, decisiones_aprobadas(historial)))
        print(f"\nLínea base registrada: {len(baseline) - 1} archivo(s) autorizados "
              f"+ foto del árbol (§12: toda desviación futura será visible).")
    except (PinError, PlanError, SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0


def cmd_pin_check(args) -> int:
    raiz = _raiz(args)
    try:
        tarea = None
        for plan_id in mod_plan._indice(raiz):
            _info, tareas = mod_tasks._cargar_tareas(raiz, plan_id)
            tarea = next((t for t in tareas if t.id == args.check), None)
            if tarea is not None:
                break
        if tarea is None:
            print(f"⛔ tarea inexistente: {args.check}")
            return 1
        desvs, parcial = chequear(raiz, tarea)
    except (PlanError, TasksError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    if parcial:
        print("⚠️ sin línea base previa: verificación parcial (foto actual registrada).")
    if not desvs:
        print(f"✅ {tarea.id} sin desviaciones: cambios trazables a la tarea (§12.A).")
        return 0
    for d in desvs:
        marca = "🔴" if d.clase == "C" else "🟡"
        print(f"{marca} [{d.clase}] {d.archivo}: {d.detalle}")
    if any(d.clase == "C" for d in desvs):
        print("⛔ cambio ajeno: exclúyalo de esta implementación y registre la idea "
              "con `pin --suggest \"...\"` (§12.C).")
        return 1
    print("🟡 cambios técnicos: documéntelos con --nota al completar (§12.B).")
    return 0


def cmd_pin_suggest(args) -> int:
    raiz = _raiz(args)
    try:
        ruta = raiz / store.SPECIFY_DIR / "sugerencias.json"
        datos = store.leer_json(ruta) if ruta.exists() else []
        if not isinstance(datos, list):
            raise PinError("el registro de sugerencias está corrupto")
        from core.build import _ahora  # noqa: PLC0415
        datos.append({"fecha": _ahora(), "idea": args.suggest,
                      "origen": "pin (§12.C, excluida de la implementación actual)"})
        store.escribir_json(ruta, datos)
    except (PinError, PlanError, SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    print(f"💡 Sugerencia registrada (no implementada): {args.suggest}")
    return 0


def despachar(args) -> int:
    if args.suggest:
        return cmd_pin_suggest(args)
    if args.check:
        return cmd_pin_check(args)
    if not args.texto or not args.task:
        print("⛔ indique PLAN-ID y --task, o use --check/--suggest")
        return 1
    return cmd_pin(args)
