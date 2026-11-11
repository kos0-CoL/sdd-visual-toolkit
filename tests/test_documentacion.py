"""La documentación del repo no puede apuntar a rutas que no existen.

Los enlaces de las notas de release son URL absolutas a `blob/<tag>` y los
revisa `scripts/verificar_release.py`; aquí se cubre lo otro: los enlaces
relativos de los documentos del repo y las referencias `ruta.py::símbolo` de
los documentos de remediación, que se rompen en silencio cuando el código se
mueve.
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Se ignoran los bloques de código: ahí hay órdenes de ejemplo, no enlaces.
_BLOQUE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
_ENLACE = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_DEFINICION = re.compile(r"^\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
# Solo rutas de paquetes del repo: si no, la prosa que cita «archivo.py::
# símbolo» como ejemplo cuenta como referencia real.
_SIMBOLO = re.compile(
    r"`((?:cli|core|mcp|scripts|state|tests)/[\w./-]+\.py)::"
    r"([A-Za-z_][A-Za-z0-9_]*)`")

# Carpetas que el toolkit escribe en el proyecto del usuario, no en este repo.
GENERADAS = (".claude/skills/", ".cursor/commands/", ".github/prompts/",
             ".windsurf/workflows/", ".agents/skills/", ".specify/")
# Notas y versiones con hueco: `release-notes-vX.Y.Z.md` es una plantilla.
PLANTILLAS = ("release-notes-vX.Y.Z.md",)


def documentos() -> list[Path]:
    return sorted(p for patron in ("*.md", "docs/*.md", "ide/*.md",
                                   "ide/vscode/*.md")
                  for p in RAIZ.glob(patron))


def _sin_bloques(ruta: Path) -> str:
    return _BLOQUE.sub("", ruta.read_text(encoding="utf-8"))


class TestEnlacesRelativos(unittest.TestCase):
    def test_los_enlaces_relativos_existen(self):
        revisados = 0
        for ruta in documentos():
            for destino in (_ENLACE.findall(_sin_bloques(ruta)) +
                            _DEFINICION.findall(_sin_bloques(ruta))):
                if destino.startswith(("http://", "https://", "mailto:", "#")):
                    continue  # los absolutos los revisa el verificador
                if destino.startswith(GENERADAS) or destino in PLANTILLAS:
                    continue
                if "X.Y.Z" in destino:
                    continue
                revisados += 1
                objetivo = (ruta.parent / destino.split("#", 1)[0]).resolve()
                self.assertTrue(objetivo.exists(),
                                f"{ruta.relative_to(RAIZ)} enlaza a "
                                f"{destino}, que no existe")
        self.assertGreater(revisados, 5,
                           "la revisión no encontró enlaces: ¿cambió el formato?")

    def test_los_documentos_estan_en_la_lista(self):
        """Si el glob deja de encontrar un documento, el test pasaría vacío."""
        nombres = {p.name for p in documentos()}
        for esperado in ("README.md", "CHANGELOG.md", "CONTRIBUTING.md",
                         "RELEASES.md", "COMPATIBILIDAD.md", "PRUEBA-MANUAL.md"):
            self.assertIn(esperado, nombres)


class TestReferenciasASimbolos(unittest.TestCase):
    """`core/build.py::ejecutar_pruebas` tiene que seguir existiendo."""

    def test_cada_simbolo_citado_existe(self):
        revisados = 0
        for ruta in documentos():
            for archivo, simbolo in _SIMBOLO.findall(_sin_bloques(ruta)):
                revisados += 1
                destino = (RAIZ / archivo)
                self.assertTrue(destino.is_file(),
                                f"{ruta.relative_to(RAIZ)} cita {archivo}, "
                                f"que no existe")
                arbol = ast.parse(destino.read_text(encoding="utf-8"))
                nombres = {n.name for n in ast.walk(arbol)
                           if isinstance(n, (ast.FunctionDef,
                                             ast.AsyncFunctionDef,
                                             ast.ClassDef))}
                nombres |= {t.id for n in ast.walk(arbol)
                            if isinstance(n, ast.Assign)
                            for t in n.targets if isinstance(t, ast.Name)}
                self.assertIn(simbolo, nombres,
                              f"{ruta.relative_to(RAIZ)} cita "
                              f"{archivo}::{simbolo}, que ya no está")
        self.assertGreater(revisados, 3, "no se encontró ninguna referencia")


if __name__ == "__main__":
    unittest.main()
