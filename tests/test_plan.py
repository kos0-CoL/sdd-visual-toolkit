"""Pruebas de RF-05 — Plan de implementación (§8)."""

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
from core.plan import (  # noqa: E402
    PlanError,
    archivos_afectados,
    decidir_sugerencia,
    derivar_orden,
    investigar,
    listar_sugerencias,
    registrar_sugerencia,
)
from state import store  # noqa: E402

KIOSCO = "Quiero un dashboard para gestionar un kiosco. Debe registrar ventas."


class TestInvestigar(unittest.TestCase):
    def test_detecta_lenguajes_dependencias_y_pruebas_reales(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "app").mkdir()
            (raiz / "app" / "caja.py").write_text("import sqlite3\n", encoding="utf-8")
            (raiz / "tests").mkdir()
            (raiz / "tests" / "test_caja.py").write_text("import unittest\n", encoding="utf-8")
            (raiz / "requirements.txt").write_text("requests==2.31\n", encoding="utf-8")
            (raiz / "README.md").write_text("# x\n", encoding="utf-8")
            hall = investigar(raiz)
            self.assertFalse(hall["es_greenfield"])
            self.assertEqual(hall["lenguajes"], {"Python": 2})
            self.assertTrue(any("requests" in d for d in hall["dependencias"]))
            self.assertEqual(len(hall["pruebas"]), 1)
            self.assertIn("README presente", hall["convenciones"])

    def test_proyecto_vacio_es_greenfield_honesto(self):
        with tempfile.TemporaryDirectory() as tmp:
            hall = investigar(Path(tmp))
            self.assertTrue(hall["es_greenfield"])
            self.assertEqual(hall["codigo"], [])
            self.assertEqual(hall["dependencias"], [])


class TestCLIPlan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        store.inicializar_proyecto(self.root)
        cmd_enrich.despachar(self._ns_enrich(texto=KIOSCO))
        cmd_enrich.despachar(self._ns_enrich(accept="ENR-001"))
        cmd_specify.despachar(self._ns_spec(texto="ENR-001"))

    def tearDown(self):
        self.tmp.cleanup()

    def _ns_enrich(self, **kw):
        base = dict(texto=None, list=False, show=None, drop=None, accept=None)
        base.update(kw)
        return self._ns(base)

    def _ns_spec(self, **kw):
        base = dict(texto=None, titulo=None, list=False, show=None,
                     approve=None, revise=None, motivo=None)
        base.update(kw)
        return self._ns(base)

    def _ns_plan(self, **kw):
        base = dict(texto=None, force=False, list=False, show=None, gate=None)
        base.update(kw)
        return self._ns(base)

    def _ns_cla(self, **kw):
        base = dict(texto=None, answer=None, skip=None, list=None, gate=False)
        base.update(kw)
        return self._ns(base)

    def _ns(self, base):
        ns = argparse.Namespace(root=str(self.root))
        for k, v in base.items():
            setattr(ns, k, v)
        return ns

    def _superar_gate1(self):
        # El gate dispara la detección; recién ahí existen las preguntas.
        self.assertEqual(
            cmd_clarify.despachar(self._ns_cla(texto="SPEC-001", gate=True)), 1)
        preguntas, _h = cmd_clarify._preguntas_de(self.root, "SPEC-001")
        self.assertTrue(preguntas)
        ns = self._ns_cla(texto="SPEC-001")
        ns.answer = [[p.id, "Definido en clarify"] for p in preguntas]
        self.assertEqual(cmd_clarify.despachar(ns), 0)

    def test_exige_gate1_superado(self):
        self.assertEqual(cmd_plan.despachar(self._ns_plan(texto="SPEC-001")), 1)
        # La carpeta la deja `init`; lo que no puede quedar es un plan dentro.
        self.assertEqual(list((self.root / ".specify" / "planes").iterdir()), [])

    def test_genera_plan_con_trazabilidad_total(self):
        self._superar_gate1()
        self.assertEqual(cmd_plan.despachar(self._ns_plan(texto="SPEC-001")), 0)
        plan = cmd_plan._cargar_plan(self.root, "PLAN-001")
        spec = cmd_specify._cargar_spec(self.root, "SPEC-001")
        self.assertEqual(plan.cobertura_funcional(spec), [])
        self.assertTrue(all(p.refs for p in plan.orden))
        self.assertTrue(all("NO aprobada" in a or "no aprobada" in a.lower()
                            for a in plan.alternativas))
        self.assertEqual(cmd_plan.despachar(self._ns_plan(gate="PLAN-001")), 0)
        self.assertEqual(
            cmd_plan._cargar_plan(self.root, "PLAN-001").status, "validado")

    def test_sin_force_no_sobrescribe(self):
        self._superar_gate1()
        self.assertEqual(cmd_plan.despachar(self._ns_plan(texto="SPEC-001")), 0)
        self.assertEqual(cmd_plan.despachar(self._ns_plan(texto="SPEC-001")), 1)
        self.assertEqual(
            cmd_plan.despachar(self._ns_plan(texto="SPEC-001", force=True)), 0)

    def test_orden_deriva_entidades_antes_que_comportamiento(self):
        from core.plan import derivar_orden  # noqa: PLC0415
        from core.spec import Spec  # noqa: PLC0415
        spec = Spec(spec_id="S", titulo="T",
                    entidades=["Productos"],
                    funcionales=[("REQ-001", "Registrar ventas", "aceptado"),
                                 ("REQ-002", "Reporte mensual", "pendiente")])
        titulos = [p.titulo for p in derivar_orden(spec)]
        idx_ent = next(i for i, t in enumerate(titulos) if "entidades" in t.lower())
        idx_fun = next(i for i, t in enumerate(titulos) if t.startswith("Implementar REQ"))
        self.assertLess(idx_ent, idx_fun)
        # Los pendientes van a un paso propio, no se implementan en silencio.
        paso_pend = next(t for t in titulos if "pendientes" in t.lower())
        self.assertIn("REQ-002", [r for p in derivar_orden(spec)
                                   if p.titulo == paso_pend for r in p.refs])


