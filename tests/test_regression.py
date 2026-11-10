"""Pruebas de RF-22 — Tests generales y de regresión (§53)."""

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.harness import _es_general, capa_regresion, ejecutar_ciclo  # noqa: E402
from core.tasks import Tarea  # noqa: E402

VERDE = ("import unittest\n\n\nclass T(unittest.TestCase):\n"
         "    def test_ok(self):\n        self.assertTrue(True)\n")
ROJO = ("import unittest\n\n\nclass T(unittest.TestCase):\n"
        "    def test_no(self):\n        self.assertTrue(False)\n")


def _tarea(archivos):
    return Tarea(id="TASK-001", descripcion="D", objetivo="O",
                 archivos=archivos, dependencias=[], precondiciones=[],
                 resultado="R", criterio="C", pruebas=[], refs=[])


class TestRegresion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "tests").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _escribir(self, rel, contenido):
        ruta = self.root / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8")

    def test_es_general_por_nombre(self):
        self.assertTrue(_es_general("tests/test_flujo_compra.py"))
        self.assertTrue(_es_general("tests/test_general_x.py"))
        self.assertTrue(_es_general("tests/test_e2e_alta.py"))
        self.assertFalse(_es_general("tests/test_stock.py"))

    def test_regresion_verde_menciona_flujo_completo(self):
        self._escribir("tests/test_stock.py", VERDE)
        self._escribir("tests/test_flujo_compra.py", VERDE)
        t = _tarea(["tests/test_stock.py", "tests/test_flujo_compra.py"])
        r = capa_regresion(self.root, t,
                            ["tests/test_stock.py", "tests/test_flujo_compra.py"],
                            ["tests/test_flujo_compra.py"])
        self.assertTrue(r["ok"], r["errores"])
        self.assertEqual(r["total"], 2)
        self.assertIn("flujo completo", r["errores"])

    def test_regresion_detecta_roto(self):
        self._escribir("tests/test_stock.py", VERDE)
        self._escribir("tests/test_flujo_compra.py", ROJO)
        t = _tarea(["tests/test_stock.py", "tests/test_flujo_compra.py"])
        r = capa_regresion(self.root, t,
                            ["tests/test_stock.py", "tests/test_flujo_compra.py"],
                            ["tests/test_flujo_compra.py"])
        self.assertFalse(r["ok"])
        self.assertEqual(r["fallidas"], 1)

    def test_regresion_sin_tests_no_inventa(self):
        r = capa_regresion(self.root, _tarea([]), [], [])
        self.assertTrue(r["ok"])
        self.assertEqual(r["total"], 0)

    def test_ciclo_completo_trae_regresion(self):
        self._escribir("tests/test_stock.py", VERDE)
        self._escribir("tests/test_flujo_compra.py", VERDE)
        r = ejecutar_ciclo(self.root,
                            _tarea(["tests/test_stock.py",
                                    "tests/test_flujo_compra.py"]))
        self.assertTrue(r["ok"])
        fases = {c["fase"]: c for c in r["capas"]}
        self.assertEqual(fases["regresión"]["total"], 2)


if __name__ == "__main__":
    unittest.main()
