"""RF-15 — Context Flush (§15).

Renovación del contexto ante degradación: mide saturación con un umbral
configurable (30.000 tokens fue un ejemplo, no un valor universal), genera
un paquete de traspaso y verifica el estado. Es aditivo: jamás borra
información durable ni finge reiniciar el chat del IDE.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

UMBRAL_POR_DEFECTO = 30000
CONFIG_FILE = "context.json"
FLUSH_DIR = "flush"


class FlushError(ValueError):
    """Condición de aceptación violada en el context flush."""


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def estimar_tokens(texto: str) -> int:
    """Heurística honesta (≈4 caracteres por token en español/código)."""
    return max(1, len(texto) // 4)


def leer_umbral(raiz) -> int:
    ruta = Path(raiz) / ".specify" / CONFIG_FILE
    if not ruta.exists():
        return UMBRAL_POR_DEFECTO
    import json  # noqa: PLC0415
    try:
        return int(json.loads(ruta.read_text(encoding="utf-8")).get(
            "umbral_tokens", UMBRAL_POR_DEFECTO))
    except (OSError, ValueError, AttributeError, TypeError):
        return UMBRAL_POR_DEFECTO


def fijar_umbral(raiz, valor: int) -> int:
    if valor <= 0:
        raise FlushError("el umbral debe ser positivo")
    import json  # noqa: PLC0415
    ruta = Path(raiz) / ".specify" / CONFIG_FILE
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"umbral_tokens": valor}, ensure_ascii=False),
                    encoding="utf-8")
    return valor


def medir(raiz, plan_id: str, eventos: list[dict], checkpoints: list[dict]) -> dict:
    """Paso 1: detectar saturación. Solo cuenta lo registrado."""
    base = sum(estimar_tokens(str(e)) for e in eventos)
    base += sum(estimar_tokens(str(c)) for c in checkpoints)
    umbral = leer_umbral(raiz)
    return {"plan_id": plan_id, "tokens_estimados": base,
            "umbral": umbral, "saturado": base >= umbral,
            "eventos": len(eventos), "checkpoints": len(checkpoints)}


def generar_pack(raiz, plan_id: str, spec, tarea_activa, tareas: list,
                 eventos: list[dict], motivo: str) -> tuple[Path, dict]:
    """Pasos 2-5 y 7: checkpoint ya existe en journal; aquí se resume lo
    pendiente, las decisiones y los errores en un archivo de traspaso."""
    pendientes = [t.id for t in tareas
                  if t.id != (tarea_activa.id if tarea_activa else None)
                  and getattr(t, "estado", "pendiente") != "completada"]
    decisiones = [f"{e.get('tarea')}: {e.get('decisiones')}"
                  for e in eventos
                  if e.get("evento") == "checkpoint" and e.get("decisiones")]
    fallos = [f"{e.get('tarea')}: {e.get('nota') or e.get('pruebas') or 'sin detalle'}"
              for e in eventos if e.get("evento") == "fallida"]
    pack = {
        "fecha": _ahora(), "plan": plan_id, "motivo": motivo,
        "spec": getattr(spec, "spec_id", "?"),
        "fase": "implement",
        "tarea_activa": tarea_activa.id if tarea_activa else None,
        "pendientes": pendientes,
        "decisiones": decisiones,
        "errores_y_estrategias_fallidas": fallos,
        "inyectar_al_retomar": [
            f"SPEC {getattr(spec, 'spec_id', '?')}",
            f"plan {plan_id}",
            f"tarea {tarea_activa.id if tarea_activa else '—'}",
        ],
    }
    dest = Path(raiz) / ".specify" / FLUSH_DIR
    dest.mkdir(parents=True, exist_ok=True)
    sello = pack["fecha"].replace(":", "").replace("+", "")
    ruta = dest / f"FLUSH-{plan_id}-{sello}.md"
    ruta.write_text(render_pack(pack), encoding="utf-8")
    return ruta, pack


def render_pack(pack: dict) -> str:
    lineas = [
        f"# Traspaso de contexto — {pack['plan']} ({pack['fecha']})",
        "", f"Motivo: {pack['motivo']}", "",
        "## Qué inyectar al retomar (§15.7)",
    ]
    lineas += [f"- {x}" for x in pack["inyectar_al_retomar"]]
    lineas += ["", f"## Tarea activa: {pack['tarea_activa'] or '—'}", "",
               "## Trabajo pendiente (§15.3)"]
    lineas += [f"- {t}" for t in pack["pendientes"]] or ["- (nada)"]
    lineas += ["", "## Decisiones importantes (§15.4)"]
    lineas += [f"- {d}" for d in pack["decisiones"]] or ["- (ninguna registrada)"]
    lineas += ["", "## Errores y estrategias fallidas (§15.5)"]
    lineas += [f"- {e}" for e in pack["errores_y_estrategias_fallidas"]
               ] or ["- (ninguno)"]
    lineas += ["",
               "Nota: este traspaso no borró nada. Verifique el estado con "
               "`recover` antes de continuar (§15.8)."]
    return "\n".join(lineas) + "\n"
