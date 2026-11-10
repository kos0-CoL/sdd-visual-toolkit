"""RF-31 — Panel de estado general (§20).

Render puro del tablero: proyecto, SPEC activa, fase, progreso,
tarea actual, última completada, pendientes, pruebas, errores y
próxima acción. La recolección de datos vive en la CLI sobre los
artefactos reales; aquí solo se presenta. Sin datos, se dice.
"""

from __future__ import annotations


def barra(hechas: int, total: int, ancho: int = 20) -> str:
    """Barra de progreso textual."""
    if total <= 0:
        return "[%s] sin tareas" % ("·" * ancho)
    llenas = round(hechas / total * ancho)
    return "[%s%s] %d/%d" % ("█" * llenas, "·" * (ancho - llenas),
                             hechas, total)


def render(estado: dict) -> str:
    """estado: claves proyecto, spec_id, spec_status, fase, hechas,
    total, tarea_actual, ultima_completada, pruebas, errores, proxima.
    """
    if not estado.get("spec_id"):
        return ("📊 Tablero «%s»: sin SPEC todavía.\n"
                "Próxima acción: %s" % (
                    estado.get("proyecto", "?"),
                    estado.get("proxima", "enrich «idea»")))
    lineas = ["📊 Tablero «%s» — %s [%s]." % (
        estado.get("proyecto", "?"), estado["spec_id"],
        estado.get("spec_status", "?"))]
    lineas.append("Fase actual: %s." % estado.get("fase", "—"))
    hechas = estado.get("hechas", 0)
    total = estado.get("total", 0)
    lineas.append("Progreso: %s." % barra(hechas, total))
    lineas.append("Tarea actual: %s." % (
        estado.get("tarea_actual") or "ninguna en curso"))
    lineas.append("Última completada: %s." % (
        estado.get("ultima_completada") or "ninguna todavía"))
    lineas.append("Pendientes: %d." % estado.get("pendientes", 0))
    lineas.append("Pruebas: %s." % estado.get("pruebas", "sin corridas"))
    errores = estado.get("errores") or []
    if errores:
        lineas.append("Errores (%d):" % len(errores))
        for error in errores[:5]:
            lineas.append("   🔴 %s" % error)
        if len(errores) > 5:
            lineas.append("   …y %d más" % (len(errores) - 5))
    else:
        lineas.append("Errores: ninguno registrado.")
    lineas.append("Próxima acción: %s" % estado.get("proxima", "—"))
    return "\n".join(lineas)
