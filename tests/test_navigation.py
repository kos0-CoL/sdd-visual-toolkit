"""Pruebas de RF-35 — Navegación mediante píldoras (§26)."""

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.navigation import render, sugerir  # noqa: E402


class TestSugerir(unittest.TestCase):
    def test_sin_spec_pide_enrich(self):
        nav = sugerir({"proyecto": "demo"})
        self.assertEqual(nav["recomendada"]["comando"], "enrich «idea»")
        self.assertIn("enrich", render(nav))

    def test_especificacion_recomienda_clarify(self):
        nav = sugerir({"spec_id": "SPEC-001", "fase": "📝 Especificación"})
        self.assertEqual(nav["recomendada"]["comando"], "clarify SPEC-001")
        self.assertTrue(nav["requiere_aprobacion"])
        texto = render(nav)
        self.assertIn("[ clarify SPEC-001 ]", texto)
        self.assertIn("[ specify --show SPEC-001 ]", texto)

    def test_clarify_pendiente_bloquea_plan(self):
        nav = sugerir({"spec_id": "SPEC-001", "fase": "🔍 Aclaraciones",
                       "pendientes": 2})
        comandos = [p["comando"] for p in nav["pills"]]
        self.assertIn("plan SPEC-001", comandos)
        bloqueada = [p for p in nav["pills"]
                     if p["comando"] == "plan SPEC-001"][0]
        self.assertTrue(bloqueada["bloqueada"])
        self.assertTrue(nav["bloqueos"])
        self.assertIn("🔒", render(nav))

    def test_arquitectura_pide_gate_y_bloquea_tasks(self):
        nav = sugerir({"spec_id": "SPEC-001", "fase": "📐 Arquitectura",
                       "proxima": "plan --gate PLAN-001"})
        self.assertEqual(nav["recomendada"]["comando"],
                         "plan --gate PLAN-001")
        bloqueada = [p for p in nav["pills"]
                     if p["comando"] == "tasks PLAN-001"][0]
        self.assertTrue(bloqueada["bloqueada"])

    def test_implementacion_pide_test(self):
        nav = sugerir({"spec_id": "SPEC-001", "fase": "⚡ Implementación",
                       "tarea_actual": "TASK-003",
                       "proxima": "build PLAN-001 (continuar TASK-003)"})
        self.assertEqual(nav["recomendada"]["comando"], "test TASK-003")
        texto = render(nav)
        self.assertIn("test TASK-003", texto)
        self.assertIn("diff TASK-003", texto)

    def test_completado_pide_traza(self):
        nav = sugerir({"spec_id": "SPEC-001", "fase": "✅ Completado",
                       "tarea_actual": "TASK-002"})
        self.assertEqual(nav["recomendada"]["comando"], "traza SPEC-001")

    def test_pruebas_en_verde_cierra_la_tarea(self):
        nav = sugerir({"spec_id": "SPEC-001", "plan_id": "PLAN-001",
                       "fase": "🧪 Pruebas", "pruebas_ok": True,
                       "pruebas_tarea": "TASK-007",
                       "tarea_actual": "TASK-007"})
        self.assertEqual(nav["recomendada"]["comando"],
                         "build PLAN-001 --done TASK-007")
        texto = render(nav)
        self.assertIn("[ build PLAN-001 --done TASK-007 ]", texto)
        self.assertNotIn("rojo", texto)

    def test_pruebas_en_verde_sin_tarea_en_curso_avanza_el_plan(self):
        nav = sugerir({"spec_id": "SPEC-001", "plan_id": "PLAN-001",
                       "fase": "🧪 Pruebas", "pruebas_ok": True,
                       "pruebas_tarea": "TASK-001", "tarea_actual": None})
        self.assertEqual(nav["recomendada"]["comando"], "build PLAN-001")
        self.assertNotIn("rojo", render(nav))

    def test_pruebas_en_rojo_manda_repetir_el_test(self):
        nav = sugerir({"spec_id": "SPEC-001", "plan_id": "PLAN-001",
                       "fase": "🧪 Pruebas", "pruebas_ok": False,
                       "pruebas_tarea": "TASK-002",
                       "proxima": "test TASK-002"})
        self.assertEqual(nav["recomendada"]["comando"], "test TASK-002")
        self.assertIn("rojo", nav["nota"])

    def test_render_mantiene_estado(self):
        nav = sugerir({"spec_id": "SPEC-001", "fase": "💾 Tareas",
                       "proxima": "build PLAN-001"})
        texto = render(nav)
        self.assertIn("solo lectura, nada se ejecutó", texto)
        self.assertIn("[ build PLAN-001 ]", texto)


class TestSiguienteCLI(unittest.TestCase):
    def test_cli_sobre_pipeline_real(self):
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
        buf = io.StringIO()
        with redirect_stdout(buf):
            from cli.commands import siguiente as mod  # noqa: PLC0415
            rc = mod.despachar(NS(root=str(root)))
        self.assertEqual(rc, 0)
        self.assertIn("enrich", buf.getvalue())

        cli("enrich", "Quiero un dashboard para gestionar un kiosco.")
        cli("enrich", "--accept", "ENR-001")
        cli("specify", "ENR-001", "--titulo", "Kiosco")
        out = subprocess.run(
            [*toolkit, "siguiente"], capture_output=True, text=True,
            cwd=Path.cwd(), input="", timeout=60).stdout
        # Tras specify: o pide clarify o, con Gate 1 superado, plan.
        self.assertIn("SPEC-001", out)
        self.assertTrue("clarify SPEC-001" in out or "plan SPEC-001" in out,
                        out)
        self.assertIn("solo lectura", out)


if __name__ == "__main__":
    unittest.main()
