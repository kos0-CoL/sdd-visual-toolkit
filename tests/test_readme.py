"""README: el badge de tests no puede quedar desfasado.

El número del badge se escribe a mano; esta prueba lo compara con lo que
recolecta pytest, así al agregar o quitar pruebas el fallo señala qué
actualizar.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BADGE = re.compile(r"badge/tests-(\d+)%20passed")


class TestBadgeDeTests(unittest.TestCase):
    def test_badge_coincide_con_la_suite(self):
        texto = (RAIZ / "README.md").read_text(encoding="utf-8")
        badge = BADGE.search(texto)
        self.assertIsNotNone(badge, "el README no tiene un badge tests-N")

        coleccion = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
            cwd=RAIZ, capture_output=True, text=True, check=False,
        )
        self.assertEqual(coleccion.returncode, 0,
                         f"pytest no pudo recolectar:\n{coleccion.stderr}")

        recolectadas = re.search(r"(\d+) tests? collected", coleccion.stdout)
        self.assertIsNotNone(recolectadas,
                             f"salida inesperada de pytest:\n{coleccion.stdout}")
        self.assertEqual(
            int(badge.group(1)), int(recolectadas.group(1)),
            "el badge `tests-N` del README no coincide con la suite: "
            "actualice N en README.md",
        )


if __name__ == "__main__":
    unittest.main()
