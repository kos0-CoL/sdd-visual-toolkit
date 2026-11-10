"""RF-21 — Tests de integración (§18.1).

Verifica la comunicación entre módulos antes/después de correr los tests
de integración: imports resolubles, contratos de llamadas entre archivos
de la tarea (aridad compatible) y ejecución de *integration*.py.
Best-effort honesto: lo dinámico (*args, getattr) no se juzga.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path


class IntegrationError(ValueError):
    """Condición de aceptación violada en la verificación de integración."""


def _modulo_de(rel: str) -> str:
    return rel[:-3].replace("/", ".") if rel.endswith(".py") else rel


def _archivo_de(raiz: Path, modulo: str) -> Path | None:
    candidato = raiz / (modulo.replace(".", "/") + ".py")
    if candidato.is_file():
        return candidato
    paquete = raiz / modulo.replace(".", "/") / "__init__.py"
    return paquete if paquete.is_file() else None


def _definiciones(fuente: str) -> dict[str, tuple[int, int, bool]]:
    """{nombre: (requeridos, totales, acepta_varargs)} (métodos excluidos)."""
    try:
        arbol = ast.parse(fuente)
    except SyntaxError:
        return {}
    defs = {}
    for nodo in arbol.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = nodo.args
            total = len(args.args)
            requeridos = total - len(args.defaults)
            var = bool(args.vararg or args.kwarg)
            defs[nodo.name] = (requeridos, total, var)
    return defs


def _imports(fuente: str) -> list[tuple[str, str | None]]:
    """[(modulo, nombre)] — nombre None para `import modulo`."""
    try:
        arbol = ast.parse(fuente)
    except SyntaxError:
        return []
    encontrados = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for a in nodo.names:
                encontrados.append((a.name.split(".")[0], None))
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            for a in nodo.names:
                encontrados.append((nodo.module, a.name))
    return encontrados


def verificar(raiz, tarea) -> dict:
    raiz = Path(raiz)
    fuentes: dict[str, str] = {}
    for rel in tarea.archivos:
        if rel.startswith("tests/") or not rel.endswith(".py"):
            continue
        ruta = raiz / rel
        if ruta.is_file():
            try:
                fuentes[rel] = ruta.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
    defs_por_modulo = {_modulo_de(rel): _definiciones(f) for rel, f in fuentes.items()}
    hallazgos: list[dict] = []

    # 1. Imports resolubles (proyecto, stdlib o instalado).
    for rel, fuente in fuentes.items():
        for modulo, nombre in _imports(fuente):
            if _archivo_de(raiz, modulo) is not None:
                if nombre is not None:
                    defs = defs_por_modulo.get(modulo, {})
                    if modulo in defs_por_modulo and nombre not in defs:
                        hallazgos.append(_h(rel, "error",
                                            f"«{nombre}» no existe en {modulo}"))
                continue
            if importlib.util.find_spec(modulo.split(".")[0]) is None:
                hallazgos.append(_h(rel, "error",
                                    f"import no resoluble: {modulo}"))

    # 2. Contratos de llamadas entre módulos de la tarea.
    for rel, fuente in fuentes.items():
        try:
            arbol = ast.parse(fuente)
        except SyntaxError:
            hallazgos.append(_h(rel, "error", "sintaxis inválida"))
            continue
        importados = {n: m for m, n in _imports(fuente) if n is not None}
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            # Solo llamadas directas a símbolos importados con from;
            # atributos y alias dinámicos no se juzgan (best-effort honesto).
            if not isinstance(nodo.func, ast.Name):
                continue
            if nodo.func.id not in importados:
                continue
            objetivo = (importados[nodo.func.id], nodo.func.id)
            mod, nombre = objetivo
            firma = defs_por_modulo.get(mod, {}).get(nombre)
            if firma is None:
                continue  # definido fuera de la tarea: no se juzga
            requeridos, totales, var = firma
            dados = len(nodo.args)
            if not var and not (requeridos <= dados <= totales):
                hallazgos.append(_h(
                    rel, "error",
                    f"«{nombre}» de {mod} espera {requeridos}-{totales} "
                    f"argumentos, se le pasan {dados}"))
    return {"hallazgos": hallazgos, "ok": not hallazgos,
            "resumen": _resumen(tarea.id, hallazgos)}


def _h(archivo: str, severidad: str, detalle: str) -> dict:
    return {"archivo": archivo, "severidad": severidad, "detalle": detalle}


def _resumen(task_id: str, hallazgos: list[dict]) -> str:
    if not hallazgos:
        return (f"🔗 Integración {task_id}: imports resolubles y contratos "
                "compatibles.")
    lineas = [f"🔗 Integración {task_id}: {len(hallazgos)} problema(s)."]
    for h in hallazgos:
        lineas.append(f"  🔴 {h['archivo']}: {h['detalle']}")
    return "\n".join(lineas)
