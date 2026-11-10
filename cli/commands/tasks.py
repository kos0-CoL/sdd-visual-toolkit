"""Comandos `toolkit tasks` — RF-06 (§9)."""

from __future__ import annotations

import pathlib

from cli.commands import plan as mod_plan
from cli.commands import specify as mod_specify
from core.plan import PlanError
from core.tasks import Tarea, TasksError, generar_desde_plan, render_markdown, verificar_gate3
from state import store

TAREAS_DIR = "tareas"
TAREAS_INDEX = "tareas.json"


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def _indice(raiz) -> dict:
    ruta = raiz / store.SPECIFY_DIR / TAREAS_INDEX
    if not ruta.exists():
        return {}
    datos = store.leer_json(ruta)
    if not isinstance(datos, dict):
        raise TasksError("el índice de tareas está corrupto")
    return datos


def _guardar_indice(raiz, indice: dict) -> None:
    store.escribir_json(raiz / store.SPECIFY_DIR / TAREAS_INDEX, indice)


def _cargar_tareas(raiz, plan_id: str) -> tuple[dict, list[Tarea]]:
    indice = _indice(raiz)
    if plan_id not in indice:
        raise TasksError(f"sin tareas para {plan_id}; ejecute `tasks {plan_id}`")
    ruta = raiz / indice[plan_id]["archivo"]
    datos = store.leer_json(ruta.with_suffix(".json"))
    return indice[plan_id], [Tarea.from_dict(t) for t in datos["tareas"]]


def _persistir(raiz, plan_id: str, spec_id: str, tareas: list[Tarea]) -> pathlib.Path:
    ruta_md = raiz / store.SPECIFY_DIR / TAREAS_DIR / f"TASKS-{plan_id}.md"
    ruta_md.parent.mkdir(parents=True, exist_ok=True)
    ruta_md.write_text(render_markdown(tareas, plan_id, spec_id) + "\n", encoding="utf-8")
    store.escribir_json(ruta_md.with_suffix(".json"),
                        {"plan_id": plan_id, "spec_id": spec_id,
                         "tareas": [t.to_dict() for t in tareas]})
    return ruta_md


def cmd_tasks(args) -> int:
    raiz = _raiz(args)
    try:
        plan = mod_plan._cargar_plan(raiz, args.texto)
        if plan.status != "validado":
            raise TasksError(
                f"{plan.plan_id} no está validado; ejecute `plan --gate {plan.plan_id}`"
            )
        indice = _indice(raiz)
        if args.texto in indice and not args.force:
            raise TasksError(
                f"ya existen tareas para {args.texto}; regenere con --force"
            )
        existentes = sum(len(v["tareas"]) for v in indice.values())
        spec = mod_specify._cargar_spec(raiz, plan.spec_id)
        tareas = generar_desde_plan(plan, spec, inicio=existentes + 1)
        ruta = _persistir(raiz, plan.plan_id, spec.spec_id, tareas)
        indice[plan.plan_id] = {
            "plan_id": plan.plan_id, "spec_id": spec.spec_id,
            "archivo": str(ruta.relative_to(raiz)),
            "tareas": [t.id for t in tareas],
        }
        _guardar_indice(raiz, indice)
    except (TasksError, PlanError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    print(f"🧩 {len(tareas)} tareas derivadas de {plan.plan_id} "
          f"({tareas[0].id}…{tareas[-1].id}), cadena secuencial explícita.")
    print("\n🟢 FASE COMPLETADA: TASKS")
    print(f"Archivo generado: {ruta.relative_to(raiz)} (+ JSON máquina)")
    print("Validaciones: 1 paso → 1 tarea; toda tarea cita SPEC, archivos y pruebas.")
    print("Estado persistido: sí.")
    print("¿Qué desea hacer ahora?")
    print(f"[ tasks --show {tareas[0].id} ]  [ tasks --gate {plan.plan_id} ]")
    return 0


def cmd_tasks_list(args) -> int:
    raiz = _raiz(args)
    if args.list == "all":
        for plan_id, info in _indice(raiz).items():
            print(f"{plan_id}: {', '.join(info['tareas'])}")
        return 0
    try:
        _info, tareas = _cargar_tareas(raiz, args.list)
    except (TasksError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    for t in tareas:
        marca = {"pendiente": "○"}.get(t.estado, "•")
        print(f"{marca} {t.id} [deps: {', '.join(t.dependencias) or '—'}] {t.descripcion}")
    return 0


def cmd_tasks_show(args) -> int:
    raiz = _raiz(args)
    try:
        for plan_id in _indice(raiz):
            _info, tareas = _cargar_tareas(raiz, plan_id)
            for t in tareas:
                if t.id == args.show:
                    print(f"## {t.id} — {t.descripcion}")
                    print(f"Objetivo: {t.objetivo}")
                    print(f"Archivos: {', '.join(t.archivos)}")
                    print(f"Dependencias: {', '.join(t.dependencias) or 'ninguna'}")
                    print(f"Resultado: {t.resultado}")
                    print(f"Criterio: {t.criterio}")
                    print(f"Pruebas: {', '.join(t.pruebas)}")
                    print(f"Estado: {t.estado} | Intentos: {t.intentos}")
                    return 0
        print(f"⛔ tarea inexistente: {args.show}")
        return 1
    except (TasksError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1


def cmd_tasks_gate(args) -> int:
    raiz = _raiz(args)
    try:
        _info, tareas = _cargar_tareas(raiz, args.gate)
        problemas = verificar_gate3(tareas)
    except (TasksError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    if problemas:
        print(f"🔴 QUALITY GATE 3: BLOQUEADO — {args.gate}")
        for problema in problemas:
            print(f"   • {problema}")
        return 1
    print(f"🟢 QUALITY GATE 3: SUPERADO — {len(tareas)} tareas verificables, "
          f"dependencias resueltas, {args.gate} listo para implementar.")
    return 0


def despachar(args) -> int:
    if args.list is not None:
        return cmd_tasks_list(args)
    if args.show:
        return cmd_tasks_show(args)
    if args.gate:
        return cmd_tasks_gate(args)
    if not args.texto:
        print("⛔ indique el PLAN-ID o use --list/--show/--gate")
        return 1
    return cmd_tasks(args)
