"""El `.vsix` se revisa antes de darlo por bueno (`scripts/verificar_vsix.py`).

El empaquetado lo arma `vsce` con red, así que aquí se prueba el verificador
contra paquetes sintéticos: no hace falta `npx` ni el editor.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "verificar_vsix.py"

BASE = {
    "[Content_Types].xml": "<Types/>",
    "extension.vsixmanifest": "<PackageManifest/>",
    "extension/extension.js": "// extension\n",
    "extension/package.json": '{"name": "sdd-visual-toolkit"}',
    "extension/readme.md": "# SDD\n",
    "extension/LICENSE.txt": "MIT\n",
}


class TestVerificarVsix(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)

    def _rex(self, entradas):
        ruta = self.base / "paquete.vsix"
        with zipfile.ZipFile(ruta, "w") as paquete:
            for nombre, contenido in entradas.items():
                paquete.writestr(nombre, contenido)
        proceso = subprocess.run([sys.executable, str(SCRIPT), str(ruta)],
                                 capture_output=True, text=True, timeout=60)
        return proceso.returncode, proceso.stdout + proceso.stderr

    def test_paquete_correcto(self):
        codigo, salida = self._rex(BASE)
        self.assertEqual(codigo, 0, salida)
        self.assertIn("verificado", salida)

    def test_falta_la_extension(self):
        entradas = dict(BASE)
        del entradas["extension/extension.js"]
        codigo, salida = self._rex(entradas)
        self.assertEqual(codigo, 1, salida)
        self.assertIn("falta extension/extension.js", salida)

    def test_archivo_vacio(self):
        entradas = dict(BASE)
        entradas["extension/extension.js"] = ""
        codigo, salida = self._rex(entradas)
        self.assertEqual(codigo, 1, salida)
        self.assertIn("extension/extension.js está vacío", salida)

    def test_sobra_algo_que_no_viaja(self):
        entradas = dict(BASE)
        entradas[".vscodeignore"] = "# nada\n"
        codigo, salida = self._rex(entradas)
        self.assertEqual(codigo, 1, salida)
        self.assertIn("sobra .vscodeignore", salida)

    def test_no_es_un_zip(self):
        ruta = self.base / "roto.vsix"
        ruta.write_text("no soy un zip", encoding="utf-8")
        proceso = subprocess.run([sys.executable, str(SCRIPT), str(ruta)],
                                 capture_output=True, text=True, timeout=60)
        self.assertEqual(proceso.returncode, 1)
        self.assertIn("no es un .vsix válido", proceso.stdout)


if __name__ == "__main__":
    unittest.main()
