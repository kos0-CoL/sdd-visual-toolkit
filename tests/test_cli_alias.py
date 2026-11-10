"""Pruebas de RF-36 — CLI independiente (§31)."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestCliIndependiente(unittest.TestCase):
    def test_status_implement_history_specs(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        toolkit = [sys.executable, "cli/main.py", "--root", str(root)]

        def cli(*args):
            return subprocess.run(
                [*toolkit, *args], capture_output=True, text=True,
                cwd=Path.cwd(), input="", timeout=60)

        r = cli("init", str(root))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        # init ya anuncia [ status ]: ahora existe de verdad.
        r = cli("status")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Tablero", r.stdout)
        self.assertIn("Navegaci", r.stdout)

        cli("enrich", "Quiero un dashboard para gestionar un kiosco.")
        cli("enrich", "--accept", "ENR-001")
        cli("specify", "ENR-001", "--titulo", "Kiosco")

        r = cli("specs", "list")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SPEC-001", r.stdout)

        r = cli("status")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SPEC-001", r.stdout)

        # Alias implement = build (falla con gate como build, no por comando).
        r = cli("implement", "PLAN-001")
        self.assertIn("PLAN-001", r.stdout + r.stderr)

        # Alias history = historia (pide TASK-ID igual que historia).
        r = cli("history")
        self.assertIn("TASK-ID", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
