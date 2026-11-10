"""Pruebas de RF-06 — Desglose en tareas (§9)."""

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent))

from cli.commands import clarify as cmd_clarify  # noqa: E402
from cli.commands import enrich as cmd_enrich  # noqa: E402
from cli.commands import plan as cmd_plan  # noqa: E402
from cli.commands import specify as cmd_specify  # noqa: E402
from cli.commands import tasks as cmd_tasks  # noqa: E402
from core.tasks import Tarea, generar_desde_plan, verificar_gate3  # noqa: E402
from state import store  # noqa: E402

KIOSCO = "Quiero un dashboard para gestionar un kiosco. Debe registrar ventas."


def _tarea_minima(tid="TASK-001", **kw):
    base = dict(descripcion="D", objetivo="O", archivos=["src/a.py"],
                dependencias=[], precondiciones=[], resultado="R",
                criterio="C", pruebas=["CP-001"], refs=["REQ-001"])
    base.update(kw)
    return Tarea(id=tid, **base)


class TestGate3Puro(unittest.TestCase):
    def test_pasa_con_tarea_completa_y_falla_con_huecos(self):
        self.assertEqual(verificar_gate3([_tarea_minima()]), [])
        sin_criterio = _tarea_minima("TASK-002", criterio="  ")
        sin_archivos = _tarea_minima("TASK-003", archivos=[])
        sin_refs = _tarea_minima("TASK-004", refs=[])
        colgada = _tarea_minima("TASK-005", dependencias=["TASK-999"])
        problemas = verificar_gate3([sin_criterio, sin_archivos, sin_refs, colgada])
        self.assertEqual(len(problemas), 4)

    def test_detecta_ciclos(self):
        a = _tarea_minima("TASK-001", dependencias=["TASK-002"])
        b = _tarea_minima("TASK-002", dependencias=["TASK-001"])
        self.assertTrue(any("ciclo" in p for p in verificar_gate3([a, b])))


class TestCLITasks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        store.inicializar_proyecto(self.root)
        cmd_enrich.despachar(self._ns_enrich(texto=KIOSCO))
        cmd_enrich.despachar(self._ns_enrich(accept="ENR-001"))
        cmd_specify.despachar(self._ns_spec(texto="ENR-001"))
        self.assertEqual(
            cmd_clarify.despachar(self._ns_cla(texto="SPEC-001", gate=True)), 1)
        preguntas, _h = cmd_clarify._preguntas_de(self.root, "SPEC-001")
        ns = self._ns_cla(texto="SPEC-001")
        ns.answer = [[p.id, "Definido"] for p in preguntas]
        self.assertEqual(cmd_clarify.despachar(ns), 0)

    def tearDown(self):
        self.tmp.cleanup()

    def _ns(self, base):
        ns = argparse.Namespace(root=str(self.root))
        for k, v in base.items():
            setattr(ns, k, v)
        return ns

    def _ns_enrich(self, **kw):
        return self._ns({"texto": None, "list": False, "show": None,
                        "drop": None, "accept": None, **kw})

    def _ns_spec(self, **kw):
        return self._ns({"texto": None, "titulo": None, "list": False,
                         "show": None, "approve": None, "revise": None,
                         "motivo": None, **kw})

    def _ns_cla(self, **kw):
        return self._ns({"texto": None, "answer": None, "skip": None,
                         "list": None, "gate": False, **kw})

    def _ns_plan(self, **kw):
        return self._ns({"texto": None, "force": False, "list": False,
                         "show": None, "gate": None, **kw})

    def _ns_tasks(self, **kw):
        return self._ns({"texto": None, "force": False, "list": None,
                         "show": None, "gate": None, **kw})

    def test_exige_plan_validado(self):
        cmd_plan.despachar(self._ns_plan(texto="SPEC-001"))
        # Plan en draft (sin gate 2) → tasks bloqueado.
        self.assertEqual(cmd_tasks.despachar(self._ns_tasks(texto="PLAN-001")), 1)
        self.assertEqual(cmd_plan.despachar(self._ns_plan(gate="PLAN-001")), 0)
        self.assertEqual(cmd_tasks.despachar(self._ns_tasks(texto="PLAN-001")), 0)
        _info, tareas = cmd_tasks._cargar_tareas(self.root, "PLAN-001")
        self.assertTrue(tareas)
        # Cadena secuencial: cada tarea depende de la anterior.
        for anterior, actual in zip(tareas, tareas[1:]):
            self.assertEqual(actual.dependencias, [anterior.id])
        # Toda tarea con criterio, archivos, pruebas y refs (§9.5).
        self.assertEqual(verificar_gate3(tareas), [])
        self.assertEqual(cmd_tasks.despachar(self._ns_tasks(gate="PLAN-001")), 0)

    def test_sin_force_no_sobrescribe(self):
        cmd_plan.despachar(self._ns_plan(texto="SPEC-001"))
        cmd_plan.despachar(self._ns_plan(gate="PLAN-001"))
        self.assertEqual(cmd_tasks.despachar(self._ns_tasks(texto="PLAN-001")), 0)
        self.assertEqual(cmd_tasks.despachar(self._ns_tasks(texto="PLAN-001")), 1)
        self.assertEqual(
            cmd_tasks.despachar(self._ns_tasks(texto="PLAN-001", force=True)), 0)

    def test_pruebas_vienen_de_los_casos_spec(self):
        cmd_plan.despachar(self._ns_plan(texto="SPEC-001"))
        cmd_plan.despachar(self._ns_plan(gate="PLAN-001"))
        cmd_tasks.despachar(self._ns_tasks(texto="PLAN-001"))
        _info, tareas = cmd_tasks._cargar_tareas(self.root, "PLAN-001")
        con_caso = [t for t in tareas if any(p.startswith("CP-") for p in t.pruebas)]
        self.assertTrue(con_caso)


if __name__ == "__main__":
    unittest.main()
