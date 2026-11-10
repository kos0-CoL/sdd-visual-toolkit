"""RF-08 — Investigación del repositorio (§8.2, §44 item 5).

Presentación pura de los hallazgos de `core.plan.investigar`:
estructura, lenguajes, dependencias, arquitectura, persistencia,
pruebas y convenciones. Sin hallazgos, se dice; nada se inventa.
"""

from __future__ import annotations


def render(hallazgos: dict) -> str:
    """Informe legible de la investigación del repositorio real."""
    lineas = ["🔎 Investigación del repositorio."]
    if hallazgos.get("es_greenfield"):
        lineas.append("Greenfield: sin código propio todavía.")
    else:
        lineas.append("Greenfield: no (hay código propio).")
    lineas.append("Archivos analizados: %d." % hallazgos.get("total_archivos", 0))

    lenguajes = hallazgos.get("lenguajes") or {}
    if lenguajes:
        detalle = ", ".join("%s (%d)" % (leng, n)
                            for leng, n in sorted(lenguajes.items()))
        lineas.append("Lenguajes: %s." % detalle)
    else:
        lineas.append("Lenguajes: (ninguno detectado).")

    lineas.append("Carpetas superiores: %s." % (
        ", ".join(hallazgos.get("carpetas") or []) or "(ninguna)"))

    codigo = hallazgos.get("codigo") or []
    lineas.append("Componentes de código (%d):" % len(codigo))
    for rel in codigo[:15]:
        lineas.append("   • %s" % rel)
    if len(codigo) > 15:
        lineas.append("   …y %d más" % (len(codigo) - 15))
    if not codigo:
        lineas.append("   (sin archivos de código)")

    internos = hallazgos.get("modulos_internos") or []
    lineas.append("Módulos internos: %s." % (
        ", ".join(internos) or "(ninguno)"))
    externos = hallazgos.get("imports_externos") or []
    lineas.append("Imports externos detectados: %s." % (
        ", ".join(externos) or "(ninguno)"))

    lineas.append("Dependencias (%s): %s." % (
        ", ".join(hallazgos.get("manifiestos") or []) or "sin manifiestos",
        ", ".join(hallazgos.get("dependencias") or []) or "(ninguna)"))

    lineas.append("Persistencia: %s." % (
        ", ".join(hallazgos.get("datos") or []) or "(no detectada)"))

    pruebas = hallazgos.get("pruebas") or []
    lineas.append("Pruebas existentes (%d):" % len(pruebas))
    for rel in pruebas[:10]:
        lineas.append("   • %s" % rel)
    if len(pruebas) > 10:
        lineas.append("   …y %d más" % (len(pruebas) - 10))
    if not pruebas:
        lineas.append("   (sin suite de pruebas)")

    lineas.append("Convenciones: %s." % (
        "; ".join(hallazgos.get("convenciones") or []) or "(ninguna)"))
    return "\n".join(lineas)
