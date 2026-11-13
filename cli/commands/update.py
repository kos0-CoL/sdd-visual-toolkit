"""Comando `toolkit update` — verificar y aplicar actualizaciones del toolkit.

Nunca actualiza sin consentimiento explícito del usuario. El flujo es:

1. `update --verificar` consulta PyPI (solo lectura) y reporta si hay versión
   nueva. No instala nada ni toca ningún archivo del proyecto.
2. `update --aplicar` solo procede si hay versión nueva Y el usuario confirma.
   Actualiza el core instalado globalmente (`pip install -U`) y refresca los
   archivos del proyecto que dejó `sdd init` (.vscode/, .gitignore) para que
   apunten a la copia en uso.

Desde el panel integrado de VS Code se dispara con el mismo comando: el
usuario ve el aviso de versión nueva y decide si acepta o no.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

from core import ide_entorno
from core.version import verificar_actualizacion, version


def _raiz(args) -> pathlib.Path:
    if getattr(args, "root", None):
        return pathlib.Path(args.root).resolve()
    return pathlib.Path.cwd()


def _ejecutar_pip() -> tuple[int, str]:
    """Ejecuta `pip install -U sdd-toolkit`. Devuelve (código, salida)."""
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "sdd-toolkit"]
    try:
        resultado = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
        salida = (resultado.stdout or "") + (resultado.stderr or "")
        return resultado.returncode, salida
    except subprocess.TimeoutExpired:
        return 1, "pip install excedió el tiempo de espera (5 min)"
    except OSError as error:
        return 1, f"no se pudo ejecutar pip: {error}"


def despachar(args) -> int:
    raiz = _raiz(args)
    estado = verificar_actualizacion()
    instalada = estado["instalada"]
    disponible = estado["disponible"]
    error = estado["error"]

    if error:
        print(f"⛔ {error}")
        return 1

    print(f"📦 Versión instalada: {instalada}")
    if disponible is None:
        print("⚠️  No se pudo consultar la versión disponible en PyPI.")
        return 1

    print(f"📦 Última versión en PyPI: {disponible}")

    if not estado["hay_actualizacion"]:
        print("🟢 Ya tienes la versión más reciente. Nada que hacer.")
        return 0

    print(f"🆕 Hay una versión nueva disponible: {disponible}")

    if not getattr(args, "aplicar", False):
        print(
            "Para actualizar ejecuta: toolkit update --aplicar "
            "(o desde el panel de VS Code: SDD: Actualizar toolkit)"
        )
        return 0

    # --aplicar: confirmación explícita del usuario
    confirmado = getattr(args, "forzar", False)
    if not confirmado and sys.stdin.isatty():
        respuesta = input(
            f"¿Actualizar de {instalada} a {disponible}? (s/N): "
        ).strip().lower()
        confirmado = respuesta in ("s", "si", "sí", "y", "yes")

    if not confirmado:
        print("· actualización cancelada por el usuario")
        return 0

    # 1. Actualizar el core instalado globalmente
    print("⬇️  Actualizando el core (pip install -U sdd-toolkit)…")
    codigo, salida = _ejecutar_pip()
    print(salida)
    if codigo != 0:
        print(
            "⛔ No se pudo actualizar el core. Los archivos del proyecto no se tocaron."
        )
        return 1

    nueva = version()
    print(f"🟢 Core actualizado a {nueva}")

    # 2. Refrescar los archivos del proyecto que dejó `sdd init`
    cli = pathlib.Path(__file__).resolve()
    python = sys.executable or "python3"
    escritos, existentes, añadidas = ide_entorno.actualizar_ide(
        raiz, cli, python,
        gitignore=not getattr(args, "sin_gitignore", False))

    if escritos:
        print("✓ Archivos del proyecto actualizados:")
        for ruta in escritos:
            print(f"    {ruta}")
    if existentes:
        print("· Ya estaban al día:")
        for ruta in existentes:
            print(f"    {ruta}")
    if añadidas:
        print(f"✓ .gitignore: añadidas reglas que faltaban")
        for regla in añadidas:
            print(f"    {regla}")

    print("🟢 Proyecto actualizado a la versión más reciente del toolkit.")
    return 0
