"""RF-30 — Historial y trazabilidad (§44.30).

El journal ya persiste cada evento de forma apendicular (RF-11); este
módulo compone el relato cronológico de una tarea: qué pasó, cuándo,
con qué evidencia. Todo sale de `execution_history.jsonl`; sin
eventos, se dice, no se inventa.
"""

from __future__ import annotations


def eventos_de(eventos: list[dict], task_id: str) -> list[dict]:
    """Eventos de la tarea, en orden cronológico."""
    return [e for e in eventos if e.get("tarea") == task_id]


def relato(eventos: list[dict], task_id: str) -> str:
    """Historia narrativa de la tarea con su evidencia."""
    runs = eventos_de(eventos, task_id)
    if not runs:
        return ("Sin historia para %s: nada registrado en el journal "
                "(no se inventa pasado)." % task_id)
    lineas = ["📜 Historia %s: %d evento(s)." % (task_id, len(runs))]
    for e in runs:
        fecha = e.get("fecha", "?")
        tipo = e.get("evento")
        if tipo == "en_curso":
            lineas.append("   %s ▶ puesta en curso." % fecha)
        elif tipo == "tests":
            marca = "✅" if e.get("pruebas_ok") else "❌"
            cob = e.get("cobertura_pct")
            lineas.append(
                "   %s %s corrida: P=%s F=%s %ss cob=%s" % (
                    fecha, marca, e.get("pasadas", "?"),
                    e.get("fallidas", "?"), e.get("duracion_s", "?"),
                    "—" if cob is None else "%s%%" % cob))
        elif tipo in ("completada", "fallida"):
            marca = "✅" if tipo == "completada" else "❌"
            n_hash = len(e.get("hashes_tests") or {})
            extras = []
            evid = e.get("evidencia_tests") or {}
            if evid.get("cobertura_pct") is not None:
                extras.append("cob=%s%%" % evid["cobertura_pct"])
            if e.get("tests_modificados"):
                extras.append("tests modificados: %s" % ", ".join(
                    e["tests_modificados"]))
            if e.get("tests_sospechosos"):
                extras.append("sospechosos: %s" % ", ".join(
                    e["tests_sospechosos"]))
            lineas.append(
                "   %s %s cerrada como %s: %s "
                "(evidencia: %d hash(es)%s)." % (
                    fecha, marca, tipo,
                    e.get("pruebas") or e.get("nota") or "—",
                    n_hash, "; " + "; ".join(extras) if extras else ""))
        elif tipo == "rollback":
            lineas.append("   %s ↩ rollback: %s" % (fecha, e.get("nota", "—")))
        elif tipo == "checkpoint":
            n_arch = len(e.get("archivos") or [])
            lineas.append("   %s 🔖 checkpoint (%d archivo(s)): %s" % (
                fecha, n_arch, e.get("decisiones") or "—"))
        else:
            lineas.append("   %s · %s" % (fecha, tipo))
    return "\n".join(lineas)
