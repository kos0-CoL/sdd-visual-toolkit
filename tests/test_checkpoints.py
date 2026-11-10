"""Pruebas de RF-12 — Checkpoints (§13.4, §35)."""

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.checkpoints import (  # noqa: E402
    CheckpointError,
    cargar,
    guardar,
    listar,
)


def _registro(tarea="TASK-001", plan="PLAN-001"):
    return {"fecha": "2026-01-01T00:00:00+00:00", "plan": plan,
            "spec": "SPEC-001", "fase": "implement", "evento": "checkpoint",
            "tarea": tarea, "proxima": "TASK-002",
            "archivos": ["src/a.py"], "hashes": {"src/a.py": "abc123"},
            "pruebas": "tests: OK", "pruebas_ok": True, "decisiones": "nota"}


class TestCheckpoints(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_guardar_y_cargar_redondo(self):
        ruta = guardar(self.root, "PLAN-001", _registro())
        self.assertTrue(ruta.name == "TASK-001.json")
        cp = cargar(self.root, "TASK-001")
        self.assertEqual(cp["hashes"], {"src/a.py": "abc123"})
        self.assertEqual(cp["proxima"], "TASK-002")

    def test_rechaza_lo_que_no_es_checkpoint(self):
        with self.assertRaises(CheckpointError):
            guardar(self.root, "PLAN-001", {"evento": "completada",
                                            "tarea": "TASK-001"})
        incompleto = {k: v for k, v in _registro().items()
                      if k not in ("hashes", "pruebas")}
        with self.assertRaises(CheckpointError):
            guardar(self.root, "PLAN-001", incompleto)

    def test_tarea_sin_checkpoint_no_inventa(self):
        self.assertIsNone(cargar(self.root, "TASK-999"))

    def test_listar_ordena_y_filtra_por_plan(self):
        guardar(self.root, "PLAN-001", _registro("TASK-002"))
        guardar(self.root, "PLAN-001", _registro("TASK-001"))
        guardar(self.root, "PLAN-002", _registro("TASK-009", plan="PLAN-002"))
        puntos = listar(self.root, "PLAN-001")
        self.assertEqual([p["tarea"] for p in puntos], ["TASK-001", "TASK-002"])


if __name__ == "__main__":
    unittest.main()
