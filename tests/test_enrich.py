"""Pruebas de RF-02 — Enriquecimiento inicial (§5)."""

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent))

from cli.commands import enrich as cmd_enrich  # noqa: E402
from core.enrich import (  # noqa: E402
    EnriquecimientoError,
    RegistroEnriquecimientos,
    analizar,
)
from core.requirements import RegistroRequerimientos  # noqa: E402
from state import store  # noqa: E402

KIOSCO = "Quiero un dashboard para gestionar un kiosco."


class TestAnalizar(unittest.TestCase):
    def test_ejemplo_de_la_spec(self):
        enr = analizar(KIOSCO, "ENR-001")
        self.assertIn("kiosco", enr.objetivo.lower())
        self.assertEqual(enr.dominio, "comercio")
        textos = [i.texto for i in enr.items]
        self.assertIn("Productos", textos)  # entidad inferida
        self.assertIn("Registro de ventas", textos)  # funcionalidad inferida
        self.assertIn("Alertas de stock mínimo", textos)  # mejora sugerida
        self.assertIn("Gestión de franquicias", textos)  # fuera de alcance
        # Stack desconocido → pendiente de aclaración, no inventado (§5.6).
        faltantes = [i.texto for i in enr.por_seccion("faltante")]
        self.assertTrue(any("stack" in f.lower() for f in faltantes))

    def test_preserva_cita_textual_y_procedencias(self):
        enr = analizar(KIOSCO, "ENR-001")
        self.assertEqual(enr.entrada, KIOSCO)
        procs = {i.procedencia for i in enr.items}
        self.assertTrue({"explicito", "inferido", "sugerido", "desconocido", "excluido"} <= procs)
        for item in enr.por_seccion("funcionalidad"):
            if item.procedencia == "explicito":
                self.assertIn(item.cita, KIOSCO)

    def test_pregunta_del_usuario_es_desconocido(self):
        enr = analizar("Quiero un dashboard. ¿Cuántos usuarios lo usarán?", "ENR-001")
        faltantes = enr.por_seccion("faltante")
        self.assertTrue(any("?" in i.cita for i in faltantes))

    def test_negacion_del_usuario_es_exclusion(self):
        enr = analizar("Quiero un dashboard. No quiero pasarela de pago.", "ENR-001")
        exc = [i.texto for i in enr.por_seccion("exclusion")]
        self.assertTrue(any("pasarela" in e.lower() for e in exc))

    def test_stack_declarado_no_pide_aclaracion(self):
        enr = analizar("Quiero un dashboard en Python con SQLite.", "ENR-001")
        faltantes = [i.texto for i in enr.por_seccion("faltante")]
        self.assertFalse(any("stack" in f.lower() for f in faltantes))
        rest = [i.texto for i in enr.por_seccion("restriccion")]
        self.assertTrue(any("python" in r.lower() for r in rest))

    def test_idea_vacia_rechazada(self):
        with self.assertRaises(EnriquecimientoError):
            analizar("   ")


class TestValidacion(unittest.TestCase):
    def test_accept_registra_reqs_con_estados_correctos(self):
        enr = analizar(KIOSCO + " Debe registrar ventas.", "ENR-001")
        reqs = RegistroRequerimientos()
        creados = enr.validar(reqs)
        self.assertEqual(enr.estado, "validado")
        por_proc = {}
        for req in creados:
            por_proc.setdefault(req.procedencia, []).append(req.estado)
            self.assertEqual(req.origen, "ENR-001")  # trazabilidad §39
        self.assertTrue(all(e == "aceptado" for e in por_proc["explicito"]))
        for proc in ("inferido", "sugerido", "desconocido", "excluido"):
            self.assertTrue(all(e == "pendiente" for e in por_proc[proc]))

    def test_validar_dos_veces_falla(self):
        enr = analizar(KIOSCO, "ENR-001")
        enr.validar(RegistroRequerimientos())
        with self.assertRaises(EnriquecimientoError):
            enr.validar(RegistroRequerimientos())

    def test_drop_poda_antes_de_validar(self):
        enr = analizar(KIOSCO, "ENR-001")
        mejora = enr.por_seccion("mejora")[0]
        quitados = enr.quitar([mejora.item_id])
        self.assertEqual(len(quitados), 1)
        reqs = RegistroRequerimientos()
        enr.validar(reqs)
        self.assertFalse(any(mejora.texto in r.texto for r in reqs.listar()))

    def test_drop_con_id_inexistente_falla(self):
        enr = analizar(KIOSCO, "ENR-001")
        with self.assertRaises(EnriquecimientoError):
            enr.quitar(["MEJ-999"])


class TestCLIEnrich(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        store.inicializar_proyecto(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def ns(self, **kw):
        base = dict(texto=None, list=False, show=None, drop=None, accept=None)
        base.update(kw)
        ns = argparse.Namespace(root=str(self.root))
        for clave, valor in base.items():
            setattr(ns, clave, valor)
        return ns

    def test_flujo_completo_por_cli(self):
        self.assertEqual(cmd_enrich.despachar(self.ns(texto=KIOSCO)), 0)
        registro = cmd_enrich._registro(self.root)
        self.assertEqual([e.id for e in registro.listar()], ["ENR-001"])
        # Podar una mejora y validar.
        mejora = registro.obtener("ENR-001").por_seccion("mejora")[0]
        self.assertEqual(
            cmd_enrich.despachar(self.ns(drop=["ENR-001", mejora.item_id])), 0
        )
        self.assertEqual(cmd_enrich.despachar(self.ns(accept="ENR-001")), 0)
        reqs = cmd_enrich._registro_req(self.root)
        self.assertGreater(len(reqs.listar()), 0)
        self.assertTrue(all(r.origen == "ENR-001" for r in reqs.listar()))
        # Validar dos veces falla sin duplicar.
        antes = len(reqs.listar())
        self.assertEqual(cmd_enrich.despachar(self.ns(accept="ENR-001")), 1)
        self.assertEqual(len(cmd_enrich._registro_req(self.root).listar()), antes)

    def test_show_y_list(self):
        cmd_enrich.despachar(self.ns(texto=KIOSCO))
        self.assertEqual(cmd_enrich.despachar(self.ns(list=True)), 0)
        self.assertEqual(cmd_enrich.despachar(self.ns(show="ENR-001")), 0)
        self.assertEqual(cmd_enrich.despachar(self.ns(show="ENR-999")), 1)

    def test_sin_texto_falla_claro(self):
        self.assertEqual(cmd_enrich.despachar(self.ns()), 1)


if __name__ == "__main__":
    unittest.main()
