"""Pruebas de RF-27 — Consolidación y cierre (§18.5)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.build import EN_CURSO, registrar_done  # noqa: E402
from core.pin import tomar_baseline  # noqa: E402
from core.tasks import Tarea  # noqa: E402
from core.validate import validar  # noqa: E402

ACC_GREEN = ("import unittest\n\n\nclass TestA(unittest.TestCase):\n"
             "    def test_cubre(self):\n"
             "        \"\"\"Cubre CP-001.\"\"\"\n"
             "        self.assertTrue(True)\n")
ACC_RED = ACC_GREEN.replace("assertTrue(True)", "assertTrue(False)")


def _spec():
    return SimpleNamespace(
        spec_id="SPEC-001",
        funcionales=[("REQ-001", "Vender", "aceptado")],
        fuera_alcance=[], supuestos=[],
        criterios=[SimpleNamespace(id="CRI-001", texto="t",
                                   req_id="REQ-001")],
        casos=[SimpleNamespace(id="CP-001", texto="t",
                               criterio_id="CRI-001")])


class FakePlan:
    plan_id = "PLAN-001"


def _tarea(**kw):
    base = dict(descripcion="D", objetivo="O",
                archivos=["src/a.py", "tests/test_accept_a.py"],
                dependencias=[], precondiciones=[], resultado="R",
                criterio="C", pruebas=["CP-001"], refs=["REQ-001"])
    base.update(kw)
    t = Tarea(id="TASK-001", **base)
    t.estado = EN_CURSO
    return t


class TestConsolidacion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "src" / "a.py").write_text("X = 1\n",
                                                encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _pin(self, tarea):
        base = tomar_baseline(tarea, self.root)
        from core.pin import foto_arbol  # noqa: PLC0415
        base["__arbol__"] = foto_arbol(self.root)
        carpeta = self.root / ".specify" / "pines"
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "TASK-001.json").write_text(
            json.dumps({"baseline": base, "desviaciones": []}),
            encoding="utf-8")

    def test_caso_en_rojo_bloquea_aun_con_nota(self):
        (self.root / "tests" / "test_accept_a.py").write_text(
            ACC_RED, encoding="utf-8")
        t = _tarea()
        self._pin(t)
        r = validar(self.root, t, FakePlan(), _spec(), [], nota="la justifico")
        self.assertEqual(r["veredicto"], "RECHAZADO")
        self.assertTrue(any("criterio incumplido" in x for x in r["rechazos"]))

    def test_caso_sin_prueba_observa_y_con_nota_valida(self):
        (self.root / "tests" / "test_accept_a.py").write_text(
            "import unittest\n", encoding="utf-8")
        t = _tarea()
        self._pin(t)
        r_sin = validar(self.root, t, FakePlan(), _spec(), [])
        self.assertEqual(r_sin["veredicto"], "OBSERVADO")
        self.assertTrue(any("sin evidencia" in x
                            for x in r_sin["observaciones"]))
        r_con = validar(self.root, t, FakePlan(), _spec(), [],
                        nota="verificado manualmente")
        self.assertEqual(r_con["veredicto"], "VALIDADO")

    def test_cierre_conserva_hashes_y_evidencia(self):
        (self.root / "tests" / "test_accept_a.py").write_text(
            ACC_GREEN, encoding="utf-8")
        t = _tarea()
        ev = registrar_done(
            t, [t], self.root, nota="ok",
            evidencia={"fecha": "f", "pruebas_ok": True, "total": 1,
                       "pasadas": 1, "fallidas": 0, "omitidas": 0,
                       "duracion_s": 0.1, "cobertura_pct": 100,
                       "pruebas": "verde"})
        self.assertEqual(ev["evento"], "completada")
        self.assertIn("tests/test_accept_a.py", ev["hashes_tests"])
        self.assertEqual(ev["evidencia_tests"]["cobertura_pct"], 100)

    def test_sin_cps_reales_no_cambia_puerta(self):
        (self.root / "src" / "a.py").write_text(
            "X = 1\n\n\ndef nueva():\n    return 1\n", encoding="utf-8")
        t = _tarea(pruebas=[], archivos=["src/a.py"])
        self._pin(t)
        r = validar(self.root, t, FakePlan(), _spec(), [],
                    nota="nueva() exigida")
        self.assertEqual(r["veredicto"], "VALIDADO")


if __name__ == "__main__":
    unittest.main()
