"""`init` también acepta `--root` (§31).

`--root` es la opción global de todos los comandos y la extensión de VS Code
la pasa en cada invocación. `init` solo miraba su path posicional, así que
`toolkit --root /tmp/proyecto init` creaba `.specify/` en la carpeta actual.
"""

from __future__ import annotations

import contextlib
import io
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


if __name__ == "__main__":
    unittest.main()
