"""Comandos `toolkit flush` — RF-15 (§15)."""

from __future__ import annotations

import pathlib

from cli.commands import plan as mod_plan
from cli.commands import specify as mod_specify
from cli.commands import tasks as mod_tasks
from core.checkpoints import listar as listar_checkpoints
from core.flush import (
    FlushError,
    fijar_umbral,
    generar_pack,
    medir,
)
from core.journal import historial, registrar
from core.recover import diagnosticar, formatear
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        if args.umbral is not None:
            valor = fijar_umbral(raiz, args.umbral)
            print(f"Umbral de saturación: {valor} tokens (configurable, §15).")
            if args.texto is None:
                return 0
        if args.texto is None:
            print("⛔ indique el PLAN-ID")
            return 1
        plan = mod_plan._cargar_plan(raiz, args.texto)
        spec = mod_specify._cargar_spec(raiz, plan.spec_id)
        _info, tareas = mod_tasks._cargar_tareas(raiz, plan.plan_id)
        eventos = historial(raiz, plan.plan_id)
        puntos = listar_checkpoints(raiz, plan.plan_id)
        medicion = medir(raiz, plan.plan_id, eventos, puntos)
        print(f"Contexto estimado: {medicion['tokens_estimados']} tokens "
              f"(umbral {medicion['umbral']}, {medicion['eventos']} eventos, "
              f"{medicion['checkpoints']} checkpoints).")
        if not medicion["saturado"] and not args.force:
            print("Sin saturación: no hace falta renovar (§15.1). "
                  "Use --force para generar el traspaso igualmente.")
            return 0
        hechas = {e.get("tarea") for e in eventos
                  if e.get("evento") == "completada"}
        activa = next((t for t in tareas if t.id not in hechas), None)
        motivo = args.motivo or ("saturación detectada"
                                 if medicion["saturado"] else "traspaso manual")
        ruta, _pack = generar_pack(raiz, plan.plan_id, spec, activa, tareas,
                                   eventos, motivo)
        if activa is not None:
            registrar(raiz, plan.plan_id,
                      {"tarea": activa.id, "evento": "flush",
                       "nota": f"traspaso en {ruta.name}"})
        print(f"📦 Traspaso escrito en {ruta.relative_to(raiz)} "
              "(nada fue borrado, §15).")
        try:
            spec_d = {"funcionales": spec.funcionales}
            print(formatear(diagnosticar(raiz, plan.plan_id, spec_d, tareas)))
        except (store.StoreError, FlushError) as error:
            print(f"⚠️ verificación posterior incompleta: {error}")
    except (FlushError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0
