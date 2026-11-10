"""Pruebas de RF-28 — Protección de pruebas (§18.3)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.pin import tomar_baseline  # noqa: E402
from core.tasks import Tarea  # noqa: E402
from core.testguard import verificar  # noqa: E402
from core.validate import validar  # noqa: E402


def _tarea(**kw):
    base = dict(descripcion="D", objetivo="O",
                archivos=["src/a.py", "tests/test_a.py"],
                dependencias=[], precondiciones=[], resultado="R",
                criterio="C", pruebas=[], refs=["REQ-001"])
    base.update(kw)
    return Tarea(id="TASK-001", **base)


class FakePlan:
    plan_id = "PLAN-001"


class FakeSpec:
    spec_id = "SPEC-001"
    funcionales = [("REQ-001", "Vender", "aceptado")]
    fuera_alcance = []
    supuestos = []


class TestTestguard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "src" / "a.py").write_text("X = 1\n",
                                                encoding="utf-8")
        (self.root / "tests" / "test_a.py").write_text(
            "import unittest\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _base(self, tarea):
        return tomar_baseline(tarea, self.root)

    def test_sin_cambios_sin_observaciones(self):
        t = _tarea()
        r = verificar(self.root, t, self._base(t), [])
        self.assertEqual(r["modificados"], [])
        self.assertEqual(r["observaciones"], [])

    def test_modificado_sin_nota_observa_con_nota_pasa(self):
        t = _tarea()
        base = self._base(t)
        (self.root / "tests" / "test_a.py").write_text(
            "import unittest  # ajustado\n", encoding="utf-8")
        r_sin = verificar(self.root, t, base, [])
        self.assertEqual(r_sin["modificados"], ["tests/test_a.py"])
        self.assertTrue(any("--nota" in o for o in r_sin["observaciones"]))
        r_con = verificar(self.root, t, base, [], nota="test incorrecto")
        self.assertEqual(r_con["observaciones"], [])

    def test_cambiado_tras_rojo_es_sospechoso(self):
        t = _tarea()
        base = self._base(t)
        import hashlib  # noqa: PLC0415
        viejo = hashlib.sha256(
            (self.root / "tests" / "test_a.py").read_bytes()
        ).hexdigest()[:16]
        (self.root / "tests" / "test_a.py").write_text(
            "import unittest  # verde por edición\n", encoding="utf-8")
        eventos = [{"evento": "tests", "tarea": "TASK-001",
                    "pruebas_ok": False,
                    "hashes_tests": {"tests/test_a.py": viejo}}]
        r = verificar(self.root, t, base, eventos)
        self.assertEqual(r["sospechosos"], ["tests/test_a.py"])
        self.assertTrue(any("verde por edici" in o
                            for o in r["observaciones"]))

    def test_cambiado_tras_corrida_exige_reejecutar(self):
        t = _tarea()
        base = self._base(t)
        import hashlib  # noqa: PLC0415
        viejo = hashlib.sha256(
            (self.root / "tests" / "test_a.py").read_bytes()
        ).hexdigest()[:16]
        (self.root / "tests" / "test_a.py").write_text(
            "import unittest  # cosmético\n", encoding="utf-8")
        eventos = [{"evento": "tests", "tarea": "TASK-001",
                    "pruebas_ok": True,
                    "hashes_tests": {"tests/test_a.py": viejo}}]
        r = verificar(self.root, t, base, eventos)
        self.assertEqual(r["desactualizados"], ["tests/test_a.py"])
        self.assertTrue(any("re-ejecute" in o for o in r["observaciones"]))

    def test_cierre_exige_nota_si_test_cambio(self):
        t = _tarea()
        base = tomar_baseline(t, self.root)
        from core.pin import foto_arbol  # noqa: PLC0415
        base["__arbol__"] = foto_arbol(self.root)
        carpeta = self.root / ".specify" / "pines"
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "TASK-001.json").write_text(
            json.dumps({"baseline": base, "desviaciones": []}),
            encoding="utf-8")
        (self.root / "tests" / "test_a.py").write_text(
            "import unittest  # cambio silencioso\n", encoding="utf-8")
        r_sin = validar(self.root, t, FakePlan(), FakeSpec(), [])
        self.assertEqual(r_sin["veredicto"], "OBSERVADO")
        r_con = validar(self.root, t, FakePlan(), FakeSpec(), [],
                        nota="test desactualizado por REQ-001 aprobado")
        self.assertEqual(r_con["veredicto"], "VALIDADO")


if __name__ == "__main__":
    unittest.main()
