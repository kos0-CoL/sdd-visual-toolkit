"""RF-09 — Ejecución de implementación (§11).

Bucle incremental supervisado: el humano implementa, el motor verifica.
Sin Gate 4 no hay build (§26). Cada avance verifica dependencias,
archivos objetivo y pruebas ejecutables, y registra el resultado.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

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


def ejecutar_pruebas(tarea, raiz: Path, timeout: int = 120) -> tuple[bool, str]:
    """Corre los archivos de prueba existentes de la tarea. Si no hay
    ninguno ejecutable, lo informa en vez de inventar un resultado."""
    objetivos = [a for a in tarea.archivos
                 if a.startswith("tests/") and a.endswith(".py")
                 and (Path(raiz) / a).exists()]
    if not objetivos:
        return True, "sin pruebas ejecutables todavía (ningún archivo tests/ existe)"
    ok_global, salidas = True, []
    for objetivo in objetivos:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", _a_dotted(objetivo)],
            cwd=str(raiz), capture_output=True, text=True, timeout=timeout)
        ok_global = ok_global and proc.returncode == 0
        ultimo = (proc.stderr.strip() or proc.stdout.strip()).splitlines()
        salidas.append(f"{objetivo}: {'OK' if proc.returncode == 0 else 'FALLA'} "
                       f"({ultimo[-1] if ultimo else 'sin salida'})")
    return ok_global, "; ".join(salidas)


def registrar_done(tarea, tareas: list, raiz: Path, nota: str = "",
                   evidencia: dict | None = None,
                   vigilancia: dict | None = None) -> dict:
    """Verifica archivos + pruebas y completa. No oculta fallos (§46.13).

    §18.5: el cierre conserva evidencia (hashes de tests + última
    corrida registrada); `evidencia` la aporta el CLI desde el journal.
    """
    if tarea.estado != EN_CURSO:
        raise BuildError(f"{tarea.id} no está en curso; avance con `build` primero")
    faltan = archivos_faltantes(tarea, raiz)
    if faltan:
        raise BuildError(f"archivos objetivo inexistentes: {', '.join(faltan)}")
    ok, salida = ejecutar_pruebas(tarea, raiz)
    tarea.intentos += 1
    from core.harness import hashes_tests  # noqa: PLC0415
    evento = {
        "fecha": _ahora(), "tarea": tarea.id, "evento": "completada",
        "pruebas_ok": ok, "pruebas": salida, "nota": nota,
        "hashes_tests": hashes_tests(raiz, tarea.archivos),
    }
    if evidencia is not None:
        evento["evidencia_tests"] = evidencia
    if vigilancia is not None:
        # RF-28: qué tests cambiaron durante la tarea (auditable).
        evento["tests_modificados"] = vigilancia.get("modificados", [])
        evento["tests_sospechosos"] = vigilancia.get("sospechosos", [])
    if not ok:
        tarea.estado = FALLIDA
        evento["evento"] = "fallida"
        return evento
    tarea.estado = COMPLETADA
    return evento


def registrar_fail(tarea, nota: str) -> dict:
    if not nota.strip():
        raise BuildError("registre la situación con --nota (no se avanza en silencio)")
    tarea.intentos += 1
    tarea.estado = FALLIDA
    return {"fecha": _ahora(), "tarea": tarea.id, "evento": "fallida",
            "pruebas_ok": False, "pruebas": "", "nota": nota}


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
