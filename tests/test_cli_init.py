"""`init` también acepta `--root` (§31).

`--root` es la opción global de todos los comandos y la extensión de VS Code
la pasa en cada invocación. `init` solo miraba su path posicional, así que
`toolkit --root /tmp/proyecto init` creaba `.specify/` en la carpeta actual.
"""

from __future__ import annotations

import contextlib
import io
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent))

from cli import main as cli_main  # noqa: E402


def _despachar(argv):
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo = cli_main.main(argv)
    return codigo, salida.getvalue()


class TestInitNoTocaGitignore(unittest.TestCase):
    """Decisión del README: `init` no crea ni edita `.gitignore`."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.proyecto = Path(tmp.name).resolve() / "proyecto"
        self.proyecto.mkdir()

    def _init(self):
        codigo, salida = _despachar(
            ["--root", str(self.proyecto), "init", "--sin-comandos"])
        self.assertEqual(codigo, 0, salida)

    def test_no_crea_gitignore_si_no_existe(self):
        self._init()
        self.assertTrue((self.proyecto / ".specify").is_dir())
        self.assertFalse((self.proyecto / ".gitignore").exists())

    def test_no_modifica_un_gitignore_existente(self):
        original = "# mío\nnode_modules/\n"
        (self.proyecto / ".gitignore").write_text(original, encoding="utf-8")
        self._init()
        self.assertEqual(
            (self.proyecto / ".gitignore").read_text(encoding="utf-8"),
            original)


class TestInitConRoot(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        # Espejo de lo que hace la extensión: --root y ningún path.
        self.destino = self.base / "proyecto"

    def _desde(self, carpeta: Path) -> None:
        """Ejecuta en `carpeta` para probar que init no usa la carpeta actual."""
        anterior = Path.cwd()
        os.chdir(carpeta)
        self.addCleanup(os.chdir, anterior)

    def test_root_es_el_destino_sin_path_posicional(self):
        self._desde(self.base)
        codigo, salida = _despachar(["--root", str(self.destino), "init"])
        self.assertEqual(codigo, 0, salida)
        self.assertTrue(
            (self.destino / ".specify" / "requerimientos.json").is_file())
        self.assertIn(str(self.destino), salida)

    def test_no_inicializa_la_carpeta_en_que_se_ejecuta(self):
        actual = self.base / "actual"
        actual.mkdir()
        self._desde(actual)
        codigo, salida = _despachar(["--root", str(self.destino), "init"])
        self.assertEqual(codigo, 0, salida)
        self.assertTrue((self.destino / ".specify").is_dir())
        self.assertFalse((actual / ".specify").exists())

    def test_el_path_posicional_sigue_mandando(self):
        otro = self.base / "otro"
        codigo, salida = _despachar(
            ["--root", str(self.destino), "init", str(otro)])
        self.assertEqual(codigo, 0, salida)
        self.assertTrue((otro / ".specify").is_dir())
        self.assertFalse(self.destino.exists())


class TestInitNoAnida(unittest.TestCase):
    """Un segundo `.specify/` dentro del primero deja dos raíces en conflicto."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        codigo, salida = _despachar(["--root", str(self.base), "init"])
        self.assertEqual(codigo, 0, salida)

    def test_no_crea_un_specify_anidado(self):
        dentro = self.base / "sub"
        dentro.mkdir()
        codigo, salida = _despachar(["--root", str(dentro), "init"])
        self.assertEqual(codigo, 1, salida)
        self.assertFalse((dentro / ".specify").exists())
        self.assertIn(str(self.base), salida)

    def test_reinicializar_el_mismo_proyecto_es_inocuo(self):
        nota = self.base / "specs" / "nota.md"
        nota.write_text("mia", encoding="utf-8")
        codigo, salida = _despachar(["init", str(self.base)])
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(nota.read_text(encoding="utf-8"), "mia")


class TestInitEstructuraReal(unittest.TestCase):
    """init crea donde escriben los comandos, no carpetas que nadie usa."""

    def test_las_carpetas_son_las_que_usan_los_comandos(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp).resolve() / "proyecto"
            codigo, salida = _despachar(["--root", str(raiz), "init"])
            self.assertEqual(codigo, 0, salida)
            for ruta in (".specify/planes", ".specify/tareas",
                         ".specify/informes", "specs"):
                self.assertTrue((raiz / ruta).is_dir(), ruta)
            self.assertFalse((raiz / "plans").exists())
            self.assertFalse((raiz / "tasks").exists())
            self.assertIn(".specify/planes", salida)
            self.assertIn("specs/", salida)
            self.assertNotIn("plans/", salida)
            # Estado e historial son del journal, en `memory/`.
            self.assertTrue((raiz / ".specify" / "memory").is_dir())
            self.assertFalse(
                (raiz / ".specify" / "current_task.json").exists())
            self.assertFalse(
                (raiz / ".specify" / "execution_history.jsonl").exists())


class TestInitMencionaLosComandos(unittest.TestCase):
    """Quien termina `init` tiene que saber cómo darle los comandos al agente."""

    def test_la_salida_invita_a_comandos(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp).resolve() / "proyecto"
            codigo, salida = _despachar(["--root", str(raiz), "init"])
            self.assertEqual(codigo, 0, salida)
            self.assertIn("comandos --cliente copilot", salida)
            self.assertIn(str(Path(cli_main.__file__).resolve()), salida)
            # La ruta absoluta se graba: hay que decirlo y ofrecer repetirlo.
            self.assertIn("ruta absoluta queda grabada", salida)
            self.assertIn("[ comandos ]", salida)


