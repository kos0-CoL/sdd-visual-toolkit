"""IDs inexistentes y `pin --task`: la CLI avisa en vez de reventar (§31).

Un traceback no es cosmético: quien empieza escribe un ID equivocado antes
que cualquier otra cosa, y ahí se encuentra con el fallo. Estas pruebas
despachan con el parser real sobre un proyecto vacío, que es el peor caso.
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent))

from cli import main as cli_main  # noqa: E402
from state import store  # noqa: E402

FIXTURE = TESTS_DIR / "fixtures" / "estado-0.1.0"

# Comando → fragmento esperado del aviso. Todos tenían un traceback cuando el
# error venía de cargar la SPEC, el plan o la tarea en vez de su propio módulo.
CASOS = [
    (["ast", "TASK-999"], "tarea inexistente: TASK-999"),
    (["diff", "TASK-999"], "tarea inexistente: TASK-999"),
    (["historia", "TASK-999"], "tarea inexistente: TASK-999"),
    (["reporte", "TASK-999"], "tarea inexistente: TASK-999"),
    (["test", "TASK-999"], "tarea inexistente: TASK-999"),
    (["validate", "TASK-999"], "tarea inexistente: TASK-999"),
    (["flush", "PLAN-999"], "plan inexistente: PLAN-999"),
    (["pin", "PLAN-999", "--task", "TASK-001"], "plan inexistente: PLAN-999"),
    (["pin", "--check", "TASK-999"], "tarea inexistente: TASK-999"),
    (["recover", "PLAN-999"], "sin tareas para PLAN-999"),
    (["traza", "SPEC-999"], "SPEC inexistente: SPEC-999"),
    (["clarify", "--list", "SPEC-999"], "SPEC inexistente: SPEC-999"),
    (["build", "PLAN-999"], "plan inexistente: PLAN-999"),
    (["build", "PLAN-999", "--done", "TASK-001"],
     "plan inexistente: PLAN-999"),
    (["implement", "PLAN-999"], "plan inexistente: PLAN-999"),
    (["specify", "XXX-999"], "enriquecimiento inexistente: XXX-999"),
    (["restricciones", "SPEC-999"], "SPEC inexistente: SPEC-999"),
    (["restricciones", "TASK-999"], "tarea inexistente: TASK-999"),
]


class TestIDsInexistentes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        store.inicializar_proyecto(self.root)
        self.parser = cli_main.construir_parser()

    def tearDown(self):
        self._tmp.cleanup()

    def _despachar(self, argv: list[str]) -> tuple[int, str]:
        args = self.parser.parse_args(["--root", str(self.root), *argv])
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = args.func(args)
        return codigo, salida.getvalue()

    def test_cada_comando_avisa_sin_reventar(self):
        for argv, esperado in CASOS:
            with self.subTest(comando=" ".join(argv)):
                codigo, salida = self._despachar(argv)
                self.assertEqual(codigo, 1, salida)
                self.assertIn(esperado, salida)


class TestGateDeBuild(unittest.TestCase):
    """El plan que existe sigue pasando por el Quality Gate 4 (§10.4)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "proyecto"
        shutil.copytree(FIXTURE, self.root)
        self.parser = cli_main.construir_parser()

    def tearDown(self):
        self._tmp.cleanup()

    def test_plan_sin_informe_sigue_pidiendo_analyze(self):
        args = self.parser.parse_args(
            ["--root", str(self.root), "build", "PLAN-001"])
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = args.func(args)
        self.assertEqual(codigo, 1)
        self.assertIn("sin informe para PLAN-001", salida.getvalue())
        self.assertIn("analyze PLAN-001", salida.getvalue())


class TestPinEscribe(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "proyecto"
        shutil.copytree(FIXTURE, self.root)
        self.parser = cli_main.construir_parser()
        self.pin = self.root / ".specify" / "pines" / "TASK-001.json"

    def tearDown(self):
        self._tmp.cleanup()

    def _despachar(self, argv: list[str]) -> tuple[int, str]:
        args = self.parser.parse_args(["--root", str(self.root), *argv])
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = args.func(args)
        return codigo, salida.getvalue()

    def test_pin_task_guarda_linea_base(self):
        """El `_guardar_pin` no importado mataba el comando justo al guardar."""
        self.pin.unlink()
        codigo, salida = self._despachar(
            ["pin", "PLAN-001", "--task", "TASK-001"])
        self.assertEqual(codigo, 0, salida)
        self.assertIn("📌 PIN TASK-001", salida)
        self.assertIn("Línea base registrada", salida)
        self.assertTrue(self.pin.is_file())
        datos = json.loads(self.pin.read_text(encoding="utf-8"))
        self.assertIn("baseline", datos)
        self.assertEqual(datos["desviaciones"], [])

    def test_avisa_cuando_reutiliza_la_linea_base(self):
        """Con pin previo no se registra nada: el mensaje no debe fingirlo."""
        codigo, salida = self._despachar(
            ["pin", "PLAN-001", "--task", "TASK-001"])
        self.assertEqual(codigo, 0, salida)
        self.assertIn("Línea base ya existente", salida)
        self.assertNotIn("Línea base registrada", salida)

    def test_pin_no_borra_las_desviaciones_registradas(self):
        """Escribir el pin desde el CLI habría puesto la lista en blanco."""
        datos = json.loads(self.pin.read_text(encoding="utf-8"))
        datos["desviaciones"] = [
            {"clase": "B", "archivo": "src/productos.py",
             "detalle": "firma cambiada"}]
        self.pin.write_text(json.dumps(datos), encoding="utf-8")
        codigo, salida = self._despachar(
            ["pin", "PLAN-001", "--task", "TASK-001"])
        self.assertEqual(codigo, 0, salida)
        despues = json.loads(self.pin.read_text(encoding="utf-8"))
        self.assertEqual(len(despues["desviaciones"]), 1)
        self.assertEqual(despues["desviaciones"][0]["clase"], "B")


if __name__ == "__main__":
    unittest.main()
