"""Empaquetado real: la suite sigue verde con `build/` y `*.egg-info/`.

`test_packaging.py` comprueba la configuración; esta prueba la ejerce: copia el
proyecto a un directorio temporal, lo empaqueta con `pip wheel` —que deja
`build/` y `sdd_toolkit.egg-info/` en el árbol— y vuelve a correr las pruebas
de empaquetado y de documentación dentro de esa copia. Ese era el escenario que
fallaba: instalar como el README indica rompía la búsqueda de paquetes reales.

Se marca `lento` porque invoca pip y tarda segundos; el ciclo rápido con
`-m "not lento"` la deja fuera.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

pytestmark = pytest.mark.lento

RAIZ = Path(__file__).resolve().parent.parent
# Lo que no viaja a la copia: historial, cachés y artefactos de otras corridas.
IGNORAR = shutil.ignore_patterns(
    ".git", ".venv", "__pycache__", "*.pyc", ".pytest_cache",
    "build", "dist", "*.egg-info",
)


class TestEmpaquetadoEnDirectorioTemporal(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("pip"), "hace falta pip")
    def test_la_suite_sigue_verde_con_los_artefactos(self):
        with tempfile.TemporaryDirectory() as tmp:
            copia = Path(tmp) / "copia"
            shutil.copytree(RAIZ, copia, ignore=IGNORAR)
            ruedas = Path(tmp) / "ruedas"
            ruedas.mkdir()

            # Sin aislamiento de build no hay red: setuptools ya está instalado.
            empaquetado = subprocess.run(
                [sys.executable, "-m", "pip", "wheel", ".", "--no-deps",
                 "--no-build-isolation", "-w", str(ruedas)],
                cwd=copia, capture_output=True, text=True, timeout=300,
            )
            if empaquetado.returncode != 0:
                self.skipTest(
                    "pip no pudo empaquetar en este entorno:\n"
                    + (empaquetado.stderr or empaquetado.stdout)[-1500:])

            self.assertTrue(list(ruedas.glob("sdd_toolkit-*.whl")),
                            "pip wheel terminó bien pero no dejó la rueda")
            # Los artefactos que antes hacían fallar la prueba de paquetes.
            self.assertTrue((copia / "build").is_dir(),
                            "pip no dejó build/: la prueba no estaría probando nada")
            self.assertTrue(list(copia.glob("*.egg-info")),
                            "pip no dejó *.egg-info/: la prueba no estaría probando nada")

            suite = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/test_packaging.py",
                 "tests/test_readme.py", "-q"],
                cwd=copia, capture_output=True, text=True, timeout=300,
            )
            self.assertEqual(
                suite.returncode, 0,
                "la suite falla con los artefactos de empaquetado:\n"
                + suite.stdout[-3000:] + suite.stderr[-1000:],
            )


if __name__ == "__main__":
    unittest.main()
