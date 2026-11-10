"""Pruebas de RF-40 — Servidor MCP (§30)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SERVIDOR = [sys.executable, "mcp/server.py"]
TOOLKIT = [sys.executable, "cli/main.py"]


def _correr(peticiones: list, root: Path) -> list:
    """Una sesión MCP fresca sobre un proyecto ya inicializado."""
    lineas = [{"jsonrpc": "2.0", "id": 0, "method": "initialize",
               "params": {"protocolVersion": "2024-11-05"}}]
    lineas += peticiones
    entrada = "\n".join(json.dumps(p) for p in lineas) + "\n"
    r = subprocess.run(SERVIDOR, capture_output=True, text=True,
                       cwd=Path.cwd(), input=entrada, timeout=60)
    assert r.returncode == 0, r.stderr
    return [json.loads(l) for l in r.stdout.splitlines() if l.strip()]


def _init(root: Path) -> None:
    subprocess.run([*TOOLKIT, "--root", str(root), "init", str(root)],
                   capture_output=True, text=True, cwd=Path.cwd(),
                   input="", timeout=60, check=True)


def _sesion(peticiones: list, root: Path) -> list:
    """Una sesión MCP fresca: init + enrich, sobre proyecto real."""
    _init(root)
    subprocess.run([*TOOLKIT, "--root", str(root),
                    "enrich", "Quiero un dashboard."],
                   capture_output=True, text=True, cwd=Path.cwd(), input="",
                   timeout=60, check=True)
    return _correr(peticiones, root)


def _tarea(tid: str, archivos: list) -> dict:
    return {"id": tid, "descripcion": "D", "objetivo": "O",
            "archivos": archivos, "dependencias": [], "precondiciones": [],
            "resultado": "R", "criterio": "C", "pruebas": [],
            "estado": "pendiente", "intentos": 0, "refs": ["REQ-001"]}


def _escribir_tareas(root: Path, tareas: list) -> None:
    specify = root / ".specify"
    (specify / "tareas").mkdir(parents=True, exist_ok=True)
    rel = ".specify/tareas/TASKS-PLAN-001.md"
    (root / rel).write_text("# Tareas\n", encoding="utf-8")
    (root / rel).with_suffix(".json").write_text(json.dumps(
        {"plan_id": "PLAN-001", "spec_id": "SPEC-001", "tareas": tareas},
        ensure_ascii=False), encoding="utf-8")
    (specify / "tareas.json").write_text(json.dumps({
        "PLAN-001": {"plan_id": "PLAN-001", "spec_id": "SPEC-001",
                     "archivo": rel, "tareas": [t["id"] for t in tareas]},
    }), encoding="utf-8")


def _implementar(root: Path, tarea: dict, pasa: bool = True) -> None:
    for a in tarea["archivos"]:
        ruta = root / a
        ruta.parent.mkdir(parents=True, exist_ok=True)
        if a.endswith(".py") and a.startswith("tests/"):
            (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
            ok = "True" if pasa else "False"
            ruta.write_text(
                "import unittest\n\n\nclass TestHumano(unittest.TestCase):\n"
                "    def test_implementado(self):\n"
                f"        self.assertTrue({ok})\n",
                encoding="utf-8")
        else:
            ruta.write_text("# implementado\n", encoding="utf-8")


class TestMcp(unittest.TestCase):
    def test_initialize_y_tools_list(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        respuestas = _sesion(
            [{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}],
            Path(tmp.name))
        init, tools = respuestas
        self.assertEqual(init["result"]["serverInfo"]["name"],
                         "sdd-visual-toolkit")
        nombres = {t["name"] for t in tools["result"]["tools"]}
        self.assertEqual(nombres, {
            "exportar_estado", "siguiente", "tablero",
            "asignar_tarea", "registrar_resultado", "marcar_completada"})

    def test_tools_sobre_proyecto_real(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = str(Path(tmp.name))
        respuestas = _sesion(
            [{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "exportar_estado",
                         "arguments": {"root": root}}},
             {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
              "params": {"name": "siguiente",
                         "arguments": {"root": root}}},
             {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
              "params": {"name": "tablero",
                         "arguments": {"root": root}}}],
            Path(tmp.name))
        por_id = {r["id"]: r["result"] for r in respuestas[1:]}
        doc = json.loads(por_id[1]["content"][0]["text"])
        self.assertEqual(doc["api"], "1.0")
        self.assertIn("enrich", doc["proxima"])
        self.assertIn("Navegación", por_id[2]["content"][0]["text"])
        self.assertTrue(por_id[3]["content"][0]["text"])

    def test_errores_se_declaran(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        respuestas = _sesion(
            [{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "inexistente", "arguments": {}}},
             {"jsonrpc": "2.0", "id": 2, "method": "metodo/raro"}],
            Path(tmp.name))
        _, mal_herr, mal_met = respuestas
        self.assertTrue(mal_herr["result"]["isError"])
        self.assertEqual(mal_met["error"]["code"], -32601)

    def test_operativas_asignar_y_cerrar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init(root)
            tarea = _tarea("TASK-001", ["src/x.py", "tests/test_ok.py"])
            _implementar(root, tarea)
            _escribir_tareas(root, [tarea])
            respuestas = _correr([
                {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                 "params": {"name": "asignar_tarea",
                            "arguments": {"root": str(root),
                                          "task_id": "TASK-001"}}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                 "params": {"name": "marcar_completada",
                            "arguments": {"root": str(root),
                                          "task_id": "TASK-001"}}},
            ], root)
            asignar, cerrar = respuestas[1:]
            self.assertFalse(asignar["result"]["isError"])
            self.assertIn("en_curso", asignar["result"]["content"][0]["text"])
            self.assertFalse(cerrar["result"]["isError"])
            self.assertIn("completada", cerrar["result"]["content"][0]["text"])
            estado = json.loads((root / ".specify/tareas/TASKS-PLAN-001.json")
                                .read_text(encoding="utf-8"))
            self.assertEqual(estado["tareas"][0]["estado"], "completada")

    def test_registrar_resultado_fallida(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init(root)
            _escribir_tareas(root, [_tarea("TASK-001", [])])
            respuestas = _correr([
                {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                 "params": {"name": "asignar_tarea",
                            "arguments": {"root": str(root),
                                          "task_id": "TASK-001"}}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                 "params": {"name": "registrar_resultado",
                            "arguments": {"root": str(root),
                                          "task_id": "TASK-001",
                                          "resultado": "fallida",
                                          "nota": "roto"}}},
            ], root)
            fallida = respuestas[2]
            self.assertFalse(fallida["result"]["isError"])
            self.assertIn("fallida", fallida["result"]["content"][0]["text"])

    def test_operativas_errores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init(root)
            _escribir_tareas(root, [_tarea("TASK-001", [])])
            respuestas = _correr([
                {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                 "params": {"name": "asignar_tarea",
                            "arguments": {"root": str(root)}}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                 "params": {"name": "registrar_resultado",
                            "arguments": {"root": str(root),
                                          "task_id": "TASK-999",
                                          "resultado": "fallida"}}},
            ], root)
            falta, inexistente = respuestas[1:]
            self.assertTrue(falta["result"]["isError"])
            self.assertIn("task_id", falta["result"]["content"][0]["text"])
            self.assertTrue(inexistente["result"]["isError"])
            self.assertIn("inexistente",
                          inexistente["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
