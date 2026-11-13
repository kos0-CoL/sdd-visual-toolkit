"""Comandos `toolkit enrich` — RF-02 (§5)."""

from __future__ import annotations

from core.enrich import (
    PENDIENTE_VALIDACION,
    Enriquecimiento,
    EnriquecimientoError,
    RegistroEnriquecimientos,
)
from core.requirements import RegistroRequerimientos
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(__import__("pathlib").Path(args.root))
    return store.descubrir_raiz()


def _registro(raiz) -> RegistroEnriquecimientos:
    ruta = raiz / store.SPECIFY_DIR / "enriquecimientos.json"
    if not ruta.exists():
        return RegistroEnriquecimientos()
    return RegistroEnriquecimientos.from_list(store.leer_json(ruta))


def _guardar(raiz, registro: RegistroEnriquecimientos) -> None:
    store.escribir_json(
        raiz / store.SPECIFY_DIR / "enriquecimientos.json", registro.to_list()
    )


def _registro_req(raiz) -> RegistroRequerimientos:
    ruta = store.ruta_requerimientos(raiz)
    if not ruta.exists():
        return RegistroRequerimientos()
    return RegistroRequerimientos.from_list(store.leer_json(ruta))


TITULOS = {
    "objetivo": "🎯 Objetivo",
    "entidad": "📦 Entidades potenciales (inferido)",
    "funcionalidad": "⚙️ Funcionalidades",
    "mejora": "💡 Mejoras / sugerencias",
    "faltante": "❓ Falta información (desconocido)",
    "exclusion": "🚫 Fuera de alcance inicial",
    "regla": "📏 Posibles reglas de negocio (inferido)",
    "restriccion": "🔒 Restricciones",
}


def mostrar(enr: Enriquecimiento) -> None:
    estado = "pendiente de validación" if enr.estado == PENDIENTE_VALIDACION else "validado"
    print(f"🌀 ENRIQUECIMIENTO {enr.id} ({estado}) — dominio: {enr.dominio}")
    print(f'Idea original: "{enr.entrada}"')
    for seccion in (
        "objetivo", "entidad", "funcionalidad", "mejora",
        "regla", "restriccion", "faltante", "exclusion",
    ):
        items = enr.por_seccion(seccion)
        if not items:
            continue
        print(f"\n{TITULOS[seccion]}:")
        for item in items:
            print(f"  [{item.item_id}] ({item.procedencia}) {item.texto}")


def cmd_enrich(args) -> int:
    raiz = _raiz(args)
    registro = _registro(raiz)
    try:
        enr = registro.agregar(args.texto)
        _guardar(raiz, registro)
    except (EnriquecimientoError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    mostrar(enr)
    # Mensaje final de fase §27.
    print("\n🟢 FASE COMPLETADA: ENRICH")
    print(f"Archivo generado: .specify/enriquecimientos.json ({enr.id})")
    print("Validaciones: todo lo inferido/sugerido nace pendiente; nada se aprobó solo.")
    print("Problemas pendientes: responda lo marcado como desconocido.")
    print("Estado persistido: sí.")
    print("¿Qué desea hacer ahora?")
    print(f"[ enrich --accept {enr.id} ]  [ enrich --drop {enr.id} <id-item> ]  [ req list ]")
    return 0


def despachar(args) -> int:
    """`enrich "idea"` analiza; los flags gestionan lo existente."""
    if args.list:
        return cmd_enrich_list(args)
    if args.show:
        args.enr_id = args.show
        return cmd_enrich_show(args)
    if args.drop:
        args.enr_id, args.items = args.drop[0], args.drop[1:]
        if not args.items:
            print("⛔ indique al menos un id de elemento para podar")
            return 1
        return cmd_enrich_drop(args)
    if args.accept:
        args.enr_id = args.accept
        return cmd_enrich_accept(args)
    if not args.texto:
        print("⛔ indique la idea entre comillas o use --list/--show/--drop/--accept")
        return 1
    return cmd_enrich(args)


def cmd_enrich_list(args) -> int:
    raiz = _raiz(args)
    for enr in _registro(raiz).listar():
        print(f"{enr.id} [{enr.estado}] ({len(enr.items)} elementos) {enr.objetivo}")
    return 0


def cmd_enrich_show(args) -> int:
    raiz = _raiz(args)
    try:
        mostrar(_registro(raiz).obtener(args.enr_id))
    except (EnriquecimientoError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0


def cmd_enrich_drop(args) -> int:
    raiz = _raiz(args)
    registro = _registro(raiz)
    try:
        enr = registro.obtener(args.enr_id)
        quitados = enr.quitar(args.items)
        # Podar el último elemento dejaba un ENR vacío que nadie puede usar:
        # se va con su último elemento.
        vacio = not enr.items
        if vacio:
            registro.quitar(enr.id)
        _guardar(raiz, registro)
    except (EnriquecimientoError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    for item in quitados:
        print(f"🗑️ {item.item_id} eliminado: {item.texto}")
    if vacio:
        print(f"🗑️ {enr.id} eliminado: se quedó sin elementos")
    return 0


def cmd_enrich_accept(args) -> int:
    raiz = _raiz(args)
    registro = _registro(raiz)
    try:
        enr = registro.obtener(args.enr_id)
        reqs = _registro_req(raiz)
        creados = enr.validar(reqs)
        store.escribir_json(store.ruta_requerimientos(raiz), reqs.to_list())
        _guardar(raiz, registro)
    except (EnriquecimientoError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    print(f"🟢 ENRIQUECIMIENTO VALIDADO: {enr.id}")
    print(f"Requerimientos creados: {len(creados)}")
    for req in creados:
        print(f"  {req.id} [{req.procedencia}/{req.estado}] {req.texto}")
    print("¿Qué desea hacer ahora?")
    print("[ req list ]  [ specify ]")
    return 0
