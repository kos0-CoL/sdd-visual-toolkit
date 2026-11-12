"""Pruebas de los comandos de barra para agentes (§31)."""

from __future__ import annotations

import argparse
import contextlib
import io
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

    def test_la_descripcion_dice_cuando_usarlo(self):
        """En una skill, la descripción es lo único que el agente ve antes de
        decidir si la aplica: sin el «cuándo», compite a ciegas."""
        for comando in agent_commands.COMANDOS:
            self.assertIn("Úsalo ", comando.descripcion, comando.nombre)
            self.assertLessEqual(len(comando.descripcion), 200,
                                 f"demasiado larga para el menú: {comando.nombre}")


class TestRender(unittest.TestCase):
    def test_cada_cliente_escribe_en_su_ruta(self):
        for cliente, plantilla in agent_commands.CLIENTES.items():
            with self.subTest(cliente=cliente):
                self.assertIn("{nombre}", plantilla)
                archivos = agent_commands.generar(cliente, PYTHON, CLI)
                self.assertEqual(len(archivos), len(agent_commands.COMANDOS))
                for ruta in archivos:
                    self.assertTrue(ruta.startswith(plantilla.split("{")[0]),
                                    ruta)

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
        """Se compara por ruta exacta: «name: sdd» aparece dentro de «sdd-status»
        y una búsqueda por subcadena daba por bueno el comando equivocado."""
        for cliente in set(agent_commands.CLIENTES) - agent_commands.SIN_FRONTMATTER:
            with self.subTest(cliente=cliente):
                archivos = agent_commands.generar(cliente, PYTHON, CLI)
                plantilla = agent_commands.CLIENTES[cliente]
                for comando in agent_commands.COMANDOS:
                    ruta = plantilla.format(nombre=comando.nombre)
                    cabecera = archivos[ruta].split("---\n")[1]
                    self.assertIn(f"name: '{comando.nombre}'", cabecera)
                    self.assertIn(f"description: '{comando.descripcion}'",
                                  cabecera)

    def test_copilot_escribe_solo_la_skill(self):
        """Con el `prompt.md` al lado, el menú `/` de VS Code mostraba cada
        comando dos veces: uno por la skill y otro por el prompt. La skill la
        listan los dos arneses (`Copilot` y `Local`), así que el prompt sobra."""
        archivos = agent_commands.generar("copilot", PYTHON, CLI)
        self.assertEqual(len(archivos), len(agent_commands.COMANDOS))
        self.assertFalse([ruta for ruta in archivos if "/prompts/" in ruta])
        ruta = ".github/skills/sdd-status/SKILL.md"
        self.assertIn(ruta, archivos)
        cabecera = archivos[ruta].split("---\n")[1]
        self.assertIn("name: 'sdd-status'", cabecera)
        self.assertNotIn("agent:", cabecera)
        self.assertIn("--root .", archivos[ruta])

    def test_cline_y_kilo_escriben_sus_workflows(self):
        """Cline toma el nombre del archivo como comando (`/sdd-status.md`) y
        Kilo lee `.kilo/commands/` (`/sdd-status`); ninguno documenta
        frontmatter, así que el archivo empieza por el cuerpo."""
        esperado = {
            "cline": ".clinerules/workflows/sdd-status.md",
            "kilo": ".kilo/commands/sdd-status.md",
        }
        for cliente, ruta in esperado.items():
            with self.subTest(cliente=cliente):
                archivos = agent_commands.generar(cliente, PYTHON, CLI)
                self.assertEqual(len(archivos), len(agent_commands.COMANDOS))
                self.assertIn(ruta, archivos)
                self.assertFalse(archivos[ruta].startswith("---\n"))
                self.assertIn("--root .", archivos[ruta])

    def test_instalados_ve_la_skill_de_copilot(self):
        """`--regenerar` y `status` tienen que llegar a lo que se escribió."""
        with tempfile.TemporaryDirectory() as tmp:
            for relativa, contenido in agent_commands.generar(
                    "copilot", PYTHON, CLI).items():
                destino = Path(tmp) / relativa
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_text(contenido, encoding="utf-8")
            instalados = agent_commands.instalados(tmp)["copilot"]
            self.assertEqual(len(instalados), len(agent_commands.COMANDOS))
            # La ruta horneada es inventada: todas se ven como muertas.
            self.assertEqual(agent_commands.rutas_muertas(tmp),
                             {str(CLI): len(agent_commands.COMANDOS)})

    def test_frontmatter_cita_todos_los_valores(self):
        """Sin comillas, un valor con «: » rompe el YAML del cliente."""
        for cliente in set(agent_commands.CLIENTES) - agent_commands.SIN_FRONTMATTER:
            with self.subTest(cliente=cliente):
                for ruta, contenido in agent_commands.generar(
                        cliente, PYTHON, CLI).items():
                    cabecera = contenido.split("---\n")[1]
                    for linea in cabecera.splitlines():
                        clave, valor = linea.split(": ", 1)
                        self.assertTrue(valor.startswith("'") and
                                        valor.endswith("'"),
                                        f"{ruta}: {linea}")

    def test_descripcion_con_dos_puntos_va_entre_comillas(self):
        """`sdd-status` describe «Estado del proyecto: …»: el caso que rompía."""
        archivos = agent_commands.generar("claude", PYTHON, CLI)
        cabecera = archivos[".claude/skills/sdd-status/SKILL.md"].split("---\n")[1]
        comando = next(c for c in agent_commands.COMANDOS
                       if c.nombre == "sdd-status")
        self.assertIn(": ", comando.descripcion)
        self.assertIn(f"description: '{comando.descripcion}'", cabecera)

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

    def test_la_skill_pide_el_dato_antes_de_ejecutar(self):
        """El modelo corría `plan` sin ID y dejaba que la CLI lo frenara."""
        archivos = agent_commands.generar("claude", PYTHON, CLI)
        skill = archivos[".claude/skills/sdd-plan/SKILL.md"]
        self.assertIn("**Antes de ejecutar**: este comando necesita la SPEC-ID",
                      skill)
        self.assertLess(skill.index("Antes de ejecutar"),
                        skill.index("La salida de la CLI es la fuente"))
        self.assertNotIn("Antes de ejecutar",
                         archivos[".claude/skills/sdd/SKILL.md"])

    def test_los_comandos_que_exigen_un_dato_lo_declaran(self):
        """`cierre` funciona sin identificador (da la foto): no pregunta."""
        con_dato = {"sdd-enrich", "sdd-specify", "sdd-clarify", "sdd-plan",
                    "sdd-plan-gate", "sdd-tasks", "sdd-analyze", "sdd-build",
                    "sdd-pin", "sdd-test", "sdd-traza"}
        for comando in agent_commands.COMANDOS:
            with self.subTest(comando=comando.nombre):
                self.assertEqual(bool(comando.pide), comando.nombre in con_dato)

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
        base = {"root": str(self.root), "cliente": None, "verificar": False}
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

    def _generar_con(self, cli: Path, cliente: str = "claude") -> None:
        for relativa, contenido in agent_commands.generar(
                cliente, PYTHON, cli).items():
            destino = self.root / relativa
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(contenido, encoding="utf-8")

    def test_verificar_avisa_cuando_la_ruta_ya_no_existe(self):
        """Si el toolkit se movió, el agente ejecutaría un archivo muerto."""
        fantasma = Path("/no/existe/toolkit/cli/main.py")
        self._generar_con(fantasma)
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = cmd_comandos.despachar(self._ns(verificar=True))
        self.assertEqual(codigo, 1)
        texto = salida.getvalue()
        self.assertIn(str(fantasma), texto)
        self.assertIn("ya no existe", texto)
        self.assertIn("regenere con", texto)
        self.assertIn(str(cmd_comandos._cli_actual()), texto)

    def test_verificar_esta_al_dia_tras_generar(self):
        cmd_comandos.despachar(self._ns())
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = cmd_comandos.despachar(self._ns(verificar=True))
        self.assertEqual(codigo, 0)
        texto = salida.getvalue()
        self.assertIn("AL DÍA", texto)
        self.assertIn("cliente(s)", texto)

    def test_verificar_sin_comandos_no_falla(self):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = cmd_comandos.despachar(self._ns(verificar=True))
        self.assertEqual(codigo, 0)
        self.assertIn("sin comandos de barra", salida.getvalue())

    def test_apunta_a_la_cli_de_esta_instalacion(self):
        cmd_comandos.despachar(self._ns(cliente=["windsurf"]))
        texto = (self.root / ".windsurf" / "workflows" / "sdd.md"
                 ).read_text(encoding="utf-8")
        esperada = Path(cmd_comandos.__file__).resolve().parents[2] / "cli" / "main.py"
        self.assertIn(str(esperada), texto)
        self.assertTrue(esperada.is_file())


