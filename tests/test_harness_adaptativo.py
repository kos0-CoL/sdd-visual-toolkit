"""Pruebas de RF-43 — Testing adaptativo multi-lenguaje (§51).

El repo manda: package.json/go.mod/Cargo.toml seleccionan su runner
propio sin imponer pytest. Los binarios se simulan con stubs en PATH;
lo verificado es detección, despacho y parseo, no los toolchains.
"""

import os
import stat
import tempfile
import unittest
from pathlib import Path

from core.harness import (  # noqa: E402
    _parsear_cargo,
    _parsear_go,
    _parsear_npm,
    correr,
    detectar_runner,
)

JEST_VERDE = "Tests: 3 passed, 3 total"
MOCHA_ROJO = "5 passing / 1 failing / 2 pending"
VITEST = "Test Files 1 passed (1) / Tests 4 passed (4)"
GO_OK = chr(10).join(["ok ejemplo.com/demo",
                       "--- PASS: TestSuma",
                       "--- PASS: TestResta"])
CARGO_OK = "test result: ok. 2 passed; 0 failed; 1 ignored"


def _stub(bin_dir, nombre, cuerpo, codigo=0):
    ruta = bin_dir / nombre
    inicio = "#!/bin/sh" + chr(10) + cuerpo + chr(10) + "exit %d" % codigo
    ruta.write_text(inicio, encoding="utf-8")
    ruta.chmod(ruta.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)


class TestDetectar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self._path_anterior = os.environ.get("PATH", "")
        os.environ["PATH"] = str(self.bin) + os.pathsep + self._path_anterior
        self.addCleanup(self._restaurar_path)

    def _restaurar_path(self):
        os.environ["PATH"] = self._path_anterior

    def test_repo_js_elige_npm(self):
        (self.root / "package.json").write_text(
            '{"scripts": {"test": "jest"}}', encoding="utf-8")
        _stub(self.bin, "npm", "echo hola")
        self.assertEqual(detectar_runner(self.root), "npm")

    def test_repo_go_y_rust(self):
        (self.root / "go.mod").write_text("module demo", encoding="utf-8")
        _stub(self.bin, "go", "echo hola")
        self.assertEqual(detectar_runner(self.root), "go")
        (self.root / "go.mod").unlink()
        (self.root / "Cargo.toml").write_text("[package]",
                                              encoding="utf-8")
        _stub(self.bin, "cargo", "echo hola")
        self.assertEqual(detectar_runner(self.root), "cargo")

    def test_sin_marcadores_no_impone_nada_externo(self):
        self.assertEqual(detectar_runner(self.root), "unittest")

    def test_js_sin_node_cae_a_python(self):
        (self.root / "package.json").write_text(
            '{"scripts": {"test": "jest"}}', encoding="utf-8")
        os.environ["PATH"] = str(self.bin)
        self.assertEqual(detectar_runner(self.root), "unittest")


class TestParseo(unittest.TestCase):
    def test_jest(self):
        r = _parsear_npm(JEST_VERDE)
        self.assertEqual((r["pasadas"], r["fallidas"]), (3, 0))

    def test_mocha(self):
        r = _parsear_npm(MOCHA_ROJO)
        self.assertEqual(
            (r["pasadas"], r["fallidas"], r["omitidas"]), (5, 1, 2))

    def test_vitest(self):
        r = _parsear_npm(VITEST)
        self.assertEqual(r["pasadas"], 4)

    def test_go_y_cargo(self):
        r = _parsear_go(GO_OK)
        self.assertEqual((r["total"], r["pasadas"], r["fallidas"]),
                         (2, 2, 0))
        r = _parsear_cargo(CARGO_OK)
        self.assertEqual(
            (r["pasadas"], r["fallidas"], r["omitidas"]), (2, 0, 1))

    def test_salida_desconocida_no_fabrica_conteos(self):
        self.assertEqual(_parsear_npm("algo raro sin numeros")["total"], 0)


class TestDespacho(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self._path_anterior = os.environ.get("PATH", "")
        os.environ["PATH"] = str(self.bin) + os.pathsep + self._path_anterior
        self.addCleanup(self._restaurar_path)

    def _restaurar_path(self):
        os.environ["PATH"] = self._path_anterior

    def test_npm_verde_y_rojo(self):
        (self.root / "package.json").write_text(
            '{"scripts": {"test": "jest"}}', encoding="utf-8")
        _stub(self.bin, "npm", "echo 'Tests: 3 passed, 3 total' >&2")
        r = correr(self.root, "unitarios", ["tests/x.test.js"])
        self.assertTrue(r["ok"])
        self.assertEqual(r["pasadas"], 3)
        self.assertEqual(r["runner"], "npm")
        _stub(self.bin, "npm", "echo '1 failing' >&2", codigo=1)
        r = correr(self.root, "unitarios", ["tests/x.test.js"])
        self.assertFalse(r["ok"])
        self.assertEqual(r["fallidas"], 1)

    def test_go_verde(self):
        (self.root / "go.mod").write_text("module demo", encoding="utf-8")
        cuerpo = ("printf 'ok demo" + chr(10) + "--- PASS: A" + chr(10)
                  + "--- PASS: B" + chr(10) + "'")
        _stub(self.bin, "go", cuerpo)
        r = correr(self.root, "regresion", [])
        self.assertTrue(r["ok"])
        self.assertEqual(r["total"], 2)

    def test_rojo_sin_conteo_se_declara(self):
        (self.root / "package.json").write_text(
            '{"scripts": {"test": "x"}}', encoding="utf-8")
        _stub(self.bin, "npm", "echo basura >&2", codigo=1)
        r = correr(self.root, "unitarios", [])
        self.assertFalse(r["ok"])
        self.assertEqual(r["total"], 0)
        self.assertIn("ROJA", r["errores"])


if __name__ == "__main__":
    unittest.main()
