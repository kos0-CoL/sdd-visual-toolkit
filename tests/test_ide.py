"""Pruebas de RF-39 — Integración con VS Code (§29).

La extensión es declarativa (package.json + extension.js sin build):
se verifica que cada comando de paleta exista en la CLI real, que la
vista lateral y la barra de estado estén declaradas, y que el JS
tenga sintaxis válida cuando hay node disponible.
"""

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from cli.main import construir_parser  # noqa: E402

IDE = Path("ide/vscode")


def _comandos_cli() -> set:
    parser = construir_parser()
    subs = parser._actions[-1]  # subparsers de comandos
    nombres = set(subs.choices)
    req = subs.choices["req"]._actions[-1]
    nombres |= {"req %s" % c for c in req.choices}
    specs = subs.choices["specs"]._actions[-1]
    nombres |= {"specs %s" % c for c in specs.choices}
    return nombres


class TestManifiesto(unittest.TestCase):
    def test_package_valido_y_completo(self):
        manifiesto = json.loads((IDE / "package.json").read_text(
            encoding="utf-8"))
        comandos = manifiesto["contributes"]["commands"]
        self.assertGreaterEqual(len(comandos), 25)
        for c in comandos:
            self.assertTrue(c["command"].startswith("sdd."))
            self.assertTrue(c["title"].startswith("SDD:"))
        vistas = manifiesto["contributes"]["views"]["sdd-explorer"]
        self.assertTrue(any(v["id"] == "sddFases" for v in vistas))
        self.assertIn("sdd-explorer",
                      [c["id"] for c in manifiesto["contributes"]
                       ["viewsContainers"]["activitybar"]])
        props = manifiesto["contributes"]["configuration"]["properties"]
        self.assertIn("sddToolkit.python", props)
        self.assertIn("sddToolkit.cliPath", props)

    def test_paleta_solo_invoca_cli_real(self):
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        invocados = re.findall(r"cli:\s*'([^']+)'", fuente)
        self.assertGreaterEqual(len(invocados), 25)
        cli_reales = _comandos_cli()
        for inv in invocados:
            primero = inv.split()[0]
            self.assertIn(primero, cli_reales,
                          "la paleta invoca un comando inexistente: %s" % inv)

    def test_paleta_y_manifiesto_coinciden(self):
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        en_js = set(re.findall(r"id:\s*'(sdd\.[a-z]+)'", fuente))
        manifiesto = json.loads((IDE / "package.json").read_text(
            encoding="utf-8"))
        en_json = {c["command"] for c in manifiesto["contributes"]["commands"]}
        # La paleta registrada en JS existe en el manifiesto (más 2 internos).
        self.assertTrue(en_js <= (en_json | {"sdd.ejecutar", "sdd.actualizar"}))

    def test_diez_puntos_del_29_cubiertos(self):
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        # paleta, vista lateral, estado, fases, SPEC, tareas, pruebas,
        # historial, recuperación y acceso CLI (terminal).
        marcas = ["registerCommand", "registerTreeDataProvider",
                  "createStatusBarItem", "arbol", "traza",
                  "Progreso", "Pruebas", "historia",
                  "recover", "createTerminal"]
        for marca in marcas:
            self.assertIn(marca, fuente)

    def test_js_sintaxis_valida_si_hay_node(self):
        if shutil.which("node") is None:
            self.skipTest("sin node en este equipo")
        r = subprocess.run(["node", "--check", str(IDE / "extension.js")],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
