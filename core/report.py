"""RF-26 — Resultados visibles y comparación (§18.4).

La interfaz debe mostrar por corrida: total, aprobadas, fallidas,
omitidas, duración, errores, cobertura y comparación con ejecuciones
anteriores. Este módulo lee el historial del journal (eventos
``tests``) y compone el informe; el CLI lo imprime.
"""

from __future__ import annotations


def _delta(ahora, antes, sufijo=""):
    if ahora is None or antes is None:
        return "—"
    dif = ahora - antes
    signo = "+" if dif > 0 else ""
    return "%s%s%s (%s%s%s)" % (ahora, sufijo, "", signo, dif, sufijo)


def corridas(raiz, plan_id: str, task_id: str) -> list[dict]:
    """Eventos tests de la tarea, en orden cronológico."""
    from core.journal import historial  # noqa: PLC0415
    return [e for e in historial(raiz, plan_id)
            if e.get("evento") == "tests" and e.get("tarea") == task_id]


def informe(raiz, plan_id: str, task_id: str) -> str:
    """Última corrida en detalle + tabla comparativa con anteriores."""
    runs = corridas(raiz, plan_id, task_id)
    if not runs:
        return ("Sin corridas registradas para %s (§18.4: nada medido, "
                "nada inventado)." % task_id)
    ult = runs[-1]
    lineas = ["📋 Reporte %s (%s)." % (task_id, ult.get("fecha", "?"))]
    lineas.append("   Veredicto: %s" % ("✅ TODO VERDE"
                                        if ult.get("pruebas_ok") else
                                        "❌ HAY ROJO"))
    lineas.append("   Total=%s pasadas=%s fallidas=%s omitidas=%s" % (
        ult.get("total", "?"), ult.get("pasadas", "?"),
        ult.get("fallidas", "?"), ult.get("omitidas", "?")))
    lineas.append("   Duración: %ss" % ult.get("duracion_s", "?"))
    cob = ult.get("cobertura_pct")
    lineas.append("   Cobertura: %s" % ("— (sin medir)"
                                        if cob is None else "%s%%" % cob))
    lineas.append("   %s" % (ult.get("pruebas") or ""))
    if len(runs) > 1:
        prev = runs[-2]
        lineas.append("   Comparación con corrida anterior "
                      "(%s):" % prev.get("fecha", "?"))
        lineas.append("     pasadas %s; fallidas %s; duración %s; "
                      "cobertura %s" % (
                          _delta(ult.get("pasadas"), prev.get("pasadas")),
                          _delta(ult.get("fallidas"), prev.get("fallidas")),
                          _delta(ult.get("duracion_s"),
                                 prev.get("duracion_s"), "s"),
                          _delta(ult.get("cobertura_pct"),
                                 prev.get("cobertura_pct"), "%")))
    else:
        lineas.append("   (primera corrida: sin anterior para comparar)")
    return "\n".join(lineas)


def tabla(raiz, plan_id: str, ultimas: int = 0) -> str:
    """Una línea por corrida tests del plan (para --history)."""
    from core.journal import historial  # noqa: PLC0415
    runs = [e for e in historial(raiz, plan_id)
            if e.get("evento") == "tests"]
    if ultimas > 0:
        runs = runs[-ultimas:]
    if not runs:
        return "Sin corridas de tests en %s." % plan_id
    lineas = []
    for e in runs:
        cob = e.get("cobertura_pct")
        lineas.append(
            "%s %s %s P=%s F=%s %ss cob=%s" % (
                e.get("fecha", "?"), e.get("tarea", "?"),
                "✅" if e.get("pruebas_ok") else "❌",
                e.get("pasadas", "?"), e.get("fallidas", "?"),
                e.get("duracion_s", "?"),
                "—" if cob is None else "%s%%" % cob))
    return "\n".join(lineas)
