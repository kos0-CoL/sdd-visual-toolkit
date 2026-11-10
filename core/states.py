"""RF-32 — Árbol de estados (§21).

Render puro: cada fase es un nodo con su estado §21 y un detalle
corto; abajo, el historial de transiciones registradas en el
journal. La derivación desde artefactos reales vive en la CLI.
"""

from __future__ import annotations

NODOS = [
    ("🌀", "Enriquecimiento"),
    ("📝", "Especificación"),
    ("🔍", "Aclaraciones"),
    ("📐", "Arquitectura"),
    ("💾", "Tareas"),
    ("🛡️", "Análisis"),
    ("⚡", "Implementación"),
    ("🧪", "Pruebas"),
    ("♻️", "Recuperación"),
]

SIMBOLOS = {
    "pendiente": "○",
    "en progreso": "●",
    "completado": "✔",
    "requiere intervención": "⚠",
    "fallido": "✘",
    "recuperado": "♻",
}


def render(nodos: list[tuple[str, str]], transiciones: list[str]) -> str:
    """nodos: [(fase, estado)] en orden; transiciones: líneas ya
    formateadas del journal."""
    lineas = ["🌳 Árbol de estados (%d fases)." % len(nodos)]
    for fase, estado in nodos:
        simbolo = SIMBOLOS.get(estado, "?")
        lineas.append("   %s %s: %s" % (simbolo, fase, estado))
    if transiciones:
        lineas.append("Transiciones registradas (%d):" % len(transiciones))
        for t in transiciones[-12:]:
            lineas.append("   %s" % t)
        if len(transiciones) > 12:
            lineas.append("   …y %d anteriores" % (len(transiciones) - 12))
    else:
        lineas.append("Sin transiciones registradas todavía.")
    return "\n".join(lineas)
