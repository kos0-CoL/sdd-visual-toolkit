"""Pruebas de RF-31 — Panel de estado general (§20)."""

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.board import barra, render  # noqa: E402


class TestRender(unittest.TestCase):
    def test_sin_spec_lo_dice(self):
        texto = render({"proyecto": "demo"})
        self.assertIn("sin SPEC", texto)
        self.assertIn("enrich", texto)

    def test_tablero_completo(self):
        texto = render({
            "proyecto": "demo", "spec_id": "SPEC-001",
            "spec_status": "aprobada", "fase": "🧪 Pruebas",
            "hechas": 3, "total": 4, "tarea_actual": "TASK-004",
            "ultima_completada": "TASK-003", "pendientes": 1,
            "pruebas": "✅ P=5 F=0 cob=80% (TASK-003)",
            "errores": ["TASK-002: falló validación"],
            "proxima": "build PLAN-001"})
        for marca in ("SPEC-001", "aprobada", "🧪 Pruebas", "3/4",
                      "TASK-004", "TASK-003", "✅", "🔴", "build PLAN-001"):
            self.assertIn(marca, texto)

    def test_sin_errores_lo_dice(self):
        texto = render({"proyecto": "d", "spec_id": "SPEC-001",
                        "spec_status": "draft", "fase": "📝 Especificación",
                        "hechas": 0, "total": 0, "pendientes": 0,
                        "errores": [], "proxima": "clarify SPEC-001"})
        self.assertIn("ninguno registrado", texto)

    def test_barra(self):
        self.assertIn("sin tareas", barra(0, 0))
        self.assertIn("2/4", barra(2, 4))


class TestRecopilar(unittest.TestCase):
    """recopilar() sobre un proyecto real construido con la CLI."""

    def _proyecto(self):
        """Crea el proyecto hasta el plan validado; devuelve (root, cli)."""
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
        cli("enrich", "--accept", "ENR-001")
        cli("specify", "ENR-001", "--titulo", "Kiosco")
        ids = [l.split()[1] for l in cli("clarify", "--list", "SPEC-001")
               .splitlines() if l.strip().startswith("○")]
        args = ["clarify", "SPEC-001"]
        for i in ids:
            args += ["--answer", i, "Aceptado"]
        cli(*args)
        cli("plan", "SPEC-001")
        cli("plan", "--gate", "PLAN-001")
        return root, cli

    def test_pipeline_medio_muestra_fase_y_proxima(self):
        root, cli = self._proyecto()
        out = cli("tablero")
        self.assertIn("SPEC-001", out)
        self.assertIn("tasks PLAN-001", out)
        cli("tasks", "PLAN-001")
        buf = io.StringIO()
        with redirect_stdout(buf):
            from cli.commands import tablero as mod  # noqa: PLC0415
            from types import SimpleNamespace as NS  # noqa: PLC0415
            rc = mod.despachar(NS(root=str(root), texto=None))
        self.assertEqual(rc, 0)
        self.assertIn("💾 Tareas", buf.getvalue())
        self.assertIn("build PLAN-001", buf.getvalue())

    def test_tarea_en_curso_aparece_como_actual(self):
        """La tarea marcada `en_curso` debe ser la «Tarea actual»."""
        root, cli = self._proyecto()
        cli("tasks", "PLAN-001")
        cli("analyze", "PLAN-001")
        cli("tasks", "--gate", "PLAN-001")
        cli("build", "PLAN-001")

        from cli.commands import tablero as mod  # noqa: PLC0415
        estado = mod.recopilar(root)
        self.assertEqual(estado["tarea_actual"], "TASK-001")
        self.assertIn("continuar TASK-001", estado["proxima"])
        self.assertIn("Tarea actual: TASK-001", render(estado))


if __name__ == "__main__":
    unittest.main()