class TestRegenerar(unittest.TestCase):
    """`comandos --regenerar` reescribe solo los clientes ya instalados."""

    def setUp(self):
        from core import agent_commands  # noqa: PLC0415 — solo para estas pruebas
        self.agent_commands = agent_commands
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "proyecto"
        self.pi = (Path(agent_commands.__file__).resolve().parents[1]
                   / "cli" / "main.py")

    def _cli(self, *args):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = cli_main.main(["--root", str(self.root), *args])
        return codigo, salida.getvalue()

    def test_reescribe_solo_lo_instalado(self):
        self.assertEqual(self._cli("init", "--sin-comandos")[0], 0)
        self.assertEqual(self._cli("comandos", "--cliente", "cursor")[0], 0)
        generados = list((self.root / ".cursor" / "commands").glob("*.md"))
        self.assertEqual(len(generados), 14)
        for ruta in generados:
            ruta.write_text(ruta.read_text(encoding="utf-8").replace(
                str(self.pi), "/tmp/toolkit-viejo/cli/main.py"),
                encoding="utf-8")
        self.assertTrue(self.agent_commands.rutas_muertas(self.root))

        codigo, salida = self._cli("comandos", "--regenerar")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("cursor", salida)
        self.assertEqual(self.agent_commands.rutas_muertas(self.root), {})
        for ajena in (".claude", ".github", ".windsurf", ".agents"):
            self.assertFalse((self.root / ajena).exists(), ajena)

    def test_retira_los_prompts_del_formato_anterior(self):
        """Un `.prompt.md` viejo al lado de la skill duplica el menú `/`."""
        self.assertEqual(self._cli("init", "--sin-comandos")[0], 0)
        self.assertEqual(self._cli("comandos", "--cliente", "copilot")[0], 0)
        viejo = self.root / ".github" / "prompts" / "sdd-status.prompt.md"
        viejo.parent.mkdir(parents=True)
        viejo.write_text(
            "<!-- generado por `toolkit comandos`; se sobrescribe -->\n\n"
            f'python3 "{self.pi}" --root . status\n', encoding="utf-8")
        ajeno = viejo.parent / "mio.prompt.md"
        ajeno.write_text("# mi prompt\n", encoding="utf-8")

        codigo, salida = self._cli("comandos", "--regenerar")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("formato anterior", salida)
        self.assertFalse(viejo.exists())
        self.assertTrue(ajeno.exists(), "lo que escribió el usuario se queda")
        self.assertTrue((self.root / ".github" / "skills").is_dir())

    def test_proyecto_viejo_con_solo_prompts(self):
        """Sin skills, `instalados()` no los ve: el retiro tiene que bastar
        para que el cliente cuente como instalado y se regenere la skill."""
        self.assertEqual(self._cli("init", "--sin-comandos")[0], 0)
        carpeta = self.root / ".github" / "prompts"
        carpeta.mkdir(parents=True)
        for comando in self.agent_commands.COMANDOS:
            (carpeta / f"{comando.nombre}.prompt.md").write_text(
                "<!-- generado por `toolkit comandos`; se sobrescribe -->\n\n"
                f'python3 "{self.pi}" --root . status\n', encoding="utf-8")

        codigo, salida = self._cli("comandos", "--regenerar")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("copilot", salida)
        self.assertFalse(list(carpeta.glob("*.md")))
        skills = self.root / ".github" / "skills"
        self.assertEqual(len(list(skills.glob("*/SKILL.md"))),
                         len(self.agent_commands.COMANDOS))

    def test_sin_nada_instalado_avisa(self):
        self.assertEqual(self._cli("init", "--sin-comandos")[0], 0)
        codigo, salida = self._cli("comandos", "--regenerar")
        self.assertEqual(codigo, 1)
        self.assertIn("no hay comandos de barra", salida)


