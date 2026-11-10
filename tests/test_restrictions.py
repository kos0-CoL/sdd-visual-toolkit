"""Pruebas de RF-33 — Panel de restricciones (§23)."""

import io
import subprocess  # noqa: E402
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.restrictions import clasificar, render  # noqa: E402


class TestRender(unittest.TestCase):
    def test_siete_bloques(self):
        secciones = [
            ("⛔", "Fuera de alcance", ["fiado"]),
            ("🔒", "Archivos protegidos (intactos)", []),
            ("✏️", "Archivos modificables", ["src/kiosco.py"]),
            ("🔌", "Interfaces protegidas (reutilizar intactas)", []),
            ("📏", "Reglas de negocio", ["no vender sin stock"]),
            ("⚙️", "Restricciones técnicas", ["stdlib"]),
            ("✅", "Decisiones aprobadas en clarify", ["CLA-001 → Aceptado"])]
        texto = render("Panel de restricciones SPEC-001", secciones)
        for _icono, nombre, _items in secciones:
            self.assertIn(nombre, texto)
        self.assertIn("fiado", texto)
        self.assertIn("(sin datos registrados)", texto)

    def test_tarea_clasificada(self):
        tarea = {"id": "TASK-001",
                 "archivos": [("src/a.py", clasificar("src/a.py", ["src/a.py"],
                                                     ["src/b.py"])),
                              ("src/b.py", clasificar("src/b.py", ["src/a.py"],
                                                     ["src/b.py"])),
                              ("src/c.py", clasificar("src/c.py", ["src/a.py"],
                                                     ["src/b.py"]))]}
        texto = render("P", [("⛔", "Fuera de alcance", [])], tarea)
        self.assertIn("Verificando TASK-001 (3 archivo(s))", texto)
        self.assertIn("✏️ src/a.py", texto)
        self.assertIn("🔒 src/b.py", texto)
        self.assertIn("❓ src/c.py", texto)

    def test_clasificar(self):
        self.assertTrue(clasificar("a", ["a"], []).startswith("✏️"))
        self.assertTrue(clasificar("b", ["a"], ["b"]).startswith("🔒"))
        self.assertTrue(clasificar("c", ["a"], ["b"]).startswith("❓"))


class TestPanel(unittest.TestCase):
    def test_pipeline_muestra_panel_y_tarea(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        toolkit = [sys.executable, "cli/main.py", "--root", str(root)]

        def cli(*args):
            r = subprocess.run([*toolkit, *args], capture_output=True,
                               text=True, cwd=Path.cwd(), input="",
                               timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        cli("init", str(root))
        cli("enrich", "Quiero un dashboard para gestionar un kiosco.")
        cli("enrich", "--accept", "ENR-001")
        cli("specify", "ENR-001", "--titulo", "Kiosco")
        out = subprocess.run(
            [*toolkit, "clarify", "--list", "SPEC-001"],
            capture_output=True, text=True, cwd=Path.cwd(), input="",
            timeout=60).stdout
        ids = [l.split()[1] for l in out.splitlines()
               if l.strip().startswith("○")]
        args = ["clarify", "SPEC-001"]
        for i in ids:
            args += ["--answer", i, "Aceptado"]
        cli(*args)
        cli("plan", "SPEC-001")
        cli("plan", "--gate", "PLAN-001")
        buf = io.StringIO()
        with redirect_stdout(buf):
            from cli.commands import restricciones as mod  # noqa: PLC0415
            rc = mod.despachar(NS(root=str(root), texto=None))
        self.assertEqual(rc, 0)
        texto = buf.getvalue()
        for bloque in ("Fuera de alcance", "Archivos protegidos",
                       "Archivos modificables", "Interfaces protegidas",
                       "Reglas de negocio", "Restricciones técnicas",
                       "Decisiones aprobadas"):
            self.assertIn(bloque, texto)
        # Decisiones reales de clarify visibles.
        self.assertIn("→ Aceptado", texto)


if __name__ == "__main__":
    unittest.main()
