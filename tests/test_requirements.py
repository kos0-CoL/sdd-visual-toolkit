"""Pruebas de RF-01 — Gestión de requerimientos."""

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent))

from cli import main as cli  # noqa: E402
from core.requirements import RegistroRequerimientos, RequerimientoError  # noqa: E402
from state import store  # noqa: E402


class TestRegistroRequerimientos(unittest.TestCase):
    def test_agregar_asigna_id_secuencial_y_nace_pendiente(self):
        registro = RegistroRequerimientos()
        primero = registro.agregar("Ver inventario", "explicito")
        segundo = registro.agregar("Alertas de stock", "inferido")
        self.assertEqual((primero.id, segundo.id), ("REQ-001", "REQ-002"))
        self.assertEqual(primero.estado, "pendiente")

    def test_texto_vacio_rechazado(self):
        with self.assertRaises(RequerimientoError):
            RegistroRequerimientos().agregar("   ", "explicito")

    def test_procedencia_invalida_rechazada(self):
        with self.assertRaises(RequerimientoError):
            RegistroRequerimientos().agregar("Algo", "inventada")

    def test_excluido_no_puede_aceptarse(self):
        registro = RegistroRequerimientos()
        req = registro.agregar("Franquicias", "excluido")
        with self.assertRaises(RequerimientoError):
            registro.cambiar_estado(req.id, "aceptado")
        # …pero sí puede rechazarse formalmente.
        registro.cambiar_estado(req.id, "rechazado")
        self.assertEqual(registro.obtener(req.id).estado, "rechazado")

    def test_puede_aceptar_inferencia_tras_revision_humana(self):
        registro = RegistroRequerimientos()
        req = registro.agregar("Cierre de caja", "inferido")
        registro.cambiar_estado(req.id, "aceptado")
        self.assertEqual(registro.obtener(req.id).estado, "aceptado")

    def test_obtener_inexistente_falla(self):
        with self.assertRaises(RequerimientoError):
            RegistroRequerimientos().obtener("REQ-999")

    def test_listar_filtra_por_procedencia_y_estado(self):
        registro = RegistroRequerimientos()
        registro.agregar("A", "explicito")
        registro.agregar("B", "sugerido")
        registro.cambiar_estado("REQ-001", "aceptado")
        self.assertEqual(len(registro.listar(procedencia="sugerido")), 1)
        self.assertEqual(len(registro.listar(estado="aceptado")), 1)
        self.assertEqual(len(registro.listar()), 2)


class TestPersistenciaYCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        store.inicializar_proyecto(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_crea_estructura_sin_tocar_lo_existente(self):
        ya = self.root / "specs" / "nota.md"
        ya.parent.mkdir(exist_ok=True)
        ya.write_text("mia", encoding="utf-8")
        store.inicializar_proyecto(self.root)
        self.assertEqual(ya.read_text(encoding="utf-8"), "mia")
        for ruta in (
            ".specify/memory",
            ".specify/checkpoints",
            ".specify/current_task.json",
            ".specify/execution_history.jsonl",
            ".specify/requerimientos.json",
            ".specify/planes",
            ".specify/tareas",
            ".specify/informes",
            "specs",
        ):
            self.assertTrue((self.root / ruta).exists(), ruta)
        # Lo que nadie escribe no se crea: eran carpetas muertas en la raiz.
        self.assertFalse((self.root / "plans").exists())
        self.assertFalse((self.root / "tasks").exists())

    def test_cli_add_list_show_set_de_punta_a_punta(self):
        ns = lambda **kw: argparse_ns(self.root, **kw)  # noqa: E731
        self.assertEqual(cli.cmd_req_add(ns(texto="Ver ventas", procedencia="explicito")), 0)
        self.assertEqual(cli.cmd_req_add(ns(texto="Pasarela de pago", procedencia="excluido")), 0)
        # IDs secuenciales persistidos.
        registro = cli._registro(self.root)
        self.assertEqual([r.id for r in registro.listar()], ["REQ-001", "REQ-002"])
        # Aceptar un excluido falla y no persiste el cambio.
        self.assertEqual(cli.cmd_req_set(ns(req_id="REQ-002", estado="aceptado")), 1)
        self.assertEqual(cli._registro(self.root).obtener("REQ-002").estado, "pendiente")
        self.assertEqual(cli.cmd_req_set(ns(req_id="REQ-001", estado="aceptado")), 0)
        self.assertEqual(cli._registro(self.root).obtener("REQ-001").estado, "aceptado")
        self.assertEqual(cli.cmd_req_show(ns(req_id="REQ-001")), 0)
        self.assertEqual(cli.cmd_req_list(ns(procedencia=None, estado=None)), 0)
        self.assertEqual(cli.cmd_req_show(ns(req_id="REQ-999")), 1)

    def test_fuera_de_proyecto_falla_claro(self):
        otro = tempfile.TemporaryDirectory()
        self.addCleanup(otro.cleanup)
        with self.assertRaises(store.StoreError):
            store.descubrir_raiz(Path(otro.name))


def argparse_ns(root, **kw):
    ns = argparse.Namespace(root=str(root))
    for clave, valor in kw.items():
        setattr(ns, clave, valor)
    return ns


import argparse  # noqa: E402


if __name__ == "__main__":
    unittest.main()
