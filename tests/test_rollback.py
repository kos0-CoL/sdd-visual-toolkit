"""Pruebas de RF-16 — Snapshot Rollback (§16)."""

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.rollback import (  # noqa: E402
    RollbackError,
    debe_frenar,
    firma,
    listar,
    prohibir,
    restaurar,
    tomar,
)
from core.tasks import Tarea  # noqa: E402


def _tarea():
    return Tarea(id="TASK-001", descripcion="D", objetivo="O",
                 archivos=["src/a.py", "src/b.py"], dependencias=[],
                 precondiciones=[], resultado="R", criterio="C",
                 pruebas=[], refs=[])


class TestRollback(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("BUENO = 1\n", encoding="utf-8")
        (self.root / "src" / "ajeno.py").write_text("AJENO = 1\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_snapshot_y_restauracion_selectiva(self):
        tomar(self.root, _tarea())
        (self.root / "src" / "a.py").write_text("ROTO = 1\n", encoding="utf-8")
        (self.root / "src" / "ajeno.py").write_text("TOCADO = 1\n", encoding="utf-8")
        carpeta = restaurar(self.root, "TASK-001")
        self.assertEqual((self.root / "src" / "a.py").read_text(encoding="utf-8"),
                         "BUENO = 1\n")
        # Lo ajeno a la tarea no se toca (§16).
        self.assertEqual((self.root / "src" / "ajeno.py").read_text(encoding="utf-8"),
                         "TOCADO = 1\n")
        self.assertEqual(listar(self.root, "TASK-001"), [carpeta.name])

    def test_dos_fallos_misma_firma_frenan(self):
        eventos = [
            {"evento": "fallida", "tarea": "TASK-001", "nota": "TypeError: x"},
            {"evento": "fallida", "tarea": "TASK-001", "nota": "TypeError: x"},
        ]
        freno = debe_frenar(eventos, "TASK-001")
        self.assertIsNotNone(freno)
        self.assertIn("typeerror", freno["firma"])
        reg = prohibir(self.root, "TASK-001", freno["firma"], 2)
        self.assertEqual(reg["attempts"], 2)
        self.assertIn("mismo error", reg["reason"])

    def test_firmas_distintas_no_frenan(self):
        eventos = [
            {"evento": "fallida", "tarea": "TASK-001", "nota": "Error A"},
            {"evento": "fallida", "tarea": "TASK-001", "nota": "Error B"},
        ]
        self.assertIsNone(debe_frenar(eventos, "TASK-001"))
        self.assertIsNone(debe_frenar(eventos[:1], "TASK-001"))

    def test_sin_snapshot_no_hay_nada_que_restaurar(self):
        self.assertEqual(listar(self.root, "TASK-999"), [])
        with self.assertRaises(RollbackError):
            restaurar(self.root, "TASK-999")

    def test_archivo_creado_por_intento_fallido_se_retira(self):
        tomar(self.root, _tarea())
        nuevo = self.root / "src" / "b.py"
        nuevo.write_text("DEFECTUOSO = 1\n", encoding="utf-8")
        restaurar(self.root, "TASK-001")
        self.assertFalse(nuevo.exists())

    def test_firma_vacia_no_rompe(self):
        self.assertEqual(firma(""), "(sin descripción)")

    def test_restaurar_rechaza_rutas_fuera_del_proyecto(self):
        tomar(self.root, _tarea())
        (self.root / "src" / "a.py").write_text("ROTO = 1\n", encoding="utf-8")
        snapshots = self.root / ".specify" / "snapshots" / "TASK-001"
        numero = sorted(p for p in snapshots.iterdir()
                        if p.is_dir() and p.name.isdigit())
        (numero[-1] / "archivos.txt").write_text("../outside.txt\n",
                                                  encoding="utf-8")
        with self.assertRaises(RollbackError):
            restaurar(self.root, "TASK-001")


if __name__ == "__main__":
    unittest.main()
