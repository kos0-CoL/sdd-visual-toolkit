"""Pruebas de RF-38 — Capa de integración IDE (§29-30, §32)."""

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS

from core.export import documento, render  # noqa: E402
from core.states import NODOS  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "estado-0.1.0"


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

    def test_publica_las_rutas_de_skills_que_no_existen(self):
        """El IDE avisa con esto: la cuenta la hace la CLI, no el editor."""
        doc = documento({"proyecto": "d"}, [], [], {"pills": []},
                        skills={"/tmp/viejo/cli/main.py": 14})
        self.assertEqual(doc["avisos"]["skills"]["total"], 14)
        self.assertEqual(doc["avisos"]["skills"]["rutas"],
                         [{"ruta": "/tmp/viejo/cli/main.py", "archivos": 14}])
        sano = documento({"proyecto": "d"}, [], [], {"pills": []})
        self.assertEqual(sano["avisos"]["skills"], {"total": 0, "rutas": []})

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


class TestAvisoDeSkillsEnExport(unittest.TestCase):
    """Una skill con la ruta muerta tiene que llegar al `export`."""

    def test_export_reporta_un_archivo_generado_con_ruta_muerta(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "proyecto"
        cli = [sys.executable, "cli/main.py", "--root", str(root)]

        def correr(*args):
            r = subprocess.run([*cli, *args], capture_output=True, text=True,
                               cwd=Path.cwd(), input="", timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return r.stdout

        correr("init", "--sin-comandos")
        sano = json.loads(correr("export"))
        self.assertEqual(sano["avisos"]["skills"]["total"], 0)

        generado = root / ".github" / "prompts" / "sdd-status.prompt.md"
        generado.parent.mkdir(parents=True, exist_ok=True)
        generado.write_text(
            'python3 "/tmp/toolkit-viejo/cli/main.py" --root . status\n',
            encoding="utf-8")
        doc = json.loads(correr("export"))
        self.assertEqual(doc["avisos"]["skills"]["total"], 1)
        self.assertEqual(doc["avisos"]["skills"]["rutas"][0]["ruta"],
                         "/tmp/toolkit-viejo/cli/main.py")


class TestArtefactosDelFlujo(unittest.TestCase):
    """Las rutas del panel tienen que ser las que la CLI escribe de verdad."""

    def test_cada_fase_publica_su_artefacto(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "proyecto"

        def cli(*args):
            r = subprocess.run(
                [sys.executable, "cli/main.py", "--root", str(root), *args],
                capture_output=True, text=True, cwd=Path.cwd(), input="",
                timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return r.stdout

        cli("init", str(root))
        cli("enrich", "Quiero un dashboard para gestionar un kiosco.")
        cli("enrich", "--accept", "ENR-001")
        cli("specify", "ENR-001", "--titulo", "Kiosco")
        cli("specify", "--approve", "SPEC-001")
        pendientes = [linea.split()[1]
                      for linea in cli("clarify", "--list", "SPEC-001").splitlines()
                      if linea.strip().startswith("○")]
        self.assertTrue(pendientes)
        for numero, cla in enumerate(pendientes, start=1):
            cli("clarify", "SPEC-001", "--answer", cla, "respuesta %d" % numero)
        cli("plan", "SPEC-001")
        cli("plan", "--gate", "PLAN-001")
        cli("tasks", "PLAN-001")
        cli("analyze", "PLAN-001")

        por_fase = {fila["fase"]: fila
                    for fila in json.loads(cli("export"))["flujo"]}
        self.assertEqual(por_fase["Arquitectura"]["artefacto"],
                         ".specify/planes/PLAN-001.md")
        self.assertEqual(por_fase["Tareas"]["artefacto"],
                         ".specify/tareas/TASKS-PLAN-001.md")
        self.assertEqual(por_fase["Análisis"]["artefacto"],
                         ".specify/informes/INFORME-PLAN-001.md")


class TestOrdenDelMetodo(unittest.TestCase):
    """§21: árbol y flujo se leen en el orden del método, no del dict."""

    def test_arbol_y_flujo_respetan_el_orden_de_las_fases(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "proyecto"
        shutil.copytree(FIXTURE, root)
        esperadas = [fase for _icono, fase in NODOS]

        def cli(*args):
            r = subprocess.run(
                [sys.executable, "cli/main.py", "--root", str(root), *args],
                capture_output=True, text=True, cwd=Path.cwd(), input="",
                timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return r.stdout

        simbolos = ("○", "●", "✔", "⚠", "✘", "♻")
        fases = [linea.strip().split(" ", 1)[1].split(":")[0]
                 for linea in cli("arbol").splitlines()
                 if linea.strip().startswith(simbolos)]
        self.assertEqual(fases, esperadas)

        filas = json.loads(cli("export"))["flujo"]
        self.assertEqual([f["fase"] for f in filas], esperadas)


if __name__ == "__main__":
    unittest.main()
