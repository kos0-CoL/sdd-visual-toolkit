"""La preparación de la pasada manual es repetible (§29).

`scripts/preparar-manual.sh` hace lo que antes se copiaba a mano en
`ide/PRUEBA-MANUAL.md`: fixture, ajustes del workspace, `src/` restaurado y
comandos del agente. Aquí se comprueba con `--sin-vsix`, que no necesita red.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "preparar-manual.sh"


class TestPrepararManual(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.destino = self.base / "proyecto"

    def _preparar(self, *extra):
        return subprocess.run(
            ["bash", str(SCRIPT), "--sin-vsix", "--destino", str(self.destino),
             *extra],
            capture_output=True, text=True, timeout=180)

    def test_deja_el_proyecto_listo(self):
        r = self._preparar()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ajustes = json.loads(
            (self.destino / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        cli = Path(ajustes["sddToolkit.cliPath"])
        self.assertTrue(cli.is_absolute(), cli)
        self.assertTrue(cli.is_file(), cli)
        self.assertTrue(ajustes["sddToolkit.python"])
        skills = list((self.destino / ".github" / "skills").glob("*/SKILL.md"))
        self.assertEqual(len(skills), 14)
        self.assertTrue((self.destino / "src" / "productos.py").is_file())
        self.assertTrue(
            (self.destino / ".specify" / "memory" / "current_task.json").is_file())
        self.assertIn("AL DÍA", r.stdout)
        self.assertIn("PRUEBA-MANUAL.md", r.stdout)

    def test_no_pisa_un_destino_existente_sin_force(self):
        self.assertEqual(self._preparar().returncode, 0)
        r = self._preparar()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--force", r.stderr)
        self.assertTrue((self.destino / ".vscode" / "settings.json").is_file())

    def test_instalar_exige_empaquetar_el_vsix(self):
        r = self._preparar("--instalar")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--instalar necesita", r.stderr)
        self.assertFalse(self.destino.exists())

    def _solo_verificar(self, *extra):
        return subprocess.run(
            ["bash", str(SCRIPT), "--solo-verificar", "--destino",
             str(self.destino), *extra],
            capture_output=True, text=True, timeout=300)

    def test_solo_verificar_informa_sobre_lo_ya_preparado(self):
        self.assertEqual(self._preparar().returncode, 0)
        (self.destino / "marca.txt").write_text("x", encoding="utf-8")
        r = self._solo_verificar()
        # El arnés queda pendiente de editor: eso ya cuenta como fallo de salida.
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("pendiente(s) de editor", r.stderr)
        self.assertIn("Verificación de", r.stdout)
        self.assertIn("comprobación", r.stdout)
        for nombre in ("ajustes", "snapshot", "artefactos", "comandos", "estado",
                       "extensión", "arnés"):
            self.assertRegex(r.stdout, rf"(?m)^  {nombre}\s+[✓☐⚠⛔]")
        for nombre in ("ajustes", "artefactos", "estado", "comandos"):
            self.assertRegex(r.stdout, rf"(?m)^  {nombre}\s+✓")
        # El arnés se separa: pasa en el stub, pero el editor no lo vio.
        self.assertRegex(r.stdout, r"(?m)^  arnés\s+(☐|⚠️)")
        self.assertNotRegex(r.stdout, r"(?m)^  arnés\s+✓")
        self.assertIn("☐ pendiente de editor", r.stdout)
        self.assertIn("pendiente de editor:", r.stdout)
        self.assertIn("Casillas de ide/PRUEBA-MANUAL.md", r.stdout)
        self.assertIn("VS Code — extensión:", r.stdout)
        # No rehace nada: el archivo de más sigue donde estaba.
        self.assertTrue((self.destino / "marca.txt").is_file())

    def test_solo_verificar_sin_proyecto_avisa(self):
        r = self._solo_verificar()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no está preparado", r.stderr)
        self.assertFalse(self.destino.exists())

    def test_solo_verificar_no_se_mezcla_con_force(self):
        self.assertEqual(self._preparar().returncode, 0)
        r = self._solo_verificar("--force")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--solo-verificar no rehace", r.stderr)

    def test_force_rehace_el_destino(self):
        self.assertEqual(self._preparar().returncode, 0)
        (self.destino / "basura.txt").write_text("x", encoding="utf-8")
        r = self._preparar("--force")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.destino / "basura.txt").exists())


if __name__ == "__main__":
    unittest.main()
