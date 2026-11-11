"""Comando `toolkit comandos` — comandos de barra para agentes (§31)."""

from __future__ import annotations

import pathlib
import sys

from core import agent_commands


def _raiz(args) -> pathlib.Path:
    """El proyecto donde vive el agente; no exige `.specify/` inicializado."""
    if getattr(args, "root", None):
        return pathlib.Path(args.root).resolve()
    return pathlib.Path.cwd()


def despachar(args) -> int:
    raiz = _raiz(args)
    clientes = getattr(args, "cliente", None) or list(agent_commands.CLIENTES)
    # El proyecto del usuario no tiene la CLI dentro: se hornea su ruta
    # absoluta, igual que la extensión necesita `sddToolkit.cliPath`.
    cli = pathlib.Path(__file__).resolve().parents[2] / "cli" / "main.py"
    try:
        for cliente in clientes:
            archivos = agent_commands.generar(cliente, sys.executable, cli)
            for relativa, contenido in archivos.items():
                ruta = raiz / relativa
                ruta.parent.mkdir(parents=True, exist_ok=True)
                ruta.write_text(contenido, encoding="utf-8")
            print(f"🧩 {cliente}: {len(archivos)} comando(s) en "
                  f"{agent_commands.CLIENTES[cliente]}")
    except (ValueError, OSError) as error:
        print(f"⛔ {error}")
        return 1
    print(f"✓ Comandos de barra instalados en {raiz}")
    return 0
