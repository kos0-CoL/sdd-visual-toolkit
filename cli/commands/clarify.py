"""Comandos `toolkit clarify` — RF-04 (§7)."""

from __future__ import annotations

import argparse
import pathlib

from cli.commands import enrich as mod_enrich
from cli.commands import specify as mod_specify
from core.clarify import (
    PENDIENTE,
    ClarifyError,
    consolidar,
    detectar,
    pendientes,
    responder,
)
from core.spec import Spec, SpecError
from state import store

CLARIF_FILE = "clarifications.json"


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def _ruta(raiz) -> pathlib.Path:
    return raiz / store.SPECIFY_DIR / CLARIF_FILE


def _cargar_todo(raiz) -> dict:
    ruta = _ruta(raiz)
    if not ruta.exists():
        return {}
    datos = store.leer_json(ruta)
    if not isinstance(datos, dict):
        raise ClarifyError("el registro de clarificaciones está corrupto")
    return datos


def _guardar_todo(raiz, datos: dict) -> None:
    store.escribir_json(_ruta(raiz), datos)


def _preguntas_de(raiz, spec_id: str):
    from core.clarify import Pregunta  # noqa: PLC0415

    entrada = _cargar_todo(raiz).get(spec_id, {"preguntas": [], "historial": []})
    return [Pregunta.from_dict(p) for p in entrada["preguntas"]], entrada["historial"]


def _persistir(raiz, spec: Spec, preguntas, historial) -> None:
    from core.spec import render_markdown  # noqa: PLC0415

    todo = _cargar_todo(raiz)
    todo[spec.spec_id] = {
        "preguntas": [p.to_dict() for p in preguntas],
        "historial": historial,
    }
    _guardar_todo(raiz, todo)
    mod_specify._persistir_spec(raiz, spec)  # la SPEC se actualiza con cada respuesta
    registro_req = mod_enrich._registro_req(raiz)
    store.escribir_json(store.ruta_requerimientos(raiz), registro_req.to_list())
    indice = mod_specify._indice(raiz)
    if spec.spec_id in indice:
        from core.spec import _ahora  # noqa: PLC0415

        indice[spec.spec_id]["updated_at"] = _ahora()
        _guardar_indice(raiz, indice)


def _guardar_indice(raiz, indice: dict) -> None:
    mod_specify._guardar_indice(raiz, indice)


def _asegurar_preguntas(raiz, spec: Spec, registro_req):
    preguntas, historial = _preguntas_de(raiz, spec.spec_id)
    nuevas = detectar(spec, registro_req.listar(), existentes=preguntas)
    if nuevas:
        preguntas = consolidar(preguntas, nuevas)
        _persistir(raiz, spec, preguntas, historial)
    return preguntas, historial


def mostrar_pregunta(p) -> None:
    print(f"\n❓ {p.id} [{p.kind}]")
    print(f"   {p.texto}")
    if p.contexto:
        print(f"   ↳ {p.contexto}")
    if p.tipo == "opciones":
        for n, op in enumerate(p.opciones, 1):
            print(f"   {n}. {op}")
        print("   (número, texto libre, o 's' para omitir)")


