"""Pruebas de RF-42 — Hooks de agente (§47)."""

import argparse
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cli.commands import analyze as cmd_analyze  # noqa: E402
from cli.commands import build as cmd_build  # noqa: E402
from cli.commands import clarify as cmd_clarify  # noqa: E402
from cli.commands import enrich as cmd_enrich  # noqa: E402
from cli.commands import hooks as cmd_hooks  # noqa: E402
from cli.commands import plan as cmd_plan  # noqa: E402
from cli.commands import specify as cmd_specify  # noqa: E402
from cli.commands import tasks as cmd_tasks  # noqa: E402
from core.hooks import EVENTOS, disparar, listar  # noqa: E402
from core.journal import historial  # noqa: E402
from state import store  # noqa: E402

KIOSCO = "Quiero un dashboard para gestionar un kiosco. Debe registrar ventas."


def _gancho(raiz, evento, nombre, cuerpo):
    carpeta = raiz / ".specify" / "hooks" / evento
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre
    ruta.write_text("#!/bin/sh\n%s\n" % cuerpo, encoding="utf-8")
    ruta.chmod(ruta.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    return ruta


class TestHooks(unittest.TestCase):
    def test_disparar_pasa_entorno_y_no_existe_sin_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            store.inicializar_proyecto(raiz)
            self.assertEqual(disparar(raiz, "tarea_abierta", {}), [])
            _gancho(raiz, "tarea_abierta", "eco.sh",
                    'echo "$SDD_EVENTO $SDD_PLAN $SDD_TAREA $SDD_RESULTADO"')
            (raiz / ".specify" / "hooks" / "tarea_abierta" / "plano.txt"
             ).write_text("no ejecutable\n", encoding="utf-8")
            res = disparar(raiz, "tarea_abierta",
                           {"plan": "PLAN-001", "tarea": "TASK-001",
                            "resultado": "en_curso"})
            self.assertEqual(len(res), 1)  # el .txt se omite
            self.assertTrue(res[0]["ok"])
            self.assertIn("tarea_abierta PLAN-001 TASK-001 en_curso",
                          res[0]["salida"])

    def test_hook_que_falla_se_declara_sin_romper(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            store.inicializar_proyecto(raiz)
            _gancho(raiz, "tarea_cerrada", "roto.sh", "echo ups >&2\nexit 3")
            res = disparar(raiz, "tarea_cerrada", {})
            self.assertFalse(res[0]["ok"])
            self.assertEqual(res[0]["codigo"], 3)
            self.assertIn("ups", res[0]["salida"])


class TestHooksCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        store.inicializar_proyecto(self.root)
        cmd_enrich.despachar(self._ns("enrich", texto=KIOSCO))
        cmd_enrich.despachar(self._ns("enrich", accept="ENR-001"))
        cmd_specify.despachar(self._ns("spec", texto="ENR-001"))

    def tearDown(self):
        self.tmp.cleanup()

    def _ns(self, cual, **kw):
        bases = {
            "enrich": {"texto": None, "list": False, "show": None,
                       "drop": None, "accept": None},
            "spec": {"texto": None, "titulo": None, "list": False,
                     "show": None, "approve": None, "revise": None,
                     "motivo": None},
            "cla": {"texto": None, "answer": None, "skip": None,
                    "list": None, "gate": False},
            "plan": {"texto": None, "force": False, "list": False,
                     "show": None, "gate": None},
            "tasks": {"texto": None, "force": False, "list": None,
                      "show": None, "gate": None},
        }
        base = dict(bases[cual])
        base.update(kw)
        ns = argparse.Namespace(root=str(self.root))
        for k, v in base.items():
            setattr(ns, k, v)
        return ns

    def _b(self, **kw):
        base = {"texto": None, "done": None, "fail": None, "nota": ""}
        base.update(kw)
        ns = argparse.Namespace(root=str(self.root))
        for k, v in base.items():
            setattr(ns, k, v)
        return ns

    def _pipeline(self):
        cmd_clarify.despachar(self._ns("cla", texto="SPEC-001", gate=True))
        preguntas, _h = cmd_clarify._preguntas_de(self.root, "SPEC-001")
        ns = self._ns("cla", texto="SPEC-001")
        ns.answer = [[p.id, "Definido"] for p in preguntas]
        cmd_clarify.despachar(ns)
        cmd_plan.despachar(self._ns("plan", texto="SPEC-001"))
        cmd_plan.despachar(self._ns("plan", gate="PLAN-001"))
        cmd_tasks.despachar(self._ns("tasks", texto="PLAN-001"))
        cmd_analyze.despachar(argparse.Namespace(
            root=str(self.root), texto="PLAN-001", gate=None))

    def test_hooks_list_sin_hooks_y_con_hooks(self):
        r = subprocess.run(
            [sys.executable, "cli/main.py", "--root", str(self.root), "hooks"],
            capture_output=True, text=True, cwd=Path.cwd(), input="",
            timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("sin hooks", r.stdout)
        _gancho(self.root, "tarea_abierta", "eco.sh", "true")
        r = subprocess.run(
            [sys.executable, "cli/main.py", "--root", str(self.root), "hooks"],
            capture_output=True, text=True, cwd=Path.cwd(), input="",
            timeout=60)
        self.assertIn("eco.sh — ▶ ejecutable", r.stdout)

    def test_build_dispara_hooks_y_registra_en_journal(self):
        self._pipeline()
        log = self.root / "hooks.log"
        _gancho(self.root, "tarea_abierta", "abre.sh",
                'echo "$SDD_TAREA abierta" >> "$SDD_ROOT/hooks.log"')
        _gancho(self.root, "tarea_cerrada", "cierra.sh",
                'echo "$SDD_TAREA $SDD_RESULTADO" >> "$SDD_ROOT/hooks.log"')
        self.assertEqual(cmd_build.despachar(self._b(texto="PLAN-001")), 0)
        _info, tareas = cmd_tasks._cargar_tareas(self.root, "PLAN-001")
        primera = tareas[0]
        self.assertIn("%s abierta" % primera.id,
                      log.read_text(encoding="utf-8"))
        self.assertEqual(cmd_build.despachar(
            self._b(texto="PLAN-001", fail=primera.id,
                    nota="falla provocada")), 0)
        lineas = log.read_text(encoding="utf-8")
        self.assertIn("%s fallida" % primera.id, lineas)
        eventos = [e for e in historial(self.root, "PLAN-001")
                   if e.get("evento") == "hook"]
        self.assertTrue(any("tarea_abierta/abre.sh: ok" in e.get("nota", "")
                            for e in eventos))
        self.assertTrue(any("tarea_cerrada/cierra.sh: ok" in e.get("nota", "")
                            for e in eventos))


if __name__ == "__main__":
    unittest.main()
