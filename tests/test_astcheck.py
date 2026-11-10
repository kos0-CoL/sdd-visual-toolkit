"""Pruebas de RF-17 — Post-Diff Structural Check (§17)."""

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.astcheck import comparar  # noqa: E402
from core.pin import tomar_baseline  # noqa: E402
from core.tasks import Tarea  # noqa: E402

BASE = "import os\n\nX = 1\n\n\ndef f(a):\n    return a\n"


def _tarea(**kw):
    base = dict(descripcion="D", objetivo="O", archivos=["src/a.py"],
                dependencias=[], precondiciones=[], resultado="R",
                criterio="C", pruebas=[], refs=[])
    base.update(kw)
    return Tarea(id="TASK-001", **base)


class TestAstCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text(BASE, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_sin_cambios_aceptado(self):
        base = tomar_baseline(_tarea(), self.root)
        r = comparar(_tarea(), base, self.root)
        self.assertEqual(r["veredicto"], "ACEPTADO")

    def test_nueva_funcion_retorno_e_import_advertencia(self):
        (self.root / "src" / "a.py").write_text(
            BASE.replace("def f(a):", "def f(a) -> str:"), encoding="utf-8")
        base = tomar_baseline(_tarea(), self.root)
        (self.root / "src" / "a.py").write_text(
            "import os\nimport sys\n\nX = 1\n\n\ndef f(a) -> int:\n    return a\n\n\n"
            "def g():\n    return 1\n", encoding="utf-8")
        r = comparar(_tarea(), base, self.root)
        tipos = {h["tipo"] for h in r["hallazgos"]}
        self.assertIn("nueva_funcion", tipos)
        self.assertIn("retorno_cambiado", tipos)
        self.assertIn("import_nuevo", tipos)
        self.assertEqual(r["veredicto"], "ADVERTENCIA")

    def test_simbolo_eliminado_advertencia(self):
        base = tomar_baseline(_tarea(), self.root)
        (self.root / "src" / "a.py").write_text("import os\n\nX = 1\n",
                                                encoding="utf-8")
        r = comparar(_tarea(), base, self.root)
        self.assertTrue(any(h["tipo"] == "simbolo_eliminado"
                            for h in r["hallazgos"]))
        self.assertEqual(r["veredicto"], "ADVERTENCIA")

    def test_archivo_ajeno_rechazado(self):
        base = tomar_baseline(_tarea(), self.root)
        (self.root / "src" / "ajeno.py").write_text("Z = 1\n", encoding="utf-8")
        from core.pin import foto_arbol  # noqa: PLC0415
        base["__arbol__"] = foto_arbol(self.root)
        (self.root / "src" / "ajeno.py").write_text("Z = 2\n", encoding="utf-8")
        r = comparar(_tarea(), base, self.root)
        self.assertEqual(r["veredicto"], "RECHAZADO")


if __name__ == "__main__":
    unittest.main()
