"""Pruebas de RF-26 — Resultados visibles y comparación (§18.4)."""

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.harness import ejecutar_ciclo, render  # noqa: E402
from core.journal import registrar  # noqa: E402
from core.report import corridas, informe, tabla  # noqa: E402
from core.tasks import Tarea  # noqa: E402

VERDE = ("import unittest\n\n\nclass T(unittest.TestCase):\n"
         "    def test_ok(self):\n        self.assertTrue(True)\n")


def _tarea(**kw):
    base = dict(descripcion="D", objetivo="O", archivos=["tests/test_x.py"],
                dependencias=[], precondiciones=[], resultado="R",
                criterio="C", pruebas=[], refs=[])
    base.update(kw)
    return Tarea(id="TASK-001", **base)


def _evento(**kw):
    base = {"tarea": "TASK-001", "evento": "tests",
            "pruebas": "x", "pruebas_ok": True, "total": 2, "pasadas": 2,
            "fallidas": 0, "omitidas": 0, "duracion_s": 1.5,
            "cobertura_pct": 80}
    base.update(kw)
    return base


class TestReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "tests").mkdir()
        (self.root / ".specify" / "memory").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_render_muestra_duracion_y_cobertura(self):
        (self.root / "src").mkdir()
        (self.root / "src" / "m.py").write_text("X = 1\n",
                                                   encoding="utf-8")
        (self.root / "tests" / "test_x.py").write_text(
            "import unittest\nimport src.m\n\n\n"
            "class T(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertEqual(src.m.X, 1)\n",
            encoding="utf-8")
        r = ejecutar_ciclo(self.root,
                            _tarea(archivos=["src/m.py",
                                             "tests/test_x.py"]))
        self.assertIn("⏱ duración total:", r["resumen"])
        self.assertIn("📊 cobertura:", r["resumen"])

    def test_informe_sin_corridas_no_inventa(self):
        texto = informe(self.root, "PLAN-001", "TASK-001")
        self.assertIn("Sin corridas", texto)

    def test_informe_muestra_ultima_y_comparacion(self):
        registrar(self.root, "PLAN-001", _evento(pasadas=1, fallidas=1,
                                                pruebas_ok=False))
        registrar(self.root, "PLAN-001", _evento())
        texto = informe(self.root, "PLAN-001", "TASK-001")
        self.assertIn("TODO VERDE", texto)
        self.assertIn("Cobertura: 80%", texto)
        self.assertIn("Comparación con corrida anterior", texto)
        self.assertIn("pasadas 2 (+1)", texto)
        self.assertIn("fallidas 0 (-1)", texto)

    def test_informe_primera_corrida_sin_anterior(self):
        registrar(self.root, "PLAN-001", _evento())
        texto = informe(self.root, "PLAN-001", "TASK-001")
        self.assertIn("primera corrida", texto)

    def test_tabla_history_una_linea_por_corrida(self):
        registrar(self.root, "PLAN-001", _evento())
        registrar(self.root, "PLAN-001", _evento(pruebas_ok=False,
                                                fallidas=1, pasadas=1))
        lineas = tabla(self.root, "PLAN-001").splitlines()
        self.assertEqual(len(lineas), 2)
        self.assertIn("✅", lineas[0])
        self.assertIn("❌", lineas[1])
        self.assertIn("cob=80%", lineas[0])

    def test_corridas_solo_eventos_tests_de_la_tarea(self):
        registrar(self.root, "PLAN-001", _evento())
        registrar(self.root, "PLAN-001", _evento(tarea="TASK-002"))
        registrar(self.root, "PLAN-001", {"tarea": "TASK-001",
                                          "evento": "checkpoint"})
        self.assertEqual(len(corridas(self.root, "PLAN-001",
                                      "TASK-001")), 1)


if __name__ == "__main__":
    unittest.main()
