"""Comandos `toolkit build` — RF-09 (§11)."""

from __future__ import annotations

import pathlib

from cli.commands import analyze as mod_analyze
from cli.commands import plan as mod_plan
from cli.commands import specify as mod_specify
from cli.commands import pin as mod_pin
from cli.commands import tasks as mod_tasks
from core import hooks as mod_hooks
from core import rollback as mod_rb
from core.checkpoints import guardar as guardar_checkpoint
from core.validate import validar
from core.journal import (
    actualizar_estado,
    checkpoint,
    estado_inicial,
    historial,
    leer_estado,
    nuevo_run_id,
    registrar,
)
from core.plan import PlanError
from core.build import (
    COMPLETADA,
    BuildError,
    ejecutar_pruebas,
    en_curso,
    marcar_en_curso,
    registrar_done,
    registrar_fail,
    siguiente_tarea,
    tarjeta_pin,
)
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def _exigir_gate4(raiz, plan_id: str) -> None:
    # Un plan que no existe no tiene informe pendiente: decirlo así evita
    # mandar a `analyze` con un ID que tampoco existe.
    if plan_id not in mod_plan._indice(raiz):
        raise PlanError(f"plan inexistente: {plan_id}")
    try:
        informe = mod_analyze._indice(raiz).get(plan_id)
    except store.StoreError as error:
        raise BuildError(str(error)) from error
    if informe is None:
        raise BuildError(
            f"sin informe para {plan_id}; ejecute `analyze {plan_id}` primero")
    if informe["criticas"]:
        raise BuildError(
            f"Quality Gate 4 bloqueado: {informe['criticas']} crítica(s); "
            f"resuélvalas antes de implementar (§10.4)")


def _cargar_todo(raiz, plan_id: str):
    plan = mod_plan._cargar_plan(raiz, plan_id)
    spec = mod_specify._cargar_spec(raiz, plan.spec_id)
    info, tareas = mod_tasks._cargar_tareas(raiz, plan_id)
    return plan, spec, info, tareas


def _guardar(raiz, plan_id: str, spec_id: str, tareas) -> None:
    mod_tasks._persistir(raiz, plan_id, spec_id, tareas)


def _sincronizar_estado(raiz, plan, spec, tareas) -> None:
    """El estado actual siempre refleja tareas + historial (§13.3)."""
    eventos = historial(raiz, plan.plan_id)
    hechas = [i for i, t in enumerate(tareas) if t.estado == COMPLETADA]
    activa = en_curso(tareas)
    racha_fallos = 0
    for e in reversed(eventos):
        if e.get("evento") == "fallida":
            racha_fallos += 1
        elif e.get("evento") == "completada":
            break
    checks = [e for e in eventos if e.get("evento") == "checkpoint"]
    previo = leer_estado(raiz)
    run_id = previo["run_id"] if previo and previo.get("plan_id") == plan.plan_id else nuevo_run_id()
    actualizar_estado(raiz, {
        **estado_inicial(plan.plan_id, spec.spec_id, len(tareas), run_id),
        "ultimo_exito_indice": max(hechas, default=-1),
        "tarea_en_curso": (
            {"id": activa.id, "descripcion": activa.descripcion,
             "target_files": activa.archivos, "status": "in_progress"}
            if activa is not None else None),
        "fallos_consecutivos": racha_fallos,
        "ultimo_checkpoint": (f"{checks[-1]['tarea']}-SUCCESS"
                                if checks else None),
    })


def _disparar_hooks(raiz, plan_id: str, tarea_id: str, evento: str,
                    resultado: str) -> None:
    """RF-42: ganchos del usuario/IDE. Fallar se declara, no bloquea."""
    for r in mod_hooks.disparar(raiz, evento,
                                {"plan": plan_id, "tarea": tarea_id,
                                 "resultado": resultado}):
        print("🪝 hook %s: %s" % (
            r["hook"], "ok" if r["ok"] else "FALLÓ (código %s)" % r["codigo"]))
        if r["salida"]:
            print("   %s" % r["salida"])
        registrar(raiz, plan_id,
                  {"tarea": tarea_id, "evento": "hook",
                   "nota": "%s/%s: %s" % (
                       evento, r["hook"],
                       "ok" if r["ok"] else "falló: %s" % r["salida"][:300])})


