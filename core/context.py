"""RF-14 — Context Split-Streaming (§14).

En lugar de volcar el repositorio entero, el contexto se construye por
modos desde los artefactos persistentes. Cada modo entrega solo lo que
la tarea necesita; lo que no cabe se marca [truncado], jamás se inventa.
"""

from __future__ import annotations

from pathlib import Path

MODOS = ("requerimientos", "arquitectura", "implementacion", "pruebas",
         "recuperacion")

LIMITE = 4000  # caracteres por modo; lo excedente se trunca con aviso


class ContextError(ValueError):
    """Condición de aceptación violada en la construcción de contexto."""


def _cortar(texto: str) -> str:
    if len(texto) <= LIMITE:
        return texto
    return texto[:LIMITE] + "\n[…truncado: pida el resto por partes (§14)]"


def requerimientos(spec, reqs: list) -> str:
    lineas = [f"## Requerimientos — {spec.spec_id} «{spec.titulo}»",
              f"Origen: {spec.enr_origen}", "",
              "Funcionales aceptados (solo estos obligan):"]
    for rid, texto, estado in spec.funcionales:
        if estado == "aceptado":
            lineas.append(f"  ✓ {rid}: {texto}")
    lineas.append("")
    lineas.append("Supuestos registrados:")
    for s in (spec.supuestos or ["(ninguno)"]):
        lineas.append(f"  · {s}")
    lineas.append("")
    lineas.append("Fuera de alcance (no tocar):")
    for f in (spec.fuera_alcance or ["(nada declarado)"]):
        lineas.append(f"  ✕ {f}")
    propias = [r for r in reqs if getattr(r, "spec_id", None) == spec.spec_id]
    if propias:
        lineas += ["", "Trazabilidad a requerimientos:"]
        for r in propias:
            lineas.append(f"  {r.id} [{r.procedencia}/{r.estado}]: {r.texto}")
    return _cortar("\n".join(lineas))


def arquitectura(plan) -> str:
    lineas = [f"## Arquitectura — {plan.plan_id} (SPEC {plan.spec_id})", ""]
    if plan.arquitectura:
        lineas += ["Decisión de arquitectura:", f"  {plan.arquitectura}", ""]
    lineas.append("Fronteras: lo reutilizable no se reescribe; "
                  "lo intacto no se toca.")
    for etiqueta, grupo in (("reutilizar", plan.reutilizables),
                             ("modificar", plan.modificables),
                             ("crear", plan.creables),
                             ("no tocar", plan.intactos)):
        lineas.append(f"  {etiqueta}: {', '.join(grupo) or '—'}")
    if plan.orden:
        lineas += ["", "Orden derivado (la tarea vive dentro de esta secuencia):"]
        for p in plan.orden:
            lineas.append(f"  {p.id}: {p.titulo}")
    if plan.riesgos:
        lineas += ["", "Riesgos:"] + [f"  ! {r}" for r in plan.riesgos]
    return _cortar("\n".join(lineas))


def implementacion(tarea, pin_tarjeta: str, raiz) -> str:
    from core.pin import snapshot_archivo  # noqa: PLC0415

    lineas = [f"## Implementación — {tarea.id}: {tarea.descripcion}",
              f"Objetivo: {tarea.objetivo}",
              f"Criterio de hecho: {tarea.criterio}", "",
              "Interfaces existentes (firmas, no código completo):"]
    for rel in tarea.archivos:
        if rel.startswith("tests/"):
            continue
        ruta = Path(raiz) / rel
        if not ruta.is_file():
            lineas.append(f"  {rel}: (aún no existe — crearlo)")
            continue
        snap = snapshot_archivo(ruta)
        pub = snap["publicas"] if snap else {}
        if pub:
            firmas = ", ".join(f"{n}{f}" for n, f in sorted(pub.items()))
            lineas.append(f"  {rel}: {firmas}")
        else:
            lineas.append(f"  {rel}: (sin símbolos públicos)")
    lineas += ["", pin_tarjeta]
    return _cortar("\n".join(lineas))


def pruebas(tarea, eventos: list[dict]) -> str:
    lineas = [f"## Pruebas — {tarea.id}", "",
              "Estrategia de esta tarea:"]
    for p in (tarea.pruebas or ["(sin estrategia declarada)"]):
        lineas.append(f"  · {p}")
    lineas.append("")
    lineas.append("Últimos resultados registrados:")
    vistos = [e for e in eventos
              if e.get("tarea") == tarea.id and "pruebas" in e]
    if not vistos:
        lineas.append("  (sin ejecuciones registradas: nada asumido como verde)")
    for e in vistos[-3:]:
        marca = "✅" if e.get("pruebas_ok") else "❌"
        lineas.append(f"  {marca} {e.get('evento')}: {e.get('pruebas')}")
    return _cortar("\n".join(lineas))


def recuperacion(reporte_formateado: str) -> str:
    return _cortar("## Recuperación\n\n" + reporte_formateado)
