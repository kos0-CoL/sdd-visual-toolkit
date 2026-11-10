"""Compatibilidad: un estado escrito por 0.1.0 se abre con la CLI actual.

El fixture `tests/fixtures/estado-0.1.0/` salió del tag `v0.1.0` y no se
regenera (ver su LEEME). Aquí se comprueba lo que ningún test de unidad ve:
que los ficheros de estado antiguos siguen leyéndose, que leer no los
reescribe y que escribir con la versión actual no rompe lo anterior.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "estado-0.1.0"
CLI = RAIZ / "cli" / "main.py"


def ejecutar(raiz: Path, *argumentos: str) -> tuple[int, str]:
    """Corre la CLI sobre `raiz` y devuelve (código, salida junta)."""
    proceso = subprocess.run(
        [sys.executable, str(CLI), "--root", str(raiz), *argumentos],
        capture_output=True, text=True)
    return proceso.returncode, proceso.stdout + proceso.stderr


def huella(raiz: Path) -> dict[str, str]:
    """Hash de cada archivo del proyecto, para detectar escrituras."""
    return {str(ruta.relative_to(raiz)): sha256(ruta.read_bytes()).hexdigest()
            for ruta in sorted(raiz.rglob("*")) if ruta.is_file()}


class TestEstadoDe010(unittest.TestCase):
    """El estado de 0.1.0 sigue siendo legible y escribible."""

    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self._temporal.name) / "proyecto"
        shutil.copytree(FIXTURE, self.raiz)

    def tearDown(self):
        self._temporal.cleanup()

    def test_tablero_lee_el_estado_antiguo(self):
        codigo, salida = ejecutar(self.raiz, "tablero")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("SPEC-001", salida)
        self.assertIn("approved", salida)
        self.assertIn("TASK-001", salida)

    def test_status_no_se_queda_sin_siguiente_paso(self):
        codigo, salida = ejecutar(self.raiz, "status")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("¿Qué desea hacer ahora?", salida)

    def test_export_conserva_la_api_del_formato(self):
        codigo, salida = ejecutar(self.raiz, "export")
        self.assertEqual(codigo, 0, salida)
        datos = json.loads(salida)
        self.assertEqual(datos["api"], "1.0")
        self.assertEqual(datos["spec_id"], "SPEC-001")

    def test_leer_no_reescribe_el_estado(self):
        antes = huella(self.raiz)
        for comando in (["tablero"], ["status"], ["export"], ["siguiente"],
                        ["history", "TASK-001"]):
            codigo, salida = ejecutar(self.raiz, *comando)
            self.assertEqual(codigo, 0, "%s: %s" % (comando, salida))
        self.assertEqual(huella(self.raiz), antes,
                         "un comando de lectura reescribió el estado")

    def test_escribir_conserva_lo_anterior(self):
        codigo, salida = ejecutar(self.raiz, "req", "add", "Caja diaria")
        self.assertEqual(codigo, 0, salida)
        codigo, salida = ejecutar(self.raiz, "req", "list")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("22 requerimiento(s)", salida)
        codigo, salida = ejecutar(self.raiz, "tablero")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("SPEC-001", salida)


if __name__ == "__main__":
    unittest.main()
