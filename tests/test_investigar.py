"""Pruebas de RF-08 — Investigación del repositorio (§8.2)."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.plan import investigar  # noqa: E402
from core.repo import render  # noqa: E402


class TestRender(unittest.TestCase):
    def test_informe_completo(self):
        texto = render(investigar(Path.cwd()))
        for marca in ("Investigación del repositorio",
                      "Archivos analizados:", "Lenguajes:",
                      "Componentes de código", "Persistencia:",
                      "Pruebas existentes", "Convenciones:"):
            self.assertIn(marca, texto)
        self.assertIn("Python", texto)

    def test_greenfield_lo_dice(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        texto = render(investigar(Path(tmp.name)))
        self.assertIn("Greenfield: sin código propio", texto)
        self.assertIn("sin suite de pruebas", texto)


class TestInvestigarCLI(unittest.TestCase):
    def test_cli_sobre_proyecto_real(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "kiosco.py").write_text(
            "import json\n\nSTOCK = 5\n", encoding="utf-8")
        (root / "tests" / "test_kiosco.py").write_text(
            "import unittest\n", encoding="utf-8")
        r = subprocess.run(
            [sys.executable, "cli/main.py", "--root", str(root),
             "investigar"],
            capture_output=True, text=True, cwd=Path.cwd(), input="",
            timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("src/kiosco.py", r.stdout)
        self.assertIn("test_kiosco.py", r.stdout)
        self.assertIn("json", r.stdout)
        self.assertIn("¿Qué desea hacer ahora?", r.stdout)

    def test_directorio_inexistente_falla(self):
        r = subprocess.run(
            [sys.executable, "cli/main.py", "--root", "/no/existe/xyz",
             "investigar"],
            capture_output=True, text=True, cwd=Path.cwd(), input="",
            timeout=60)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
