"""RF-28 — Protección de pruebas (§18.3).

La IA no debe modificar los tests para conseguir que el resultado sea
verde. El pin ignora los tests a propósito (la evidencia evoluciona);
esta capa los vigila en el cierre:

- Test modificado desde la línea base sin --nota → observación
  (exige documentar el cambio).
- Test modificado con --nota → permitido (la nota ES la
  documentación que exige §18.3: prueba incorrecta o desactualizada
  por cambio aprobado).
- Test modificado después de una corrida en rojo → se marca
  "verde por edición" (sospechoso): exige --nota igualmente.

Nunca se impide corregir un test; se impide hacerlo en silencio.
"""

from __future__ import annotations

from pathlib import Path


def _sha16(ruta: Path) -> str | None:
    try:
        import hashlib
        return hashlib.sha256(ruta.read_bytes()).hexdigest()[:16]
    except OSError:
        return None


def verificar(raiz, tarea, baseline: dict, eventos: list[dict],
              nota: str = "") -> dict:
    """Devuelve {modificados, sospechosos, observaciones}."""
    raiz = Path(raiz)
    tests = [a for a in tarea.archivos
             if a.startswith("tests/") and a.endswith(".py")
             and (raiz / a).is_file()]
    ultima_roja = {}
    ultima = None
    for e in reversed(eventos):
        if e.get("evento") == "tests" and e.get("tarea") == tarea.id:
            if ultima is None:
                ultima = e
            if not e.get("pruebas_ok"):
                ultima_roja = e.get("hashes_tests") or {}
                break
    modificados, sospechosos, desactualizados = [], [], []
    observaciones = []
    documentado = bool((nota or "").strip())
    for rel in sorted(tests):
        actual = _sha16(raiz / rel)
        if actual is None:
            continue
        viejo_pin = (baseline.get(rel) or {}).get("sha", "")
        if viejo_pin and actual != viejo_pin[:16]:
            modificados.append(rel)
            if not documentado:
                observaciones.append(
                    "%s modificado desde el inicio de la tarea "
                    "sin documentar: justifique con --nota (§18.3)" % rel)
        if ultima_roja and ultima_roja.get(rel) != actual:
            sospechosos.append(rel)
            if not documentado:
                observaciones.append(
                    "%s cambiado tras una corrida en rojo "
                    "(posible «verde por edición»): justifique con "
                    "--nota (§18.3)" % rel)
        if ultima is not None:
            vistos = ultima.get("hashes_tests") or {}
            if rel in vistos and vistos[rel] != actual:
                desactualizados.append(rel)
                if not documentado:
                    observaciones.append(
                        "%s cambió tras la última corrida: la evidencia "
                        "es anterior al cambio; re-ejecute `test %s` o "
                        "justifique con --nota" % (rel, tarea.id))
    return {"modificados": modificados, "sospechosos": sospechosos,
            "desactualizados": desactualizados,
            "observaciones": observaciones}
