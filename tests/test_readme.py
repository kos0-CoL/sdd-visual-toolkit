"""README: los conteos de pruebas no pueden quedar desfasados.

El número del badge y las menciones «N tests» de la prosa se escriben a mano;
esta prueba los compara con lo que recolecta pytest, así al agregar o quitar
pruebas el fallo señala qué actualizar.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BADGE = re.compile(r"badge/tests-(\d+)%20passed")
PROSA = re.compile(r"(\d+) tests\b")


@lru_cache(maxsize=1)
def recolectadas() -> int:
    """Cuántas pruebas recolecta pytest en `tests/`."""
    coleccion = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
        cwd=RAIZ, capture_output=True, text=True, check=False,
    )
    if coleccion.returncode != 0:
        raise AssertionError(f"pytest no pudo recolectar:\n{coleccion.stderr}")
    encontrado = re.search(r"(\d+) tests? collected", coleccion.stdout)
    if encontrado is None:
        raise AssertionError(f"salida inesperada de pytest:\n{coleccion.stdout}")
    return int(encontrado.group(1))


class TestBadgeDeTests(unittest.TestCase):
    def test_badge_coincide_con_la_suite(self):
        texto = (RAIZ / "README.md").read_text(encoding="utf-8")
        badge = BADGE.search(texto)
        self.assertIsNotNone(badge, "el README no tiene un badge tests-N")
        self.assertEqual(
            int(badge.group(1)), recolectadas(),
            "el badge `tests-N` del README no coincide con la suite: "
            "actualice N en README.md",
        )


class TestConteosEnProsa(unittest.TestCase):
    def test_prosa_coincide_con_la_suite(self):
        texto = (RAIZ / "README.md").read_text(encoding="utf-8")
        menciones = [(texto[:m.start()].count("\n") + 1, int(m.group(1)))
                     for m in PROSA.finditer(texto)]
        self.assertTrue(
            menciones,
            "el README no menciona en prosa cuántas pruebas tiene la suite",
        )
        for linea, numero in menciones:
            with self.subTest(linea=linea):
                self.assertEqual(
                    numero, recolectadas(),
                    f"README.md:{linea} anuncia {numero} pruebas y la suite "
                    f"tiene {recolectadas()}: actualice el número",
                )


if __name__ == "__main__":
    unittest.main()
