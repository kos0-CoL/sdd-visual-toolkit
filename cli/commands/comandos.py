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


def _cli_actual() -> pathlib.Path:
    """El `cli/main.py` de la copia del toolkit que está corriendo."""
    return pathlib.Path(__file__).resolve().parents[2] / "cli" / "main.py"


def _sugerencia() -> str:
    """Orden para regenerar, lista para copiar."""
    return f'{sys.executable or "python3"} "{_cli_actual()}" comandos'


def _verificar(raiz: pathlib.Path) -> int:
    """Comprueba que las rutas horneadas en las skills sigan existiendo.

    No genera nada: solo lee lo que hay. Una ruta muerta significa que el
    toolkit se movió (o se borró) y el agente ejecutaría un archivo que ya no
    está, así que el aviso tiene que decir cuál es y cómo arreglarlo.
    """
    generados = agent_commands.instalados(raiz)
    total = sum(len(archivos) for archivos in generados.values())
    if not total:
        print("· sin comandos de barra en este proyecto")
        print(f"  genérelos con: {_sugerencia()}")
        return 0
    rotas: dict[str, int] = {}
    for archivos in generados.values():
        for cli in archivos.values():
            if not pathlib.Path(cli).is_file():
                rotas[cli] = rotas.get(cli, 0) + 1
    if not rotas:
        print(f"🟢 COMANDOS AL DÍA: {total} archivo(s) de "
              f"{len(generados)} cliente(s); sus rutas existen")
        return 0
    for ruta, cuantos in sorted(rotas.items(), key=lambda par: (-par[1], par[0])):
        print(f"⛔ {cuantos} archivo(s) apuntan a una ruta que ya no existe:")
        print(f"   {ruta}")
    print(f"  este toolkit está en: {_cli_actual()}")
    print(f"  regenere con: {_sugerencia()}")
    return 1


def despachar(args) -> int:
    raiz = _raiz(args)
    if getattr(args, "verificar", False):
        return _verificar(raiz)
    clientes = getattr(args, "cliente", None) or list(agent_commands.CLIENTES)
    # El proyecto del usuario no tiene la CLI dentro: se hornea su ruta
    # absoluta, igual que la extensión necesita `sddToolkit.cliPath`.
    cli = _cli_actual()
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
