"""Pruebas de RF-21 — Tests de integración (§18.1)."""

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.integration import verificar  # noqa: E402
from core.tasks import Tarea  # noqa: E402


def _tarea(archivos):
    return Tarea(id="TASK-001", descripcion="D", objetivo="O",
                 archivos=archivos, dependencias=[], precondiciones=[],
                 resultado="R", criterio="C", pruebas=[], refs=[])


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _escribir(self, rel, contenido):
        ruta = self.root / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8")

    def test_contrato_compatible_pasa(self):
        self._escribir("src/b.py", "def total(items):\n    return len(items)\n")
        self._escribir("src/a.py", "from src.b import total\n\nX = total([1])\n")
        r = verificar(self.root, _tarea(["src/a.py", "src/b.py"]))
        self.assertTrue(r["ok"], r["resumen"])

    def test_import_no_resoluble_falla(self):
        self._escribir("src/a.py", "import modulo_que_no_existe\n")
        r = verificar(self.root, _tarea(["src/a.py"]))
        self.assertFalse(r["ok"])
        self.assertTrue(any("no resoluble" in h["detalle"] for h in r["hallazgos"]))

    def test_simbolo_inexistente_en_modulo_falla(self):
        self._escribir("src/b.py", "def total(items):\n    return 1\n")
        self._escribir("src/a.py", "from src.b import promedio\n\nX = promedio([1])\n")
        r = verificar(self.root, _tarea(["src/a.py", "src/b.py"]))
        self.assertFalse(r["ok"])
        self.assertTrue(any("no existe" in h["detalle"] for h in r["hallazgos"]))

    def test_aridad_incompatible_falla(self):
        self._escribir("src/b.py", "def total(items, flag):\n    return 1\n")
        self._escribir("src/a.py", "from src.b import total\n\nX = total([1])\n")
        r = verificar(self.root, _tarea(["src/a.py", "src/b.py"]))
        self.assertFalse(r["ok"])
        self.assertTrue(any("argumentos" in h["detalle"] for h in r["hallazgos"]))

    def test_varargs_no_se_juzga(self):
        self._escribir("src/b.py", "def total(*items):\n    return 1\n")
        self._escribir("src/a.py", "from src.b import total\n\nX = total(1, 2, 3)\n")
        r = verificar(self.root, _tarea(["src/a.py", "src/b.py"]))
        self.assertTrue(r["ok"], r["resumen"])


if __name__ == "__main__":
    unittest.main()
