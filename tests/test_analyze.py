"""Pruebas de RF-07 — Análisis de consistencia (§10)."""

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent))

from cli.commands import analyze as cmd_analyze  # noqa: E402
from cli.commands import clarify as cmd_clarify  # noqa: E402
from cli.commands import enrich as cmd_enrich  # noqa: E402
from cli.commands import plan as cmd_plan  # noqa: E402
from cli.commands import specify as cmd_specify  # noqa: E402
from cli.commands import tasks as cmd_tasks  # noqa: E402
from core.analyze import analizar  # noqa: E402
from core.plan import Plan  # noqa: E402
from core.spec import Spec  # noqa: E402
from core.tasks import Tarea  # noqa: E402
from state import store  # noqa: E402

KIOSCO = "Quiero un dashboard para gestionar un kiosco. Debe registrar ventas."


def _espec_base(**kw):
    base = dict(spec_id="SPEC-001", titulo="T",
                funcionales=[("REQ-001", "Registrar ventas", "aceptado")],
                fuera_alcance=["Pasarela de pago"])
    base.update(kw)
    return Spec(**base)


def _plan_base(**kw):
    base = dict(plan_id="PLAN-001", spec_id="SPEC-001",
                hallazgos={"codigo": [], "es_greenfield": True},
                modificables=["src/ventas.py"], riesgos=[])
    base.update(kw)
    return Plan(**base)


def _tarea_base(tid="TASK-001", **kw):
    base = dict(descripcion="D", objetivo="O", archivos=["src/ventas.py"],
                dependencias=[], precondiciones=[], resultado="R",
                criterio="C: verificar", pruebas=["CP-001"], refs=["REQ-001"])
    base.update(kw)
    return Tarea(id=tid, **base)


class TestComprobaciones(unittest.TestCase):
    def test_req_sin_tarea_es_critica(self):
        probs = analizar(_plan_base(), _espec_base(), [], Path("."))
        self.assertTrue(any(p.severidad == "critica" and "REQ-001" in p.artefactos
                            for p in probs))

    def test_tarea_sin_refs_es_critica_y_solo_seccion_advierte(self):
        probs = analizar(_plan_base(), _espec_base(), [_tarea_base(refs=[])], Path("."))
        self.assertTrue(any(p.severidad == "critica" and "sin trazabilidad" in p.explicacion
                            for p in probs))
        probs2 = analizar(_plan_base(), _espec_base(),
                          [_tarea_base(refs=["§6:algo"])], Path("."))
        self.assertTrue(any(p.severidad == "advertencia" and "indirecta" in p.explicacion
                            for p in probs2))

    def test_archivo_protegido_y_fuera_de_alcance(self):
        plan = _plan_base(modificables=[".specify/dato.json"])
        probs = analizar(plan, _espec_base(), [_tarea_base(archivos=[".specify/dato.json"])],
                         Path("."))
        self.assertTrue(any("protegido" in p.evidencia for p in probs))
        plan2 = _plan_base(modificables=["src/pasarela_pago.py"])
        spec2 = _espec_base(fuera_alcance=["Integración con pasarela de pago externa"])
        probs2 = analizar(plan2, spec2, [_tarea_base(archivos=["src/pasarela_pago.py"])],
                          Path("."))
        self.assertTrue(any("fuera de alcance" in p.explicacion for p in probs2))

    def test_dependencia_inexistente_y_riesgo_como_advertencia(self):
        plan = _plan_base(riesgos=["Falta definir persistencia"])
        t = _tarea_base(dependencias=["TASK-999"])
        severidades = {p.severidad for p in analizar(plan, _espec_base(), [t], Path("."))}
        self.assertIn("critica", severidades)
        self.assertIn("advertencia", severidades)

    def test_informe_limpio_sin_falsos_positivos(self):
        probs = analizar(_plan_base(), _espec_base(), [_tarea_base()], Path("."))
        self.assertEqual(probs, [])


class TestCLIAnalyze(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        store.inicializar_proyecto(self.root)
        cmd_enrich.despachar(self._ns("enrich", texto=KIOSCO))
        cmd_enrich.despachar(self._ns("enrich", accept="ENR-001"))
        cmd_specify.despachar(self._ns("spec", texto="ENR-001"))
        self.assertEqual(cmd_clarify.despachar(self._ns("cla", texto="SPEC-001", gate=True)), 1)
        preguntas, _h = cmd_clarify._preguntas_de(self.root, "SPEC-001")
        ns = self._ns("cla", texto="SPEC-001")
        ns.answer = [[p.id, "Definido"] for p in preguntas]
        self.assertEqual(cmd_clarify.despachar(ns), 0)
        cmd_plan.despachar(self._ns("plan", texto="SPEC-001"))
        cmd_plan.despachar(self._ns("plan", gate="PLAN-001"))
        cmd_tasks.despachar(self._ns("tasks", texto="PLAN-001"))

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

    def test_informe_y_gate4_end_to_end(self):
        self.assertEqual(cmd_analyze.despachar(
            argparse.Namespace(root=str(self.root), texto="PLAN-001", gate=None)), 0)
        ruta = self.root / ".specify" / "informes" / "INFORME-PLAN-001.md"
        self.assertTrue(ruta.exists())
        rc = cmd_analyze.despachar(
            argparse.Namespace(root=str(self.root), texto=None, gate="PLAN-001"))
        # El informe del flujo demo solo tiene advertencias → gate superado.
        self.assertEqual(rc, 0)
        self.assertIn("ADVERTENCIA",
                      (self.root / ".specify" / "informes" / "INFORME-PLAN-001.md").read_text())


if __name__ == "__main__":
    unittest.main()
