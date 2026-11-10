"""RF-33 — Panel de restricciones (§23).

Render puro del panel lateral: fuera de alcance, archivos
protegidos/modificables, interfaces protegidas, reglas de negocio,
restricciones técnicas y decisiones aprobadas. Con contexto de tarea,
clasifica cada archivo contra las fronteras del plan. Sin datos de
un bloque, se dice; nada se inventa.
"""

from __future__ import annotations


def clasificar(archivo: str, modificables: list, intactos: list) -> str:
    """Clasificación de un archivo de tarea contra las fronteras."""
    if archivo in intactos:
        return "🔒 protegido (intacto según plan)"
    if archivo in modificables:
        return "✏️ modificable según plan"
    return "❓ no clasificado en el plan"


def render(titulo: str, secciones: list, tarea: dict | None = None) -> str:
    """secciones: [(icono, nombre, [items])]; tarea: {id, archivos:
    [(ruta, clasificacion)]} o None."""
    lineas = ["🧱 %s." % titulo]
    for icono, nombre, items in secciones:
        lineas.append("%s %s (%d):" % (icono, nombre, len(items)))
        if items:
            for item in items[:10]:
                lineas.append("   · %s" % item)
            if len(items) > 10:
                lineas.append("   …y %d más" % (len(items) - 10))
        else:
            lineas.append("   (sin datos registrados)")
    if tarea is not None:
        lineas.append("Verificando %s (%d archivo(s)):" % (
            tarea.get("id", "?"), len(tarea.get("archivos", []))))
        if not tarea.get("archivos"):
            lineas.append("   (la tarea no declara archivos)")
        for ruta, marca in tarea.get("archivos", []):
            lineas.append("   %s %s" % (marca.split(" ")[0], ruta))
    return "\n".join(lineas)
