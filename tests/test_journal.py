"""Pruebas de RF-11 — State Journaling (§13)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.journal import (  # noqa: E402
    JournalError,
    actualizar_estado,
    checkpoint,
    estado_inicial,
    historial,
    leer_estado,
    registrar,
    resumen,
)


class TestJournal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_eventos_se_agregan_como_jsonl_valido(self):
        registrar(self.root, "PLAN-001", {"tarea": "TASK-001", "evento": "en_curso"})
        registrar(self.root, "PLAN-001", {"tarea": "TASK-001", "evento": "completada"})
        eventos = historial(self.root, "PLAN-001")
        self.assertEqual([e["evento"] for e in eventos], ["en_curso", "completada"])
        for linea in (self.root / ".specify" / "memory" / "execution_history.jsonl"
                      ).read_text(encoding="utf-8").splitlines():
            json.loads(linea)  # cada línea es un JSON completo o nada

    def test_evento_sin_campos_requeridos_falla(self):
        with self.assertRaises(JournalError):
            registrar(self.root, "PLAN-001", {"tarea": "TASK-001"})

    def test_estado_exige_esquema_y_deja_respaldo(self):
        with self.assertRaises(JournalError):
            actualizar_estado(self.root, {"plan_id": "P"})
        estado = actualizar_estado(
            self.root, estado_inicial("PLAN-001", "SPEC-001", 3, "run1"))
        self.assertEqual(leer_estado(self.root)["run_id"], "run1")
        actualizar_estado(self.root, estado_inicial("PLAN-001", "SPEC-001", 3, "run2"))
        respaldo = json.loads(
            (self.root / ".specify" / "memory" / "current_task.json.bak"
             ).read_text(encoding="utf-8"))
        self.assertEqual(respaldo["run_id"], "run1")  # corte deja el viejo intacto
        self.assertEqual(leer_estado(self.root)["run_id"], "run2")

    def test_checkpoint_contiene_hashes_y_proxima(self):
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("X = 1\n", encoding="utf-8")

        class T:
            id = "TASK-001"
            archivos = ["src/a.py"]

        cp = checkpoint(self.root, "PLAN-001", "SPEC-001", T(), "TASK-002",
                        "tests/test_a.py: OK", True, nota="decisión X")
        self.assertEqual(cp["proxima"], "TASK-002")
        self.assertIn("src/a.py", cp["hashes"])
        self.assertEqual(cp["decisiones"], "decisión X")

    def test_resumen_cuenta_sin_inventar(self):
        registrar(self.root, "PLAN-001", {"tarea": "TASK-001", "evento": "completada"})
        texto = resumen(self.root, "PLAN-001")
        self.assertIn("1 completada(s)", texto)
        self.assertIn("TASK-001", texto)


if __name__ == "__main__":
    unittest.main()
