"""Pruebas de RF-24 — Validación estructural (§18)."""

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.pin import snapshot_archivo  # noqa: E402
from core.structure import verificar  # noqa: E402
from core.tasks import Tarea  # noqa: E402


def _tarea(archivos):
    return Tarea(id="TASK-001", descripcion="D", objetivo="O",
                 archivos=archivos, dependencias=[], precondiciones=[],
                 resultado="R", criterio="C", pruebas=[], refs=[])


def _baseline(root: Path, rels: list[str]) -> dict:
    return {rel: snapshot_archivo(root / rel) for rel in rels}


class TestStructure(unittest.TestCase):
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

    def test_sin_cambios_no_hay_hallazgos(self):
        self._escribir("src/a.py", "def f():\n    return 1\n")
        base = _baseline(self.root, ["src/a.py"])
        r = verificar(self.root, _tarea(["src/a.py"]), base)
        self.assertEqual(r["hallazgos"], [])

    def test_ciclo_de_importacion_rechaza(self):
        self._escribir("src/a.py", "from src.b import g\n\ndef f():\n    return g()\n")
        self._escribir("src/b.py", "from src.a import f\n\ndef g():\n    return f()\n")
        base = _baseline(self.root, ["src/a.py", "src/b.py"])
        r = verificar(self.root, _tarea(["src/a.py", "src/b.py"]), base)
        tipos = [h["tipo"] for h in r["hallazgos"]]
        self.assertIn("dependencia_circular", tipos)
        self.assertTrue(all(h["severidad"] == "rechazado"
                            for h in r["hallazgos"]
                            if h["tipo"] == "dependencia_circular"))

    def test_simbolo_eliminado_en_uso_rompe_contrato(self):
        self._escribir("src/b.py", "def total(items):\n    return 1\n")
        self._escribir("src/a.py", "from src.b import total\n\nX = total([1])\n")
        base = _baseline(self.root, ["src/a.py", "src/b.py"])
        self._escribir("src/b.py", "def otra():\n    return 2\n")
        r = verificar(self.root, _tarea(["src/a.py", "src/b.py"]), base)
        rotos = [h for h in r["hallazgos"] if h["tipo"] == "contrato_roto"]
        self.assertEqual(len(rotos), 1)
        self.assertEqual(rotos[0]["severidad"], "rechazado")
        self.assertIn("src/a.py", rotos[0]["detalle"])

    def test_simbolo_eliminado_sin_uso_no_es_roto(self):
        self._escribir("src/b.py", "def total(items):\n    return 1\n")
        self._escribir("src/a.py", "X = 1\n")
        base = _baseline(self.root, ["src/a.py", "src/b.py"])
        self._escribir("src/b.py", "def otra():\n    return 2\n")
        r = verificar(self.root, _tarea(["src/a.py", "src/b.py"]), base)
        self.assertFalse([h for h in r["hallazgos"]
                          if h["tipo"] == "contrato_roto"])

    def test_publico_nuevo_sin_test_advierte(self):
        self._escribir("src/a.py", "def f():\n    return 1\n")
        base = _baseline(self.root, ["src/a.py"])
        self._escribir("src/a.py", "def f():\n    return 1\n\ndef nueva():\n    return 2\n")
        self._escribir("tests/test_a.py", "import unittest\n")
        r = verificar(self.root, _tarea(["src/a.py", "tests/test_a.py"]),
                      base)
        avisos = [h for h in r["hallazgos"]
                  if h["tipo"] == "publico_sin_prueba"]
        self.assertEqual(len(avisos), 1)
        self.assertEqual(avisos[0]["severidad"], "advertencia")

    def test_publico_nuevo_mencionado_no_advierte(self):
        self._escribir("src/a.py", "def f():\n    return 1\n")
        base = _baseline(self.root, ["src/a.py"])
        self._escribir("src/a.py", "def f():\n    return 1\n\ndef nueva():\n    return 2\n")
        self._escribir("tests/test_a.py", "# prueba nueva()\nimport unittest\n")
        r = verificar(self.root, _tarea(["src/a.py", "tests/test_a.py"]),
                      base)
        self.assertFalse([h for h in r["hallazgos"]
                          if h["tipo"] == "publico_sin_prueba"])


if __name__ == "__main__":
    unittest.main()
