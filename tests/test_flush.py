"""Pruebas de RF-15 — Context Flush (§15)."""

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.flush import (  # noqa: E402
    FlushError,
    estimar_tokens,
    fijar_umbral,
    generar_pack,
    leer_umbral,
    medir,
)
from core.tasks import Tarea  # noqa: E402


def _tarea(id_, estado="pendiente"):
    t = Tarea(id=id_, descripcion="D", objetivo="O", archivos=[],
              dependencias=[], precondiciones=[], resultado="R",
              criterio="C", pruebas=[], refs=[])
    t.estado = estado
    return t


class FakeSpec:
    spec_id = "SPEC-001"


class TestFlush(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".specify").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_umbral_por_defecto_y_configurable(self):
        self.assertEqual(leer_umbral(self.root), 30000)  # ejemplo, no dogma
        self.assertEqual(fijar_umbral(self.root, 500), 500)
        self.assertEqual(leer_umbral(self.root), 500)
        with self.assertRaises(FlushError):
            fijar_umbral(self.root, 0)

    def test_medir_detecta_saturacion_solo_con_datos(self):
        eventos = [{"evento": "nota", "tarea": "TASK-001", "x": "y" * 100}]
        m = medir(self.root, "PLAN-001", eventos, [])
        self.assertGreater(m["tokens_estimados"], 0)
        self.assertFalse(m["saturado"])  # umbral 30000, sin saturación real
        fijar_umbral(self.root, 1)
        self.assertTrue(medir(self.root, "PLAN-001", eventos, [])["saturado"])

    def test_pack_no_borra_y_resume_pendientes_y_fallos(self):
        (self.root / ".specify" / "durable.txt").write_text("durable", encoding="utf-8")
        eventos = [
            {"evento": "checkpoint", "tarea": "TASK-001",
             "decisiones": "usar listas"},
            {"evento": "fallida", "tarea": "TASK-002",
             "nota": "float directo falló"},
        ]
        tareas = [_tarea("TASK-001", "completada"), _tarea("TASK-002")]
        ruta, pack = generar_pack(self.root, "PLAN-001", FakeSpec(),
                                  tareas[1], tareas, eventos, "corte simulado")
        self.assertTrue(ruta.exists())
        texto = ruta.read_text(encoding="utf-8")
        self.assertIn("TASK-002", texto)
        self.assertIn("float directo", texto)
        self.assertIn("usar listas", texto)
        self.assertTrue((self.root / ".specify" / "durable.txt").exists())
        self.assertGreater(estimar_tokens("hola mundo"), 0)


if __name__ == "__main__":
    unittest.main()
