"""RF-34 — Visual AST Diff (§24).

Vista estructural (AST: funciones, firmas, variables, imports) +
vista comparativa (diff de código) + cambios fuera de alcance +
resultado de validación: por qué el cambio fue aceptado o rechazado.
Todo sale de snapshots reales y del árbol actual; sin antes, se dice.
"""

from __future__ import annotations

import ast as py_ast
import difflib


def analizar_fuente(src: str) -> dict:
    """Símbolos estructurales de una fuente Python."""
    try:
        arbol = py_ast.parse(src)
    except SyntaxError:
        return {"error": "no analizable (SyntaxError)"}
    funciones, clases, imports, variables = {}, [], [], {}
    for nodo in arbol.body:
        if isinstance(nodo, (py_ast.FunctionDef, py_ast.AsyncFunctionDef)):
            args = [a.arg for a in nodo.args.args]
            ret = py_ast.unparse(nodo.returns) if nodo.returns else "—"
            funciones[nodo.name] = "(%s) -> %s" % (", ".join(args), ret)
        elif isinstance(nodo, py_ast.ClassDef):
            clases.append(nodo.name)
        elif isinstance(nodo, (py_ast.Import, py_ast.ImportFrom)):
            imports.append(py_ast.unparse(nodo))
        elif isinstance(nodo, py_ast.Assign):
            for t in nodo.targets:
                if isinstance(t, py_ast.Name):
                    variables[t.id] = py_ast.unparse(nodo.value)[:60]
        elif isinstance(nodo, py_ast.AnnAssign):
            if isinstance(nodo.target, py_ast.Name) and nodo.value:
                variables[nodo.target.id] = py_ast.unparse(nodo.value)[:60]
    return {"funciones": funciones, "clases": clases, "imports": imports,
            "variables": variables}


def comparar_estructural(antes: dict, despues: dict) -> dict:
    """Diferencia estructural entre dos análisis."""
    if "error" in antes or "error" in despues:
        return {"no_analizable": True}
    fa, fd = antes["funciones"], despues["funciones"]
    va, vd = antes["variables"], despues["variables"]
    ia, id_ = set(antes["imports"]), set(despues["imports"])
    ca, cd = set(antes["clases"]), set(despues["clases"])
    return {
        "funciones_agregadas": sorted(set(fd) - set(fa)),
        "funciones_eliminadas": sorted(set(fa) - set(fd)),
        "firmas_modificadas": sorted(
            n for n in set(fa) & set(fd) if fa[n] != fd[n]),
        "variables_agregadas": sorted(set(vd) - set(va)),
        "variables_eliminadas": sorted(set(va) - set(vd)),
        "variables_modificadas": sorted(
            n for n in set(va) & set(vd) if va[n] != vd[n]),
        "imports_agregados": sorted(id_ - ia),
        "imports_eliminados": sorted(ia - id_),
        "clases_agregadas": sorted(cd - ca),
        "clases_eliminadas": sorted(ca - cd),
    }


def comparativa(antes: str, despues: str, archivo: str,
                max_lineas: int = 60) -> list[str]:
    """Diff unificado truncado y marcado."""
    diff = list(difflib.unified_diff(
        antes.splitlines(), despues.splitlines(),
        fromfile="antes/%s" % archivo, tofile="después/%s" % archivo,
        lineterm=""))
    if len(diff) > max_lineas:
        return diff[:max_lineas] + ["… (truncado: %d líneas más)" % (
            len(diff) - max_lineas)]
    return diff


def fuera_de_alcance(arbol_pin: set, actuales: set,
                     autorizados: set) -> list[str]:
    """Archivos actuales fuera de la línea base y de la tarea."""
    return sorted(a for a in actuales
                  if a not in arbol_pin and a not in autorizados)


def vista(archivo: str, estado_archivo: str, estructural: dict,
          lineas_diff: list[str], sin_antes: bool = False) -> str:
    """Render §24 de un archivo."""
    lineas = ["📄 %s: %s." % (archivo, estado_archivo)]
    if sin_antes:
        lineas.append("   (sin antes: solo se muestra el después)")
    if estructural.get("no_analizable"):
        lineas.append("   Estructural: no analizable.")
    else:
        pares = [
            ("Funciones agregadas",
             estructural.get("funciones_agregadas", [])),
            ("Funciones eliminadas",
             estructural.get("funciones_eliminadas", [])),
            ("Firmas modificadas",
             estructural.get("firmas_modificadas", [])),
            ("Variables agregadas",
             estructural.get("variables_agregadas", [])),
            ("Variables eliminadas",
             estructural.get("variables_eliminadas", [])),
            ("Variables con valor distinto",
             estructural.get("variables_modificadas", [])),
            ("Imports agregados",
             estructural.get("imports_agregados", [])),
            ("Imports eliminados",
             estructural.get("imports_eliminados", [])),
            ("Clases agregadas",
             estructural.get("clases_agregadas", [])),
            ("Clases eliminadas",
             estructural.get("clases_eliminadas", [])),
        ]
        mostrados = [(e, v) for e, v in pares if v]
        if not mostrados:
            lineas.append("   Estructural: sin cambios.")
        for etiqueta, vals in mostrados:
            lineas.append("   %s: %s." % (
                etiqueta, ", ".join(str(v) for v in vals)))
    if lineas_diff:
        lineas.append("   Comparativa:")
        lineas.extend("   %s" % l for l in lineas_diff)
    else:
        lineas.append("   Comparativa: sin diferencias de texto.")
    return "\n".join(lineas)
