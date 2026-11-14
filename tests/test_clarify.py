"""Pruebas de RF-04 — Clarificación interactiva (§7)."""

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent))

from cli.commands import clarify as cmd_clarify  # noqa: E402
from cli.commands import enrich as cmd_enrich  # noqa: E402
from cli.commands import specify as cmd_specify  # noqa: E402
from core.clarify import (  # noqa: E402
    ClarifyError,
    consolidar,
    detectar,
    es_indefinida,
    pendientes,
    raices,
    responder,
)
from core.spec import Spec  # noqa: E402
from state import store  # noqa: E402

KIOSCO = "Quiero un dashboard para gestionar un kiosco. Debe registrar ventas."


def _spec_con_evidencia() -> tuple[Spec, object]:
    from core.enrich import analizar  # noqa: PLC0415
    from core.requirements import RegistroRequerimientos  # noqa: PLC0415
    from core.spec import generar_desde_enriquecimiento  # noqa: PLC0415

    enr = analizar(KIOSCO, "ENR-001")
    reqs = RegistroRequerimientos()
    enr.validar(reqs)
    return generar_desde_enriquecimiento(enr, reqs.listar(), "SPEC-001"), reqs


class TestDeteccion(unittest.TestCase):
    def test_pregunta_sobre_supuestos_y_placeholders(self):
        spec, reqs = _spec_con_evidencia()
        preguntas = detectar(spec, reqs.listar())
        kinds = {p.kind for p in preguntas}
        self.assertIn("supuesto", kinds)  # stack sin definir
        self.assertIn("confirmar_req", kinds)  # reqs pendientes
        self.assertIn("entidad_datos", kinds)  # entidades sin atributos
        # Nada sobre lo ya definido: FUN-1 aceptado no genera confirmación.
        refs = [p.ref for p in preguntas if p.kind == "confirmar_req"]
        self.assertNotIn("REQ-001", refs)

    def test_detecta_contradiccion_funcional_vs_exclusion(self):
        spec = Spec(spec_id="S", titulo="T")
        spec.funcionales = [("REQ-001", "Registrar ventas en caja", "aceptado")]
        spec.fuera_alcance = ["Registro de ventas"]
        preguntas = detectar(spec, [])
        contra = [p for p in preguntas if p.kind == "contradiccion"]
        self.assertEqual(len(contra), 1)
        self.assertEqual(contra[0].tipo, "opciones")
        etiquetas = [getattr(o, "etiqueta", str(o)) for o in contra[0].opciones]
        self.assertIn("Todavía no lo sé", etiquetas)

    def test_sin_duplicados_y_sin_repetir_contestadas(self):
        spec, reqs = _spec_con_evidencia()
        primeras = consolidar([], detectar(spec, reqs.listar()))
        # Simular respuesta y regenerar: las contestadas no reaparecen.
        primeras[0].estado = "respondida"
        segundas = consolidar(primeras, detectar(spec, reqs.listar(), existentes=primeras))
        ids = [p.id for p in segundas]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(segundas), len(primeras))

    def test_raices_detecta_misma_familia(self):
        self.assertTrue(raices("Registrar ventas") & raices("Registro de ventas"))

    def test_indefinida_reconoce_variantes(self):
        self.assertTrue(es_indefinida("Todavía no lo sé"))
        self.assertFalse(es_indefinida("PostgreSQL"))


