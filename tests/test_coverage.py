"""Pruebas de RF-25 — Cobertura de tests (§18.4)."""

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.coverage import UMBRAL, ejecutables, medir  # noqa: E402
from core.tasks import Tarea  # noqa: E402

FUENTE = "STOCK = 10\n\ndef vender(cant):\n    return STOCK - cant\n"
TEST_VERDE = ("import unittest\nimport sys\nsys.path.insert(0, 'src')\n"
              "from kiosco import vender\n\n\n"
              "class T(unittest.TestCase):\n"
              "    def test_vende(self):\n"
              "        self.assertEqual(vender(2), 8)\n")


def _tarea(archivos):
    return Tarea(id="TASK-001", descripcion="D", objetivo="O",
                 archivos=archivos, dependencias=[], precondiciones=[],
                 resultado="R", criterio="C", pruebas=[], refs=[])


class TestCoverage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _escribir(self, rel, contenido):
        ruta = self.root / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8")

    def test_ejecutables_cuenta_sentencias(self):
        lineas = ejecutables(FUENTE)
        self.assertIn(1, lineas)  # STOCK = 10
        self.assertIn(3, lineas)  # def vender
        self.assertIn(4, lineas)  # return

    def test_cobertura_total_con_test_completo(self):
        self._escribir("src/kiosco.py", FUENTE)
        self._escribir("tests/test_kiosco.py", TEST_VERDE)
        r = medir(self.root, _tarea(["src/kiosco.py",
                                     "tests/test_kiosco.py"]))
        self.assertTrue(r["ok"])
        self.assertEqual(r["total"], 3)
        self.assertEqual(r["pasadas"], 3)
        self.assertIn("100%", r["errores"])

    def test_cobertura_parcial_avisa_bajo_umbral(self):
        self._escribir("src/kiosco.py", FUENTE + "\ndef extra():\n    return 0\n")
        test_solo_stock = ("import unittest\nimport sys\n"
                           "sys.path.insert(0, 'src')\n"
                           "import kiosco\n\n\n"
                           "class T(unittest.TestCase):\n"
                           "    def test_importa(self):\n"
                           "        self.assertEqual(kiosco.STOCK, 10)\n")
        self._escribir("tests/test_kiosco.py", test_solo_stock)
        r = medir(self.root, _tarea(["src/kiosco.py",
                                     "tests/test_kiosco.py"]))
        self.assertTrue(r["ok"])  # informativa: no bloquea
        self.assertLess(r["pasadas"], r["total"])
        self.assertIn("umbral %d" % UMBRAL, r["errores"])

    def test_sin_tests_no_inventa(self):
        self._escribir("src/kiosco.py", FUENTE)
        r = medir(self.root, _tarea(["src/kiosco.py"]))
        self.assertTrue(r["ok"])
        self.assertEqual(r["total"], 0)
        self.assertIn("cobertura 0%", r["errores"])

    def test_sin_fuentes_no_inventa(self):
        self._escribir("tests/test_kiosco.py", TEST_VERDE)
        r = medir(self.root, _tarea(["tests/test_kiosco.py"]))
        self.assertTrue(r["ok"])
        self.assertIn("sin fuentes", r["errores"])


if __name__ == "__main__":
    unittest.main()
