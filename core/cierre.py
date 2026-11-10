"""RF-37 — Mensajes finales de cada fase (§27).

Bloque uniforme de cierre con los 7 puntos §27: resumen, archivos,
validaciones, pendientes, estado persistido, siguiente paso y
controles. Render puro; la CLI lo rellena con artefactos reales y,
sin datos, lo dice en vez de inventar.
"""

from __future__ import annotations


def bloque(fase: str, resumen: str, archivos: list[str],
           validaciones: list[str], pendientes: list[str],
           estado: str, proxima: str, pills: list[str]) -> str:
    """Mensaje final §27. Listas vacías se declaran, no se rellenan."""
    lineas = ["🟢 CIERRE: %s." % fase,
              "1. Resumen: %s" % (resumen or "—")]
    if archivos:
        lineas.append("2. Archivos generados o modificados (%d):" % len(archivos))
        for rel in archivos[:12]:
            lineas.append("   • %s" % rel)
        if len(archivos) > 12:
            lineas.append("   …y %d más" % (len(archivos) - 12))
    else:
        lineas.append("2. Archivos: (sin archivos registrados).")
    if validaciones:
        lineas.append("3. Validaciones:")
        for valid in validaciones[:8]:
            lineas.append("   • %s" % valid)
        if len(validaciones) > 8:
            lineas.append("   …y %d más" % (len(validaciones) - 8))
    else:
        lineas.append("3. Validaciones: (sin validaciones registradas).")
    if pendientes:
        lineas.append("4. Problemas pendientes (%d):" % len(pendientes))
        for pend in pendientes[:8]:
            lineas.append("   • %s" % pend)
        if len(pendientes) > 8:
            lineas.append("   …y %d más" % (len(pendientes) - 8))
    else:
        lineas.append("4. Problemas pendientes: ninguno registrado.")
    lineas.append("5. Estado persistido: %s" % (estado or "—"))
    lineas.append("6. Siguiente paso recomendado: %s" % (proxima or "—"))
    if pills:
        lineas.append("7. Controles: %s" % "  ".join("[ %s ]" % p for p in pills))
    else:
        lineas.append("7. Controles: (sin controles disponibles).")
    return "\n".join(lineas)
