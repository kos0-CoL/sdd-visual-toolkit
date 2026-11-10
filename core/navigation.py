"""RF-35 — Navegación mediante píldoras (§26).

Decisión pura: dada la foto del tablero (artefactos reales), propone
la siguiente fase recomendada, píldoras ejecutables (comandos CLI
equivalentes, no decorativos), vía de retorno, revisión y bloqueos
cuando faltan condiciones obligatorias. No ejecuta nada ni muta
estado; solo orienta. La CLI solo lee.
"""

from __future__ import annotations

import re


def _plan_id_de(estado: dict) -> str | None:
    proxima = str(estado.get("proxima") or "")
    hallado = re.search(r"PLAN-\d+", proxima)
    if hallado:
        return hallado.group(0)
    if estado.get("plan_id"):
        return str(estado["plan_id"])
    return None


def sugerir(estado: dict) -> dict:
    """Píldoras de navegación desde el estado del tablero.

    Devuelve: fase, recomendada {etiqueta, comando}, pills
    [{etiqueta, comando, recomendada, bloqueada, motivo}], bloqueos,
    requiere_aprobacion, nota.
    """
    spec_id = estado.get("spec_id")
    fase = estado.get("fase") or "sin SPEC"
    tarea = estado.get("tarea_actual")
    plan_id = _plan_id_de(estado)
    pendientes = estado.get("pendientes", 0) or 0

    if not spec_id:
        pills = [
            {"etiqueta": "Enriquecer idea", "comando": "enrich «idea»",
             "recomendada": True, "bloqueada": False, "motivo": ""},
            {"etiqueta": "Ver tablero", "comando": "tablero",
             "recomendada": False, "bloqueada": False, "motivo": ""},
        ]
        return {"fase": "sin SPEC", "recomendada": pills[0], "pills": pills,
                "bloqueos": [], "requiere_aprobacion": False,
                "nota": "Sin SPEC todavía: el primer paso es enrich."}

    spec_id = str(spec_id)

    def _pildora(etiqueta: str, comando: str, rec: bool = False,
                 bloqueada: bool = False, motivo: str = "") -> dict:
        return {"etiqueta": etiqueta, "comando": comando,
                "recomendada": rec, "bloqueada": bloqueada, "motivo": motivo}

    # Aclaraciones con pendientes: plan bloqueado (§26: no avanzar).
    if fase.startswith("🔍") and pendientes:
        pills = [
            _pildora("Responder clarify",
                     "clarify %s --answer …" % spec_id, rec=True),
            _pildora("Revisar preguntas",
                     "clarify --list %s" % spec_id),
            _pildora("Revisar SPEC", "specify --show %s" % spec_id),
            _pildora("Avanzar a plan", "plan %s" % spec_id,
                     bloqueada=True,
                     motivo="%d pregunta(s) pendientes" % pendientes),
        ]
        return {"fase": fase, "recomendada": pills[0], "pills": pills,
                "bloqueos": ["Quality Gate 1 bloqueado: %d pregunta(s) "
                             "pendientes en %s" % (pendientes, spec_id)],
                "requiere_aprobacion": True,
                "nota": "Clarify requiere respuestas humanas; "
                        "nada se ejecuta solo."}

    if fase.startswith("📝"):
        pills = [
            _pildora("Continuar con clarify",
                     "clarify %s" % spec_id, rec=True),
            _pildora("Revisar SPEC", "specify --show %s" % spec_id),
            _pildora("Ver tablero", "tablero"),
        ]
        return {"fase": fase, "recomendada": pills[0], "pills": pills,
                "bloqueos": [], "requiere_aprobacion": True,
                "nota": "SPEC generada: revísela o avance a clarify."}

    if fase.startswith("🔍"):
        pills = [
            _pildora("Generar plan", "plan %s" % spec_id, rec=True),
            _pildora("Revisar preguntas",
                     "clarify --list %s" % spec_id),
            _pildora("Volver a SPEC", "specify --show %s" % spec_id),
        ]
        return {"fase": fase, "recomendada": pills[0], "pills": pills,
                "bloqueos": [], "requiere_aprobacion": False,
                "nota": "Clarify superado: el plan puede generarse."}

    if fase.startswith("📐"):
        destino = plan_id or "PLAN-001"
        pills = [
            _pildora("Validar plan", "plan --gate %s" % destino, rec=True),
            _pildora("Revisar plan", "plan --show %s" % destino),
            _pildora("Volver a clarify", "clarify --list %s" % spec_id),
        ]
        if plan_id:
            pills.insert(
                2, _pildora("Desglosar tareas", "tasks %s" % plan_id,
                            bloqueada=True,
                            motivo="requiere Quality Gate 2 superado"))
        return {"fase": fase, "recomendada": pills[0], "pills": pills,
                "bloqueos": ["Quality Gate 2 pendiente: valide el plan "
                             "antes de desglosar tareas"],
                "requiere_aprobacion": True,
                "nota": "El gate del plan requiere validación; "
                        "no se avanza solo."}

    if fase.startswith("💾"):
        destino = plan_id or "PLAN-001"
        pills = [
            _pildora("Empezar implementación", "build %s" % destino,
                     rec=True),
            _pildora("Revisar consistencia", "analyze %s" % destino),
            _pildora("Revisar tareas", "tasks --list %s" % destino),
            _pildora("Volver al plan", "plan --show %s" % destino),
        ]
        return {"fase": fase, "recomendada": pills[0], "pills": pills,
                "bloqueos": [], "requiere_aprobacion": False,
                "nota": "Tareas listas: la implementación avanza por build."}

    if fase.startswith("⚡"):
        destino = tarea or (plan_id or "PLAN-001")
        pills = [
            _pildora("Correr pruebas",
                     "test %s" % destino if tarea else "build %s" % destino,
                     rec=True),
            _pildora("Ver diff estructural",
                     "diff %s" % tarea if tarea else "arbol"),
            _pildora("Validar cambios",
                     "validate %s" % tarea if tarea else "tablero"),
            _pildora("Volver a tareas",
                     "tasks --list %s" % plan_id if plan_id else "arbol"),
        ]
        return {"fase": fase, "recomendada": pills[0], "pills": pills,
                "bloqueos": [], "requiere_aprobacion": False,
                "nota": "Implementación en curso: pruebe antes de cerrar."}

    if fase.startswith("🧪"):
        destino = estado.get("pruebas_tarea") or tarea or "TASK-001"
        proxima = str(estado.get("proxima") or "")
        if proxima.startswith("test "):
            destino = proxima.split("test ", 1)[1].strip().split()[0]
        plan = plan_id or "PLAN-001"
        if estado.get("pruebas_ok"):
            # La última corrida fue verde: no hay nada roto que repetir. Si la
            # tarea sigue en curso, se cierra; si ya se cerró, avanza el plan.
            if tarea:
                recomendada = _pildora("Cerrar la tarea",
                                       "build %s --done %s" % (plan, tarea),
                                       rec=True)
                nota = "Pruebas en verde: cierre la tarea para avanzar."
            else:
                recomendada = _pildora("Seguir con la próxima tarea",
                                       "build %s" % plan, rec=True)
                nota = ("Pruebas en verde y sin tarea en curso: "
                        "el plan puede avanzar.")
            # Sin tarea en curso, «volver a build» repetiría la recomendada.
            vuelta = (_pildora("Volver a build",
                               "build %s" % plan_id if plan_id else "tablero")
                      if tarea else
                      _pildora("Ver tareas",
                               "tasks --list %s" % plan if plan_id else "arbol"))
            pills = [
                recomendada,
                _pildora("Ver reporte", "reporte %s" % destino),
                _pildora("Ver diff", "diff %s" % destino),
                vuelta,
            ]
            return {"fase": fase, "recomendada": pills[0], "pills": pills,
                    "bloqueos": [], "requiere_aprobacion": False,
                    "nota": nota}
        pills = [
            _pildora("Repetir pruebas en rojo", "test %s" % destino,
                     rec=True),
            _pildora("Ver reporte", "reporte %s" % destino),
            _pildora("Ver diff", "diff %s" % destino),
            _pildora("Volver a build",
                     "build %s" % plan_id if plan_id else "tablero"),
        ]
        return {"fase": fase, "recomendada": pills[0], "pills": pills,
                "bloqueos": [], "requiere_aprobacion": False,
                "nota": "Pruebas con rojo: corrija y repita el test."}

    if fase.startswith("✅"):
        pills = [
            _pildora("Ver trazabilidad", "traza %s" % spec_id, rec=True),
            _pildora("Ver historial",
                     "historia %s" % tarea if tarea else "tablero"),
            _pildora("Ver tablero", "tablero"),
        ]
        return {"fase": fase, "recomendada": pills[0], "pills": pills,
                "bloqueos": [], "requiere_aprobacion": False,
                "nota": "SPEC completada: puede trazar evidencia o abrir "
                        "una SPEC nueva con specify."}

    # Fase genérica (p.ej. ♻️ Recuperación u otras): orientar sin inventar.
    pills = [
        _pildora("Ver tablero", "tablero", rec=True),
        _pildora("Ver árbol", "arbol"),
    ]
    return {"fase": fase, "recomendada": pills[0], "pills": pills,
            "bloqueos": [], "requiere_aprobacion": False,
            "nota": "Fase %s: revise tablero y árbol antes de avanzar." % fase}


