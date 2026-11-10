"""RF-41 — Archivo de instrucciones del agente (§47, §11.3).

Documento markdown generado desde el estado real: reglas del motor,
foto viva del proyecto, restricciones activas y siguiente paso
ejecutable. Lo consume cualquier agente o IDE como contexto inicial.
Render puro; la CLI lo rellena con artefactos reales.
"""

from __future__ import annotations


REGLAS = [
    "Lea el estado actual antes de actuar (`tablero`, `export`).",
    "No avance de fase con gates bloqueados: la validación es humana.",
    "No avance a otra tarea sin completar o registrar la actual.",
    "Solo toque archivos modificables del plan; lo intacto no se toca.",
    "Si encuentra algo fuera de alcance, regístrelo como sugerencia "
    "(pin), no lo implemente en silencio.",
    "Pruebe antes de cerrar (`test`, `validate`, `diff`).",
    "Los fallos se declaran (`fallida` con nota); nada se oculta.",
    "Regenere este archivo tras cada fase (`instrucciones --guardar`).",
]


def documento(estado: dict, secciones: list, navegacion: dict) -> str:
    """secciones: [(icono, nombre, [items])] como en restricciones."""
    lineas = ["# Instrucciones del agente — SDD Visual Toolkit",
              "",
              "Generado desde el estado real del proyecto. Si contradice "
              "una suposición, manda el estado.",
              "",
              "## 1. Reglas del motor"]
    for n, regla in enumerate(REGLAS, 1):
        lineas.append("%d. %s" % (n, regla))
    lineas += ["",
               "## 2. Estado actual",
               "",
               "- Fase: %s" % estado.get("fase", "sin SPEC"),
               "- SPEC: %s" % (estado.get("spec_id") or "—"),
               "- Tarea actual: %s" % (estado.get("tarea_actual") or "—"),
               "- Última completada: %s"
               % (estado.get("ultima_completada") or "—"),
               "- Pruebas: %s" % estado.get("pruebas", "sin corridas"),
               "- Próxima: %s" % estado.get("proxima", "—")]
    for err in estado.get("errores") or []:
        lineas.append("- ⛔ %s" % err)
    lineas += ["", "## 3. Restricciones activas", ""]
    if not secciones:
        lineas.append("(sin SPEC: sin fronteras todavía)")
    for icono, nombre, items in secciones:
        lineas.append("### %s %s" % (icono, nombre))
        lineas.append("")
        if items:
            for item in items[:15]:
                lineas.append("- %s" % item)
            if len(items) > 15:
                lineas.append("- …y %d más" % (len(items) - 15))
        else:
            lineas.append("(sin datos registrados)")
        lineas.append("")
    rec = (navegacion.get("recomendada") or {}).get("comando")
    lineas += ["## 4. Siguiente paso", ""]
    lineas.append("- Recomendado: `%s`" % (rec or "—"))
    for p in navegacion.get("pills") or []:
        marca = "🔒" if p.get("bloqueada") else "▫"
        lineas.append("- %s `%s` — %s%s" % (
            marca, p.get("comando", "?"), p.get("etiqueta", ""),
            (" (%s)" % p["motivo"]) if p.get("motivo") else ""))
    for bloqueo in navegacion.get("bloqueos") or []:
        lineas.append("- ⛔ %s" % bloqueo)
    if navegacion.get("requiere_aprobacion"):
        lineas.append("- Requiere aprobación humana: no avance solo.")
    return "\n".join(lineas).rstrip() + "\n"
