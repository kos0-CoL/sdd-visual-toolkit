"""Pruebas de RF-34 — Visual AST Diff (§24)."""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from core.diffview import (analizar_fuente, comparativa,  # noqa: E402
                           comparar_estructural, fuera_de_alcance, vista)

ANTES = ("import os\n\nSTOCK = 5\n\n\ndef vender(cant):\n"
         "    return cant\n")
DESPUES = ("import os\nimport sys\n\nSTOCK = 10\n\n\ndef vender(cant, desc=0):\n"
           "    return cant - desc\n\n\ndef nuevo():\n"
           "    return 1\n")


class TestEstructural(unittest.TestCase):
    def test_detecta_todo(self):
        est = comparar_estructural(analizar_fuente(ANTES),
                                   analizar_fuente(DESPUES))
        self.assertEqual(est["funciones_agregadas"], ["nuevo"])
        self.assertEqual(est["funciones_eliminadas"], [])
        self.assertEqual(est["firmas_modificadas"], ["vender"])
        self.assertEqual(est["variables_modificadas"], ["STOCK"])
        self.assertEqual(est["imports_agregados"], ["import sys"])

    def test_sin_cambios(self):
        est = comparar_estructural(analizar_fuente(ANTES),
                                   analizar_fuente(ANTES))
        self.assertTrue(all(not v for v in est.values()))

    def test_no_analizable(self):
        est = comparar_estructural(analizar_fuente("def (("),
                                   analizar_fuente("x = 1"))
        self.assertTrue(est.get("no_analizable"))

    def test_comparativa_trunca_y_marca(self):
        grande_antes = "\n".join("a%d = %d" % (i, i) for i in range(100))
        grande_despues = "\n".join("a%d = %d" % (i, i + 1)
                                   for i in range(100))
        lineas = comparativa(grande_antes, grande_despues, "f.py",
                             max_lineas=10)
        self.assertEqual(len(lineas), 11)
        self.assertIn("truncado", lineas[-1])

    def test_fuera_de_alcance(self):
        self.assertEqual(
            fuera_de_alcance({"src/a.py"}, {"src/a.py", "src/b.py"},
                             {"src/c.py"}),
            ["src/b.py"])
        self.assertEqual(fuera_de_alcance(set(), set(), set()), [])

    def test_vista(self):
        est = comparar_estructural(analizar_fuente(ANTES),
                                   analizar_fuente(DESPUES))
        texto = vista("src/k.py", "modificado", est,
                      comparativa(ANTES, DESPUES, "src/k.py"))
        for marca in ("Funciones agregadas: nuevo",
                      "Firmas modificadas: vender",
                      "Variables con valor distinto: STOCK",
                      "Imports agregados: import sys",
                      "Comparativa:", "+++"):
            self.assertIn(marca, texto)


class TestDiffCLI(unittest.TestCase):
    def test_diff_sobre_snapshot_real(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "kiosco.py").write_text(ANTES, encoding="utf-8")
        (root / "tests" / "test_k.py").write_text(
            "import unittest\n", encoding="utf-8")
        sys.path.insert(0, str(Path.cwd()))
        from state import store  # noqa: PLC0415
        from cli.commands import tasks as mod_tasks  # noqa: PLC0415
        from core.rollback import tomar  # noqa: PLC0415
        store.inicializar_proyecto(root)
        store.escribir_json(
            root / store.SPECIFY_DIR / "tareas.json",
            {"PLAN-001": {"archivo": ".specify/tareas/TASKS-PLAN-001.md"}})
        store.escribir_json(
            root / store.SPECIFY_DIR / "planes.json",
            {"PLAN-001": {"archivo": ".specify/planes/PLAN-001.md",
                           "spec_id": "SPEC-001"}})
        (root / store.SPECIFY_DIR / "planes").mkdir(exist_ok=True)
        store.escribir_json(
            root / store.SPECIFY_DIR / "planes" / "PLAN-001.json",
            {"plan_id": "PLAN-001", "spec_id": "SPEC-001"})
        store.escribir_json(
            root / store.SPECIFY_DIR / "specs.json",
            {"SPEC-001": {"archivo": ".specify/specs/SPEC-001.md"}})
        (root / store.SPECIFY_DIR / "specs").mkdir(exist_ok=True)
        store.escribir_json(
            root / store.SPECIFY_DIR / "specs" / "SPEC-001.json",
            {"spec_id": "SPEC-001", "titulo": "T"})
        tarea = mod_tasks.Tarea(
            id="TASK-001", descripcion="d", objetivo="o",
            archivos=["src/kiosco.py"], dependencias=[],
            precondiciones=[], resultado="r", criterio="c",
            pruebas=[], refs=["§6:X"])
        mod_tasks._persistir(root, "PLAN-001", "SPEC-001", [tarea])
        tomar(root, tarea)
        (root / "src" / "kiosco.py").write_text(DESPUES, encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            from cli.commands import diff as mod  # noqa: PLC0415
            rc = mod.despachar(NS(root=str(root), texto="TASK-001", n=None))
        self.assertEqual(rc, 0)
        texto = buf.getvalue()
        self.assertIn("snapshot 0", texto)
        self.assertIn("Funciones agregadas: nuevo", texto)
        self.assertIn("Firmas modificadas: vender", texto)
        self.assertIn("Comparativa:", texto)
        self.assertIn("Validación:", texto)


if __name__ == "__main__":
    unittest.main()
