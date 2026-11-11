"""Pruebas de los comandos de barra para agentes (§31)."""

from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent))

from cli import main as cli_main  # noqa: E402
from cli.commands import comandos as cmd_comandos  # noqa: E402
from core import agent_commands  # noqa: E402

CLI = Path("/ruta/al/toolkit/cli/main.py")
PYTHON = "/usr/bin/python3"


def _subcomandos() -> set:
    for accion in cli_main.construir_parser()._actions:
        if isinstance(accion, argparse._SubParsersAction):
            return set(accion.choices)
    return set()


class TestCatalogo(unittest.TestCase):
    def test_nombres_unicos_y_con_prefijo(self):
        nombres = [c.nombre for c in agent_commands.COMANDOS]
        self.assertEqual(len(nombres), len(set(nombres)))
        for nombre in nombres:
            self.assertTrue(nombre == "sdd" or nombre.startswith("sdd-"),
                            f"nombre sin prefijo: {nombre}")

    def test_cada_comando_invoca_un_subcomando_real(self):
        """Un catálogo que nombra un subcomando inexistente sería un typo."""
        disponibles = _subcomandos()
        for comando in agent_commands.COMANDOS:
            primero = comando.argv.split()[0]
            self.assertIn(primero, disponibles,
                          f"{comando.nombre} invoca «{primero}», que no existe")

    def test_todos_declaran_descripcion(self):
        for comando in agent_commands.COMANDOS:
            self.assertTrue(comando.descripcion.strip(), comando.nombre)
            self.assertNotIn("\n", comando.descripcion)


class TestRender(unittest.TestCase):
    def test_cada_cliente_escribe_en_su_ruta(self):
        for cliente, plantilla in agent_commands.CLIENTES.items():
            with self.subTest(cliente=cliente):
                self.assertIn("{nombre}", plantilla)
                archivos = agent_commands.generar(cliente, PYTHON, CLI)
                self.assertEqual(len(archivos), len(agent_commands.COMANDOS))
                for ruta in archivos:
                    self.assertTrue(ruta.startswith(plantilla.split("{")[0]))

    def test_frontmatter_solo_donde_corresponde(self):
        for cliente in agent_commands.CLIENTES:
            with self.subTest(cliente=cliente):
                archivos = agent_commands.generar(cliente, PYTHON, CLI)
                for nombre, contenido in archivos.items():
                    empieza = contenido.startswith("---\n")
                    if cliente in agent_commands.SIN_FRONTMATTER:
                        self.assertFalse(empieza, nombre)
                    else:
                        self.assertTrue(empieza, nombre)

    def test_frontmatter_declara_nombre_y_descripcion(self):
        for cliente in set(agent_commands.CLIENTES) - agent_commands.SIN_FRONTMATTER:
            with self.subTest(cliente=cliente):
                archivos = agent_commands.generar(cliente, PYTHON, CLI)
                for ruta, contenido in archivos.items():
                    cabecera = contenido.split("---\n")[1]
                    comando = next(c for c in agent_commands.COMANDOS
                                   if f"/{c.nombre}/" in f"/{ruta}/"
                                   or c.nombre in ruta)
                    self.assertIn(f"name: {comando.nombre}", cabecera)
                    self.assertIn("description: ", cabecera)

    def test_copilot_pide_el_agente_con_terminal(self):
        archivos = agent_commands.generar("copilot", PYTHON, CLI)
        for contenido in archivos.values():
            self.assertIn("agent: agent", contenido.split("---\n")[1])

    def test_cuerpo_invoca_la_cli_con_ruta_absoluta(self):
        for cliente in agent_commands.CLIENTES:
            with self.subTest(cliente=cliente):
                archivos = agent_commands.generar(cliente, PYTHON, CLI)
                for contenido in archivos.values():
                    self.assertIn(f'"{CLI}"', contenido)
                    self.assertIn("--root .", contenido)

    def test_argumentos_solo_donde_el_cliente_los_pasa(self):
        for cliente in agent_commands.CLIENTES:
            with self.subTest(cliente=cliente):
                archivos = agent_commands.generar(cliente, PYTHON, CLI)
                for contenido in archivos.values():
                    if cliente in agent_commands.CON_ARGUMENTOS:
                        self.assertIn("$ARGUMENTS", contenido)
                    else:
                        self.assertNotIn("$ARGUMENTS", contenido)
                        self.assertIn("pásalo tal cual", contenido)

    def test_reglas_comunes_en_todos_los_archivos(self):
        for cliente in agent_commands.CLIENTES:
            archivos = agent_commands.generar(cliente, PYTHON, CLI)
            for contenido in archivos.values():
                self.assertIn("fuente de la verdad", contenido)
                self.assertIn("no lo inventes", contenido)

    def test_generar_es_determinista(self):
        uno = agent_commands.generar("claude", PYTHON, CLI)
        otro = agent_commands.generar("claude", PYTHON, CLI)
        self.assertEqual(uno, otro)

    def test_cliente_desconocido_falla(self):
        with self.assertRaises(ValueError):
            agent_commands.generar("emacs", PYTHON, CLI)


class TestCLIComandos(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _ns(self, **kw):
        base = {"root": str(self.root), "cliente": None}
        base.update(kw)
        return argparse.Namespace(**base)

    def test_escribe_todos_los_clientes(self):
        self.assertEqual(cmd_comandos.despachar(self._ns()), 0)
        for plantilla in agent_commands.CLIENTES.values():
            carpeta = plantilla.split("{")[0].rstrip("/")
            self.assertTrue((self.root / carpeta).is_dir(), carpeta)

    def test_un_solo_cliente_no_escribe_los_demas(self):
        self.assertEqual(
            cmd_comandos.despachar(self._ns(cliente=["cursor"])), 0)
        self.assertTrue((self.root / ".cursor" / "commands").is_dir())
        self.assertFalse((self.root / ".claude").exists())

    def test_repetir_la_instalacion_deja_lo_mismo(self):
        cmd_comandos.despachar(self._ns())
        antes = (self.root / ".claude" / "skills" / "sdd" / "SKILL.md"
                 ).read_text(encoding="utf-8")
        cmd_comandos.despachar(self._ns())
        despues = (self.root / ".claude" / "skills" / "sdd" / "SKILL.md"
                   ).read_text(encoding="utf-8")
        self.assertEqual(antes, despues)

    def test_apunta_a_la_cli_de_esta_instalacion(self):
        cmd_comandos.despachar(self._ns(cliente=["windsurf"]))
        texto = (self.root / ".windsurf" / "workflows" / "sdd.md"
                 ).read_text(encoding="utf-8")
        esperada = Path(cmd_comandos.__file__).resolve().parents[2] / "cli" / "main.py"
        self.assertIn(str(esperada), texto)
        self.assertTrue(esperada.is_file())


if __name__ == "__main__":
    unittest.main()
