"""Empaquetado: `pip install -e .` debe exponer el comando `toolkit`.

El repo usa paquetes de espacio de nombres (sin `__init__.py`), así que el
descubrimiento automático de setuptools falla con "Multiple top-level
packages discovered". Estas pruebas fijan la configuración explícita y evitan
que vuelva a romperse.
"""

from __future__ import annotations

import fnmatch
import importlib
import tomllib
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _config() -> dict:
    return tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))


def _find() -> dict:
    return _config()["tool"]["setuptools"]["packages"]["find"]


def _paquetes_reales() -> set[str]:
    """Carpetas de la raíz con módulos Python, excluyendo la suite y los docs."""
    encontrados = set()
    for carpeta in sorted(RAIZ.iterdir()):
        if not carpeta.is_dir() or carpeta.name.startswith("."):
            continue
        if carpeta.name in {"tests", "docs", "ide"}:
            continue
        if any(carpeta.rglob("*.py")):
            encontrados.add(carpeta.name)
    return encontrados


class TestEmpaquetado(unittest.TestCase):
    def test_backend_declarado(self):
        cfg = _config()
        self.assertEqual(cfg["build-system"]["build-backend"],
                         "setuptools.build_meta")
        self.assertTrue(any("setuptools" in r
                            for r in cfg["build-system"]["requires"]))

    def test_guion_toolkit_apunta_a_cli_main(self):
        cfg = _config()
        self.assertEqual(cfg["project"]["scripts"]["toolkit"], "cli.main:main")
        modulo, _, atributo = "cli.main:main".partition(":")
        importado = importlib.import_module(modulo)
        self.assertTrue(callable(getattr(importado, atributo)))

    def test_patrones_cubren_todos_los_paquetes(self):
        patrones = _find()["include"]
        self.assertTrue(patrones)
        for paquete in _paquetes_reales():
            self.assertTrue(any(fnmatch.fnmatch(paquete, p) for p in patrones),
                            f"el paquete {paquete!r} no está incluido en {patrones}")

    def test_namespaces_habilitado(self):
        find = _find()
        self.assertTrue(find.get("namespaces") is True)
        self.assertFalse((RAIZ / "core" / "__init__.py").exists(),
                         "si se agregan __init__.py, revise esta configuración")



if __name__ == "__main__":
    unittest.main()
