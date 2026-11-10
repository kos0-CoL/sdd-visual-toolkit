"""RF-12 — Checkpoints (§13.4, §35).

Cada tarea completada deja un artefacto durable e individualmente
direccionable en `.specify/checkpoints/{TASK-ID}.json`, además del evento
en el journal. Un checkpoint responde: qué SPEC, qué tarea, qué sigue,
qué archivos con qué hashes, qué pruebas con qué resultado, qué se
decidió y qué queda pendiente.
"""

from __future__ import annotations

import json
from pathlib import Path


class CheckpointError(ValueError):
    """Condición de aceptación violada en los checkpoints."""


CHECKPOINTS_DIR = "checkpoints"

CLAVES = {"fecha", "plan", "spec", "fase", "evento", "tarea", "proxima",
          "archivos", "hashes", "pruebas", "pruebas_ok", "decisiones"}


def _dir(raiz: Path) -> Path:
    ruta = Path(raiz) / ".specify" / CHECKPOINTS_DIR
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def guardar(raiz, plan_id: str, registro: dict) -> Path:
    """Persiste el checkpoint semántico de una tarea (§13.4)."""
    if registro.get("evento") != "checkpoint" or not registro.get("tarea"):
        raise CheckpointError("solo se archivan eventos de tipo checkpoint")
    faltantes = CLAVES - set(registro)
    if faltantes:
        raise CheckpointError(f"checkpoint incompleto, faltan: {sorted(faltantes)}")
    ruta = _dir(Path(raiz)) / f"{registro['tarea']}.json"
    ruta.write_text(json.dumps(registro, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return ruta


def cargar(raiz, task_id: str) -> dict | None:
    ruta = Path(raiz) / ".specify" / CHECKPOINTS_DIR / f"{task_id}.json"
    if not ruta.exists():
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CheckpointError(f"checkpoint {task_id} ilegible: {error}") from error
    if datos.get("tarea") != task_id:
        raise CheckpointError(f"checkpoint {task_id} no corresponde a su archivo")
    return datos


def listar(raiz, plan_id: str) -> list[dict]:
    """Checkpoints de un plan, en orden cronológico."""
    base = Path(raiz) / ".specify" / CHECKPOINTS_DIR
    if not base.exists():
        return []
    puntos = []
    for ruta in sorted(base.glob("TASK-*.json")):
        datos = cargar(raiz, ruta.stem)
        if datos is not None and datos.get("plan") == plan_id:
            puntos.append(datos)
    puntos.sort(key=lambda d: d.get("fecha", ""))
    return puntos


def formatear(punto: dict) -> str:
    ok = "✅" if punto.get("pruebas_ok") else "❌"
    lineas = [
        f"📍 Checkpoint {punto['tarea']} ({punto.get('fecha')}) — plan {punto.get('plan')}.",
        f"SPEC {punto.get('spec')} · fase {punto.get('fase')} · siguiente: "
        f"{punto.get('proxima') or 'ninguna (era la última)'}.",
        "Archivos (hash corto):",
    ]
    for rel in punto.get("archivos", []):
        lineas.append(f"  {rel}: {punto.get('hashes', {}).get(rel, '?')}")
    lineas += [
        f"Pruebas {ok}: {punto.get('pruebas')}.",
        f"Decisiones: {punto.get('decisiones') or '—'}.",
    ]
    return "\n".join(lineas)
