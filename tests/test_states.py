"""Pruebas de RF-32 — Árbol de estados (§21)."""

import io
import subprocess  # noqa: E402
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.states import NODOS, SIMBOLOS, render  # noqa: E402


class TestRender(unittest.TestCase):
    def test_nueve_fases_con_simbolos(self):
        nodos = [("Enriquecimiento", "completado"),
                 ("Especificación", "requiere intervención"),
                 ("Aclaraciones", "en progreso"),
                 ("Arquitectura", "pendiente"),
                 ("Tareas", "pendiente"),
                 ("Análisis", "pendiente"),
                 ("Implementación", "fallido"),
                 ("Pruebas", "fallido"),
                 ("Recuperación", "recuperado")]
        texto = render(nodos, ["f1 → ⚡ Implementación: TASK-001 en curso"])
        self.assertEqual(len(NODOS), 9)
        for simbolo in ("✔", "⚠", "●", "○", "✘", "♻"):
            self.assertIn(simbolo, texto)
        self.assertIn("Transiciones registradas (1)", texto)

    def test_sin_transiciones_lo_dice(self):
        texto = render([("Enriquecimiento", "pendiente")], [])
        self.assertIn("Sin transiciones", texto)

    def test_simbolos_cubren_seis_estados(self):
        self.assertEqual(len(SIMBOLOS), 6)


class TestArbol(unittest.TestCase):
    def test_pipeline_medio(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        toolkit = [sys.executable, "cli/main.py", "--root", str(root)]

        def cli(*args):
            r = subprocess.run([*toolkit, *args], capture_output=True,
                               text=True, cwd=Path.cwd(), input="",
                               timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        cli("init", str(root))
        cli("enrich", "Quiero un dashboard para gestionar un kiosco.")
        cli("enrich", "--accept", "ENR-001")
        cli("specify", "ENR-001", "--titulo", "Kiosco")
        out = subprocess.run(
            [*toolkit, "clarify", "--list", "SPEC-001"],
            capture_output=True, text=True, cwd=Path.cwd(), input="",
            timeout=60).stdout
        ids = [l.split()[1] for l in out.splitlines()
               if l.strip().startswith("○")]
        args = ["clarify", "SPEC-001"]
        for i in ids:
            args += ["--answer", i, "Aceptado"]
        cli(*args)
        cli("plan", "SPEC-001")
        cli("plan", "--gate", "PLAN-001")
        cli("tasks", "PLAN-001")
        cli("specify", "--approve", "SPEC-001")
        buf = io.StringIO()
        with redirect_stdout(buf):
            from cli.commands import arbol as mod  # noqa: PLC0415
            rc = mod.despachar(NS(root=str(root), texto=None))
        self.assertEqual(rc, 0)
        texto = buf.getvalue()
        # SPEC aprobada + Aclaraciones + Arquitectura completadas;
        # resto pendiente.
        self.assertIn("✔ Enriquecimiento: completado", texto)
        self.assertIn("✔ Especificación: completado", texto)
        self.assertIn("✔ Aclaraciones: completado", texto)
        self.assertIn("✔ Arquitectura: completado", texto)
        self.assertIn("○ Análisis: pendiente", texto)
        self.assertIn("○ Recuperación: pendiente", texto)
        self.assertIn("Sin transiciones", texto)


if __name__ == "__main__":
    unittest.main()
