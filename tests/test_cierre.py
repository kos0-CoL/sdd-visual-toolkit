"""Pruebas de RF-37 — Mensajes finales de fase (§27)."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.cierre import bloque  # noqa: E402


class TestBloque(unittest.TestCase):
    def test_siete_puntos_completos(self):
        texto = bloque(
            "TASK-001 (PLAN-001)", "TASK-001 completada; pruebas: verde.",
            ["src/a.py"], ["2026-01-01 TASK-001: ✅ verdes"],
            [], "checkpoint TASK-001.json + journal.",
            "test TASK-002", ["test TASK-002", "traza SPEC-001"])
        for punto in ("1. Resumen:", "2. Archivos", "3. Validaciones:",
                      "4. Problemas pendientes", "5. Estado persistido:",
                      "6. Siguiente paso", "7. Controles:"):
            self.assertIn(punto, texto)
        self.assertIn("src/a.py", texto)
        self.assertIn("[ test TASK-002 ]", texto)

    def test_vacio_lo_dice(self):
        texto = bloque("proyecto", "Foto actual.", [], [], [], "lectura.",
                       "enrich «idea»", [])
        self.assertIn("sin archivos registrados", texto)
        self.assertIn("sin validaciones registradas", texto)
        self.assertIn("ninguno registrado", texto)
        self.assertIn("sin controles disponibles", texto)


class TestCierreCLI(unittest.TestCase):
    def test_pipeline_muestra_cierre_plan_y_tarea(self):
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

        cierre_plan = cli("cierre", "PLAN-001")
        for punto in ("1. Resumen:", "2. Archivos", "3. Validaciones:",
                      "4. Problemas pendientes", "5. Estado persistido:",
                      "6. Siguiente paso", "7. Controles:"):
            self.assertIn(punto, cierre_plan)
        # Sin checkpoints todavía: se declara, no se inventa.
        self.assertIn("0 checkpoint", cierre_plan)

        out_tasks = subprocess.run(
            [*toolkit, "tasks", "--list", "PLAN-001"],
            capture_output=True, text=True, cwd=Path.cwd(), input="",
            timeout=60).stdout
        task_id = [l.split()[1] for l in out_tasks.splitlines()
                   if "TASK-" in l][0]
        cierre_tarea = cli("cierre", task_id)
        self.assertIn("CIERRE: %s" % task_id, cierre_tarea)
        self.assertIn("sin checkpoint", cierre_tarea)


if __name__ == "__main__":
    unittest.main()
