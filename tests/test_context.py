"""Pruebas de RF-14 — Context Split-Streaming (§14)."""

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from cli.commands import context as cmd_context  # noqa: E402
from cli.commands import tasks as cmd_tasks  # noqa: E402
from core.context import ContextError, MODOS, _cortar  # noqa: E402

from test_build import TestCLIBuild  # noqa: E402


class TestContexto(TestCLIBuild):
    def _hasta_tasks(self):
        self._pipeline_hasta_tasks()

    def _ctx(self, task_id, modo):
        return cmd_context.despachar(argparse.Namespace(
            root=str(self.root), texto=task_id, modo=modo))

    def test_modos_entregan_su_parte_y_nada_mas(self):
        self._hasta_tasks()
        _info, tareas = cmd_tasks._cargar_tareas(self.root, "PLAN-001")
        tid = tareas[0].id
        for modo in MODOS:
            self.assertEqual(self._ctx(tid, modo), 0, modo)

    def test_modo_invalido_y_tarea_inexistente_fallan(self):
        self._hasta_tasks()
        self.assertEqual(self._ctx("TASK-001", "inexistente"), 1)
        self.assertEqual(self._ctx("TASK-999", "implementacion"), 1)

    def test_implementacion_muestra_firmas_no_codigo(self):
        self._hasta_tasks()
        (self.root / "src").mkdir(exist_ok=True)
        (self.root / "src" / "x.py").write_text(
            "SECRETO = 'no debe salir el valor'\n\n\ndef api(a, b=1):\n"
            "    return a\n", encoding="utf-8")
        _info, tareas = cmd_tasks._cargar_tareas(self.root, "PLAN-001")
        tareas[0].archivos = ["src/x.py"]
        cmd_tasks._persistir(self.root, "PLAN-001", "SPEC-001", tareas)
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(self._ctx(tareas[0].id, "implementacion"), 0)
        salida = buf.getvalue()
        self.assertIn("api(a, b)", salida)
        self.assertNotIn("no debe salir el valor", salida)

    def test_truncado_marca_no_inventa(self):
        texto = _cortar("x" * 5000)
        self.assertIn("truncado", texto)
        self.assertLess(len(texto), 5000 + 100)


if __name__ == "__main__":
    unittest.main()
