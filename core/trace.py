"""RF-29 — Trazabilidad completa (§39).

Recorre la cadena REQUERIMIENTO → SPEC → PLAN → TASK → CAMBIO →
TEST → EVIDENCIA. Todo sale de artefactos reales (SPEC, planes,
tareas, pines, journal); lo ausente se declara, no se inventa.
"""

from __future__ import annotations

from pathlib import Path


def _estado_cambio(raiz: Path, tarea, baseline: dict, rel: str) -> str:
    ruta = raiz / rel
    if not ruta.is_file():
        return "eliminado"
    if not baseline:
        return "sin línea base"
    viejo = (baseline.get(rel) or {}).get("sha")
    if viejo is None:
        return "nuevo en la tarea"
    from core.pin import snapshot_archivo  # noqa: PLC0415
    ahora = snapshot_archivo(ruta)
    if ahora is None or ahora["sha"] == viejo:
        return "igual"
    return "modificado"


def matriz(spec, planes_tareas: list, eventos: list, raiz) -> str:
    """spec: Spec; planes_tareas: [(plan, [tareas])]; eventos: journal."""
    from core.acceptance import es_accept, extraer_cobertura  # noqa: PLC0415
    from core.pin import _cargar_pin  # noqa: PLC0415

    raiz = Path(raiz)
    lineas = ["🔗 Trazabilidad %s ← %s." % (
        spec.spec_id, spec.enr_origen or "sin ENR")]
    for plan, _tareas in planes_tareas:
        lineas.append("   PLAN %s [%s]: %d tarea(s)." % (
            plan.plan_id, getattr(plan, "status", "?"), len(_tareas)))
    todas = [t for _p, ts in planes_tareas for t in ts]

    # Cobertura estática global de casos → tests (una sola pasada AST).
    accept_files = sorted({a for t in todas for a in t.archivos
                           if es_accept(a) and (raiz / a).is_file()})
    cobertura = extraer_cobertura(raiz, accept_files)

    crit_por_req: dict[str, list] = {}
    for c in (spec.criterios or []):
        crit_por_req.setdefault(c.req_id, []).append(c)
    casos_por_crit: dict[str, list] = {}
    for k in (spec.casos or []):
        casos_por_crit.setdefault(k.criterio_id, []).append(k)

    from core.acceptance import RE_CASO  # noqa: PLC0415

    def tareas_de(caso_id: str):
        sale = []
        for t in todas:
            for p in (t.pruebas or []):
                m = RE_CASO.search(p)
                if m and m.group(0) == caso_id:
                    sale.append(t)
                    break
        return sale

    def evidencia(tarea) -> str:
        runs = [e for e in eventos if e.get("evento") == "tests"
                and e.get("tarea") == tarea.id]
        cierre = [e for e in eventos if e.get("evento") == "completada"
                  and e.get("tarea") == tarea.id]
        if not runs:
            base = "sin corridas"
        else:
            ult = runs[-1]
            base = "%s %s" % ("✅" if ult.get("pruebas_ok") else "❌",
                              ult.get("fecha", "?"))
            if ult.get("cobertura_pct") is not None:
                base += " cob=%s%%" % ult.get("cobertura_pct")
        if cierre:
            base += "; cerrada %s" % cierre[-1].get("fecha", "?")
        else:
            base += "; sin cerrar"
        return base

    for req_id, texto, estado in (spec.funcionales or []):
        marca = "✅" if estado == "aceptado" else "⏳"
        lineas.append("%s %s [%s] %s" % (marca, req_id, estado, texto))
        criterios = crit_por_req.get(req_id, [])
        if not criterios:
            lineas.append("   └ (sin criterios: pendiente de clarify)")
            continue
        for cri in criterios:
            lineas.append("   └ %s: %s" % (cri.id, cri.texto))
            casos = casos_por_crit.get(cri.id, [])
            if not casos:
                lineas.append("      └ (sin casos de prueba)")
                continue
            for caso in casos:
                lineas.append("      └ %s: %s" % (caso.id, caso.texto))
                dueñas = tareas_de(caso.id)
                if not dueñas:
                    lineas.append("         └ (sin tarea que lo pida)")
                    continue
                for t in dueñas:
                    sels = cobertura.get(caso.id, [])
                    base = _cargar_pin(raiz, t.id) or {}
                    linea_base = base.get("baseline", {}) if base else {}
                    cambios = ", ".join(
                        "%s (%s)" % (a, _estado_cambio(raiz, t, linea_base, a))
                        for a in t.archivos
                        if not a.startswith("tests/")) or "(sin fuentes)"
                    lineas.append(
                        "         ├─ %s [%s]: %s" % (
                            t.id, getattr(t, "estado", "?"), cambios))
                    lineas.append("         ├─ tests: %s" % (
                        "; ".join(sels) if sels else "SIN PRUEBA ejecutable"))
                    lineas.append("         └─ evidencia: %s" % evidencia(t))
    return "\n".join(lineas)
