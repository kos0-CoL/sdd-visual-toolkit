"""Pruebas de RF-38 — Capa de integración IDE (§29-30, §32)."""

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS

from core.export import documento, render  # noqa: E402


class TestDocumento(unittest.TestCase):
    def test_mismo_estado_que_tablero_y_navegacion(self):
        estado = {"proyecto": "demo", "spec_id": "SPEC-001",
                  "spec_status": "draft", "fase": "📝 Especificación",
                  "hechas": 0, "total": 0, "pendientes": 0,
                  "tarea_actual": None, "ultima_completada": None,
                  "pruebas": "sin corridas", "errores": [],
                  "proxima": "clarify SPEC-001"}
        nav = {"recomendada": {"etiqueta": "X", "comando": "clarify SPEC-001"},
               "pills": [{"etiqueta": "X", "comando": "clarify SPEC-001",
                           "recomendada": True, "bloqueada": False,
                           "motivo": ""}],
               "bloqueos": [], "requiere_aprobacion": True}
        doc = documento(estado, [("Especificación", "en progreso")], [],
                        nav)
        self.assertEqual(doc["spec_id"], "SPEC-001")
        self.assertEqual(doc["proxima"], "clarify SPEC-001")
        self.assertEqual(doc["navegacion"]["recomendada"], "clarify SPEC-001")
        self.assertTrue(doc["navegacion"]["requiere_aprobacion"])
        self.assertEqual(doc["arbol"][0]["fase"], "Especificación")
        # Serializa sin fugas: lo que un adaptador externo leería.
        visto = json.loads(render(doc))
        self.assertEqual(visto, doc)

    def test_sin_spec_tambien_serializa(self):
        doc = documento({"proyecto": "d"}, [], [], {"pills": []})
        self.assertIsNone(doc["spec_id"])
        json.loads(render(doc))


class TestExportCLI(unittest.TestCase):
    def test_export_espeja_tablero_y_siguiente(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        toolkit = [sys.executable, "cli/main.py", "--root", str(root)]

        def cli(*args):
            r = subprocess.run([*toolkit, *args], capture_output=True,
                               text=True, cwd=Path.cwd(), input="",
                               timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return r.stdout

        cli("init", str(root))
        buf = io.StringIO()
        with redirect_stdout(buf):
            from cli.commands import export as mod  # noqa: PLC0415
            rc = mod.despachar(NS(root=str(root)))
        self.assertEqual(rc, 0)
        doc = json.loads(buf.getvalue())
        self.assertIsNone(doc["spec_id"])
        self.assertIn("enrich", doc["proxima"])

        cli("enrich", "Quiero un dashboard para gestionar un kiosco.")
        cli("enrich", "--accept", "ENR-001")
        cli("specify", "ENR-001", "--titulo", "Kiosco")
        doc = json.loads(cli("export"))
        tab = cli("tablero")
        sig = cli("siguiente")
        # Mismo estado central (§32): export refleja lo visible.
        self.assertIn(doc["spec_id"], tab)
        self.assertIn(doc["navegacion"]["recomendada"], sig)
        self.assertTrue(doc["arbol"])

    def test_el_flujo_casa_fase_artefacto_y_skill(self):
        """El panel del IDE pinta esto tal cual: fase, estado, artefacto,
        skill y comando, sin inventar lo que todavía no existe."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        toolkit = [sys.executable, "cli/main.py", "--root", str(root)]

        def cli(*args):
            r = subprocess.run([*toolkit, *args], capture_output=True,
                               text=True, cwd=Path.cwd(), input="",
                               timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return r.stdout

        cli("init", str(root))
        filas = json.loads(cli("export"))["flujo"]
        self.assertEqual([f["fase"] for f in filas][:3],
                         ["Enriquecimiento", "Especificación", "Aclaraciones"])
        self.assertTrue(all(f["estado"] for f in filas))
        spec = filas[1]
        self.assertEqual(spec["skill"], "sdd-specify")
        self.assertIsNone(spec["artefacto"])  # todavía no hay SPEC
        self.assertIsNone(spec["comando"])

        cli("enrich", "Quiero un dashboard para gestionar un kiosco.")
        cli("enrich", "--accept", "ENR-001")
        cli("specify", "ENR-001", "--titulo", "Kiosco")
        filas = json.loads(cli("export"))["flujo"]
        por_fase = {f["fase"]: f for f in filas}
        self.assertEqual(por_fase["Especificación"]["artefacto"],
                         "specs/SPEC-001.md")
        self.assertEqual(por_fase["Especificación"]["comando"],
                         "specify --show SPEC-001")
        self.assertEqual(por_fase["Aclaraciones"]["skill"], "sdd-clarify")
        self.assertEqual(por_fase["Aclaraciones"]["comando"],
                         "clarify SPEC-001")
        # Sin plan no hay artefacto ni comando de fases posteriores.
        self.assertIsNone(por_fase["Tareas"]["artefacto"])
        self.assertIsNone(por_fase["Tareas"]["comando"])


if __name__ == "__main__":
    unittest.main()
