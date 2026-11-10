"""RF-23 — Tests de aceptación (§18, SPEC: casos Given-When-Then).

Los casos de aceptación (CP-XXX) viven en la SPEC y se vinculan a
criterios de los requerimientos de la tarea. Esta capa los hace
EJECUTABLES: un test de aceptación es un archivo *accept*.py /
*aceptacion*.py cuyo método menciona el ID del caso que cubre
(docstring o comentario con ``CP-001``).

- Caso vinculado + cubierto + verde → pasada.
- Caso vinculado + cubierto + rojo → fallida (con el error real).
- Caso vinculado + sin prueba → omitida (honesto: falta escribirla,
  no se inventa resultado).
- Casos de otros requerimientos: se ignoran (no son de esta tarea).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

PATRONES_ACCEPT = ("accept", "aceptacion", "aceptación")
RE_CASO = re.compile(r"\b(?:CP|CAS)-\d+\b")


def es_accept(rel: str) -> bool:
    """¿Es un archivo de tests de aceptación por convención de nombre?"""
    nombre = rel.rsplit("/", 1)[-1].lower()
    return (nombre.endswith(".py") and rel.startswith("tests/")
            and any(p in nombre for p in PATRONES_ACCEPT))


def extraer_cobertura(raiz, archivos: list[str]) -> dict[str, list[str]]:
    """Mapea caso_id → [selectores que lo cubren].

    Un método ``test_*`` cubre un caso si su docstring o su código
    menciona el ID del caso. El selector es ``modulo.Clase.metodo``.
    """
    cobertura: dict[str, list[str]] = {}
    for rel in archivos:
        ruta = Path(raiz) / rel
        if not ruta.is_file():
            continue
        try:
            fuente = ruta.read_text(encoding="utf-8")
            arbol = ast.parse(fuente, filename=rel)
        except (SyntaxError, UnicodeDecodeError):
            continue
        modulo = rel[:-3].replace("/", ".")
        for nodo in ast.walk(arbol):
            if not (isinstance(nodo, ast.ClassDef)
                    and nodo.name.startswith("Test")):
                continue
            for metodo in nodo.body:
                if not (isinstance(metodo, ast.FunctionDef)
                        and metodo.name.startswith("test")):
                    continue
                texto = ast.get_docstring(metodo) or ""
                texto += "\n" + (ast.get_source_segment(fuente, metodo) or "")
                for caso_id in sorted(set(RE_CASO.findall(texto))):
                    selector = "%s.%s.%s" % (modulo, nodo.name, metodo.name)
                    cobertura.setdefault(caso_id, []).append(selector)
    return {caso: sorted(set(sels)) for caso, sels in cobertura.items()}


def evaluar(raiz, tarea, spec) -> dict:
    """Capa de aceptación ejecutable. Nunca inventa casos."""
    from core.harness import (  # noqa: PLC0415  (evita import circular)
        _correr_pytest, _correr_unittest, detectar_runner)
    base = {"fase": "aceptación", "total": 0, "pasadas": 0,
            "fallidas": 0, "omitidas": 0, "duracion_s": 0.0,
            "ok": True, "errores": "", "casos": []}
    if spec is None:
        base["errores"] = "sin SPEC vinculada (no se inventan casos)"
        return base
    # La tarea declara sus casos en `pruebas` (["CP-001", ...]); las
    # entradas "(crear con la implementación)" son placeholders, no casos.
    pedidos = []
    for p in (tarea.pruebas or []):
        m = RE_CASO.search(p)
        if m and "crear con la implementaci" not in p:
            pedidos.append(m.group(0))
    por_id = {k.id: k for k in (getattr(spec, "casos", None) or [])}
    casos = [por_id[c] for c in pedidos if c in por_id]
    if not casos:
        base["errores"] = ("sin casos Given-When-Then para estos refs: "
                           "verificación humana pendiente")
        return base
    tests_tarea = [a for a in tarea.archivos if es_accept(a)
                   and (Path(raiz) / a).is_file()]
    cobertura = extraer_cobertura(raiz, tests_tarea)
    runner = detectar_runner(raiz)
    if runner == "pytest":
        def correr(r, sels, _r=_correr_pytest):
            conv = []
            for s in sels:
                partes = s.split(".")
                conv.append("/".join(partes[:-2]) + ".py::"
                            + "::".join(partes[-2:]))
            return _r(r, conv)
    else:
        correr = _correr_unittest
    detalles = []
    estados = []
    total = pasadas = fallidas = omitidas = 0
    dur = 0.0
    for caso in casos:
        total += 1
        sels = cobertura.get(caso.id, [])
        if not sels:
            omitidas += 1
            detalle = ("%s: SIN PRUEBA ejecutable "
                       "(verificación humana pendiente)" % caso.id)
            detalles.append(detalle)
            estados.append({"id": caso.id, "estado": "omitida",
                            "detalle": detalle})
            continue
        r = correr(raiz, sels)
        dur += r.get("duracion_s", 0.0)
        if r["ok"]:
            pasadas += 1
            detalle = ("%s: CUBIERTO y verde (%d pruebas)"
                       % (caso.id, r["total"]))
            detalles.append(detalle)
            estados.append({"id": caso.id, "estado": "pasada",
                            "detalle": detalle})
        else:
            fallidas += 1
            detalle = ("%s: CUBIERTO pero ROJO — %s"
                       % (caso.id, r["errores"]))
            detalles.append(detalle)
            estados.append({"id": caso.id, "estado": "fallida",
                            "detalle": detalle})
    base.update({"total": total, "pasadas": pasadas,
                 "fallidas": fallidas, "omitidas": omitidas,
                 "duracion_s": round(dur, 3),
                 "ok": fallidas == 0, "errores": "; ".join(detalles),
                 "casos": estados})
    return base
