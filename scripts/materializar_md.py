"""Materializa los `.md` de plan y tareas a partir de sus JSON.

El fixture de 0.1.0 guarda `.specify/planes/PLAN-001.json` y
`.specify/tareas/TASKS-PLAN-001.json` sin sus `.md`, pero regenerarlos con
`--force` mueve el estado (el proyecto salta a Arquitectura 0/18 y deja de
servir para probar la vista). Esto los reescribe con los mismos renderizadores
que usa la CLI, sin tocar nada más.

Uso: python3 scripts/materializar_md.py RAIZ
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parent.parent
if str(RAIZ_REPO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPO))  # la CLI vive en el repo, no en el proyecto

from cli.commands import plan as mod_plan  # noqa: E402
from cli.commands import tasks as mod_tasks  # noqa: E402
from core.plan import render_markdown as render_plan  # noqa: E402
from core.tasks import render_markdown as render_tareas  # noqa: E402
from state import store  # noqa: E402


def _escribir(ruta: Path, texto: str) -> bool:
    """Escribe solo si cambia; devuelve si tocó el archivo."""
    if ruta.exists() and ruta.read_text(encoding="utf-8") == texto:
        return False
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    return True


def _planes(raiz: Path) -> list[Path]:
    carpeta = raiz / store.SPECIFY_DIR / "planes"
    return sorted(carpeta.glob("PLAN-*.json")) if carpeta.is_dir() else []


def _tareas(raiz: Path) -> list[Path]:
    carpeta = raiz / store.SPECIFY_DIR / "tareas"
    return sorted(carpeta.glob("TASKS-*.json")) if carpeta.is_dir() else []


def materializar(raiz: Path) -> list[str]:
    """Escribe los `.md` que falten; devuelve sus rutas relativas al proyecto."""
    escritos: list[str] = []

    for archivo in _planes(raiz):
        plan_id = archivo.stem
        try:
            plan = mod_plan._cargar_plan(raiz, plan_id)
        except Exception as error:  # noqa: BLE001 — uno ilegible no frena el resto
            print(f"· {plan_id}: no se pudo leer ({error})")
            continue
        destino = archivo.with_suffix(".md")
        if _escribir(destino, render_plan(plan) + "\n"):
            escritos.append(str(destino.relative_to(raiz)))

    for archivo in _tareas(raiz):
        plan_id = archivo.stem.removeprefix("TASKS-")
        try:
            carga = mod_tasks._cargar_tareas(raiz, plan_id)
        except Exception as error:  # noqa: BLE001
            print(f"· TASKS-{plan_id}: no se pudieron leer ({error})")
            continue
        if isinstance(carga, tuple) and len(carga) == 2:
            cabecera, tareas = carga
        else:
            cabecera, tareas = {}, carga
        cabecera = cabecera if isinstance(cabecera, dict) else {}
        texto = render_tareas(tareas, cabecera.get("plan", plan_id),
                              cabecera.get("spec", ""))
        destino = archivo.with_suffix(".md")
        if _escribir(destino, texto + "\n"):
            escritos.append(str(destino.relative_to(raiz)))

    return escritos


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("uso: materializar_md.py RAIZ", file=sys.stderr)
        return 2
    raiz = Path(argv[0]).resolve()
    if not raiz.is_dir():
        print(f"⛔ no existe la carpeta {raiz}", file=sys.stderr)
        return 1
    escritos = materializar(raiz)
    if not escritos:
        print("· sin .md que materializar")
        return 0
    for relativa in escritos:
        print(f"· {relativa} materializado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
