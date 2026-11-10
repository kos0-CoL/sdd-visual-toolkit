"""Pruebas de RF-03 — Generación de SPEC (§6)."""

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent))

from cli.commands import enrich as cmd_enrich  # noqa: E402
from cli.commands import specify as cmd_specify  # noqa: E402
from core.spec import Spec, SpecError, generar_desde_enriquecimiento  # noqa: E402
from state import store  # noqa: E402

KIOSCO = "Quiero un dashboard para gestionar un kiosco. Debe registrar ventas."


class TestGenerar(unittest.TestCase):
    def test_spec_con_las_15_secciones_y_sin_invenciones(self):
        from core.enrich import analizar  # noqa: PLC0415
        from core.requirements import RegistroRequerimientos  # noqa: PLC0415

        enr = analizar(KIOSCO, "ENR-001")
        reqs = RegistroRequerimientos()
        enr.validar(reqs)
        spec = generar_desde_enriquecimiento(enr, reqs.listar(), "SPEC-001")
        md = __import__("core.spec", fromlist=["render_markdown"]).render_markdown(spec)
        for n, titulo in enumerate(
            ["Identificación", "Contexto", "Problema", "funcionales",
             "no funcionales", "Entidades", "Reglas", "Comportamientos",
             "Restricciones", "Dependencias", "aceptación", "prueba",
             "alcance", "Suposiciones", "Referencias"],
            1,
        ):
            self.assertIn(f"## {n}.", md)
            self.assertIn(titulo, md)
        # Metadatos §6.3: draft real, sin aprobar, con gates.
        self.assertIn("status: draft", md)
        self.assertIn("approved_at: null", md)
        for gate in ("clarification", "testing", "structural_validation"):
            self.assertIn(gate, md)
        # Trazabilidad: cada funcional cita su REQ.
        for req_id, _t, _e in spec.funcionales:
            self.assertIn(req_id, spec.referencias)
        # Criterios y casos cubren 1:1 los funcionales.
        self.assertEqual(len(spec.criterios), len(spec.funcionales))
        self.assertEqual(len(spec.casos), len(spec.criterios))

    def test_atomicidad_advierte_sin_fragmentar(self):
        spec = Spec(spec_id="S", titulo="T")
        spec.funcionales = [(f"R{i}", "x", "aceptado") for i in range(20)]
        self.assertTrue(spec.recomienda_dividir())
        self.assertEqual(len(spec.funcionales), 20)  # nada se fragmentó solo
        spec2 = Spec(spec_id="S", titulo="T")
        spec2.funcionales = [("R1", "x", "aceptado")]
        self.assertFalse(spec2.recomienda_dividir())

    def test_aprobar_es_explicita_y_no_repetible_en_silencio(self):
        spec = Spec(spec_id="S", titulo="T")
        self.assertIsNone(spec.approved_at)
        spec.aprobar()
        self.assertEqual(spec.status, "approved")
        self.assertIsNotNone(spec.approved_at)
        with self.assertRaises(SpecError):
            spec.aprobar()


class TestCLISpecify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        store.inicializar_proyecto(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def ns_enrich(self, **kw):
        base = dict(texto=None, list=False, show=None, drop=None, accept=None)
        base.update(kw)
        ns = argparse.Namespace(root=str(self.root))
        for k, v in base.items():
            setattr(ns, k, v)
        return ns

    def ns_spec(self, **kw):
        base = dict(texto=None, titulo=None, list=False, show=None,
                     approve=None, revise=None, motivo=None)
        base.update(kw)
        ns = argparse.Namespace(root=str(self.root))
        for k, v in base.items():
            setattr(ns, k, v)
        return ns

    def _flujo_hasta_spec(self):
        cmd_enrich.despachar(self.ns_enrich(texto=KIOSCO))
        cmd_enrich.despachar(self.ns_enrich(accept="ENR-001"))
        self.assertEqual(cmd_specify.despachar(self.ns_spec(texto="ENR-001")), 0)

    def test_generar_vincula_reqs_y_persiste_md_y_json(self):
        self._flujo_hasta_spec()
        self.assertTrue((self.root / "specs" / "SPEC-001.md").exists())
        self.assertTrue((self.root / "specs" / "SPEC-001.json").exists())
        reqs = cmd_enrich._registro_req(self.root)
        vinculados = [r for r in reqs.listar() if r.origen == "ENR-001"]
        self.assertTrue(vinculados)
        self.assertTrue(all(r.spec_id == "SPEC-001" for r in vinculados))
        self.assertEqual(cmd_specify.despachar(self.ns_spec(show="SPEC-001")), 0)

    def test_exige_enriquecimiento_validado(self):
        cmd_enrich.despachar(self.ns_enrich(texto=KIOSCO))
        self.assertEqual(cmd_specify.despachar(self.ns_spec(texto="ENR-001")), 1)
        self.assertFalse((self.root / "specs" / "SPEC-001.md").exists())

    def test_approve_es_humana_y_registra_fecha(self):
        self._flujo_hasta_spec()
        self.assertEqual(cmd_specify.despachar(self.ns_spec(approve="SPEC-001")), 0)
        spec = cmd_specify._cargar_spec(self.root, "SPEC-001")
        self.assertEqual(spec.status, "approved")
        self.assertIsNotNone(spec.approved_at)
        self.assertEqual(cmd_specify.despachar(self.ns_spec(approve="SPEC-001")), 1)

    def test_revise_versiona_y_conserva_historial(self):
        self._flujo_hasta_spec()
        # Nuevo requerimiento aceptado después de generar la SPEC.
        reqs = cmd_enrich._registro_req(self.root)
        nuevo = reqs.agregar("Emitir ticket de venta", "explicito")
        nuevo.origen = "ENR-001"
        reqs.cambiar_estado(nuevo.id, "aceptado")
        from state import store as _store  # noqa: PLC0415
        _store.escribir_json(_store.ruta_requerimientos(self.root), reqs.to_list())
        self.assertEqual(
            cmd_specify.despachar(
                self.ns_spec(revise="SPEC-001", motivo="Se aceptó ticket de venta")
            ),
            0,
        )
        spec = cmd_specify._cargar_spec(self.root, "SPEC-001")
        self.assertEqual(spec.version, "1.0.1")
        self.assertTrue(
            (self.root / ".specify" / "spec_history" / "SPEC-001_v1.0.0.md").exists()
        )
        self.assertTrue(any("ticket" in t.lower() for _r, t, _e in spec.funcionales))

    def test_revise_sin_motivo_falla(self):
        self._flujo_hasta_spec()
        self.assertEqual(cmd_specify.despachar(self.ns_spec(revise="SPEC-001")), 1)


if __name__ == "__main__":
    unittest.main()
