"""Pruebas de RF-13 — Recuperación de sesiones (§13.6)."""

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.journal import (  # noqa: E402
    actualizar_estado,
    estado_inicial,
    registrar,
)
from core.recover import diagnosticar, formatear  # noqa: E402
from core.tasks import Tarea  # noqa: E402


def _tarea(id_, archivos):
    return Tarea(id=id_, descripcion="D", objetivo="O", archivos=archivos,
                 dependencias=[], precondiciones=[], resultado="R",
                 criterio="C", pruebas=[], refs=["REQ-001"])


class TestRecover(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("X = 1\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _journal_interrumpido(self):
        registrar(self.root, "PLAN-001", {"tarea": "TASK-001", "evento": "en_curso"})
        registrar(self.root, "PLAN-001", {"tarea": "TASK-001", "evento": "completada",
                                          "pruebas": "tests: OK", "pruebas_ok": True})
        registrar(self.root, "PLAN-001", {
            "evento": "checkpoint", "tarea": "TASK-001", "spec": "SPEC-001",
            "fase": "implement", "proxima": "TASK-002",
            "archivos": ["src/a.py"], "hashes": {"src/a.py": "x" * 16},
            "pruebas": "tests: OK", "pruebas_ok": True, "decisiones": ""})
        registrar(self.root, "PLAN-001", {"tarea": "TASK-002", "evento": "en_curso"})
        actualizar_estado(
            self.root, estado_inicial("PLAN-001", "SPEC-001", 2, "run1"))

    def test_detecta_interrumpida_y_hash_que_no_coincide(self):
        self._journal_interrumpido()
        spec = {"spec_id": "SPEC-001", "funcionales": [("REQ-001", "T", "aceptado")]}
        rep = diagnosticar(self.root, "PLAN-001", spec,
                           [_tarea("TASK-001", ["src/a.py"]),
                            _tarea("TASK-002", ["src/b.py"])])
        self.assertEqual(rep["situacion"], "interrumpida")
        self.assertEqual(rep["tarea_pendiente"], "TASK-002")
        self.assertIn("revalidar", rep["archivos"]["src/a.py"])
        self.assertTrue(rep["spec_ok"])
        texto = formatear(rep)
        self.assertIn("build PLAN-001", texto)

    def test_archivo_que_sobrevive_y_plan_completo(self):
        import hashlib
        sha = hashlib.sha256(b"X = 1\n").hexdigest()[:16]
        registrar(self.root, "PLAN-001", {"tarea": "TASK-001", "evento": "completada",
                                          "pruebas": "tests: OK", "pruebas_ok": True})
        registrar(self.root, "PLAN-001", {
            "evento": "checkpoint", "tarea": "TASK-001", "spec": "SPEC-001",
            "fase": "implement", "proxima": None, "archivos": ["src/a.py"],
            "hashes": {"src/a.py": sha}, "pruebas": "tests: OK",
            "pruebas_ok": True, "decisiones": ""})
        rep = diagnosticar(self.root, "PLAN-001", None, [_tarea("TASK-001", ["src/a.py"])])
        self.assertEqual(rep["situacion"], "limpia")
        self.assertEqual(rep["archivos"]["src/a.py"], "sobrevive intacto")
        self.assertIsNone(rep["tarea_pendiente"])
        self.assertFalse(rep["spec_ok"])  # spec ausente: no se asume válida

    def test_sin_journal_no_inventa_estado(self):
        rep = diagnosticar(self.root, "PLAN-001", None, [])
        self.assertEqual(rep["situacion"], "sin_journal")
        self.assertIn("nada que recuperar", formatear(rep))


if __name__ == "__main__":
    unittest.main()