def cmd_build_avanzar(args) -> int:
    raiz = _raiz(args)
    try:
        _exigir_gate4(raiz, args.texto)
        plan, spec, _info, tareas = _cargar_todo(raiz, args.texto)
        hechas = sum(1 for t in tareas if t.estado == COMPLETADA)
        print(f"🏗️ {plan.plan_id}: {hechas}/{len(tareas)} completadas.")
        activa = en_curso(tareas)
        if activa is not None:
            print(f"En curso: {activa.id} — {activa.descripcion}")
            print("Use `--done/--fail " + activa.id + "` para registrar su situación "
                  "(§11.3: no se avanza sin registrar).")
            print(tarjeta_pin(activa, spec))
            return 0
        siguiente = siguiente_tarea(tareas)
        if siguiente is None:
            if hechas == len(tareas):
                print("✅ Todas las tareas completadas.")
                return 0
            print("⛔ sin tarea disponible (revise dependencias y fallidas con --list).")
            return 1
        marcar_en_curso(siguiente, tareas)
        mod_rb.tomar(raiz, siguiente)  # §16: estado seguro antes de tocar
        mod_pin.asegurar_baseline(raiz, siguiente)  # §12: línea base al iniciar
        _guardar(raiz, plan.plan_id, spec.spec_id, tareas)
        registrar(raiz, plan.plan_id,
                  {"tarea": siguiente.id, "evento": "en_curso"})
        _disparar_hooks(raiz, plan.plan_id, siguiente.id,
                        "tarea_abierta", "en_curso")
        _sincronizar_estado(raiz, plan, spec, tareas)
        print(tarjeta_pin(siguiente, spec))
        print(f"\n▶ {siguiente.id} en curso. Implemente, luego "
              f"`build {plan.plan_id} --done {siguiente.id}`.")
    except (BuildError, PlanError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0


def cmd_build_done(args) -> int:
    raiz = _raiz(args)
    try:
        _exigir_gate4(raiz, args.texto)
        plan, spec, _info, tareas = _cargar_todo(raiz, args.texto)
        tarea = next((t for t in tareas if t.id == args.done), None)
        if tarea is None:
            raise BuildError(f"tarea inexistente: {args.done}")
        eventos = historial(raiz, plan.plan_id)
        reporte = validar(raiz, tarea, plan, spec,  # RF-18: puerta unificada
                          eventos, nota=args.nota or "")
        if reporte["veredicto"] != "VALIDADO":
            raise BuildError(reporte["resumen"])
        if reporte["observaciones"]:
            print(reporte["resumen"])
        # RF-27 §18.5: el cierre cita la última corrida (evidencia).
        ult_tests = next((e for e in reversed(eventos)
                          if e.get("evento") == "tests"
                          and e.get("tarea") == tarea.id), None)
        evidencia = None
        if ult_tests is not None:
            evidencia = {
                k: ult_tests.get(k)
                for k in ("fecha", "pruebas", "pruebas_ok", "total",
                          "pasadas", "fallidas", "omitidas",
                          "duracion_s", "cobertura_pct")}
        from core.pin import asegurar_baseline  # noqa: PLC0415
        from core.testguard import verificar as vigilar  # noqa: PLC0415
        linea, _parcial = asegurar_baseline(raiz, tarea)
        vigilancia = vigilar(raiz, tarea, linea, eventos,
                             args.nota or "")
        evento = registrar_done(tarea, tareas, raiz, nota=args.nota or "",
                                evidencia=evidencia,
                                vigilancia=vigilancia)
        _guardar(raiz, plan.plan_id, spec.spec_id, tareas)
        registrar(raiz, plan.plan_id, evento)
        _disparar_hooks(raiz, plan.plan_id, tarea.id,
                        "tarea_cerrada", evento["evento"])
        if evento["evento"] == "completada":
            resto = siguiente_tarea(tareas)
            cp = checkpoint(raiz, plan.plan_id, spec.spec_id, tarea,
                            resto.id if resto else None,
                            evento["pruebas"], evento["pruebas_ok"],
                            args.nota or "")
            guardar_checkpoint(raiz, plan.plan_id, cp)  # RF-12: artefacto durable
        _sincronizar_estado(raiz, plan, spec, tareas)
    except (BuildError, PlanError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    if evento["evento"] == "completada":
        print(f"✅ {tarea.id} completada (intento {tarea.intentos}). {evento['pruebas']}")
    else:
        print(f"❌ {tarea.id} marcada fallida: pruebas no pasan. {evento['pruebas']}")
        print("Corrija y vuelva a intentarlo; el fallo queda registrado (§46.13).")
    return 0


def cmd_build_fail(args) -> int:
    raiz = _raiz(args)
    try:
        _exigir_gate4(raiz, args.texto)
        plan, spec, _info, tareas = _cargar_todo(raiz, args.texto)
        tarea = next((t for t in tareas if t.id == args.fail), None)
        if tarea is None:
            raise BuildError(f"tarea inexistente: {args.fail}")
        evento = registrar_fail(tarea, args.nota or "")
        _guardar(raiz, plan.plan_id, spec.spec_id, tareas)
        registrar(raiz, plan.plan_id, evento)
        _disparar_hooks(raiz, plan.plan_id, tarea.id,
                        "tarea_cerrada", "fallida")
        freno = mod_rb.debe_frenar(historial(raiz, plan.plan_id), tarea.id)
        if freno is not None:
            carpeta = mod_rb.restaurar(raiz, tarea.id)
            mod_rb.prohibir(raiz, tarea.id, freno["firma"], tarea.intentos)
            registrar(raiz, plan.plan_id,
                      {"tarea": tarea.id, "evento": "rollback",
                       "nota": f"misma firma 2 veces ({freno['firma']}): "
                                f"restaurado desde {carpeta.name}; "
                                "proponga una solución diferente (§16)"})
            print(f"🛑 {tarea.id} detenida: el mismo error se repitió. "
                  f"Archivos restaurados ({carpeta.name}), estrategia "
                  "registrada como prohibida. Reinicie con otra solución.")
        _sincronizar_estado(raiz, plan, spec, tareas)
    except (BuildError, PlanError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    print(f"📝 {tarea.id} fallida registrada (intento {tarea.intentos}): {args.nota}")
    return 0


def despachar(args) -> int:
    if args.done:
        return cmd_build_done(args)
    if args.fail:
        return cmd_build_fail(args)
    if not args.texto:
        print("⛔ indique el PLAN-ID o use --done/--fail")
        return 1
    return cmd_build_avanzar(args)
