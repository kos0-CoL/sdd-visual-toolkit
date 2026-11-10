"""Pruebas de RF-19 — Testing Harness (§18)."""

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.harness import (  # noqa: E402
    HarnessError,
    correr,
    detectar_runner,
    ejecutar_ciclo,
    hashes_tests,
)
from core.tasks import Tarea  # noqa: E402

VERDE = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n"
ROJO = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_no(self):\n        self.assertTrue(False)\n"


def _tarea(**kw):
    base = dict(descripcion="D", objetivo="O",
                archivos=["tests/test_x.py", "tests/test_x_integration.py"],
                dependencias=[], precondiciones=[], resultado="R",
                criterio="C", pruebas=[], refs=[])
    base.update(kw)
    return Tarea(id="TASK-001", **base)


class TestHarness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "tests").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_ciclo_verde_con_capas_visibles(self):
        (self.root / "tests" / "test_x.py").write_text(VERDE, encoding="utf-8")
        (self.root / "tests" / "test_x_integration.py").write_text(
            VERDE, encoding="utf-8")
        r = ejecutar_ciclo(self.root, _tarea())
        self.assertTrue(r["ok"])
        fases = {c["fase"]: c for c in r["capas"]}
        self.assertEqual(fases["unitarios"]["total"], 1)
        self.assertEqual(fases["integración"]["total"], 1)
        self.assertGreaterEqual(fases["regresión"]["total"], 2)
        self.assertIn("tests/test_x.py", r["hashes_tests"])

    def test_rojo_se_reporta_sin_ocultar(self):
        (self.root / "tests" / "test_x.py").write_text(ROJO, encoding="utf-8")
        (self.root / "tests" / "test_x_integration.py").write_text(
            VERDE, encoding="utf-8")
        r = ejecutar_ciclo(self.root, _tarea())
        self.assertFalse(r["ok"])
        fases = {c["fase"]: c for c in r["capas"]}
        self.assertEqual(fases["unitarios"]["fallidas"], 1)
        self.assertIn("FALLA", fases["unitarios"]["errores"])

    def test_sin_tests_no_inventa_resultado(self):
        r = correr(self.root, "unitarios", [])
        self.assertTrue(r["ok"])
        self.assertEqual(r["total"], 0)
        self.assertIn("no se inventa", r["errores"])

    def test_arnes_no_modifica_tests(self):
        ruta = self.root / "tests" / "test_x.py"
        ruta.write_text(VERDE, encoding="utf-8")
        antes = hashlib.sha256(ruta.read_bytes()).hexdigest()
        ejecutar_ciclo(self.root, _tarea())
        despues = hashlib.sha256(ruta.read_bytes()).hexdigest()
        self.assertEqual(antes, despues)  # §18.3: solo ejecuta

    def test_detecta_unittest_y_respeta_pytest_del_repo(self):
        self.assertEqual(detectar_runner(self.root), "unittest")
        (self.root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        self.assertIn(detectar_runner(self.root), ("unittest", "pytest"))

    def test_fase_dirigida_corre_solo_lo_pedido(self):
        (self.root / "tests" / "test_x.py").write_text(VERDE, encoding="utf-8")
        (self.root / "tests" / "test_x_integration.py").write_text(
            VERDE, encoding="utf-8")
        r = ejecutar_ciclo(self.root, _tarea(), solo=("unitarios",))
        self.assertEqual([c["fase"] for c in r["capas"]], ["unitarios"])
        with self.assertRaises(HarnessError):
            ejecutar_ciclo(self.root, _tarea(), solo=("inexistente",))

    def test_hashes_solo_tests_existentes(self):
        (self.root / "tests" / "test_x.py").write_text(VERDE, encoding="utf-8")
        h = hashes_tests(self.root, ["tests/test_x.py", "tests/no_existe.py"])
        self.assertIn("tests/test_x.py", h)
        self.assertNotIn("tests/no_existe.py", h)

    def test_una_sola_invocacion_por_fase(self):
        from core import harness as mod  # noqa: PLC0415

        (self.root / "tests" / "test_x.py").write_text(VERDE, encoding="utf-8")
        (self.root / "tests" / "test_y.py").write_text(VERDE, encoding="utf-8")
        llamadas = []
        original = mod._invocar

        def espia(*args, **kwargs):
            llamadas.append(args[1])
            return original(*args, **kwargs)

        mod._invocar = espia
        try:
            r = mod.correr(self.root, "unitarios",
                           ["tests/test_x.py", "tests/test_y.py"])
        finally:
            mod._invocar = original
        self.assertEqual(len(llamadas), 1)
        self.assertEqual(r["total"], 2)
        self.assertTrue(r["ok"])


if __name__ == "__main__":
    unittest.main()
