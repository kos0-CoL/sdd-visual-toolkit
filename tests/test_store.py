"""Pruebas de durabilidad de persistencia — state/store.py (§13.5, §35)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent))

from state import store  # noqa: E402


class TestStoreDurabilidad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_escribir_json_sincroniza_archivo_y_directorio(self):
        destino = self.root / "datos.json"
        llamadas = []
        real = store.os.fsync

        def espia(fd):
            llamadas.append(fd)
            return real(fd)

        with mock.patch.object(store.os, "fsync", espia):
            store.escribir_json(destino, {"a": 1})
        self.assertEqual(json.loads(destino.read_text(encoding="utf-8"))["a"], 1)
        self.assertGreaterEqual(len(llamadas), 2)  # archivo + directorio

    def test_escritura_atomica_no_deja_temporales(self):
        destino = self.root / "sub" / "datos.json"
        store.escribir_json(destino, {"a": 1})
        self.assertEqual(list(destino.parent.glob("*.tmp")), [])

    def test_escritura_texto_atomica(self):
        destino = self.root / "nota.txt"
        store._escritura_atomica(destino, "hola\n", texto=True)
        self.assertEqual(destino.read_text(encoding="utf-8"), "hola\n")

    def test_fsync_dir_no_falla_sin_soporte(self):
        with mock.patch.object(store.os, "open", side_effect=OSError("no")):
            store._fsync_dir(self.root)  # se declara no disponible, no rompe


if __name__ == "__main__":
    unittest.main()
