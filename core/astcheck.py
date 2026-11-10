"""RF-17 — Post-Diff Structural Check (§17).

Compara AST base vs. AST final y cruza cada hallazgo con la trazabilidad
semántica (tarea activa, archivos autorizados, objetivo funcional,
contratos de interfaces, evidencias de pruebas). Veredicto §17.4:
ACEPTADO (compatible), ADVERTENCIA (justificable, revisar) o RECHAZADO
(no autorizado o incompatible).
"""

from __future__ import annotations

from pathlib import Path

from core.pin import _es_protegido, snapshot_archivo


class AstCheckError(ValueError):
    """Condición de aceptación violada en el chequeo estructural."""


def comparar(tarea, baseline: dict, raiz) -> dict:
    """Devuelve {hallazgos: [...], veredicto, resumen}."""
    autorizados = set(tarea.archivos)
    hallazgos: list[dict] = []
    for rel in sorted(autorizados):
        snap_viejo = baseline.get(rel)
        snap_nuevo = snapshot_archivo(Path(raiz) / rel)
        if snap_nuevo is None:
            continue
        es_prueba = rel.startswith("tests/")  # la evidencia misma no es sospechosa
        viejo_pub = (snap_viejo or {}).get("publicas", {})
        nuevo_pub = snap_nuevo.get("publicas", {})
        if not es_prueba:
            for nombre in sorted(set(nuevo_pub) - set(viejo_pub)):
                if not nombre.startswith("_"):
                    hallazgos.append(_h(rel, "nueva_funcion" if "(" in nuevo_pub[nombre]
                                        else "nueva_clase",
                                        nombre, "advertencia",
                                        "símbolo público nuevo: justifique trazabilidad "
                                        "a la tarea"))
        for nombre in sorted(set(viejo_pub) - set(nuevo_pub)):
            hallazgos.append(_h(rel, "simbolo_eliminado", nombre, "advertencia",
                                "puede romper llamadores: verifique compatibilidad"))
        for nombre in sorted(set(viejo_pub) & set(nuevo_pub)):
            if viejo_pub[nombre] != nuevo_pub[nombre]:
                hallazgos.append(_h(rel, "firma_cambiada", nombre, "advertencia",
                                    f"{viejo_pub[nombre]} → {nuevo_pub[nombre]}"))
        viejo_ret = (snap_viejo or {}).get("retornos", {})
        for nombre, tipo in sorted(snap_nuevo.get("retornos", {}).items()):
            if nombre in viejo_ret and viejo_ret[nombre] != tipo:
                hallazgos.append(_h(rel, "retorno_cambiado", nombre, "advertencia",
                                    f"{viejo_ret[nombre]} → {tipo}"))
        viejo_imp = (snap_viejo or {}).get("imports", {})
        if not es_prueba:
            for nombre in sorted(set(snap_nuevo.get("imports", {})) - set(viejo_imp)):
                hallazgos.append(_h(rel, "import_nuevo", nombre, "advertencia",
                                    "nueva dependencia: ¿la exige la tarea?"))
        for nombre in sorted(set(viejo_imp) - set(snap_nuevo.get("imports", {}))):
            hallazgos.append(_h(rel, "import_eliminado", nombre, "advertencia",
                                "dependencia retirada: verifique que nada la use"))
        viejo_glo = (snap_viejo or {}).get("globales", {})
        if not es_prueba:
            for nombre in sorted(set(snap_nuevo.get("globales", {})) - set(viejo_glo)):
                hallazgos.append(_h(rel, "global_nueva", nombre, "advertencia",
                                    "estado global nuevo: prefiera parámetros"))
    # Archivos fuera de autorización: §17.3 — sin trazabilidad a la tarea.
    for rel2, detalle in _ajenos(tarea, baseline, raiz):
        hallazgos.append(_h(rel2, "fuera_de_autorizacion", "—", "rechazado",
                            detalle))
    if any(h["severidad"] == "rechazado" for h in hallazgos):
        veredicto = "RECHAZADO"
    elif hallazgos:
        veredicto = "ADVERTENCIA"
    else:
        veredicto = "ACEPTADO"
    return {"hallazgos": hallazgos, "veredicto": veredicto,
            "resumen": _resumen(tarea, hallazgos, veredicto)}


def _h(archivo: str, tipo: str, simbolo: str, severidad: str,
       detalle: str) -> dict:
    return {"archivo": archivo, "tipo": tipo, "simbolo": simbolo,
            "severidad": severidad, "detalle": detalle}


def _ajenos(tarea, baseline: dict, raiz) -> list[tuple[str, str]]:
    """Cambios en .py fuera de los autorizados (foto amplia, §12/§17.3)."""
    from core.pin import foto_arbol  # noqa: PLC0415

    autorizados = set(tarea.archivos)
    amplia = baseline.get("__arbol__", {})
    actual = foto_arbol(raiz)
    ajenos = []
    for rel in sorted(set(amplia) | set(actual)):
        if rel in autorizados or rel.startswith("tests/"):
            continue
        if not (Path(raiz) / rel).is_file():
            continue
        sha_vieja = amplia.get(rel, {}).get("sha")
        ahora = snapshot_archivo(Path(raiz) / rel)
        if ahora is None or ahora["sha"] == sha_vieja:
            continue
        if _es_protegido(rel):
            ajenos.append((rel, "archivo protegido modificado sin autorización"))
        else:
            ajenos.append((rel, "cambio sin trazabilidad a la tarea activa"))
    return ajenos


def _resumen(tarea, hallazgos: list[dict], veredicto: str) -> str:
    lineas = [f"🔍 AST {tarea.id}: {len(hallazgos)} hallazgo(s) → {veredicto}."]
    for h in hallazgos:
        marca = "🔴" if h["severidad"] == "rechazado" else "🟡"
        lineas.append(f"{marca} [{h['tipo']}] {h['archivo']}::{h['simbolo']}: "
                      f"{h['detalle']}")
    if veredicto == "ACEPTADO":
        lineas.append("Cambios compatibles con la tarea: continuar.")
    elif veredicto == "ADVERTENCIA":
        lineas.append("Revisar antes de cerrar: toda advertencia necesita "
                      "justificación con --nota.")
    else:
        lineas.append("Rechazar o revisar: hay cambios no autorizados.")
    return "\n".join(lineas)
