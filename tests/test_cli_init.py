"""`init` también acepta `--root` (§31).

`--root` es la opción global de todos los comandos y la extensión de VS Code
la pasa en cada invocación. `init` solo miraba su path posicional, así que
`toolkit --root /tmp/proyecto init` creaba `.specify/` en la carpeta actual.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent))

from cli import main as cli_main  # noqa: E402


def _despachar(argv):
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo = cli_main.main(argv)
    return codigo, salida.getvalue()


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
