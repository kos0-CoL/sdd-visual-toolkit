"""Pruebas de RF-41 — Archivo de instrucciones del agente (§47)."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.instrucciones import REGLAS, documento  # noqa: E402


class TestDocumento(unittest.TestCase):
    def test_cuatro_bloques_y_reglas_fijas(self):
        texto = documento(
            {"fase": "📝 Especificación", "spec_id": "SPEC-001",
             "tarea_actual": None, "ultima_completada": None,
             "pruebas": "sin corridas", "errores": ["x en mal estado"],
             "proxima": "clarify SPEC-001"},
            [("⛔", "Fuera de alcance", ["juegos"])],
            {"recomendada": {"comando": "clarify SPEC-001"},
             "pills": [{"etiqueta": "A", "comando": "clarify SPEC-001",
                         "recomendada": True, "bloqueada": False,
                         "motivo": ""}],
             "bloqueos": [], "requiere_aprobacion": True})
        for bloque in ("## 1. Reglas del motor", "## 2. Estado actual",
                       "## 3. Restricciones activas", "## 4. Siguiente paso"):
            self.assertIn(bloque, texto)
        for regla in REGLAS:
            self.assertIn(regla, texto)
        self.assertIn("juegos", texto)
        self.assertIn("clarify SPEC-001", texto)
        self.assertIn("⛔ x en mal estado", texto)

    def test_sin_spec_lo_dice(self):
        texto = documento({"fase": "sin SPEC"}, [], {"pills": []})
        self.assertIn("sin fronteras todavía", texto)


class TestInstruccionesCLI(unittest.TestCase):
    def test_stdout_y_guardar(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        toolkit = [sys.executable, "cli/main.py", "--root", str(root)]

        def cli(*args):
            r = subprocess.run([*toolkit, *args], capture_output=True,
                               text=True, cwd=Path.cwd(), input="",
                               timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return r.stdout

        cli("init", str(root))
        cli("enrich", "Quiero un dashboard para gestionar un kiosco.")
        texto = cli("instrucciones")
        self.assertIn("# Instrucciones del agente", texto)
        self.assertIn("## 1. Reglas del motor", texto)

        cli("instrucciones", "--guardar")
        guardado = (root / ".specify" / "INSTRUCCIONES.md").read_text(
            encoding="utf-8")
        self.assertEqual(guardado, texto)


if __name__ == "__main__":
    unittest.main()
