"""Pruebas de RF-18 — Validación de cambios (§48)."""

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.pin import tomar_baseline  # noqa: E402
from core.tasks import Tarea  # noqa: E402
from core.validate import validar  # noqa: E402


class FakeSpec:
    spec_id = "SPEC-001"
    funcionales = [("REQ-001", "Registrar ventas", "aceptado")]


class FakePlan:
    plan_id = "PLAN-001"


def _tarea(**kw):
    base = dict(descripcion="D", objetivo="O", archivos=["src/a.py"],
                dependencias=[], precondiciones=[], resultado="R",
                criterio="C", pruebas=[], refs=["REQ-001"])
    base.update(kw)
    return Tarea(id="TASK-001", **base)


class TestValidate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("X = 1\n", encoding="utf-8")
        (self.root / "src" / "b.py").write_text("Y = 1\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _base(self, tarea):
        base = tomar_baseline(tarea, self.root)
        from core.pin import foto_arbol  # noqa: PLC0415
        base["__arbol__"] = foto_arbol(self.root)
        (self.root / ".specify" / "pines").mkdir(parents=True, exist_ok=True)
        import json  # noqa: PLC0415
        (self.root / ".specify" / "pines" / "TASK-001.json").write_text(
            json.dumps({"baseline": base, "desviaciones": []}), encoding="utf-8")
        return base

    def test_ref_sin_trazabilidad_rechaza(self):
        t = _tarea(refs=["REQ-999"])
        self._base(t)
        r = validar(self.root, t, FakePlan(), FakeSpec(), [], nota="x")
        self.assertEqual(r["veredicto"], "RECHAZADO")

    def test_archivo_ajeno_rechaza_aunque_haya_nota(self):
        t = _tarea()
        self._base(t)
        (self.root / "src" / "b.py").write_text("Y = 2\n", encoding="utf-8")
        r = validar(self.root, t, FakePlan(), FakeSpec(), [], nota="la justifico")
        self.assertEqual(r["veredicto"], "RECHAZADO")
        self.assertTrue(r["rechazos"])

    def test_novedad_justificada_valida_y_sin_nota_observa(self):
        t = _tarea()
        self._base(t)
        (self.root / "src" / "a.py").write_text(
            "X = 1\n\n\ndef nueva():\n    return 1\n", encoding="utf-8")
        r_sin = validar(self.root, t, FakePlan(), FakeSpec(), [])
        self.assertEqual(r_sin["veredicto"], "OBSERVADO")
        r_con = validar(self.root, t, FakePlan(), FakeSpec(), [],
                        nota="nueva() exigida por el criterio")
        self.assertEqual(r_con["veredicto"], "VALIDADO")
        self.assertTrue(r_con["observaciones"])  # justificadas, visibles igual


if __name__ == "__main__":
    unittest.main()
