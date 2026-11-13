"""Comando `toolkit modo` — consulta y cambia el modo operativo (§A6).

Modos:
- gestor (por defecto): humano implementa, el motor verifica.
- orquestador: el motor puede sugerir cambios y cerrar con justificación.
"""

from __future__ import annotations

from pathlib import Path

from state import store


def _raiz(args) -> Path:
    if getattr(args, "root", None):
        return Path(args.root).resolve()
    return Path.cwd()


def despachar(args) -> int:
    raiz = _raiz(args)
    valor = getattr(args, "valor", None)
    if valor is not None:
        store.escribir_modo_operacion(raiz, valor)
        print(f"✓ modo operativo: {valor}")
        return 0
    actual = store.leer_modo_operacion(raiz)
    print(f"modo operativo actual: {actual}")
    return 0
