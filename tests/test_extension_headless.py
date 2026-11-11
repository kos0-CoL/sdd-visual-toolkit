"""Arnés de la extensión sin editor (`tests/js/arnes_extension.js`).

`tests/test_ide.py` mira la estructura del manifiesto y del código; esto
ejecuta `extension.js` con un stub de `vscode` contra un proyecto real y la CLI
real, para comprobar qué nodos arma la vista, qué comando lleva cada uno y qué
corre y avisa la paleta. No sustituye la pasada manual: no hay editor.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARNES = RAIZ / "tests" / "js" / "arnes_extension.js"
CLI = RAIZ / "cli" / "main.py"
FIXTURE = RAIZ / "tests" / "fixtures" / "estado-0.1.0"
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "hace falta node para el arnés de la extensión")
class TestArnesDeLaExtension(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.proyecto = self.base / "proyecto"
        shutil.copytree(FIXTURE, self.proyecto)

    def _cli(self, *argumentos):
        proceso = subprocess.run(
            [sys.executable, str(CLI), "--root", str(self.proyecto), *argumentos],
            capture_output=True, text=True, cwd=RAIZ, timeout=180)
        self.assertEqual(proceso.returncode, 0, proceso.stdout + proceso.stderr)
        return proceso.stdout

    def _preparar(self):
        """Lo mismo que deja la preparación manual, sin `vsce`."""
        materializar = subprocess.run(
            [sys.executable, str(RAIZ / "scripts" / "materializar_md.py"),
             str(self.proyecto)],
            capture_output=True, text=True, cwd=RAIZ, timeout=180)
        self.assertEqual(materializar.returncode, 0,
                         materializar.stdout + materializar.stderr)
        self._cli("analyze", "PLAN-001")
        self._cli("comandos", "--cliente", "copilot")

    def test_el_arnes_pasa_entero(self):
        self._preparar()
        proceso = subprocess.run(
            [NODE, str(ARNES), str(RAIZ), str(self.proyecto), sys.executable],
            capture_output=True, text=True, cwd=self.base, timeout=300)
        salida = proceso.stdout + proceso.stderr
        self.assertEqual(proceso.returncode, 0, salida)
        self.assertIn("comprobaciones en verde", salida)
        fallos = [linea for linea in salida.splitlines() if linea.startswith("FAIL")]
        self.assertEqual(fallos, [], salida)
        self.assertRegex(salida, r"== \d+/\d+ comprobaciones en verde ==")

    def test_el_proyecto_queda_intacto(self):
        """El arnés rompe una skill y la restaura: no deja basura en el proyecto."""
        self._preparar()
        antes = sorted(p.relative_to(self.proyecto)
                       for p in self.proyecto.rglob("*"))
        proceso = subprocess.run(
            [NODE, str(ARNES), str(RAIZ), str(self.proyecto), sys.executable],
            capture_output=True, text=True, cwd=self.base, timeout=300)
        self.assertEqual(proceso.returncode, 0, proceso.stdout + proceso.stderr)
        despues = sorted(p.relative_to(self.proyecto)
                         for p in self.proyecto.rglob("*"))
        self.assertEqual(antes, despues)
        self.assertIn(str(RAIZ / "cli" / "main.py"),
                      (self.proyecto / ".github" / "prompts"
                       / "sdd-status.prompt.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
