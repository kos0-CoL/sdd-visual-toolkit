"""RF-09 — Ejecución de implementación (§11).

Bucle incremental supervisado: el humano implementa, el motor verifica.
Sin Gate 4 no hay build (§26). Cada avance verifica dependencias,
archivos objetivo y pruebas ejecutables, y registra el resultado.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from state.store import MODO_ORQUESTADOR  # noqa: E402

EN_CURSO = "en_curso"
COMPLETADA = "completada"
FALLIDA = "fallida"


class BuildError(ValueError):
    """Condición de aceptación violada en la ejecución."""


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _a_dotted(rel: str) -> str:
    return rel[:-3].replace("/", ".") if rel.endswith(".py") else rel


def siguiente_tarea(tareas: list):
    """Primera pendiente con dependencias completadas (§9.4, §11.3)."""
    hechas = {t.id for t in tareas if t.estado == COMPLETADA}
    for t in tareas:
        if t.estado == "pendiente" and all(d in hechas for d in t.dependencias):
            return t
    return None


def en_curso(tareas: list):
    return next((t for t in tareas if t.estado == EN_CURSO), None)


def marcar_en_curso(tarea, tareas: list) -> None:
    if en_curso(tareas) is not None:
        raise BuildError("ya hay una tarea en curso; termine o registre su situación")
    hechas = {t.id for t in tareas if t.estado == COMPLETADA}
    faltantes = [d for d in tarea.dependencias if d not in hechas]
    if faltantes:
        raise BuildError(f"{tarea.id} depende de {', '.join(faltantes)} (no disponibles)")
    tarea.estado = EN_CURSO


def archivos_faltantes(tarea, raiz: Path) -> list[str]:
    return [a for a in tarea.archivos if not (Path(raiz) / a).exists()]


ESTADOS_PRUEBAS = ("pasadas", "fallidas", "sin_pruebas")


def ejecutar_pruebas(tarea, raiz: Path, timeout: int = 120) -> tuple[str, str]:
    """Corre los tests de la tarea con el runner detectado (§19/RF-43) y
    devuelve (estado, salida) con estado en {“pasadas”, “fallidas”,
    “sin_pruebas”}. Nunca se inventa un resultado verde sin ejecutar."""
    from core.harness import detectar_runner, archivos_test_por_runner, correr_archivos  # noqa: PLC0415
    runner = detectar_runner(raiz)
    if runner in ("npm", "go", "cargo"):
        # §51: el runner del repo ejecuta el suite completo por su cuenta;
        # los archivos de test de la tarea no se pasan sueltos.
        r = correr_archivos(raiz, [], fase="unitarios", timeout=180)
        if r.get("ok") and (r.get("fallidas") or 0) == 0:
            return "pasadas", r.get("errores") or "pruebas OK"
        return "fallidas", r.get("errores") or "pruebas en rojo"
    archivos = archivos_test_por_runner(raiz, tarea.archivos)
    archivos = [a for a in archivos if (Path(raiz) / a).exists()]
    if not archivos:
        return "sin_pruebas", "sin pruebas ejecutables todavía (ningún archivo de test para el runner detectado)"
    r = correr_archivos(raiz, archivos, fase="unitarios", timeout=timeout)
    if r.get("ok") and (r.get("fallidas") or 0) == 0:
        return "pasadas", r.get("errores") or "pruebas OK"
    return "fallidas", r.get("errores") or "pruebas en rojo"


def registrar_done(tarea, tareas: list, raiz: Path, nota: str = "",
                   evidencia: dict | None = None,
                   vigilancia: dict | None = None,
                   modo: str | None = None) -> dict:
    """Verifica archivos + pruebas y completa. No oculta fallos (§46.13).

    §18.5: el cierre conserva evidencia (hashes de tests + última
    corrida registrada); `evidencia` la aporta el CLI desde el journal.

    En modo `orquestador`, se permite cerrar con `sin_pruebas` si hay una
    nota de justificación (no bloquea, pero advierte).
    """
    if tarea.estado != EN_CURSO:
        raise BuildError(f"{tarea.id} no está en curso; avance con `build` primero")
    faltan = archivos_faltantes(tarea, raiz)
    if faltan:
        raise BuildError(f"archivos objetivo inexistentes: {', '.join(faltan)}")
    if modo is None:
        from state.store import leer_modo_operacion  # noqa: PLC0415
        modo = leer_modo_operacion(raiz)
    estado, salida = ejecutar_pruebas(tarea, raiz)
    tarea.intentos += 1
    if estado == "sin_pruebas":
        # RF-09/§11: sin evidencia ejecutable no se cierra la tarea.
        if modo != MODO_ORQUESTADOR or not nota.strip():
            raise BuildError(
                f"{tarea.id}: NOT_VERIFIED — sin pruebas ejecutables para los "
                f"archivos autorizados; escriba al menos un test por criterio de "
                f"aceptación antes de cerrar (§11).")
        # Modo orquestador con justificación: cierra con advertencia.
    from core.harness import hashes_tests  # noqa: PLC0415
    evento = {
        "fecha": _ahora(), "tarea": tarea.id, "evento": "completada",
        "estado_pruebas": estado, "pruebas_ok": estado == "pasadas",
        "pruebas": salida, "nota": nota,
        "hashes_tests": hashes_tests(raiz, tarea.archivos),
    }
    if evidencia is not None:
        evento["evidencia_tests"] = evidencia
    if vigilancia is not None:
        # RF-28: qué tests cambiaron durante la tarea (auditable).
        evento["tests_modificados"] = vigilancia.get("modificados", [])
        evento["tests_sospechosos"] = vigilancia.get("sospechosos", [])
    if not evento["pruebas_ok"]:
        tarea.estado = FALLIDA
        evento["evento"] = "fallida"
    else:
        tarea.estado = COMPLETADA
    from core.journal import compactar_si_necesario  # noqa: PLC0415
    plan_id = getattr(tarea, "plan_id", None)
    compactar_si_necesario(raiz, plan_id=plan_id)
    return evento


def registrar_fail(tarea, raiz: Path, nota: str) -> dict:
    if not nota.strip():
        raise BuildError("registre la situación con --nota (no se avanza en silencio)")
    tarea.intentos += 1
    tarea.estado = FALLIDA
    evento = {"fecha": _ahora(), "tarea": tarea.id, "evento": "fallida",
            "pruebas_ok": False, "pruebas": "", "nota": nota}
    from core.journal import compactar_si_necesario  # noqa: PLC0415
    plan_id = getattr(tarea, "plan_id", None)
    compactar_si_necesario(raiz, plan_id=plan_id)
    return evento


def sugerir(tarea, raiz: Path, plan_id: str, texto: str,
            origen: str = "") -> dict:
    """Registra una mejora detectada sin incorporarla al alcance (§40).

    La sugerencia vive en `.specify/sugerencias/<PLAN>.json`; los archivos,
    dependencias y criterio de la tarea no cambian. El evento `sugerencia`
    se anuncia a los hooks del IDE sin bloquear la tarea.
    """
    from core.hooks import disparar  # noqa: PLC0415
    from core.plan import registrar_sugerencia  # noqa: PLC0415

    alcance = {"archivos": list(tarea.archivos),
               "dependencias": list(tarea.dependencias),
               "criterio": tarea.criterio}
    sugerencia = registrar_sugerencia(raiz, plan_id, texto,
                                      origen=origen, tarea=tarea.id)
    despues = {"archivos": list(tarea.archivos),
               "dependencias": list(tarea.dependencias),
               "criterio": tarea.criterio}
    if despues != alcance:
        raise BuildError(
            "una sugerencia no puede modificar el alcance de la tarea (§40)")
    hooks = disparar(raiz, "sugerencia",
                     {"plan": plan_id, "tarea": tarea.id,
                      "resultado": sugerencia.estado,
                      "sugerencia": sugerencia.id})
    return {"sugerencia": sugerencia.to_dict(),
            "alcance_intacto": True, "hooks": hooks}


def tarjeta_pin(tarea, spec) -> str:
    """Restricciones relevantes antes de tocar código (§11.1)."""
    reqs = [f"{i}: {t}" for i, t, _e in spec.funcionales if i in tarea.refs]
    return "\n".join([
        f"📌 PIN {tarea.id} — SPEC {spec.spec_id} [{spec.status}]",
        f"Requerimiento: {'; '.join(reqs) or '(sección ' + ', '.join(tarea.refs) + ')'}",
        f"Tarea: {tarea.objetivo}",
        f"Criterio: {tarea.criterio}",
        f"Archivos autorizados: {', '.join(tarea.archivos)}",
        f"Exclusiones: {'; '.join(spec.fuera_alcance) or '—'}",
        f"Supuestos abiertos: {sum(1 for s in spec.supuestos if not s.startswith('✓'))}",
    ])