class TestResponder(unittest.TestCase):
    def test_supuesto_resuelto_actualiza_spec(self):
        spec, reqs = _spec_con_evidencia()
        p = next(x for x in detectar(spec, reqs.listar()) if x.kind == "supuesto")
        n_antes = len([s for s in spec.supuestos if not s.startswith("✓")])
        cambio = responder(p, "PostgreSQL", spec, reqs)
        self.assertIn("resuelto", cambio)
        self.assertEqual(len([s for s in spec.supuestos if not s.startswith("✓")]), n_antes - 1)

    def test_no_repite_pregunta_contestada(self):
        spec, reqs = _spec_con_evidencia()
        p = next(x for x in detectar(spec, reqs.listar()) if x.kind == "supuesto")
        responder(p, "PostgreSQL", spec, reqs)
        with self.assertRaises(ClarifyError):
            responder(p, "MySQL", spec, reqs)

    def test_confirmar_req_acepta_y_descartar_excluye(self):
        spec, reqs = _spec_con_evidencia()
        preguntas = [x for x in detectar(spec, reqs.listar()) if x.kind == "confirmar_req"]
        responder(preguntas[0], "1", spec, reqs)  # opción 1 = Confirmar
        req = next(r for r in reqs.listar() if r.id == preguntas[0].ref)
        self.assertEqual(req.estado, "aceptado")
        responder(preguntas[1], "Descartar", spec, reqs)
        req2 = next(r for r in reqs.listar() if r.id == preguntas[1].ref)
        self.assertEqual(req2.estado, "rechazado")
        self.assertNotIn(preguntas[1].ref, [f[0] for f in spec.funcionales])


class TestCLIClarify(unittest.TestCase):
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
        ns = argparse.Namespace(root=str(self.root))
        for k, v in base.items():
            setattr(ns, k, v)
        return ns

    def _ns_spec(self, **kw):
        base = dict(texto=None, titulo=None, list=False, show=None,
                     approve=None, revise=None, motivo=None)
        base.update(kw)
        ns = argparse.Namespace(root=str(self.root))
        for k, v in base.items():
            setattr(ns, k, v)
        return ns

    def _ns_cla(self, **kw):
        base = dict(texto=None, answer=None, skip=None, list=None, gate=False)
        base.update(kw)
        ns = argparse.Namespace(root=str(self.root))
        for k, v in base.items():
            setattr(ns, k, v)
        return ns

    def test_gate_bloqueado_hasta_responder_todo(self):
        self.assertEqual(
            cmd_clarify.despachar(self._ns_cla(texto="SPEC-001", gate=True)), 1
        )
        preguntas, _h = cmd_clarify._preguntas_de(self.root, "SPEC-001")
        pares = [[p.id, "PostgreSQL"] for p in preguntas]
        ns = self._ns_cla(texto="SPEC-001")
        ns.answer = pares
        self.assertEqual(cmd_clarify.despachar(ns), 0)
        self.assertEqual(
            cmd_clarify.despachar(self._ns_cla(texto="SPEC-001", gate=True)), 0
        )

    def test_skip_sin_answer_omite_la_pregunta(self):
        """`--skip` a solas es una orden válida: antes reventaba con
        TypeError porque `args.answer` llega en None."""
        self.assertEqual(
            cmd_clarify.despachar(self._ns_cla(list="SPEC-001")), 0
        )
        preguntas, _h = cmd_clarify._preguntas_de(self.root, "SPEC-001")
        pid = preguntas[0].id
        self.assertEqual(
            cmd_clarify.despachar(self._ns_cla(texto="SPEC-001", skip=[pid])), 0
        )
        despues, historial = cmd_clarify._preguntas_de(self.root, "SPEC-001")
        self.assertEqual(
            next(p for p in despues if p.id == pid).estado, "omitida"
        )
        self.assertTrue(any(h["pregunta"] == pid for h in historial))

    def test_list_muestra_pendientes_y_historial_registra_cambios(self):
        self.assertEqual(
            cmd_clarify.despachar(self._ns_cla(list="SPEC-001")), 0
        )
        preguntas, _h = cmd_clarify._preguntas_de(self.root, "SPEC-001")
        pid = next(p.id for p in preguntas if p.kind == "supuesto")
        ns = self._ns_cla(texto="SPEC-001")
        ns.answer = [[pid, "PostgreSQL"]]
        self.assertEqual(cmd_clarify.despachar(ns), 0)
        _p2, historial = cmd_clarify._preguntas_de(self.root, "SPEC-001")
        self.assertTrue(any(h["pregunta"] == pid for h in historial))
        md = (self.root / "specs" / "SPEC-001.md").read_text(encoding="utf-8")
        self.assertIn("Aclarado", md)


if __name__ == "__main__":
    unittest.main()
