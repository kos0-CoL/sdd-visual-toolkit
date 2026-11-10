"""Comandos `toolkit test` — RF-19 (§18)."""

from __future__ import annotations

import pathlib

from cli.commands.context import _localizar
from cli.commands.specify import _cargar_spec
from core.harness import HarnessError, ejecutar_ciclo
from core.journal import historial, registrar
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def despachar(args) -> int:
    if not args.texto:
        print("⛔ indique el TASK-ID")
        return 1
    raiz = _raiz(args)
    try:
        plan, tarea = _localizar(raiz, args.texto)
        try:
            spec = _cargar_spec(raiz, plan.spec_id)
        except store.StoreError:
            spec = None
        solo = tuple(args.fase) if args.fase else None
        resultado = ejecutar_ciclo(raiz, tarea, spec, solo=solo)
        print(resultado["resumen"])
        anterior = [e for e in historial(raiz, plan.plan_id)
                    if e.get("tarea") == tarea.id and e.get("evento") == "tests"]
        if anterior:
            ult = anterior[-1]
            print(f"Comparación con corrida anterior: "
                  f"pasadas {ult.get('pasadas', '?')} → "
                  f"{sum(c['pasadas'] for c in resultado['capas'])}; "
                  f"fallidas {ult.get('fallidas', '?')} → "
                  f"{sum(c['fallidas'] for c in resultado['capas'])}.")
        totales = {k: sum(c[k] for c in resultado["capas"]
                          if c["fase"] not in ("estructural", "cobertura"))
                   for k in ("total", "pasadas", "fallidas", "omitidas")}
        # RF-26: duración agregada + cobertura quedan en el historial.
        cob = next((c for c in resultado["capas"]
                    if c["fase"] == "cobertura"), None)
        cobertura_pct = (round(100.0 * cob["pasadas"] / cob["total"])
                         if cob is not None and cob["total"] else None)
        registrar(raiz, plan.plan_id,
                  {"tarea": tarea.id, "evento": "tests",
                   "pruebas": resultado["resumen"].splitlines()[0],
                   "pruebas_ok": resultado["ok"],
                   "hashes_tests": resultado["hashes_tests"],
                   "duracion_s": round(sum(c["duracion_s"]
                                             for c in resultado["capas"]), 3),
                   "cobertura_pct": cobertura_pct, **totales})
        return 0 if resultado["ok"] else 1
    except (HarnessError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0
