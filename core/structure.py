"""RF-24 — Validación estructural (§18: interfaces, firmas, dependencias,
contratos, cambios AST).

Tres comprobaciones estáticas (sin ejecutar código) sobre los archivos
de la tarea, complementarias al diff AST de RF-17:

1. Dependencias: sin ciclos de importación entre módulos de la tarea.
2. Contratos: ningún símbolo público eliminado sigue siendo usado por
   otro archivo de la tarea (contrato roto).
3. Interfaces: todo símbolo público nuevo debe estar mencionado en al
   menos un test de la tarea (trazabilidad a evidencia).

Los ciclos y contratos rotos son defectos (rechazado); la falta de
evidencia es advertencia (justificable con --nota).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from core.integration import _archivo_de, _imports, _modulo_de
from core.pin import snapshot_archivo


def _h(archivo: str, tipo: str, simbolo: str, severidad: str,
       detalle: str) -> dict:
    return {"archivo": archivo, "tipo": tipo, "simbolo": simbolo,
            "severidad": severidad, "detalle": detalle}


def _fuente(raiz: Path, rel: str) -> str | None:
    ruta = raiz / rel
    if not ruta.is_file():
        return None
    try:
        return ruta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _ciclos(raiz: Path, fuentes: dict[str, str]) -> list[dict]:
    """Dependencias circulares entre módulos de la tarea."""
    mod_de_archivo = {_modulo_de(rel): rel for rel in fuentes}
    grafo: dict[str, set[str]] = {}
    for rel, fuente in fuentes.items():
        origen = _modulo_de(rel)
        grafo.setdefault(origen, set())
        for modulo, _nombre in _imports(fuente):
            if _archivo_de(raiz, modulo) is None:
                continue  # externo: no es dependencia interna
            if modulo in mod_de_archivo:
                grafo[origen].add(modulo)
    hallazgos = []
    visitado: dict[str, int] = {}  # 1=en curso, 2=terminado

    def dfs(nodo: str, ruta: list[str]) -> None:
        visitado[nodo] = 1
        for vecino in sorted(grafo.get(nodo, ())):
            if visitado.get(vecino) == 1:
                ciclo = " → ".join(ruta + [vecino])
                hallazgos.append(_h(
                    mod_de_archivo.get(vecino, vecino),
                    "dependencia_circular", vecino, "rechazado",
                    "ciclo de importación: %s" % ciclo))
            elif vecino not in visitado:
                dfs(vecino, ruta + [vecino])
        visitado[nodo] = 2

    for modulo in sorted(grafo):
        if modulo not in visitado:
            dfs(modulo, [modulo])
    return hallazgos


def _usos(fuente: str, simbolo: str) -> bool:
    """¿El código usa `simbolo` (nombre directo o atributo)?"""
    try:
        arbol = ast.parse(fuente)
    except SyntaxError:
        return False
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Name) and nodo.id == simbolo:
            return True
        if isinstance(nodo, ast.Attribute) and nodo.attr == simbolo:
            return True
    return False


def verificar(raiz, tarea, baseline: dict) -> dict:
    """Devuelve {hallazgos} con forma compatible con astcheck."""
    raiz = Path(raiz)
    fuentes: dict[str, str] = {}
    for rel in tarea.archivos:
        if rel.startswith("tests/") or not rel.endswith(".py"):
            continue
        texto = _fuente(raiz, rel)
        if texto is not None:
            fuentes[rel] = texto
    hallazgos = _ciclos(raiz, fuentes)

    # Símbolos públicos eliminados que alguien sigue usando.
    actuales: dict[str, dict] = {}
    for rel in fuentes:
        snap = snapshot_archivo(raiz / rel)
        actuales[rel] = (snap or {}).get("publicas", {})
    for rel in sorted(fuentes):
        viejas = (baseline.get(rel) or {}).get("publicas", {})
        for nombre in sorted(set(viejas) - set(actuales.get(rel, {}))):
            if nombre.startswith("_"):
                continue
            usuarios = sorted(
                otro for otro, texto in fuentes.items()
                if otro != rel and _usos(texto, nombre))
            if usuarios:
                hallazgos.append(_h(
                    rel, "contrato_roto", nombre, "rechazado",
                    "«%s» eliminado pero usado por: %s"
                    % (nombre, ", ".join(usuarios))))

    # Públicos nuevos sin mención en los tests de la tarea.
    tests_texto = []
    for rel in tarea.archivos:
        if rel.startswith("tests/") and rel.endswith(".py"):
            texto = _fuente(raiz, rel)
            if texto is not None:
                tests_texto.append(texto)
    for rel in sorted(fuentes):
        viejas = (baseline.get(rel) or {}).get("publicas", {})
        for nombre in sorted(set(actuales.get(rel, {})) - set(viejas)):
            if nombre.startswith("_"):
                continue
            patron = re.compile(r"\b%s\b" % re.escape(nombre))
            if not any(patron.search(t) for t in tests_texto):
                hallazgos.append(_h(
                    rel, "publico_sin_prueba", nombre, "advertencia",
                    "símbolo público nuevo sin mención en tests: "
                    "agregue evidencia o justifique con --nota"))
    return {"hallazgos": hallazgos}
