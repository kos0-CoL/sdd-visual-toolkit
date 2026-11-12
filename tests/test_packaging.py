"""Empaquetado: `pip install -e .` debe exponer el comando `toolkit`.

El repo usa paquetes de espacio de nombres (sin `__init__.py`), así que el
descubrimiento automático de setuptools falla con "Multiple top-level
packages discovered". Estas pruebas fijan la configuración explícita y evitan
que vuelva a romperse.
"""

from __future__ import annotations

import contextlib
import fnmatch
import importlib
import io
import re
import tempfile
import tomllib
import unittest
from pathlib import Path

from cli.main import main
from core.version import version

RAIZ = Path(__file__).resolve().parent.parent


def _config() -> dict:
    return tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))


def _find() -> dict:
    return _config()["tool"]["setuptools"]["packages"]["find"]


# Carpetas que el empaquetado deja dentro del clon: `pip install .` y
# `python -m build` crean build/ y dist/, y setuptools deja *.egg-info/.
GENERADAS = frozenset({"build", "dist"})


def _paquetes_reales(raiz: Path = RAIZ) -> set[str]:
    """Carpetas de la raíz con módulos Python, excluyendo lo que no se instala.

    `tests`, `docs`, `ide` y `scripts` son suite, documentación y herramientas
    de mantenimiento: se ejecutan desde el árbol, no forman parte del paquete.
    Las carpetas generadas al empaquetar tampoco: incluirlas hacía fallar esta
    prueba justo después de un `pip install .` en el propio clon.
    """
    encontrados = set()
    for carpeta in sorted(raiz.iterdir()):
        if not carpeta.is_dir() or carpeta.name.startswith("."):
            continue
        if carpeta.name in {"tests", "docs", "ide", "scripts"} | GENERADAS:
            continue
        if carpeta.name.endswith((".egg-info", ".eggs")):
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

    def test_guion_sdd_es_el_mismo_programa(self):
        """`sdd` es el nombre corto para usar dentro del proyecto; no puede
        apuntar a otra función ni quedar como alias huérfano."""
        guiones = _config()["project"]["scripts"]
        self.assertEqual(guiones.get("sdd"), "cli.main:main")
        self.assertEqual(guiones["toolkit"], guiones["sdd"])

    def test_patrones_cubren_todos_los_paquetes(self):
        patrones = _find()["include"]
        self.assertTrue(patrones)
        for paquete in _paquetes_reales():
            self.assertTrue(any(fnmatch.fnmatch(paquete, p) for p in patrones),
                            f"el paquete {paquete!r} no está incluido en {patrones}")

    def test_ignora_carpetas_generadas_al_empaquetar(self):
        """`pip install .` deja build/ y *.egg-info/ dentro del clon; no son
        paquetes del proyecto y no deben romper esta prueba."""
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            for nombre in ("build/lib/cli", "dist/cli",
                           "sdd_toolkit.egg-info", "core", "docs"):
                (raiz / nombre).mkdir(parents=True)
                (raiz / nombre / "x.py").write_text("", encoding="utf-8")
            self.assertEqual(_paquetes_reales(raiz), {"core"})

    def test_namespaces_habilitado(self):
        find = _find()
        self.assertTrue(find.get("namespaces") is True)
        self.assertFalse((RAIZ / "core" / "__init__.py").exists(),
                         "si se agregan __init__.py, revise esta configuración")


class TestVersion(unittest.TestCase):
    def setUp(self):
        self.version_pyproject = _config()["project"]["version"]

    def test_version_sale_de_pyproject(self):
        self.assertEqual(version(), self.version_pyproject)

    def test_cli_expone_la_version(self):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            with self.assertRaises(SystemExit) as error:
                main(["--version"])
        self.assertEqual(error.exception.code, 0)
        self.assertEqual(salida.getvalue().strip(),
                         f"toolkit {self.version_pyproject}")

    def test_mcp_usa_la_misma_version(self):
        servidor = importlib.import_module("mcp.server")
        self.assertEqual(servidor.VERSION, version())

    def test_version_coincide_con_el_changelog(self):
        texto = (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")
        publicadas = re.findall(r"^## \[([^\]]+)\] — \d{4}-\d{2}-\d{2}$",
                                texto, re.MULTILINE)
        self.assertTrue(publicadas, "el CHANGELOG no tiene versiones publicadas")
        self.assertEqual(publicadas[0], self.version_pyproject,
                         "la versión de pyproject.toml y la primera del "
                         "CHANGELOG deben coincidir; actualice ambas al "
                         "preparar una versión")



if __name__ == "__main__":
    unittest.main()
