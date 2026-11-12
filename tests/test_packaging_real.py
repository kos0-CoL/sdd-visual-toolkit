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
import json
import os
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


def _rueda_en(tmp: str) -> tuple[Path, Path] | None:
    """Copia el proyecto a `tmp`, lo empaqueta y devuelve (copia, rueda).

    Sin `--no-build-isolation` no hay red: setuptools ya está instalado. Si pip
    no puede empaquetar, devuelve None para que quien llame decida saltarse la
    prueba en vez de fingir un verde.
    """
    copia = Path(tmp) / "copia"
    shutil.copytree(RAIZ, copia, ignore=IGNORAR)
    ruedas = Path(tmp) / "ruedas"
    ruedas.mkdir()
    empaquetado = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps",
         "--no-build-isolation", "-w", str(ruedas)],
        cwd=copia, capture_output=True, text=True, timeout=300,
    )
    rueda = next(iter(sorted(ruedas.glob("sdd_toolkit-*.whl"))), None)
    if empaquetado.returncode != 0 or rueda is None:
        return None
    return copia, rueda


class TestEmpaquetadoEnDirectorioTemporal(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("pip"), "hace falta pip")
    def test_la_suite_sigue_verde_con_los_artefactos(self):
        with tempfile.TemporaryDirectory() as tmp:
            hecho = _rueda_en(tmp)
            if hecho is None:
                self.skipTest("pip no pudo empaquetar en este entorno")
            copia, rueda = hecho
            self.assertIsNotNone(rueda)
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

    @unittest.skipUnless(importlib.util.find_spec("pip"), "hace falta pip")
    def test_la_rueda_instalada_deja_sdd_init_funcionando(self):
        """La rueda se instala en un venv temporal y, desde ahí, `sdd init`
        deja el proyecto listo: el caso que documenta el README (global)."""
        with tempfile.TemporaryDirectory() as tmp:
            hecho = _rueda_en(tmp)
            if hecho is None:
                self.skipTest("pip no pudo empaquetar en este entorno")
            _copia, rueda = hecho

            venv = Path(tmp) / "venv"
            creado = subprocess.run(
                [sys.executable, "-m", "venv", str(venv)],
                capture_output=True, text=True, timeout=300,
            )
            if creado.returncode != 0:
                self.skipTest("no se pudo crear el entorno virtual:\n"
                              + (creado.stderr or creado.stdout)[-1000:])
            binario = venv / ("Scripts" if os.name == "nt" else "bin")
            pip = binario / ("pip.exe" if os.name == "nt" else "pip")
            if not pip.exists():
                self.skipTest("el entorno virtual no trae pip (ensurepip)")

            instalado = subprocess.run(
                [str(pip), "install", "--no-index", "--no-deps", str(rueda)],
                capture_output=True, text=True, timeout=300,
            )
            self.assertEqual(
                instalado.returncode, 0,
                instalado.stdout[-2000:] + instalado.stderr[-1000:],
            )

            sdd = binario / ("sdd.exe" if os.name == "nt" else "sdd")
            self.assertTrue(sdd.exists(),
                            "la rueda no instaló el comando `sdd`")

            proyecto = Path(tmp) / "kiosco"
            proyecto.mkdir()
            init = subprocess.run(
                [str(sdd), "init", "--cliente", "cline"],
                cwd=proyecto, capture_output=True, text=True, timeout=300,
                input="",
            )
            self.assertEqual(
                init.returncode, 0,
                init.stdout[-2000:] + init.stderr[-1000:],
            )
            self.assertTrue((proyecto / ".specify").is_dir())
            workflows = list((proyecto / ".clinerules" / "workflows").glob("*.md"))
            self.assertEqual(len(workflows), 14,
                             "no se generaron los 14 comandos de Cline")

            # La ruta grabada tiene que ser la de la copia instalada, no la del
            # clon, y existir: es lo que usará la extensión del IDE.
            ajustes = json.loads(
                (proyecto / ".vscode" / "settings.json").read_text(encoding="utf-8"))
            cli = Path(ajustes["sddToolkit.cliPath"])
            self.assertTrue(cli.is_file(), f"la ruta grabada no existe: {cli}")
            self.assertIn(str(venv), str(cli))

            estado = subprocess.run(
                [str(sdd), "status"], cwd=proyecto,
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(estado.returncode, 0,
                             estado.stdout[-1000:] + estado.stderr[-1000:])
            self.assertIn("Tablero", estado.stdout)


if __name__ == "__main__":
    unittest.main()
