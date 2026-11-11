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

    def test_clarify_lee_las_aclaraciones_antiguas(self):
        codigo, salida = ejecutar(self.raiz, "clarify", "--list", "SPEC-001")
        self.assertEqual(codigo, 0, salida)
        for n in range(1, 7):
            self.assertIn("✓ CLA-00%d" % n, salida)
        self.assertNotIn("○ CLA-", salida)

    def test_clarify_gate_pasa_con_lo_aclarado_en_010(self):
        codigo, salida = ejecutar(self.raiz, "clarify", "SPEC-001", "--gate")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("6/6 aclaradas", salida)

    def test_checkpoint_antiguo_se_lee(self):
        codigo, salida = ejecutar(self.raiz, "checkpoint", "--show",
                                  "TASK-001")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("PLAN-001", salida)
        self.assertIn("TASK-002", salida)
        self.assertIn("f54bf58d7f1f9de0", salida)
        self.assertIn("ventas listas", salida)

    def test_checkpoint_lista_el_plan(self):
        codigo, salida = ejecutar(self.raiz, "checkpoint", "--list",
                                  "PLAN-001")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("✅ TASK-001", salida)

    def test_journal_state_se_lee(self):
        codigo, salida = ejecutar(self.raiz, "journal", "--state")
        self.assertEqual(codigo, 0, salida)
        estado = json.loads(salida)
        self.assertEqual(estado["plan_id"], "PLAN-001")
        self.assertEqual(estado["spec_id"], "SPEC-001")
        self.assertEqual(estado["ultimo_checkpoint"], "TASK-001-SUCCESS")
        self.assertEqual(estado["total_tareas"], 18)
        self.assertIsNone(estado["tarea_en_curso"])

    def test_la_spec_conserva_su_gemelo_markdown(self):
        texto = (self.raiz / "specs" / "SPEC-001.md").read_text(
            encoding="utf-8")
        self.assertTrue(texto.startswith("---\n"))
        self.assertIn("spec_id: SPEC-001", texto)

    def test_leer_no_reescribe_el_estado(self):
        antes = huella(self.raiz)
        for comando in (["tablero"], ["status"], ["export"], ["siguiente"],
                        ["history", "TASK-001"], ["validate", "TASK-001"],
                        ["rollback", "--list", "TASK-001"],
                        ["clarify", "--list", "SPEC-001"],
                        ["clarify", "SPEC-001", "--gate"],
                        ["checkpoint", "--show", "TASK-001"],
                        ["checkpoint", "--list", "PLAN-001"],
                        ["journal", "--state"],
                        ["specify", "--show", "SPEC-001"]):
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


class TestPinYSnapshotsDe010(unittest.TestCase):
    """`validate` y `rollback` sobre la línea base y los snapshots de 0.1.0.

    El fixture trae el pin del build y dos instantáneas de la tarea tal como
    los escribió 0.1.0. Los archivos del proyecto no están, así que el
    estado previo se materializa restaurando el snapshot 0.
    """

    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self._temporal.name) / "proyecto"
        shutil.copytree(FIXTURE, self.raiz)

    def tearDown(self):
        self._temporal.cleanup()

    def restaurar(self, *extra: str) -> tuple[int, str]:
        return ejecutar(self.raiz, "rollback", "--restore", "TASK-001",
                        *extra)

    def archivo(self, rel: str) -> str:
        return (self.raiz / rel).read_text(encoding="utf-8")

    def test_validate_lee_la_linea_base_antigua_sin_rehacerla(self):
        pin = self.raiz / ".specify" / "pines" / "TASK-001.json"
        antes = sha256(pin.read_bytes()).hexdigest()
        codigo, salida = ejecutar(self.raiz, "validate", "TASK-001")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("VALIDADO", salida)
        self.assertNotIn("sin línea base previa", salida)
        self.assertEqual(sha256(pin.read_bytes()).hexdigest(), antes,
                         "validate rehizo la línea base de 0.1.0")

    def test_rollback_lista_los_snapshots_antiguos(self):
        codigo, salida = ejecutar(self.raiz, "rollback", "--list", "TASK-001")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("snapshot TASK-001/0", salida)
        self.assertIn("snapshot TASK-001/1", salida)

    def test_rollback_restaura_el_ultimo_snapshot(self):
        codigo, salida = self.restaurar()
        self.assertEqual(codigo, 0, salida)
        self.assertIn("desde snapshot 1", salida)
        self.assertIn("def descuento", self.archivo("src/productos.py"))

    def test_restaurar_el_snapshot_previo_devuelve_el_stub(self):
        self.restaurar("--n", "1")
        codigo, salida = self.restaurar("--n", "0")
        self.assertEqual(codigo, 0, salida)
        texto = self.archivo("src/productos.py")
        self.assertNotIn("descuento", texto)
        self.assertIn("NotImplementedError", texto)

    def test_validate_ve_el_cambio_del_intento_fallido(self):
        self.restaurar("--n", "1")
        codigo, salida = ejecutar(self.raiz, "validate", "TASK-001")
        self.assertEqual(codigo, 1, salida)
        self.assertIn("OBSERVADO", salida)
        self.assertIn("[pin-B] src/productos.py", salida)
        self.assertNotIn("sin línea base previa", salida)

    def test_restaurar_y_validar_deja_el_veredicto_limpio(self):
        self.restaurar("--n", "1")
        self.restaurar("--n", "0")
        codigo, salida = ejecutar(self.raiz, "validate", "TASK-001")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("VALIDADO", salida)

    def test_rollback_no_toca_lo_ajeno(self):
        ajeno = self.raiz / "specs" / "SPEC-001.json"
        antes = sha256(ajeno.read_bytes()).hexdigest()
        self.restaurar("--n", "1")
        self.assertEqual(sha256(ajeno.read_bytes()).hexdigest(), antes,
                         "el rollback tocó un archivo fuera de la tarea")

    def test_rollback_anota_el_evento_en_el_historial(self):
        self.restaurar("--n", "0")
        historial = self.archivo(".specify/memory/execution_history.jsonl")
        ultima = json.loads(historial.strip().splitlines()[-1])
        self.assertEqual(ultima["evento"], "rollback")
        self.assertEqual(ultima["tarea"], "TASK-001")
        self.assertEqual(ultima["plan"], "PLAN-001")

    def test_snapshot_inexistente_no_inventa_estado(self):
        codigo, salida = self.restaurar("--n", "7")
        self.assertEqual(codigo, 1, salida)
        self.assertIn("snapshot inexistente", salida)
        self.assertFalse((self.raiz / "src" / "productos.py").exists())


if __name__ == "__main__":
    unittest.main()
