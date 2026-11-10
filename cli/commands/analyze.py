"""Comandos `toolkit analyze` — RF-07 (§10)."""

from __future__ import annotations

import pathlib

from cli.commands import plan as mod_plan
from cli.commands import specify as mod_specify
from cli.commands import tasks as mod_tasks
from core.analyze import AnalyzeError, analizar, render_markdown
from core.plan import PlanError
from core.tasks import TasksError
from state import store

INFORMES_DIR = "informes"
INFORMES_INDEX = "informes.json"


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def _indice(raiz) -> dict:
    ruta = raiz / store.SPECIFY_DIR / INFORMES_INDEX
    if not ruta.exists():
        return {}
    datos = store.leer_json(ruta)
    if not isinstance(datos, dict):
        raise AnalyzeError("el índice de informes está corrupto")
    return datos


def _guardar_indice(raiz, indice: dict) -> None:
    store.escribir_json(raiz / store.SPECIFY_DIR / INFORMES_INDEX, indice)


def cmd_analyze(args) -> int:
    raiz = _raiz(args)
    try:
        plan = mod_plan._cargar_plan(raiz, args.texto)
        spec = mod_specify._cargar_spec(raiz, plan.spec_id)
        _info, tareas = mod_tasks._cargar_tareas(raiz, plan.plan_id)
        problemas = analizar(plan, spec, tareas, raiz)
        ruta_md = raiz / store.SPECIFY_DIR / INFORMES_DIR / f"INFORME-{plan.plan_id}.md"
        ruta_md.parent.mkdir(parents=True, exist_ok=True)
        ruta_md.write_text(
            render_markdown(problemas, plan.plan_id, spec.spec_id) + "\n",
            encoding="utf-8")
        store.escribir_json(ruta_md.with_suffix(".json"),
                            {"plan_id": plan.plan_id, "spec_id": spec.spec_id,
                             "problemas": [p.to_dict() for p in problemas]})
        indice = _indice(raiz)
        criticas = sum(1 for p in problemas if p.severidad == "critica")
        indice[plan.plan_id] = {
            "plan_id": plan.plan_id, "spec_id": spec.spec_id,
            "archivo": str(ruta_md.relative_to(raiz)),
            "problemas": len(problemas), "criticas": criticas,
        }
        _guardar_indice(raiz, indice)
    except (AnalyzeError, PlanError, TasksError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    print(f"🔍 Informe {plan.plan_id}: {len(problemas)} hallazgo(s), "
          f"{criticas} crítica(s).")
    print("\n🟢 FASE COMPLETADA: ANALYZE")
    print(f"Archivo generado: {ruta_md.relative_to(raiz)} (+ JSON máquina)")
    print("Validaciones: 9 comprobaciones §10.2 solo con evidencia.")
    print("Estado persistido: sí.")
    print("¿Qué desea hacer ahora?")
    print(f"[ analyze --gate {plan.plan_id} ]")
    return 0


def cmd_analyze_gate(args) -> int:
    raiz = _raiz(args)
    try:
        indice = _indice(raiz)
        if args.gate not in indice:
            print(f"⛔ sin informe para {args.gate}; ejecute `analyze {args.gate}`")
            return 1
        info = indice[args.gate]
    except store.StoreError as error:
        print(f"⛔ {error}")
        return 1
    if info["criticas"]:
        print(f"🔴 QUALITY GATE 4: BLOQUEADO — {info['criticas']} crítica(s) "
              f"en {args.gate}. Resuélvalas y regenere tareas/plan.")
        return 1
    resto = info["problemas"]
    print(f"🟢 QUALITY GATE 4: SUPERADO — {args.gate} sin críticas "
          f"({resto} advertencia(s) registrada(s), §10.4). Implementación habilitada.")
    return 0


def despachar(args) -> int:
    if args.gate:
        return cmd_analyze_gate(args)
    if not args.texto:
        print("⛔ indique el PLAN-ID o use --gate")
        return 1
    return cmd_analyze(args)