class TestInitGeneraLosComandos(unittest.TestCase):
    """`init` puede dejar las skills del agente en el acto."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.raiz = Path(tmp.name).resolve() / "proyecto"

    def _init(self, *extra):
        return _despachar(["--root", str(self.raiz), "init", *extra])

    def test_con_cliente_no_pregunta(self):
        codigo, salida = self._init("--cliente", "cursor")
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(
            len(list((self.raiz / ".cursor" / "commands").glob("*.md"))), 14)
        self.assertNotIn("Cliente del agente (", salida)

    def test_varios_clientes_de_una_vez(self):
        codigo, salida = self._init("--cliente", "copilot", "--cliente", "claude")
        self.assertEqual(codigo, 0, salida)
        self.assertFalse((self.raiz / ".github" / "prompts").exists())
        self.assertEqual(
            len(list((self.raiz / ".github" / "skills").glob("*/SKILL.md"))), 14)
        self.assertEqual(
            len(list((self.raiz / ".claude" / "skills").glob("*/SKILL.md"))), 14)
        self.assertFalse((self.raiz / ".cursor").exists())

    def test_sin_terminal_no_pregunta_ni_genera(self):
        """Desde la extensión o un script no hay a quién preguntar."""
        codigo, salida = self._init()
        self.assertEqual(codigo, 0, salida)
        self.assertFalse((self.raiz / ".github").exists())
        self.assertIn("Comandos para su agente", salida)

    def test_en_terminal_pregunta_y_genera(self):
        class Tty(io.StringIO):
            def isatty(self):
                return True

        anterior = sys.stdin
        sys.stdin = Tty()
        self.addCleanup(setattr, sys, "stdin", anterior)
        with mock.patch("builtins.input", return_value="antigravity"):
            codigo, salida = self._init()
        self.assertEqual(codigo, 0, salida)
        self.assertIn("Cliente del agente (", salida)
        self.assertIn("· cliente: antigravity", salida)
        # Sin renglón vacío antes del eco (`input()` no puede simular el eco
        # del terminal, así que aquí se comprueba el texto y el hueco).
        self.assertIn("· cliente: antigravity", salida)
        self.assertNotIn("\n\n· cliente", salida)
        self.assertEqual(
            len(list((self.raiz / ".agents" / "skills").glob("*/SKILL.md"))),
            14)

    def test_todos_genera_los_cinco_y_lo_dice(self):
        class Tty(io.StringIO):
            def isatty(self):
                return True

        anterior = sys.stdin
        sys.stdin = Tty()
        self.addCleanup(setattr, sys, "stdin", anterior)
        with mock.patch("builtins.input", return_value="todos"):
            codigo, salida = self._init()
        self.assertEqual(codigo, 0, salida)
        self.assertIn("· cliente: todos", salida)
        for carpeta in (".claude", ".cursor", ".github", ".windsurf", ".agents"):
            self.assertTrue((self.raiz / carpeta).is_dir(), carpeta)

    def test_vacio_lo_dice_y_no_genera(self):
        class Tty(io.StringIO):
            def isatty(self):
                return True

        anterior = sys.stdin
        sys.stdin = Tty()
        self.addCleanup(setattr, sys, "stdin", anterior)
        with mock.patch("builtins.input", return_value=""):
            codigo, salida = self._init()
        self.assertEqual(codigo, 0, salida)
        self.assertIn("· cliente: ninguno (sin comandos de barra)", salida)
        self.assertNotIn("\n\n· cliente", salida)
        self.assertFalse((self.raiz / ".claude").exists())

    def test_sin_comandos_no_pregunta_aunque_haya_terminal(self):
        class Tty(io.StringIO):
            def isatty(self):
                return True

        anterior = sys.stdin
        sys.stdin = Tty()
        self.addCleanup(setattr, sys, "stdin", anterior)
        codigo, salida = self._init("--sin-comandos")
        self.assertEqual(codigo, 0, salida)
        self.assertNotIn("Cliente del agente (", salida)
        self.assertFalse((self.raiz / ".claude").exists())


class TestInitDejaElIDEListo(unittest.TestCase):
    """Al abrir la carpeta, la capa visual ya sabe qué ejecutar (§29)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.raiz = Path(tmp.name).resolve() / "proyecto"
        codigo, salida = _despachar(["--root", str(self.raiz), "init"])
        self.assertEqual(codigo, 0, salida)

    def _json(self, nombre):
        ruta = self.raiz / ".vscode" / nombre
        return json.loads(ruta.read_text(encoding="utf-8"))

    def test_la_extension_sabe_que_ejecutar(self):
        ajustes = self._json("settings.json")
        cli = Path(ajustes["sddToolkit.cliPath"])
        self.assertTrue(cli.is_absolute(), ajustes)
        self.assertEqual(cli.name, "main.py")
        self.assertTrue(cli.is_file())
        self.assertTrue(ajustes["sddToolkit.python"])

    def test_las_tareas_apuntan_al_workspace(self):
        tareas = self._json("tasks.json")["tasks"]
        por_etiqueta = {tarea["label"]: tarea for tarea in tareas}
        self.assertIn("SDD: estado", por_etiqueta)
        self.assertEqual(por_etiqueta["SDD: estado"]["args"][-1], "status")
        for tarea in tareas:
            self.assertIn("--root", tarea["args"])
            self.assertIn("${workspaceFolder}", tarea["args"])
            self.assertEqual(tarea["options"]["cwd"], "${workspaceFolder}")

    def test_no_toca_un_settings_que_ya_existe(self):
        destino = self.raiz / ".vscode" / "settings.json"
        mio = '{"editor.tabSize": 2}\n'
        destino.write_text(mio, encoding="utf-8")
        codigo, salida = _despachar(["--root", str(self.raiz), "init"])
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(destino.read_text(encoding="utf-8"), mio)
        self.assertIn("ya existía", salida)


if __name__ == "__main__":
    unittest.main()