def cmd_clarify_list(args) -> int:
    raiz = _raiz(args)
    try:
        spec = mod_specify._cargar_spec(raiz, args.list)
        preguntas, _h = _asegurar_preguntas(raiz, spec, mod_enrich._registro_req(raiz))
    except (ClarifyError, SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    for p in preguntas:
        marca = {"pendiente": "○", "respondida": "✓", "omitida": "—"}[p.estado]
        print(f"{marca} {p.id} [{p.kind}] {p.texto}")
    return 0


def _aplicar_respuesta(raiz, spec, preguntas, historial, pid: str, respuesta: str) -> int:
    pregunta = next((p for p in preguntas if p.id == pid), None)
    if pregunta is None:
        print(f"⛔ pregunta inexistente: {pid}")
        return 1
    try:
        cambio = responder(pregunta, respuesta, spec, mod_enrich._registro_req(raiz))
        historial.append(
            {"pregunta": pid, "respuesta": pregunta.respuesta, "cambio": cambio}
        )
        _persistir(raiz, spec, preguntas, historial)
    except (ClarifyError, SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    print(f"✓ {cambio}")
    return 0


def cmd_clarify_answer(args) -> int:
    raiz = _raiz(args)
    try:
        spec = mod_specify._cargar_spec(raiz, args.texto)
        preguntas, historial = _asegurar_preguntas(
            raiz, spec, mod_enrich._registro_req(raiz)
        )
    except (ClarifyError, SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    codigo = 0
    for pid, respuesta in args.answer or []:
        if _aplicar_respuesta(raiz, spec, preguntas, historial, pid, respuesta):
            codigo = 1
    for pid in args.skip or []:
        pregunta = next((p for p in preguntas if p.id == pid), None)
        if pregunta is None or pregunta.estado != PENDIENTE:
            print(f"⛔ no se puede omitir: {pid}")
            codigo = 1
            continue
        pregunta.estado = "omitida"
        historial.append(
            {"pregunta": pid, "respuesta": None,
             "cambio": f"{pid}: omitida explícitamente por el humano"}
        )
        print(f"— {pid} omitida (registrada, no se repetirá)")
    _persistir(raiz, spec, preguntas, historial)
    return codigo


def _mostrar_esencial(p) -> None:
    print(f"\n❓ {p.id} [{p.kind}]")
    print(f"   {p.texto}")
    if p.contexto:
        print(f"   ↳ {p.contexto}")
    if p.tipo == "opciones" and p.opciones:
        for n, op in enumerate(p.opciones, 1):
            marca_recomendada = " ✓ (recomendado)" if n == 1 else ""
            print(f"   {n}. {op}{marca_recomendada}")
        print("   (número, texto libre, o 's' para omitir)")
    else:
        print("   (texto libre, o 's' para omitir)")


def cmd_clarify_interactivo(args) -> int:
    """Modo visual por defecto: 3-7 preguntas prioritarias, múltiple choice
    con opción recomendada (primera). El humano elige qué aclarar."""
    raiz = _raiz(args)
    try:
        spec = mod_specify._cargar_spec(raiz, args.texto)
        preguntas, historial = _asegurar_preguntas(
            raiz, spec, mod_enrich._registro_req(raiz)
        )
    except (ClarifyError, SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1

    esenciales = [p for p in preguntas if p.esencial and p.estado == PENDIENTE][:7]
    if not esenciales:
        print(f"🟢 No hay preguntas esenciales pendientes para {args.texto}.")
        return cmd_clarify_gate_ns(raiz, spec.spec_id, esencial=True)

    print(f"🔍 Preguntas prioritarias — {len(esenciales)} pregunta(s):")
    for pregunta in esenciales:
        _mostrar_esencial(pregunta)
        try:
            entrada = input("   > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n— interrumpido; lo respondido quedó guardado")
            break
        if entrada.lower() in ("s", "omitir", "skip"):
            pregunta.estado = OMITIDA
            historial.append(
                {"pregunta": pregunta.id, "respuesta": None,
                 "cambio": f"{pregunta.id}: omitida explícitamente por el humano"}
            )
            _persistir(raiz, spec, preguntas, historial)
            continue
        if _aplicar_respuesta(raiz, spec, preguntas, historial,
                              pregunta.id, entrada):
            continue

    print(f"\n¿Qué desea hacer ahora?")
    print(f"[ clarify {args.texto} --gate ]  [ clarify {args.texto} --list ]")
    print(f"[ specify --show {args.texto} ]  [ plan {args.texto} ]")
    return 0


def cmd_clarify_gate_ns(raiz, spec_id: str, esencial: bool = False) -> int:
    try:
        spec = mod_specify._cargar_spec(raiz, spec_id)
        preguntas, _h = _asegurar_preguntas(raiz, spec, mod_enrich._registro_req(raiz))
    except (ClarifyError, SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    resto = pendientes(preguntas)
    total = len(preguntas)
    hechas = total - len(resto)

    if esencial:
        esenciales_pendientes = [p for p in preguntas
                                 if p.esencial and p.estado == PENDIENTE]
        if esenciales_pendientes:
            print(f"🔴 QUALITY GATE 1 (esencial): BLOQUEADO — "
                  f"{len(esenciales_pendientes)} esencial(es) pendiente(s):")
            for p in esenciales_pendientes:
                print(f"   ○ {p.id} [{p.kind}] {p.texto}")
            print(f"¿Qué desea hacer ahora?")
            print(f"[ clarify {spec_id} ]  [ clarify {spec_id} --list ]")
            return 1
        esenciales_total = sum(1 for p in preguntas if p.esencial)
        print(f"🟢 QUALITY GATE 1 (esencial): SUPERADO — "
              f"{esenciales_total}/{esenciales_total} esencial(es) aclarada(s).")
        print(f"{spec_id} lista para /plan (preguntas restantes se pueden dejar para después).")
        print("¿Qué desea hacer ahora?")
        print(f"[ specify --show {spec_id} ]  [ plan {spec_id} ]")
        return 0

    if resto:
        print(f"🔴 QUALITY GATE 1: BLOQUEADO — {hechas}/{total} aclaradas, "
              f"{len(resto)} pendiente(s)")
        for p in resto:
            print(f"   ○ {p.id} [{p.kind}] {p.texto}")
        print("¿Qué desea hacer ahora?")
        print(f"[ clarify {spec_id} ]  [ clarify {spec_id} --list ]")
        return 1
    print(f"🟢 QUALITY GATE 1: SUPERADO — {hechas}/{total} aclaradas. "
          f"{spec_id} lista para /plan")
    print("¿Qué desea hacer ahora?")
    print(f"[ specify --show {spec_id} ]")
    return 0


def despachar(args) -> int:
    if args.list:
        return cmd_clarify_list(args)
    if getattr(args, "gate", False):
        return cmd_clarify_gate_ns(_raiz(args), args.texto, esencial=False)
    if getattr(args, "answer", None) or getattr(args, "skip", None):
        return cmd_clarify_answer(args)
    if not args.texto:
        print("⛔ indique la SPEC-ID o use --list")
        return 1
    return cmd_clarify_interactivo(args)
