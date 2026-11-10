"""Comandos `toolkit plan` — RF-05 (§8)."""

from __future__ import annotations

import pathlib

from cli.commands import clarify as mod_clarify
from cli.commands import enrich as mod_enrich
from cli.commands import specify as mod_specify
from core.clarify import pendientes
from core.plan import PlanError, generar_desde_spec, investigar, render_markdown
from state import store

PLANES_DIR = "planes"
PLANES_INDEX = "planes.json"


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def _indice(raiz) -> dict:
    ruta = raiz / store.SPECIFY_DIR / PLANES_INDEX
    if not ruta.exists():
        return {}
    datos = store.leer_json(ruta)
    if not isinstance(datos, dict):
        raise PlanError("el índice de planes está corrupto")
    return datos


def _guardar_indice(raiz, indice: dict) -> None:
    store.escribir_json(raiz / store.SPECIFY_DIR / PLANES_INDEX, indice)


def _cargar_plan(raiz, plan_id: str) -> object:
    indice = _indice(raiz)
    if plan_id not in indice:
        raise PlanError(f"plan inexistente: {plan_id}")
    from core.plan import Plan  # noqa: PLC0415

    ruta = raiz / indice[plan_id]["archivo"]
    return Plan.from_dict(store.leer_json(ruta.with_suffix(".json")))


def _exigir_gate1(raiz, spec_id: str) -> tuple[object, list]:
    """Sin clarify superado no hay plan (§26: no avanzar sin condiciones)."""
    try:
        todo = mod_clarify._cargar_todo(raiz)
    except Exception as error:
        raise PlanError(
            f"{spec_id} no pasó por clarify; ejecute `clarify {spec_id}` primero"
        ) from error
    if spec_id not in todo:
        raise PlanError(
            f"{spec_id} no pasó por clarify; ejecute `clarify {spec_id}` primero"
        )
    preguntas, historial = mod_clarify._preguntas_de(raiz, spec_id)
    resto = pendientes(preguntas)
    if resto:
        raise PlanError(
            f"Quality Gate 1 bloqueado: {len(resto)} pregunta(s) pendientes en "
            f"{spec_id}; complete `clarify {spec_id}` primero"
        )
    spec = mod_specify._cargar_spec(raiz, spec_id)
    return spec, historial


def _persistir(raiz, plan: object) -> pathlib.Path:
    ruta_md = raiz / store.SPECIFY_DIR / PLANES_DIR / f"{plan.plan_id}.md"
    ruta_md.parent.mkdir(parents=True, exist_ok=True)
    ruta_md.write_text(render_markdown(plan) + "\n", encoding="utf-8")
    store.escribir_json(ruta_md.with_suffix(".json"), plan.to_dict())
    return ruta_md


def mostrar_resumen(plan: object) -> None:
    print(f"📐 PLAN {plan.plan_id} v{plan.version} [{plan.status}] → {plan.spec_id}")
    print(f"  pasos: {len(plan.orden)} | riesgos: {len(plan.riesgos)} | "
          f"validación: {len(plan.validacion)} criterios")
    print(f"  greenfield: {plan.hallazgos.get('es_greenfield')} | "
          f"archivos analizados: {plan.hallazgos.get('total_archivos')}")


def cmd_plan(args) -> int:
    raiz = _raiz(args)
    try:
        spec, historial = _exigir_gate1(raiz, args.texto)
        indice = _indice(raiz)
        plan_id = f"PLAN-{spec.spec_id.split('-')[1]}"
        if plan_id in indice and not args.force:
            raise PlanError(
                f"{plan_id} ya existe; regenere con --force "
                "(la versión anterior se conserva en el historial)"
            )
        hallazgos = investigar(raiz)  # el proyecto real donde se implementará
        plan = generar_desde_spec(spec, hallazgos, historial, plan_id)
        ruta = _persistir(raiz, plan)
        indice[plan_id] = {
            "plan_id": plan_id, "spec_id": spec.spec_id,
            "archivo": str(ruta.relative_to(raiz)),
            "version": plan.version, "status": plan.status,
            "created_at": plan.created_at, "updated_at": plan.updated_at,
        }
        _guardar_indice(raiz, indice)
    except (PlanError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    mostrar_resumen(plan)
    print("\n🟢 FASE COMPLETADA: PLAN")
    print(f"Archivo generado: {ruta.relative_to(raiz)} (+ JSON máquina)")
    print("Validaciones: investiga el repo real; cada paso cita su REQ; "
          "alternativas marcadas como NO aprobadas (§8.6).")
    print("Estado persistido: sí.")
    print("¿Qué desea hacer ahora?")
    print(f"[ plan --show {plan_id} ]  [ plan --gate {plan_id} ]")
    return 0


def cmd_plan_list(args) -> int:
    for plan_id, info in _indice(_raiz(args)).items():
        print(f"{plan_id} v{info['version']} [{info['status']}] → {info['spec_id']}")
    return 0


def cmd_plan_show(args) -> int:
    try:
        mostrar_resumen(_cargar_plan(_raiz(args), args.show))
    except (PlanError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0


def cmd_plan_gate(args) -> int:
    raiz = _raiz(args)
    try:
        plan = _cargar_plan(raiz, args.gate)
        spec = mod_specify._cargar_spec(raiz, plan.spec_id)
        faltantes = plan.cobertura_funcional(spec)
        problemas = []
        if faltantes:
            problemas.append(f"funcionales aceptados sin paso: {', '.join(faltantes)}")
        if not plan.hallazgos.get("total_archivos") and not plan.hallazgos.get(
            "es_greenfield"
        ):
            problemas.append("investigación vacía: el plan no responde al repo real")
        sin_traza = [p.id for p in plan.orden if not p.refs]
        if sin_traza:
            problemas.append(f"pasos sin trazabilidad: {', '.join(sin_traza)}")
        if problemas:
            print(f"🔴 QUALITY GATE 2: BLOQUEADO — {plan.plan_id}")
            for problema in problemas:
                print(f"   • {problema}")
            return 1
        from core.plan import Plan as _Plan  # noqa: PLC0415
        if isinstance(plan, _Plan) and plan.status != "validado":
            plan.status = "validado"
            _persistir(raiz, plan)
            indice = _indice(raiz)
            indice[plan.plan_id]["status"] = "validado"
            _guardar_indice(raiz, indice)
    except (PlanError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    print(f"🟢 QUALITY GATE 2: SUPERADO — {plan.plan_id} responde a "
          f"{plan.spec_id} y al repo real. Sin funcionalidad inventada (§8.6).")
    return 0


def despachar(args) -> int:
    if args.list:
        return cmd_plan_list(args)
    if args.show:
        return cmd_plan_show(args)
    if args.gate:
        return cmd_plan_gate(args)
    if not args.texto:
        print("⛔ indique la SPEC-ID o use --list/--show/--gate")
        return 1
    return cmd_plan(args)