class TestSugerencias(unittest.TestCase):
    """RF-07/§40: una mejora no entra al alcance actual por su cuenta."""

    def test_registra_fuera_del_plan_y_de_las_tareas(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            store.inicializar_proyecto(raiz)
            sug = registrar_sugerencia(raiz, "PLAN-001", "  Usar caché  ",
                                       origen="agente-x", tarea="TASK-001")
            self.assertEqual(sug.id, "SUG-001")
            self.assertEqual(sug.estado, "sugerida")
            self.assertEqual(sug.texto, "Usar caché")
            self.assertEqual(listar_sugerencias(raiz, "PLAN-001"), [sug])
            # No se crea plan ni tareas: la sugerencia vive aparte.
            self.assertEqual(list((raiz / ".specify" / "planes").iterdir()), [])
            self.assertFalse((raiz / ".specify" / "tareas.json").exists())
            segunda = registrar_sugerencia(raiz, "PLAN-001", "Otra")
            self.assertEqual(segunda.id, "SUG-002")

    def test_sugerencia_vacia_se_rechaza(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            store.inicializar_proyecto(raiz)
            with self.assertRaises(PlanError):
                registrar_sugerencia(raiz, "PLAN-001", "   ")

    def test_decision_humana_explicita(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            store.inicializar_proyecto(raiz)
            sug = registrar_sugerencia(raiz, "PLAN-001", "Mejora")
            with self.assertRaises(PlanError):
                decidir_sugerencia(raiz, "PLAN-001", sug.id, "auto")
            self.assertEqual(sug.estado, "sugerida")
            aprobada = decidir_sugerencia(raiz, "PLAN-001", sug.id, "aprobada")
            self.assertEqual(aprobada.estado, "aprobada")
            self.assertEqual(listar_sugerencias(raiz, "PLAN-001")[0].estado,
                             "aprobada")
            with self.assertRaises(PlanError):
                decidir_sugerencia(raiz, "PLAN-001", "SUG-999", "descartada")


class TestCacheAnalisis(unittest.TestCase):
    """§8.2/§4: análisis incremental sin repetir trabajo innecesario."""

    def test_cache_reutiliza_sin_cambios_e_invalida_al_cambiar(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            store.inicializar_proyecto(raiz)
            (raiz / "app").mkdir()
            fuente = raiz / "app" / "caja.py"
            fuente.write_text("X = 1\n", encoding="utf-8")
            primero = investigar(raiz)
            self.assertFalse(primero["es_greenfield"])
            cache = raiz / ".specify" / "cache" / "analisis.json"
            self.assertTrue(cache.exists())
            self.assertEqual(investigar(raiz), primero)  # se reutiliza
            fuente.write_text("X = 1\nY = 2\n", encoding="utf-8")
            afectados = archivos_afectados(raiz)
            self.assertTrue(afectados["hay_cache"])
            self.assertIn("app/caja.py", afectados["cambiados"])
            investigar(raiz)  # recalcula y refresca la caché
            self.assertEqual(archivos_afectados(raiz)["cambiados"], [])

    def test_sin_specify_no_escribe_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "a.py").write_text("X = 1\n", encoding="utf-8")
            hall = investigar(raiz)
            self.assertFalse(hall["es_greenfield"])
            self.assertFalse((raiz / ".specify").exists())
            self.assertFalse(archivos_afectados(raiz)["hay_cache"])

    def test_usar_cache_false_recalcula(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            store.inicializar_proyecto(raiz)
            (raiz / "a.py").write_text("X = 1\n", encoding="utf-8")
            investigar(raiz)
            self.assertEqual(investigar(raiz, usar_cache=False), investigar(raiz))


if __name__ == "__main__":
    unittest.main()
