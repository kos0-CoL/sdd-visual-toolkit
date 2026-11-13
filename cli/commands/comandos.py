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
    rotas = agent_commands.rutas_muertas(raiz)
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


def _verificar_cliente(raiz: pathlib.Path, cliente: str) -> int:
    """Comprueba que los archivos generados para un cliente existan y tengan
    la ruta absoluta correcta de la CLI.

    Devuelve 0 si todo está bien, 1 si hay archivos faltantes o rutas muertas.
    """
    if cliente not in agent_commands.CLIENTES:
        print(f"⛔ cliente desconocido: {cliente}")
        print(f"   clientes soportados: {', '.join(sorted(agent_commands.CLIENTES))}")
        return 1
    plantilla = agent_commands.CLIENTES[cliente]
    carpeta = raiz / plantilla.split("{nombre}")[0]
    cli_actual = str(_cli_actual())
    problemas = 0
    if not carpeta.is_dir():
        print(f"⛔ {cliente}: no hay carpeta de comandos ({carpeta})")
        print(f"   genere con: {_sugerencia()} --cliente {cliente}")
        return 1
    for ruta in sorted(carpeta.rglob("*.md")):
        try:
            contenido = ruta.read_text(encoding="utf-8")
        except OSError:
            problemas += 1
            print(f"⛔ {ruta}: ilegible")
            continue
        if cli_actual not in contenido:
            problemas += 1
            print(f"⛔ {ruta}: ruta de CLI desactualizada o ausente")
    if problemas:
        print(f"  regenere con: {_sugerencia()} --cliente {cliente}")
        return 1
    cuantos = sum(1 for _ in carpeta.rglob("*.md"))
    print(f"🟢 {cliente}: {cuantos} archivo(s) de comando en {plantilla}; rutas correctas")
    return 0


def despachar(args) -> int:
    raiz = _raiz(args)
    if getattr(args, "verificar", False):
        return _verificar(raiz)
    if getattr(args, "verificar_cliente", None):
        return _verificar_cliente(raiz, args.verificar_cliente)
    clientes = list(getattr(args, "cliente", None) or [])
    if getattr(args, "regenerar", False):
        # Solo los clientes que ya tienen archivos: regenerar no debe estrenar
        # carpetas que el usuario nunca pidió.
        clientes = sorted(agent_commands.instalados(raiz))
        if not clientes and agent_commands.retirados(raiz):
            # Proyecto escrito por una versión que aún generaba los
            # `.prompt.md`: se regenera la skill y de paso se retira el prompt.
            clientes = ["copilot"]
        if not clientes:
            print("⛔ no hay comandos de barra que regenerar en este proyecto")
            print(f"  genérelos con: {_sugerencia()} --cliente copilot")
            return 1
    if not clientes:
        clientes = list(agent_commands.CLIENTES)
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
            plantilla = agent_commands.CLIENTES[cliente]
            cuantos = sum(1 for relativa in archivos if relativa.startswith(
                plantilla.split("{nombre}")[0]))
            print(f"🧩 {cliente}: {cuantos} comando(s) en {plantilla}")
        if getattr(args, "regenerar", False):
            borrados = agent_commands.retirar(raiz)
            if borrados:
                carpeta = borrados[0].parent.relative_to(raiz)
                print(f"🧹 {len(borrados)} archivo(s) del formato anterior "
                      f"borrados ({carpeta}/)")
    except (ValueError, OSError) as error:
        print(f"⛔ {error}")
        return 1
    print(f"✓ Comandos de barra instalados en {raiz}")
    return 0
