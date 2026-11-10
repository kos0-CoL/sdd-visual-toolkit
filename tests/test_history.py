"""Pruebas de RF-30 — Historial y trazabilidad (§44.30)."""

import sys
import unittest

from core.history import eventos_de, relato  # noqa: E402


def _ev(**kw):
    base = {"fecha": "f", "tarea": "TASK-001", "evento": "tests",
            "pruebas_ok": True, "pasadas": 2, "fallidas": 0,
            "duracion_s": 1.0, "cobertura_pct": 80}
    base.update(kw)
    return base


class TestHistory(unittest.TestCase):
    def test_sin_eventos_no_inventa(self):
        self.assertIn("Sin historia", relato([], "TASK-001"))

    def test_filtra_por_tarea_en_orden(self):
        evs = [_ev(fecha="f2"), _ev(fecha="f1", tarea="TASK-002"),
               _ev(fecha="f3")]
        filtrados = eventos_de(evs, "TASK-001")
        self.assertEqual([e["fecha"] for e in filtrados], ["f2", "f3"])

    def test_relato_cronologico_con_evidencia(self):
        evs = [
            {"fecha": "f1", "tarea": "TASK-001", "evento": "en_curso"},
            _ev(fecha="f2"),
            _ev(fecha="f3", pruebas_ok=False, pasadas=1, fallidas=1,
                 cobertura_pct=None),
            {"fecha": "f4", "tarea": "TASK-001", "evento": "rollback",
             "nota": "misma firma 2 veces"},
            {"fecha": "f5", "tarea": "TASK-001", "evento": "completada",
             "pruebas": "verde", "pruebas_ok": True,
             "hashes_tests": {"a.py": "x"},
             "evidencia_tests": {"cobertura_pct": 100},
             "tests_modificados": ["tests/test_a.py"]},
        ]
        texto = relato(evs, "TASK-001")
        self.assertIn("5 evento(s)", texto)
        self.assertIn("puesta en curso", texto)
        self.assertIn("✅", texto)
        self.assertIn("❌", texto)
        self.assertIn("cob=80%", texto)
        self.assertIn("rollback", texto)
        self.assertIn("1 hash(es)", texto)
        self.assertIn("cob=100%", texto)
        self.assertIn("tests modificados: tests/test_a.py", texto)

    def test_completada_sin_evidencia_opcional(self):
        evs = [{"fecha": "f", "tarea": "TASK-001", "evento": "completada",
                "pruebas": "ok", "pruebas_ok": True, "hashes_tests": {}}]
        texto = relato(evs, "TASK-001")
        self.assertIn("0 hash(es)", texto)


if __name__ == "__main__":
    unittest.main()
