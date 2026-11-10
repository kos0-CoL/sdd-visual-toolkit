"""Pruebas de RF-40 — Servidor MCP (§30)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SERVIDOR = [sys.executable, "mcp/server.py"]


def _sesion(peticiones: list, root: Path) -> list:
    """Una sesión MCP fresca: init + peticiones, sobre proyecto real."""
    lineas = [{"jsonrpc": "2.0", "id": 0, "method": "initialize",
               "params": {"protocolVersion": "2024-11-05"}}]
    lineas += peticiones
    entrada = "\n".join(json.dumps(p) for p in lineas) + "\n"
    toolkit = [sys.executable, "cli/main.py", "--root", str(root)]
    subprocess.run([*toolkit, "init", str(root)], capture_output=True,
                   text=True, cwd=Path.cwd(), input="", timeout=60,
                   check=True)
    subprocess.run([*toolkit, "enrich", "Quiero un dashboard."],
                   capture_output=True, text=True, cwd=Path.cwd(), input="",
                   timeout=60, check=True)
    r = subprocess.run(SERVIDOR, capture_output=True, text=True,
                       cwd=Path.cwd(), input=entrada, timeout=60)
    self_check = r.returncode
    assert self_check == 0, r.stderr
    return [json.loads(l) for l in r.stdout.splitlines() if l.strip()]


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
        self.assertEqual(nombres, {"exportar_estado", "siguiente", "tablero"})

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


if __name__ == "__main__":
    unittest.main()
