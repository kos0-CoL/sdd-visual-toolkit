"""Pruebas de RF-10 — Spec Pinning (§11.1, §12)."""

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.pin import (  # noqa: E402
    _es_protegido,
    decisiones_aprobadas,
    foto_arbol,
    generar_pin,
    snapshot_archivo,
    tomar_baseline,
    verificar_cambios,
)
from core.plan import Plan  # noqa: E402
from core.spec import Spec  # noqa: E402
from core.tasks import Tarea  # noqa: E402

SPEC = Spec(spec_id="SPEC-001", titulo="T", enr_origen="ENR-001",
            funcionales=[("REQ-001", "Registrar ventas", "aceptado")],
            fuera_alcance=["Pasarela de pago"],
            supuestos=["✓ Aclarado (CLA-001): stack → PostgreSQL"])
PLAN = Plan(plan_id="PLAN-001", spec_id="SPEC-001")


def _tarea(**kw):
    base = dict(descripcion="D", objetivo="O", archivos=["src/a.py"],
                dependencias=[], precondiciones=[], resultado="R",
                criterio="C", pruebas=[], refs=["REQ-001"])
    base.update(kw)
    return Tarea(id="TASK-001", **base)


def _proyecto(modificado: str = "X = 1\n") -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    raiz = Path(tmp.name)
    (raiz / "src").mkdir()
    (raiz / "src" / "a.py").write_text("X = 1\n", encoding="utf-8")
    (raiz / "src" / "b.py").write_text(modificado, encoding="utf-8")
    return tmp


class TestPin(unittest.TestCase):
    def test_tarjeta_contiene_las_8_restricciones(self):
        pin = generar_pin(PLAN, SPEC, _tarea(),
                          decisiones_aprobadas([{"pregunta": "CLA-001",
                                                 "respuesta": "PostgreSQL"}]))
        for esperado in ("SPEC-001", "ENR-001", "REQ-001", "TASK-001", "Criterio",
                         "src/a.py", "Pasarela de pago", "CLA-001"):
            self.assertIn(esperado, pin)

    def test_sin_cambios_no_hay_desviaciones(self):
        tmp = _proyecto()
        try:
            raiz = Path(tmp.name)
            base = tomar_baseline(_tarea(), raiz)
            base["__arbol__"] = foto_arbol(raiz)
            self.assertEqual(verificar_cambios(_tarea(), base, raiz), [])
        finally:
            tmp.cleanup()

    def test_nueva_funcion_publica_es_B_y_privada_no(self):
        tmp = _proyecto()
        try:
            raiz = Path(tmp.name)
            base = tomar_baseline(_tarea(), raiz)
            base["__arbol__"] = foto_arbol(raiz)
            (raiz / "src" / "a.py").write_text(
                "X = 1\n\n\ndef nueva_publica():\n    return 1\n\n\n"
                "def _interna():\n    return 2\n", encoding="utf-8")
            desvs = verificar_cambios(_tarea(), base, raiz)
            self.assertTrue(any(d.clase == "B" and "nueva_publica" in d.detalle
                                for d in desvs))
            self.assertFalse(any("_interna" in d.detalle for d in desvs))
        finally:
            tmp.cleanup()

    def test_cambio_de_cuerpo_sin_firma_es_B(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            raiz = Path(tmp.name)
            (raiz / "src").mkdir()
            (raiz / "src" / "a.py").write_text(
                "def f():\n    return 1\n", encoding="utf-8")
            tarea = _tarea()
            base = tomar_baseline(tarea, raiz)
            base["__arbol__"] = foto_arbol(raiz)
            (raiz / "src" / "a.py").write_text(
                "def f():\n    return 2\n", encoding="utf-8")
            desvs = verificar_cambios(tarea, base, raiz)
            self.assertTrue(any(d.clase == "B" and "cambio de cuerpo interno" in d.detalle
                                for d in desvs))
        finally:
            tmp.cleanup()

    def test_firma_cambiada_es_B(self):
        tmp = _proyecto()
        try:
            raiz = Path(tmp.name)
            (raiz / "src" / "a.py").write_text("def f(x):\n    return x\n",
                                               encoding="utf-8")
            base = tomar_baseline(_tarea(), raiz)
            base["__arbol__"] = foto_arbol(raiz)
            (raiz / "src" / "a.py").write_text("def f(x, y=1):\n    return x\n",
                                               encoding="utf-8")
            desvs = verificar_cambios(_tarea(), base, raiz)
            self.assertTrue(any(d.clase == "B" and "firma cambiada" in d.detalle
                                for d in desvs))
        finally:
            tmp.cleanup()

    def test_archivo_fuera_de_autorizados_es_C(self):
        tmp = _proyecto()
        try:
            raiz = Path(tmp.name)
            base = tomar_baseline(_tarea(), raiz)
            base["__arbol__"] = foto_arbol(raiz)
            (raiz / "src" / "b.py").write_text("EXTRA = True\n", encoding="utf-8")
            desvs = verificar_cambios(_tarea(), base, raiz)
            self.assertTrue(any(d.clase == "C" and "b.py" in d.archivo
                                for d in desvs))
        finally:
            tmp.cleanup()

    def test_archivo_nuevo_fuera_de_autorizados_es_C(self):
        tmp = _proyecto()
        try:
            raiz = Path(tmp.name)
            base = tomar_baseline(_tarea(), raiz)
            base["__arbol__"] = foto_arbol(raiz)
            (raiz / "src" / "nuevo.py").write_text("NUEVO = 1\n", encoding="utf-8")
            desvs = verificar_cambios(_tarea(), base, raiz)
            self.assertTrue(any(d.clase == "C" and "nuevo.py" in d.archivo
                                for d in desvs))
        finally:
            tmp.cleanup()

    def test_simbolo_publico_en_archivo_nuevo_autorizado_es_B(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            raiz = Path(tmp.name)
            (raiz / "src").mkdir()
            tarea = _tarea()
            base = tomar_baseline(tarea, raiz)  # archivo aún no existe
            base["__arbol__"] = foto_arbol(raiz)
            (raiz / "src" / "a.py").write_text(
                "def creada_en_tarea():\n    return 1\n", encoding="utf-8")
            desvs = verificar_cambios(tarea, base, raiz)
            self.assertTrue(any(d.clase == "B" and "creada_en_tarea" in d.detalle
                                for d in desvs))
        finally:
            tmp.cleanup()

    def test_protegido_se_marca(self):
        self.assertTrue(_es_protegido(".specify/dato.json"))
        self.assertFalse(_es_protegido("src/a.py"))
        self.assertIsNone(snapshot_archivo(Path("/no/existe.py")))


if __name__ == "__main__":
    unittest.main()
