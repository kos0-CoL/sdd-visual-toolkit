"""`scripts/materializar_md.py` reescribe los `.md` sin mover el estado.

El fixture de 0.1.0 solo trae los JSON de plan y tareas. Regenerarlos con
`--force` cambiaría el proyecto (Arquitectura 0/18), así que el script usa los
renderizadores de la CLI sobre lo que ya hay.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "materializar_md.py"
CLI = RAIZ / "cli" / "main.py"
FIXTURE = RAIZ / "tests" / "fixtures" / "estado-0.1.0"


def _estado(proyecto: Path) -> dict:
    proceso = subprocess.run([sys.executable, str(CLI), "--root", str(proyecto),
                              "export"], capture_output=True, text=True,
                             cwd=RAIZ, timeout=120)
    return json.loads(proceso.stdout)


class TestMaterializarMd(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.proyecto = Path(tmp.name) / "proyecto"
        shutil.copytree(FIXTURE, self.proyecto)

    def _materializar(self):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.proyecto)],
                              capture_output=True, text=True, cwd=RAIZ,
                              timeout=120)

    def test_escribe_los_md_sin_mover_el_estado(self):
        antes = _estado(self.proyecto)
        plan = self.proyecto / ".specify" / "planes" / "PLAN-001.md"
        tareas = self.proyecto / ".specify" / "tareas" / "TASKS-PLAN-001.md"
        self.assertFalse(plan.exists())
        self.assertFalse(tareas.exists())

        proceso = self._materializar()
        self.assertEqual(proceso.returncode, 0, proceso.stdout + proceso.stderr)
        self.assertIn("PLAN-001.md materializado", proceso.stdout)
        self.assertIn("TASKS-PLAN-001.md materializado", proceso.stdout)
        self.assertIn("plan_id: PLAN-001", plan.read_text(encoding="utf-8"))
        self.assertIn("## TASK-001", tareas.read_text(encoding="utf-8"))

        despues = _estado(self.proyecto)
        self.assertEqual(antes["fase"], despues["fase"])
        self.assertEqual(antes["progreso"], despues["progreso"])
        self.assertEqual(antes["pruebas"], despues["pruebas"])

    def test_es_idempotente(self):
        self.assertEqual(self._materializar().returncode, 0)
        segunda = self._materializar()
        self.assertEqual(segunda.returncode, 0)
        self.assertIn("sin .md que materializar", segunda.stdout)

    def test_proyecto_sin_json_no_hace_nada(self):
        vacio = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, vacio, True)
        proceso = subprocess.run([sys.executable, str(SCRIPT), str(vacio)],
                                 capture_output=True, text=True, cwd=RAIZ,
                                 timeout=60)
        self.assertEqual(proceso.returncode, 0)
        self.assertIn("sin .md que materializar", proceso.stdout)


if __name__ == "__main__":
    unittest.main()