def render(navegacion: dict) -> str:
    """Mensaje §26 + controles §27: qué sigue y cómo ir, sin ejecutar."""
    lineas = ["🧭 Navegación — fase actual: %s." % navegacion.get("fase", "—")]
    rec = navegacion.get("recomendada") or {}
    if rec.get("comando"):
        lineas.append("Recomendada: [ %s ]" % rec["comando"])
    pills = navegacion.get("pills") or []
    if pills:
        lineas.append("¿Qué desea hacer ahora?")
        for p in pills:
            if p.get("bloqueada"):
                lineas.append("[ %s ] 🔒 %s" % (
                    p.get("comando", "—"), p.get("motivo", "bloqueado")))
            elif p.get("recomendada"):
                lineas.append("[ %s ] ★ %s" % (
                    p.get("comando", "—"), p.get("etiqueta", "")))
            else:
                lineas.append("[ %s ] %s" % (
                    p.get("comando", "—"), p.get("etiqueta", "")))
    for bloqueo in navegacion.get("bloqueos") or []:
        lineas.append("⛔ %s" % bloqueo)
    if navegacion.get("requiere_aprobacion"):
        lineas.append("Requiere aprobación humana: no se avanza solo.")
    lineas.append("Estado: se mantiene (solo lectura, nada se ejecutó).")
    if navegacion.get("nota"):
        lineas.append("%s" % navegacion["nota"])
    return "\n".join(lineas)
