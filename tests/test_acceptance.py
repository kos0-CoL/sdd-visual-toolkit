"""Pruebas de RF-23 — Tests de aceptación ejecutables (§18)."""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.acceptance import (  # noqa: E402
    es_accept,
    evaluar,
    extraer_cobertura,
)

VERDE = ("import unittest\n\n\nclass TestVenta(unittest.TestCase):\n"
         "    def test_descuenta_stock(self):\n"
         "        \"\"\"Cubre CP-001: vender descuenta del stock.\"\"\"\n"
         "        self.assertTrue(True)\n")
ROJO = ("import unittest\n\n\nclass TestVenta(unittest.TestCase):\n"
        "    def test_descuenta_stock(self):\n"
        "        # Cubre CP-001\n"
        "        self.assertTrue(False)\n")


def _spec(casos=("CP-001",), refs=("REQ-001",)):
    crit = [SimpleNamespace(id="CRI-001", texto="t", req_id="REQ-001")]
    return SimpleNamespace(
        criterios=crit,
        casos=[SimpleNamespace(id=c, texto="t", criterio_id="CRI-001")
               for c in casos])


def _tarea(archivos, pruebas=("CP-001",)):
    from core.tasks import Tarea
    return Tarea(id="TASK-001", descripcion="D", objetivo="O",
                 archivos=archivos, dependencias=[], precondiciones=[],
                 resultado="R", criterio="C", pruebas=list(pruebas),
                 refs=["REQ-001"])


class TestAcceptance(unittest.TestCase):
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

    def test_es_accept_por_nombre(self):
        self.assertTrue(es_accept("tests/test_accept_venta.py"))
        self.assertTrue(es_accept("tests/test_aceptacion_x.py"))
        self.assertFalse(es_accept("tests/test_stock.py"))
        self.assertFalse(es_accept("src/accept_algo.py"))

    def test_cobertura_detecta_caso_en_docstring(self):
        self._escribir("tests/test_accept_venta.py", VERDE)
        cob = extraer_cobertura(self.root, ["tests/test_accept_venta.py"])
        self.assertIn("CP-001", cob)
        self.assertEqual(cob["CP-001"],
                         ["tests.test_accept_venta.TestVenta."
                          "test_descuenta_stock"])

    def test_caso_cubierto_verde_pasa(self):
        self._escribir("tests/test_accept_venta.py", VERDE)
        r = evaluar(self.root, _tarea(["tests/test_accept_venta.py"]),
                    _spec())
        self.assertTrue(r["ok"], r["errores"])
        self.assertEqual((r["total"], r["pasadas"], r["omitidas"]),
                         (1, 1, 0))
        self.assertIn("CUBIERTO y verde", r["errores"])

    def test_caso_cubierto_rojo_falla(self):
        self._escribir("tests/test_accept_venta.py", ROJO)
        r = evaluar(self.root, _tarea(["tests/test_accept_venta.py"]),
                    _spec())
        self.assertFalse(r["ok"])
        self.assertEqual(r["fallidas"], 1)
        self.assertIn("CUBIERTO pero ROJO", r["errores"])

    def test_caso_sin_prueba_se_omite_sin_inventar(self):
        self._escribir("tests/test_stock.py", VERDE)
        r = evaluar(self.root, _tarea(["tests/test_stock.py"]), _spec())
        self.assertTrue(r["ok"])
        self.assertEqual(r["omitidas"], 1)
        self.assertIn("SIN PRUEBA", r["errores"])

    def test_caso_pedido_inexistente_se_ignora(self):
        self._escribir("tests/test_accept_venta.py", VERDE)
        r = evaluar(self.root, _tarea(["tests/test_accept_venta.py"],
                                      pruebas=("CP-999",)), _spec())
        self.assertTrue(r["ok"])
        self.assertEqual(r["total"], 0)

    def test_placeholder_crear_no_es_caso(self):
        r = evaluar(self.root,
                    _tarea([], pruebas=("CP-TASK-001 (crear con la "
                                        "implementación)",)), _spec())
        self.assertTrue(r["ok"])
        self.assertEqual(r["total"], 0)

    def test_sin_spec_no_inventa_casos(self):
        r = evaluar(self.root, _tarea([]), None)
        self.assertTrue(r["ok"])
        self.assertIn("no se inventan", r["errores"])


if __name__ == "__main__":
    unittest.main()
