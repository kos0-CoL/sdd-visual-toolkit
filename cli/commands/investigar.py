"""Comandos `toolkit investigar` — RF-08 (§8.2, §44 item 5).

Investiga el repositorio real sin exigir clarify ni generar un plan:
estructura, lenguajes, dependencias, persistencia, pruebas y
convenciones. Solo lectura; reutiliza `core.plan.investigar`.
"""

from __future__ import annotations

import pathlib

from core.plan import investigar as investigar_repo
from core.repo import render


def _raiz(args) -> pathlib.Path:
    # La investigación es previa a todo (vale en greenfield sin init).
    if getattr(args, "root", None):
        return pathlib.Path(args.root)
    return pathlib.Path.cwd()


def despachar(args) -> int:
    raiz = _raiz(args)
    if not raiz.is_dir():
        print(f"⛔ no existe el directorio: {raiz}")
        return 1
    print(render(investigar_repo(raiz)))
    print("¿Qué desea hacer ahora?")
    print("[ tablero ]  [ status ]")
    return 0
