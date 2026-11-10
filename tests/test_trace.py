"""Pruebas de RF-29 — Trazabilidad completa (§39)."""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.tasks import Tarea  # noqa: E402
from core.trace import matriz  # noqa: E402

ACC = ("import unittest\n\n\nclass TestA(unittest.TestCase):\n"
       "    def test_cubre(self):\n"
       "        \"\"\"Cubre CP-001.\"\"\"\n"
       "        self.assertTrue(True)\n")


def _spec():
    return SimpleNamespace(
        spec_id="SPEC-001", enr_origen="ENR-001",
        funcionales=[("REQ-001", "Vender", "aceptado"),
                     ("REQ-002", "Fiado", "pendiente")],
        criterios=[SimpleNamespace(id="CRI-001", texto="t",
                                   req_id="REQ-001")],
        casos=[SimpleNamespace(id="CP-001", texto="flujo de venta",
                               criterio_id="CRI-001")])


def _tarea(**kw):
    base = dict(descripcion="D", objetivo="O",
                archivos=["src/a.py", "tests/test_accept_a.py"],
                dependencias=[], precondiciones=[], resultado="R",
                criterio="C", pruebas=["CP-001"], refs=["REQ-001"])
    base.update(kw)
    t = Tarea(id="TASK-001", **base)
    t.estado = "completada"
    return t


class TestTrace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "src" / "a.py").write_text("X = 1\n",
                                                encoding="utf-8")
        (self.root / "tests" / "test_accept_a.py").write_text(
            ACC, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_cadena_completa_recorrida(self):
        plan = SimpleNamespace(plan_id="PLAN-001", status="validado")
        eventos = [
            {"evento": "tests", "tarea": "TASK-001", "pruebas_ok": True,
             "fecha": "f1", "cobertura_pct": 100},
            {"evento": "completada", "tarea": "TASK-001", "fecha": "f2"}]
        texto = matriz(_spec(), [(plan, [_tarea()])], eventos, self.root)
        self.assertIn("ENR-001", texto)
        self.assertIn("PLAN-001", texto)
        self.assertIn("REQ-001", texto)
        self.assertIn("CRI-001", texto)
        self.assertIn("CP-001", texto)
        self.assertIn("TASK-001", texto)
        self.assertIn("test_cubre", texto)
        self.assertIn("src/a.py", texto)
        self.assertIn("✅", texto)
        self.assertIn("cerrada f2", texto)

    def test_req_sin_criterios_y_caso_sin_tarea_se_declaran(self):
        plan = SimpleNamespace(plan_id="PLAN-001", status="x")
        texto = matriz(_spec(), [(plan, [_tarea(pruebas=[])])], [],
                       self.root)
        self.assertIn("REQ-002", texto)
        self.assertIn("sin criterios", texto)
        self.assertIn("sin tarea que lo pida", texto)

    def test_caso_sin_prueba_se_declara(self):
        (self.root / "tests" / "test_accept_a.py").write_text(
            "import unittest\n", encoding="utf-8")
        plan = SimpleNamespace(plan_id="PLAN-001", status="x")
        texto = matriz(_spec(), [(plan, [_tarea()])], [], self.root)
        self.assertIn("SIN PRUEBA ejecutable", texto)

    def test_cambio_modificado_se_reporta(self):
        plan = SimpleNamespace(plan_id="PLAN-001", status="x")
        (self.root / ".specify" / "pines").mkdir(parents=True)
        import hashlib  # noqa: PLC0415
        import json  # noqa: PLC0415
        viejo = hashlib.sha256(b"X = 0\n").hexdigest()
        (self.root / ".specify" / "pines" / "TASK-001.json").write_text(
            json.dumps({"baseline": {"src/a.py": {"sha": viejo}}}),
            encoding="utf-8")
        texto = matriz(_spec(), [(plan, [_tarea()])], [], self.root)
        self.assertIn("src/a.py (modificado)", texto)


if __name__ == "__main__":
    unittest.main()
