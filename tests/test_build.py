"""Pruebas de RF-09 — Ejecución de implementación (§11)."""

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from cli.commands import analyze as cmd_analyze  # noqa: E402
from cli.commands import build as cmd_build  # noqa: E402
from cli.commands import clarify as cmd_clarify  # noqa: E402
from cli.commands import enrich as cmd_enrich  # noqa: E402
from cli.commands import plan as cmd_plan  # noqa: E402
from cli.commands import specify as cmd_specify  # noqa: E402
from cli.commands import tasks as cmd_tasks  # noqa: E402
from core.build import (  # noqa: E402
    BuildError,
    ejecutar_pruebas,
    marcar_en_curso,
    registrar_done,
    siguiente_tarea,
    tarjeta_pin,
)
from core.spec import Spec  # noqa: E402
from core.tasks import Tarea  # noqa: E402
from state import store  # noqa: E402

KIOSCO = "Quiero un dashboard para gestionar un kiosco. Debe registrar ventas."


def _tarea(tid, deps=None, **kw):
    base = dict(descripcion="D", objetivo="O", archivos=[],
                dependencias=deps or [], precondiciones=[], resultado="R",
                criterio="C", pruebas=[], refs=["REQ-001"])
    base.update(kw)
    return Tarea(id=tid, **base)


class TestMaquina(unittest.TestCase):
    def test_cadena_respeta_dependencias(self):
        a, b = _tarea("TASK-001"), _tarea("TASK-002", deps=["TASK-001"])
        self.assertIs(siguiente_tarea([a, b]), a)
        with self.assertRaises(BuildError):
            marcar_en_curso(b, [a, b])
        a.estado = "completada"
        self.assertIs(siguiente_tarea([a, b]), b)

    def test_no_dos_en_curso(self):
        a, b = _tarea("TASK-001"), _tarea("TASK-002")
        marcar_en_curso(a, [a, b])
        with self.assertRaises(BuildError):
            marcar_en_curso(b, [a, b])

    def test_done_exige_archivos_y_corre_pruebas_reales(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "tests").mkdir()
            (raiz / "tests" / "__init__.py").write_text("", encoding="utf-8")
            (raiz / "tests" / "test_x.py").write_text(
                "import unittest\nclass T(unittest.TestCase):\n"
                "    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8")
            (raiz / "src").mkdir()
            (raiz / "src" / "x.py").write_text("X = 1\n", encoding="utf-8")
            t = _tarea("TASK-001", archivos=["src/x.py", "tests/test_x.py"])
            t.estado = "en_curso"
            evento = registrar_done(t, [t], raiz)
            self.assertEqual(evento["evento"], "completada")
            self.assertTrue(evento["pruebas_ok"])
            self.assertEqual(t.estado, "completada")

    def test_done_falla_si_pruebas_no_pasan_y_no_oculta(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "tests").mkdir()
            (raiz / "tests" / "__init__.py").write_text("", encoding="utf-8")
            (raiz / "tests" / "test_y.py").write_text(
                "import unittest\nclass T(unittest.TestCase):\n"
                "    def test_no(self):\n        self.assertTrue(False)\n",
                encoding="utf-8")
            (raiz / "src").mkdir()
            (raiz / "src" / "y.py").write_text("Y = 1\n", encoding="utf-8")
            t = _tarea("TASK-001", archivos=["src/y.py", "tests/test_y.py"])
            t.estado = "en_curso"
            evento = registrar_done(t, [t], raiz)
            self.assertEqual(evento["evento"], "fallida")
            self.assertFalse(evento["pruebas_ok"])
            self.assertEqual(t.estado, "fallida")

    def test_done_exige_archivos_objetivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = _tarea("TASK-001", archivos=["src/no_existe.py"])
            t.estado = "en_curso"
            with self.assertRaises(BuildError):
                registrar_done(t, [t], Path(tmp))

    def test_pin_muestra_restricciones(self):
        spec = Spec(spec_id="SPEC-001", titulo="T",
                    funcionales=[("REQ-001", "Registrar ventas", "aceptado")],
                    fuera_alcance=["Pasarela de pago"])
        t = _tarea("TASK-001", refs=["REQ-001"], archivos=["src/a.py"], criterio="C")
        pin = tarjeta_pin(t, spec)
        for esperado in ("SPEC-001", "REQ-001", "src/a.py", "Pasarela de pago", "Criterio"):
            self.assertIn(esperado, pin)


class TestCLIBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        store.inicializar_proyecto(self.root)
        cmd_enrich.despachar(self._ns("enrich", texto=KIOSCO))
        cmd_enrich.despachar(self._ns("enrich", accept="ENR-001"))
        cmd_specify.despachar(self._ns("spec", texto="ENR-001"))

    def tearDown(self):
        self.tmp.cleanup()

    def _ns(self, cual, **kw):
        bases = {
            "enrich": {"texto": None, "list": False, "show": None, "drop": None, "accept": None},
            "spec": {"texto": None, "titulo": None, "list": False, "show": None,
                     "approve": None, "revise": None, "motivo": None},
            "cla": {"texto": None, "answer": None, "skip": None, "list": None, "gate": False},
            "plan": {"texto": None, "force": False, "list": False, "show": None, "gate": None},
            "tasks": {"texto": None, "force": False, "list": None, "show": None, "gate": None},
        }
        base = bases[cual]
        base.update(kw)
        ns = argparse.Namespace(root=str(self.root))
        for k, v in base.items():
            setattr(ns, k, v)
        return ns

    def _pipeline_hasta_tasks(self):
        self.assertEqual(cmd_clarify.despachar(self._ns("cla", texto="SPEC-001", gate=True)), 1)
        preguntas, _h = cmd_clarify._preguntas_de(self.root, "SPEC-001")
        ns = self._ns("cla", texto="SPEC-001")
        ns.answer = [[p.id, "Definido"] for p in preguntas]
        self.assertEqual(cmd_clarify.despachar(ns), 0)
        cmd_plan.despachar(self._ns("plan", texto="SPEC-001"))
        cmd_plan.despachar(self._ns("plan", gate="PLAN-001"))
        cmd_tasks.despachar(self._ns("tasks", texto="PLAN-001"))

    def _b(self, **kw):
        base = {"texto": None, "done": None, "fail": None, "nota": ""}
        base.update(kw)
        ns = argparse.Namespace(root=str(self.root))
        for k, v in base.items():
            setattr(ns, k, v)
        return ns

    def test_exige_gate4(self):
        self._pipeline_hasta_tasks()
        self.assertEqual(cmd_build.despachar(self._b(texto="PLAN-001")), 1)
        cmd_analyze.despachar(argparse.Namespace(
            root=str(self.root), texto="PLAN-001", gate=None))
        self.assertEqual(cmd_build.despachar(self._b(texto="PLAN-001")), 0)
        _info, tareas = cmd_tasks._cargar_tareas(self.root, "PLAN-001")
        self.assertEqual(tareas[0].estado, "en_curso")

    def test_done_y_fail_registran_en_diario(self):
        self._pipeline_hasta_tasks()
        cmd_analyze.despachar(argparse.Namespace(
            root=str(self.root), texto="PLAN-001", gate=None))
        cmd_build.despachar(self._b(texto="PLAN-001"))
        _info, tareas = cmd_tasks._cargar_tareas(self.root, "PLAN-001")
        primera = tareas[0]
        # Sin archivos implementados no se puede dar por hecha.
        self.assertEqual(
            cmd_build.despachar(self._b(texto="PLAN-001", done=primera.id)), 1)
        # Implementar de verdad: crear los archivos propuestos.
        for a in primera.archivos:
            (self.root / a).parent.mkdir(parents=True, exist_ok=True)
            if a.startswith("tests/") and a.endswith(".py"):
                nombre = Path(a).stem
                (self.root / a).write_text(
                    "import unittest\n\n\nclass TestHumano(unittest.TestCase):"
                    "\n    def test_implementado(self):\n"
                    "        self.assertTrue(True)\n",
                    encoding="utf-8")
            else:
                (self.root / a).write_text("# implementado\n", encoding="utf-8")
        self.assertEqual(
            cmd_build.despachar(self._b(texto="PLAN-001", done=primera.id,
                                        nota="hecho a mano")), 0)
        from core.journal import historial as _historial  # noqa: PLC0415
        eventos = [e for e in _historial(self.root, "PLAN-001")
                   if e["tarea"] == primera.id]
        self.assertTrue(any(e["evento"] == "completada" for e in eventos))
        self.assertTrue(any(e["evento"] == "checkpoint" for e in eventos))
        from core.checkpoints import cargar as _cargar_cp  # noqa: PLC0415
        cp = _cargar_cp(self.root, primera.id)
        self.assertIsNotNone(cp)
        self.assertIn(primera.archivos[0], cp["hashes"])
        # La siguiente avanza sola al estar libre la cadena.
        self.assertEqual(cmd_build.despachar(self._b(texto="PLAN-001")), 0)
        _i2, tareas2 = cmd_tasks._cargar_tareas(self.root, "PLAN-001")
        self.assertEqual(tareas2[1].estado, "en_curso")


if __name__ == "__main__":
    unittest.main()
