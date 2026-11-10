"""RF-13 — Recuperación de sesiones (§13.6).

Diagnóstico de solo lectura: detecta ejecuciones interrumpidas, valida la
SPEC, compara los hashes registrados contra el repositorio e identifica la
tarea pendiente. No completa nada por sí mismo: reanudar es `build`, que
revalida gates y pruebas. Jamás asume que una tarea quedó completada
porque el agente dijo que terminó: solo cuentan archivos y pruebas reales.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from core.journal import historial


class RecoverError(ValueError):
    """Condición de aceptación violada en la recuperación."""


def diagnosticar(raiz, plan_id: str, spec: dict | None, tareas: list) -> dict:
    raiz = Path(raiz)
    eventos = historial(raiz, plan_id)
    if not eventos:
        return {"plan_id": plan_id, "situacion": "sin_journal",
                "detalle": "sin eventos registrados: nada que recuperar"}

    hechos = [e for e in eventos if e.get("evento") == "completada"]
    checkpoints = [e for e in eventos if e.get("evento") == "checkpoint"]
    referencia = checkpoints[-1] if checkpoints else (hechos[-1] if hechos else {})

    spec_ok = isinstance(spec, dict) and bool(spec.get("funcionales"))
    hechas_ids = {e.get("tarea") for e in hechos}
    pendiente = next((t for t in tareas if t.id not in hechas_ids), None)
    en_curso_ids = [e.get("tarea") for e in eventos
                    if e.get("evento") == "en_curso"]
    interrumpida = (pendiente is not None and pendiente.id in en_curso_ids
                    and pendiente.id not in hechas_ids)

    archivos: dict[str, str] = {}
    for rel, sha_corto in (referencia.get("hashes") or {}).items():
        ruta = raiz / rel
        if not ruta.is_file():
            archivos[rel] = "faltante (se perdió tras el checkpoint)"
            continue
        real = hashlib.sha256(ruta.read_bytes()).hexdigest()[:16]
        archivos[rel] = ("sobrevive intacto" if real == sha_corto
                         else "cambió tras el checkpoint: revalidar con pruebas")
    if pendiente is not None:
        for rel in pendiente.archivos:
            archivos.setdefault(rel, "pendiente de implementar por "
                              + pendiente.id)

    ultimas = eventos[-3:]
    pruebas = "; ".join(
        f"{e.get('tarea')}: {e.get('pruebas', 'sin registro')}"
        for e in ultimas if e.get("evento") in ("completada", "fallida"))
    return {
        "plan_id": plan_id,
        "situacion": "interrumpida" if interrumpida else "limpia",
        "ultimo_checkpoint": (f"{referencia.get('tarea')}-SUCCESS"
                              if referencia else None),
        "spec_ok": spec_ok,
        "tarea_pendiente": pendiente.id if pendiente is not None else None,
        "archivos": archivos,
        "ultimas_pruebas": pruebas or "sin pruebas registradas",
        "reanudar_con": (f"build {plan_id}" if pendiente is not None
                         else "nada pendiente: el plan está completo"),
    }


def formatear(reporte: dict) -> str:
    if reporte.get("situacion") == "sin_journal":
        return f"📭 {reporte['plan_id']}: {reporte['detalle']}."
    icono = "⚠️" if reporte["situacion"] == "interrumpida" else "✅"
    lineas = [
        f"{icono} Recuperación {reporte['plan_id']}: ejecución {reporte['situacion']}.",
        f"1-2. Último estado: checkpoint {reporte['ultimo_checkpoint']}.",
        f"3. SPEC válida: {'sí' if reporte['spec_ok'] else 'NO — revisar specs/ antes de reanudar'}.",
        "4-6. Archivos vs. hashes registrados:",
    ]
    for rel, estado in reporte["archivos"].items():
        lineas.append(f"   {rel}: {estado}")
    lineas += [
        f"7. Últimas pruebas: {reporte['ultimas_pruebas']}.",
        f"8. Tarea pendiente: {reporte['tarea_pendiente'] or 'ninguna'}.",
        "9. Resumen: solo cuentan archivos y pruebas reales, "
        "no lo que el agente dijo.",
        f"10. Reanudar con: toolkit {reporte['reanudar_con']} "
        "(revalida gates y pruebas).",
    ]
    return "\n".join(lineas)
