"""CLI del toolkit (§31). Interfaz completa e independiente del IDE."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli.commands import enrich as cmd_enrich  # noqa: E402
from cli.commands import clarify as cmd_clarify  # noqa: E402
from cli.commands import comandos as cmd_comandos  # noqa: E402
from cli.commands import investigar as cmd_investigar  # noqa: E402
from cli.commands import instrucciones as cmd_instrucciones  # noqa: E402
from cli.commands import hooks as cmd_hooks  # noqa: E402
from cli.commands import plan as cmd_plan  # noqa: E402
from cli.commands import analyze as cmd_analyze  # noqa: E402
from cli.commands import build as cmd_build  # noqa: E402
from cli.commands import checkpoint as cmd_checkpoint  # noqa: E402
from cli.commands import ast as cmd_ast  # noqa: E402
from cli.commands import test as cmd_test  # noqa: E402
from cli.commands import validate as cmd_validate  # noqa: E402
from cli.commands import context as cmd_context  # noqa: E402
from cli.commands import flush as cmd_flush  # noqa: E402
from cli.commands import rollback as cmd_rollback  # noqa: E402
from cli.commands import journal as cmd_journal  # noqa: E402
from cli.commands import pin as cmd_pin  # noqa: E402
from cli.commands import recover as cmd_recover  # noqa: E402
from cli.commands import report as cmd_report  # noqa: E402
from cli.commands import traza as cmd_traza  # noqa: E402
from cli.commands import historia as cmd_historia  # noqa: E402
from cli.commands import tablero as cmd_tablero  # noqa: E402
from cli.commands import arbol as cmd_arbol  # noqa: E402
from cli.commands import restricciones as cmd_restricciones  # noqa: E402
from cli.commands import diff as cmd_diff  # noqa: E402
from cli.commands import siguiente as cmd_siguiente  # noqa: E402
from cli.commands import status as cmd_status  # noqa: E402
from cli.commands import cierre as cmd_cierre  # noqa: E402
from cli.commands import export as cmd_export  # noqa: E402
from cli.commands import tasks as cmd_tasks  # noqa: E402
from cli.commands import specify as cmd_specify  # noqa: E402
from core.requirements import (  # noqa: E402
    ACEPTADO,
    ESTADOS,
    PROCEDENCIAS,
    RegistroRequerimientos,
    RequerimientoError,
)
from state import store  # noqa: E402
from core import ide_entorno  # noqa: E402
from core.version import version as version_herramienta  # noqa: E402


def _raiz(args) -> Path:
    if getattr(args, "root", None):
        return store.descubrir_raiz(Path(args.root))
    return store.descubrir_raiz()


def _registro(raiz: Path) -> RegistroRequerimientos:
    ruta = store.ruta_requerimientos(raiz)
    if not ruta.exists():
        return RegistroRequerimientos()
    return RegistroRequerimientos.from_list(store.leer_json(ruta))


def _guardar(raiz: Path, registro: RegistroRequerimientos) -> None:
    store.escribir_json(store.ruta_requerimientos(raiz), registro.to_list())


def _proyecto_superior(destino: Path) -> Path | None:
    """Proyecto toolkit ya inicializado por encima de `destino`, si lo hay.

    `descubrir_raiz` sube hasta el `.specify/` más cercano, así que un segundo
    estado dentro del primero dejaría dos raíces contradictorias.
    """
    for candidato in destino.parents:
        if (candidato / store.SPECIFY_DIR).is_dir():
            return candidato
    return None


def _clientes_de_init(args) -> list[str] | None:
    """Clientes del agente a generar al inicializar, o `None`.

    Con `--cliente` no se pregunta. Sin él solo se pregunta si hay terminal:
    `init` también corre desde la extensión, un hook o un script, donde un
    `input()` dejaría la ejecución colgada esperando a nadie.
    """
    if getattr(args, "cliente", None):
        return list(args.cliente)
    if getattr(args, "sin_comandos", False) or not sys.stdin.isatty():
        return None
    disponibles = sorted(cmd_comandos.agent_commands.CLIENTES)
    # Sin línea en blanco después: en un terminal el Enter ya abre el renglón
    # del eco. Una captura sin eco (pty con stdin canalizado) lo deja pegado a
    # la pregunta, que es el precio de no ensuciar la salida interactiva.
    print(f"Cliente del agente ({', '.join(disponibles)}; «todos» o vacío ="
          " ninguno): ", end="", flush=True)
    try:
        respuesta = input().strip().lower()
    except EOFError:
        print()
        return None
    # La elección se deja escrita: en un registro o una captura, lo tecleado
    # en el prompt no aparece y no se sabría qué se generó.
    if not respuesta:
        print("· cliente: ninguno (sin comandos de barra)")
        return None
    if respuesta in ("todos", "all"):
        print(f"· cliente: todos ({', '.join(disponibles)})")
        return disponibles
    elegidos = respuesta.replace(",", " ").split()
    desconocidos = [c for c in elegidos
                    if c not in cmd_comandos.agent_commands.CLIENTES]
    if desconocidos:
        print(f"· cliente(s) desconocido(s): {', '.join(desconocidos)};"
              " no se generaron comandos de barra")
        return None
    print(f"· cliente: {', '.join(elegidos)}")
    return elegidos


def cmd_init(args) -> int:
    # `--root` es la opción global de todos los comandos (la extensión de VS
    # Code la pasa siempre); init la ignoraba y creaba .specify/ en la carpeta
    # actual. El path posicional, más específico, sigue mandando si se da.
    destino = Path(args.path or getattr(args, "root", None) or ".").resolve()
    superior = _proyecto_superior(destino)
    if superior is not None:
        print(f"⛔ YA HAY UN PROYECTO TOOLKIT POR ENCIMA: {superior}")
        print("  no se crea .specify/ anidado: desde aquí ya mandan sus comandos.")
        return 1
    raiz = store.inicializar_proyecto(destino)
    cli = Path(__file__).resolve()
    # La capa visual (§29): sin esto la extensión no sabe qué `cli/main.py`
    # ejecutar y las tareas SDD no aparecen al abrir la carpeta en el IDE.
    escritos, existentes, añadidas = ide_entorno.preparar(
        raiz, cli, sys.executable or "python3")
    print(f"🟢 PROYECTO INICIALIZADO: {raiz}")
    print("Estado:")
    print("✓ .specify/ (memoria con estado e historial, checkpoints)")
    print("✓ .specify/planes/ .specify/tareas/ .specify/informes/")
    print("✓ specs/ (SPEC-001.md y su .json)")
    del_ide = [n for n in escritos if n.startswith(f"{ide_entorno.CARPETA}/")]
    if del_ide:
        print(f"✓ {', '.join(del_ide)} (ruta del toolkit y tareas SDD)")
    if ide_entorno.GITIGNORE in escritos:
        print("✓ .gitignore (ajustes y caché de esta máquina)")
    for nombre in existentes:
        print(f"· {nombre} ya existía: no se tocó")
    # Si el `.gitignore` existía y le faltaban reglas, se añaden y se dice
    # cuáles; el resto del archivo queda como estaba.
    if añadidas:
        print(f"✓ {ide_entorno.GITIGNORE}: añadidas las reglas que faltaban")
        for regla in añadidas:
            print(f"    {regla}")
    # Los comandos de barra son lo único que `init` no dejaba listo: sin ellos
    # el agente no ve `/sdd-*`. Se generan aquí si el usuario ya dijo el
    # cliente (o lo eligió en la pregunta); si no, se deja la orden a mano.
    clientes = _clientes_de_init(args)
    if clientes:
        cmd_comandos.despachar(argparse.Namespace(
            root=str(raiz), cliente=clientes, verificar=False))
    else:
        print("Comandos para su agente (opcional, repetible):")
        print(f"  {sys.executable or 'python3'} \"{cli}\" comandos"
              " --cliente copilot")
        print("  sin --cliente escribe todos; la ruta absoluta queda"
              " grabada, así que vuelva a ejecutarlo si mueve el repositorio.")
    print("¿Qué desea hacer ahora?")
    print("[ req add ]  [ status ]  [ comandos ]")
    return 0


def cmd_req_add(args) -> int:
    raiz = _raiz(args)
    registro = _registro(raiz)
    try:
        req = registro.agregar(args.texto, args.procedencia)
        _guardar(raiz, registro)
    except RequerimientoError as error:
        print(f"⛔ {error}")
        return 1
    print(f"🟢 REQUERIMIENTO REGISTRADO: {req.id}")
    print(f"  texto: {req.texto}")
    print(f"  procedencia: {req.procedencia} | estado: {req.estado}")
    return 0


def cmd_req_list(args) -> int:
    raiz = _raiz(args)
    try:
        items = _registro(raiz).listar(
            procedencia=args.procedencia, estado=args.estado
        )
    except RequerimientoError as error:
        print(f"⛔ {error}")
        return 1
    if not items:
        print("Sin requerimientos registrados.")
        return 0
    for req in items:
        marca = {"pendiente": "○", "aceptado": "✓", "rechazado": "✗"}[req.estado]
        print(f"{marca} {req.id} [{req.procedencia}] {req.texto}")
    print(f"— {len(items)} requerimiento(s)")
    return 0


def cmd_req_show(args) -> int:
    raiz = _raiz(args)
    try:
        req = _registro(raiz).obtener(args.req_id)
    except RequerimientoError as error:
        print(f"⛔ {error}")
        return 1
    print(f"{req.id}")
    print(f"  texto: {req.texto}")
    print(f"  procedencia: {req.procedencia}")
    print(f"  estado: {req.estado}")
    print(f"  creado: {req.creado_en} | actualizado: {req.actualizado_en}")
    print(f"  spec: {req.spec_id or '—'}")
    return 0


def cmd_req_set(args) -> int:
    raiz = _raiz(args)
    registro = _registro(raiz)
    try:
        req = registro.cambiar_estado(args.req_id, args.estado)
        _guardar(raiz, registro)
    except (RequerimientoError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    print(f"🟢 {req.id} → {req.estado}")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="toolkit", description="SDD Visual Toolkit")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {version_herramienta()}")
    parser.add_argument("--root", default=None, help="ruta del proyecto")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_init = sub.add_parser("init", help="inicializar proyecto")
    p_init.add_argument("path", nargs="?", default=None,
                        help="destino (por defecto, --root o la carpeta actual)")
    p_init.add_argument(
        "--cliente", action="append", default=None,
        choices=sorted(cmd_comandos.agent_commands.CLIENTES),
        help=("repetible: genera los comandos del agente ahora mismo; "
              "sin él se pregunta cuando hay terminal"))
    p_init.add_argument(
        "--sin-comandos", action="store_true",
        help="no preguntar ni generar comandos de barra")
    p_init.set_defaults(func=cmd_init)

    p_req = sub.add_parser("req", help="gestionar requerimientos (RF-01)")
    sub_req = p_req.add_subparsers(dest="sub", required=True)

    p_add = sub_req.add_parser("add", help="registrar requerimiento")
    p_add.add_argument("texto")
    p_add.add_argument("--procedencia", default="explicito", choices=PROCEDENCIAS)
    p_add.set_defaults(func=cmd_req_add)

    p_list = sub_req.add_parser("list", help="listar requerimientos")
    p_list.add_argument("--procedencia", default=None, choices=PROCEDENCIAS)
    p_list.add_argument("--estado", default=None, choices=ESTADOS)
    p_list.set_defaults(func=cmd_req_list)

    p_show = sub_req.add_parser("show", help="mostrar requerimiento")
    p_show.add_argument("req_id")
    p_show.set_defaults(func=cmd_req_show)

    p_set = sub_req.add_parser("set", help="cambiar estado")
    p_set.add_argument("req_id")
    p_set.add_argument("--estado", required=True, choices=ESTADOS)
    p_set.set_defaults(func=cmd_req_set)

    p_enrich = sub.add_parser("enrich", help="enriquecer idea inicial (RF-02)")
    # `toolkit enrich "idea"` analiza; las gestiones van con flags para no
    # ambiguar con el texto libre de la idea.
    p_enrich.add_argument("texto", nargs="?", default=None)
    p_enrich.add_argument("--list", action="store_true")
    p_enrich.add_argument("--show", default=None, metavar="ENR-ID")
    p_enrich.add_argument("--drop", nargs="+", default=None, metavar="ENR-ID")
    p_enrich.add_argument("--accept", default=None, metavar="ENR-ID")
    p_enrich.set_defaults(func=cmd_enrich.despachar)

    p_specify = sub.add_parser("specify", help="generar SPEC (RF-03)")
    p_specify.add_argument("texto", nargs="?", default=None, help="ENR-ID validado")
    p_specify.add_argument("--titulo", default=None)
    p_specify.add_argument("--list", action="store_true")
    p_specify.add_argument("--show", default=None, metavar="SPEC-ID")
    p_specify.add_argument("--approve", default=None, metavar="SPEC-ID")
    p_specify.add_argument("--revise", default=None, metavar="SPEC-ID")
    p_specify.add_argument("--motivo", default=None)
    p_specify.set_defaults(func=cmd_specify.despachar)

    p_clarify = sub.add_parser("clarify", help="aclarar SPEC (RF-04)")
    p_clarify.add_argument("texto", nargs="?", default=None, help="SPEC-ID")
    p_clarify.add_argument("--answer", nargs=2, action="append", default=None,
                           metavar=("CLA-ID", "RESPUESTA"))
    p_clarify.add_argument("--skip", action="append", default=None, metavar="CLA-ID")
    p_clarify.add_argument("--list", default=None, metavar="SPEC-ID")
    p_clarify.add_argument("--gate", action="store_true")
    p_clarify.set_defaults(func=cmd_clarify.despachar)

    p_inv = sub.add_parser("investigar",
                           help="investigar el repositorio (RF-08)")
    p_inv.set_defaults(func=cmd_investigar.despachar)

    p_instr = sub.add_parser("instrucciones",
                             help="archivo de instrucciones del agente (RF-41)")
    p_instr.add_argument("--guardar", action="store_true",
                         help="persistir en .specify/INSTRUCCIONES.md")
    p_instr.set_defaults(func=cmd_instrucciones.despachar)

    p_hooks = sub.add_parser("hooks",
                             help="hooks de agente por evento (RF-42)")
    p_hooks.set_defaults(func=cmd_hooks.despachar)

    p_plan = sub.add_parser("plan", help="plan técnico (RF-05)")
    p_plan.add_argument("texto", nargs="?", default=None, help="SPEC-ID")
    p_plan.add_argument("--force", action="store_true")
    p_plan.add_argument("--list", action="store_true")
    p_plan.add_argument("--show", default=None, metavar="PLAN-ID")
    p_plan.add_argument("--gate", default=None, metavar="PLAN-ID")
    p_plan.set_defaults(func=cmd_plan.despachar)

    p_tasks = sub.add_parser("tasks", help="desglose en tareas (RF-06)")
    p_tasks.add_argument("texto", nargs="?", default=None, help="PLAN-ID")
    p_tasks.add_argument("--force", action="store_true")
    p_tasks.add_argument("--list", nargs="?", const="all", default=None,
                         metavar="PLAN-ID")
    p_tasks.add_argument("--show", default=None, metavar="TASK-ID")
    p_tasks.add_argument("--gate", default=None, metavar="PLAN-ID")
    p_tasks.set_defaults(func=cmd_tasks.despachar)

    p_analyze = sub.add_parser("analyze", help="informe de consistencia (RF-07)")
    p_analyze.add_argument("texto", nargs="?", default=None, help="PLAN-ID")
    p_analyze.add_argument("--gate", default=None, metavar="PLAN-ID")
    p_analyze.set_defaults(func=cmd_analyze.despachar)

    p_build = sub.add_parser("build", help="ejecución guiada (RF-09)")
    p_build.add_argument("texto", nargs="?", default=None,
                         help="PLAN-ID; opcional con --done/--fail, se deduce de la tarea")
    p_build.add_argument("--done", default=None, metavar="TASK-ID")
    p_build.add_argument("--fail", default=None, metavar="TASK-ID")
    p_build.add_argument("--nota", default="")
    p_build.set_defaults(func=cmd_build.despachar)

    p_pin = sub.add_parser("pin", help="spec pinning (RF-10)")
    p_pin.add_argument("texto", nargs="?", default=None, help="PLAN-ID")
    p_pin.add_argument("--task", default=None, metavar="TASK-ID")
    p_pin.add_argument("--check", default=None, metavar="TASK-ID")
    p_pin.add_argument("--suggest", default=None, metavar="IDEA")
    p_pin.set_defaults(func=cmd_pin.despachar)

    p_journal = sub.add_parser("journal", help="memoria operativa (RF-11)")
    p_journal.add_argument("texto", nargs="?", default=None, help="PLAN-ID")
    p_journal.add_argument("--history", default=None, metavar="PLAN-ID")
    p_journal.add_argument("-n", type=int, default=0)
    p_journal.add_argument("--state", action="store_true")
    p_journal.set_defaults(func=cmd_journal.despachar)

    p_recover = sub.add_parser("recover", help="recuperar sesión (RF-13)")
    p_recover.add_argument("texto", nargs="?", default=None, help="PLAN-ID")
    p_recover.set_defaults(func=cmd_recover.despachar)

    p_checkpoint = sub.add_parser("checkpoint", help="checkpoints (RF-12)")
    p_checkpoint.add_argument("texto", nargs="?", default=None)
    p_checkpoint.add_argument("--list", default=None, metavar="PLAN-ID")
    p_checkpoint.add_argument("--show", default=None, metavar="TASK-ID")
    p_checkpoint.set_defaults(func=cmd_checkpoint.despachar)

    p_context = sub.add_parser("context", help="contexto por modos (RF-14)")
    p_context.add_argument("texto", nargs="?", default=None, help="TASK-ID")
    p_context.add_argument("--modo", default="implementacion",
                           help="requerimientos|arquitectura|implementacion|pruebas|recuperacion")
    p_context.set_defaults(func=cmd_context.despachar)

    p_flush = sub.add_parser("flush", help="renovar contexto (RF-15)")
    p_flush.add_argument("texto", nargs="?", default=None, help="PLAN-ID")
    p_flush.add_argument("--umbral", type=int, default=None)
    p_flush.add_argument("--force", action="store_true")
    p_flush.add_argument("--motivo", default=None)
    p_flush.set_defaults(func=cmd_flush.despachar)

    p_rollback = sub.add_parser("rollback", help="snapshots por tarea (RF-16)")
    p_rollback.add_argument("texto", nargs="?", default=None)
    p_rollback.add_argument("--list", default=None, metavar="TASK-ID")
    p_rollback.add_argument("--restore", default=None, metavar="TASK-ID")
    p_rollback.add_argument("--n", type=int, default=None)
    p_rollback.set_defaults(func=cmd_rollback.despachar)

    p_ast = sub.add_parser("ast", help="chequeo estructural (RF-17)")
    p_ast.add_argument("texto", nargs="?", default=None, help="TASK-ID")
    p_ast.set_defaults(func=cmd_ast.despachar)

    p_validate = sub.add_parser("validate", help="validación de cambios (RF-18)")
    p_validate.add_argument("texto", nargs="?", default=None, help="TASK-ID")
    p_validate.add_argument("--nota", default=None)
    p_validate.set_defaults(func=cmd_validate.despachar)

    p_test = sub.add_parser("test", help="arnés de testing (RF-19)")
    p_test.add_argument("texto", nargs="?", default=None, help="TASK-ID")
    p_test.add_argument("--fase", action="append", default=None,
                        help=("repetible: unitarios|integración|regresión|"
                              "cobertura|aceptación|estructural"))
    p_test.set_defaults(func=cmd_test.despachar)

    p_report = sub.add_parser("reporte", help="resultados visibles (RF-26)")
    p_report.add_argument("texto", nargs="?", default=None, help="TASK-ID")
    p_report.add_argument("--history", default=None, metavar="PLAN-ID")
    p_report.add_argument("-n", type=int, default=0)
    p_report.set_defaults(func=cmd_report.despachar)

    p_traza = sub.add_parser("traza", help="trazabilidad SPEC→evidencia (RF-29)")
    p_traza.add_argument("texto", nargs="?", default=None, help="SPEC-ID")
    p_traza.set_defaults(func=cmd_traza.despachar)

    p_historia = sub.add_parser("historia",
                                help="historial de la tarea (RF-30)")
    p_historia.add_argument("texto", nargs="?", default=None,
                            help="TASK-ID")
    p_historia.set_defaults(func=cmd_historia.despachar)

    p_tablero = sub.add_parser("tablero",
                               help="panel de estado general (RF-31)")
    p_tablero.set_defaults(func=cmd_tablero.despachar)

    p_arbol = sub.add_parser("arbol", help="árbol de estados (RF-32)")
    p_arbol.set_defaults(func=cmd_arbol.despachar)

    p_restr = sub.add_parser("restricciones",
                             help="panel de restricciones (RF-33)")
    p_restr.add_argument("texto", nargs="?", default=None,
                         help="SPEC-ID o TASK-ID (opcional)")
    p_restr.set_defaults(func=cmd_restricciones.despachar)

    p_diff = sub.add_parser("diff", help="visual AST diff (RF-34)")
    p_diff.add_argument("texto", nargs="?", default=None, help="TASK-ID")
    p_diff.add_argument("--n", type=int, default=None,
                        help="número de snapshot (0 = previo)")
    p_diff.set_defaults(func=cmd_diff.despachar)

    p_sig = sub.add_parser("siguiente",
                           help="navegación por píldoras (RF-35)")
    p_sig.set_defaults(func=cmd_siguiente.despachar)

    p_status = sub.add_parser("status",
                              help="estado + siguiente (RF-36)")
    p_status.set_defaults(func=cmd_status.despachar)

    p_cierre = sub.add_parser("cierre",
                              help="mensaje final de fase (RF-37)")
    p_cierre.add_argument("texto", nargs="?", default=None,
                          help="TASK-ID o PLAN-ID (opcional)")
    p_cierre.set_defaults(func=cmd_cierre.despachar)

    p_export = sub.add_parser("export",
                              help="foto JSON para IDE/MCP (RF-38)")
    p_export.set_defaults(func=cmd_export.despachar)

    p_comandos = sub.add_parser(
        "comandos", help="comandos de barra para agentes (§31)")
    p_comandos.add_argument(
        "--cliente", action="append", default=None,
        choices=sorted(cmd_comandos.agent_commands.CLIENTES),
        help=("repetible: claude|cursor|copilot|windsurf|antigravity; "
              "sin él, todos"))
    p_comandos.add_argument(
        "--verificar", action="store_true",
        help="solo revisar que las rutas grabadas sigan existiendo")
    p_comandos.add_argument(
        "--regenerar", action="store_true",
        help="reescribir solo los clientes ya instalados, con la ruta actual")
    p_comandos.set_defaults(func=cmd_comandos.despachar)

    p_impl = sub.add_parser("implement", help="alias de build (RF-36)")
    p_impl.add_argument("texto", nargs="?", default=None,
                        help="PLAN-ID; opcional con --done/--fail, se deduce de la tarea")
    p_impl.add_argument("--done", default=None, metavar="TASK-ID")
    p_impl.add_argument("--fail", default=None, metavar="TASK-ID")
    p_impl.add_argument("--nota", default="")
    p_impl.set_defaults(func=cmd_build.despachar)

    p_history = sub.add_parser("history", help="alias de historia (RF-36)")
    p_history.add_argument("texto", nargs="?", default=None, help="TASK-ID")
    p_history.set_defaults(func=cmd_historia.despachar)

    p_specs = sub.add_parser("specs", help="alias de specify --list (RF-36)")
    sub_specs = p_specs.add_subparsers(dest="sub_specs", required=True)
    p_specs_list = sub_specs.add_parser("list", help="listar SPECs")
    p_specs_list.set_defaults(func=cmd_specify.despachar, list=True,
                              show=None, approve=None, revise=None,
                              motivo=None, texto=None)

    return parser


def main(argv=None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (RequerimientoError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
