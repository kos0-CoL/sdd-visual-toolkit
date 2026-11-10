"""RF-18 — Validación de cambios (§48, §17.3–17.4).

Puerta unificada antes de cerrar una tarea. Combina: diffs, análisis de
interfaces (AST), dependencias, pruebas, trazabilidad de tareas y
evaluación semántica (refs contra la SPEC + evidencia de pruebas).
Veredicto: VALIDADO, OBSERVADO (revisar con --nota) o RECHAZADO.
"""

from __future__ import annotations


class ValidateError(ValueError):
    """Condición de aceptación violada en la validación."""


def validar(raiz, tarea, plan, spec, eventos: list[dict], nota: str = "") -> dict:
    """Ejecuta las 6 capas (§48). Sin nota, lo justificable queda OBSERVADO."""
    from core.astcheck import comparar as comparar_ast  # noqa: PLC0415
    from core.pin import asegurar_baseline, verificar_cambios  # noqa: PLC0415

    rechazos, observaciones = [], []

    # 1. Trazabilidad de tareas + 6. Evaluación semántica.
    aceptados = {i for i, _t, e in spec.funcionales if e == "aceptado"}
    for ref in tarea.refs:
        if ref.startswith("§"):
            continue  # referencia de sección SPEC (convención de RF-06)
        if ref not in aceptados:
            rechazos.append(f"ref {ref} sin trazabilidad a funcional aceptado")
    if not tarea.refs:
        observaciones.append("tarea sin refs: nada la ata a la SPEC")

    # 2-3. Diffs + AST/interfaces (misma línea base, sin doble estándar).
    baseline, parcial = asegurar_baseline(raiz, tarea)
    desvs = verificar_cambios(tarea, baseline, raiz)
    for d in desvs:
        (rechazos if d.clase == "C" else observaciones).append(
            f"[pin-{d.clase}] {d.archivo}: {d.detalle}")
    ast = comparar_ast(tarea, baseline, raiz)
    for h in ast["hallazgos"]:
        (rechazos if h["severidad"] == "rechazado" else observaciones).append(
            f"[ast-{h['tipo']}] {h['archivo']}::{h['simbolo']}: {h['detalle']}")
    if parcial:
        observaciones.append("sin línea base previa: validación parcial")

    # 4. Pruebas: evidencia real, no promesas. El cierre re-ejecuta los
    # tests (registrar_done decide); aquí solo se informa el historial.
    vistos = [e for e in eventos if e.get("tarea") == tarea.id
              and "pruebas" in e and e.get("evento") in
              ("completada", "fallida", "tests")]
    if not vistos:
        observaciones.append("sin evidencia de pruebas para la tarea")
    elif not vistos[-1].get("pruebas_ok"):
        observaciones.append(
            f"últimas pruebas en rojo: {vistos[-1].get('pruebas')} "
            "(el cierre las re-ejecutará)")

    # 4c. Protección de pruebas (§18.3): los tests pueden evolucionar,
    # pero no en silencio. Sin nota, el cambio queda OBSERVADO.
    from core.testguard import verificar as vigilar_tests  # noqa: PLC0415
    guardia = vigilar_tests(raiz, tarea, baseline, eventos, nota)
    observaciones.extend(guardia["observaciones"])

    # 4b. Criterios de aceptación (§18.5): los CP reales de la tarea deben
    # estar cubiertos por tests ejecutables y en verde. Ejecutar aquí es
    # intencional: el cierre no se fía del historial, lo comprueba.
    from core.acceptance import RE_CASO, evaluar as evaluar_acept  # noqa: PLC0415
    reales = []
    for p in (tarea.pruebas or []):
        m = RE_CASO.search(p)
        if m and "crear con la implementaci" not in p:
            reales.append(m.group(0))
    if reales:
        ids_spec = {getattr(k, "id", None)
                    for k in (getattr(spec, "casos", None) or [])}
        for pedido in reales:
            if pedido not in ids_spec:
                observaciones.append(
                    f"{pedido} pedido por la tarea pero inexistente en la SPEC")
        ev = evaluar_acept(raiz, tarea, spec)
        for c in ev.get("casos", []):
            if c["estado"] == "fallida":
                rechazos.append(f"criterio incumplido: {c['detalle']}")
            elif c["estado"] == "omitida":
                observaciones.append(f"criterio sin evidencia: {c['detalle']}")

    # 5. Dependencias/interfaces protegidas intactas.
    from core.analyze import _es_protegido  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    for rel in tarea.archivos:
        if _es_protegido(rel) and (Path(raiz) / rel).is_file():
            snap = baseline.get(rel)
            from core.pin import snapshot_archivo  # noqa: PLC0415
            ahora = snapshot_archivo(Path(raiz) / rel)
            if snap is not None and ahora is not None and snap["sha"] != ahora["sha"]:
                rechazos.append(f"archivo protegido modificado: {rel}")

    if rechazos:
        veredicto = "RECHAZADO"
    elif observaciones and not (nota or "").strip():
        veredicto = "OBSERVADO"
    else:
        veredicto = "VALIDADO"
    lineas = [f"✔ Validación {tarea.id}: {veredicto} "
              f"({len(rechazos)} rechazo(s), {len(observaciones)} observación(es))."]
    for r in rechazos:
        lineas.append(f"  🔴 {r}")
    for o in observaciones:
        marca = "🟡" if veredicto != "VALIDADO" else "ℹ️"
        lineas.append(f"  {marca} {o}")
    if veredicto == "OBSERVADO":
        lineas.append("Revise y justifique con --nota (§17.4).")
    return {"veredicto": veredicto, "rechazos": rechazos,
            "observaciones": observaciones, "resumen": "\n".join(lineas)}