class TestStatusAvisaSkills(unittest.TestCase):
    """El aviso llega solo: nadie va a acordarse de correr `--verificar`."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "proyecto"
        codigo = cli_main.main(
            ["--root", str(self.root), "init", "--sin-comandos"])
        self.assertEqual(codigo, 0)

    def _status(self):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = cli_main.main(["--root", str(self.root), "status"])
        return codigo, salida.getvalue()

    def test_avisa_si_la_ruta_grabada_ya_no_existe(self):
        destino = self.root / ".github" / "skills" / "sdd-status" / "SKILL.md"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            'python3 "/no/existe/toolkit/cli/main.py" --root . status\n',
            encoding="utf-8")
        codigo, salida = self._status()
        self.assertEqual(codigo, 0, salida)
        self.assertIn("COMANDOS DE BARRA DESACTUALIZADOS", salida)
        self.assertIn("/no/existe/toolkit/cli/main.py", salida)
        self.assertIn("toolkit comandos", salida)

    def test_no_avisa_sin_comandos_instalados(self):
        codigo, salida = self._status()
        self.assertEqual(codigo, 0, salida)
        self.assertNotIn("DESACTUALIZADOS", salida)

    def test_no_avisa_si_las_rutas_existen(self):
        cmd_comandos.despachar(argparse.Namespace(
            root=str(self.root), cliente=["copilot"], verificar=False))
        codigo, salida = self._status()
        self.assertEqual(codigo, 0, salida)
        self.assertNotIn("DESACTUALIZADOS", salida)


if __name__ == "__main__":
    unittest.main()
