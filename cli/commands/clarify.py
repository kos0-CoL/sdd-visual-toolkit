"""Comandos `toolkit clarify` — RF-04 (§7)."""

from __future__ import annotations

import argparse
import json
import os
import pathlib

from cli.commands import enrich as mod_enrich
from cli.commands import specify as mod_specify
from core.clarify import (
    OMITIDA,
    PENDIENTE,
    ClarifyError,
    Opcion,
    consolidar,
    detectar,
    pendientes,
    preguntas_para_panel,
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
    for entrada in args.answer or []:
        pid = entrada[0]
        respuestas = entrada[1:]
        respuesta = respuestas[0] if len(respuestas) == 1 else respuestas
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
            etiqueta = op.etiqueta if isinstance(op, Opcion) else str(op)
            op_rec = op if isinstance(op, Opcion) else None
            marca_recomendada = " ✓ (recomendado)" if (op_rec and op_rec.recomendada) else ""
            print(f"   {n}. {etiqueta}{marca_recomendada}")
        print("   (número, texto libre, o 's' para omitir)")
    else:
        print("   (texto libre, o 's' para omitir)")


def _mostrar_todas_preguntas(preguntas: list) -> None:
    """Muestra todas las preguntas pendientes con sus opciones numeradas."""
    print(f"\n🔍 Preguntas pendientes — {len(preguntas)} pregunta(s):")
    print("=" * 60)
    for i, p in enumerate(preguntas, 1):
        marca = {"pendiente": "○", "respondida": "✓", "omitida": "—"}[p.estado]
        print(f"\n{i}. {marca} {p.id} [{p.kind}] {p.texto}")
        if p.contexto:
            print(f"   ↳ {p.contexto}")
        if p.tipo == "opciones" and p.opciones:
            for n, op in enumerate(p.opciones, 1):
                etiqueta = op.etiqueta if isinstance(op, Opcion) else str(op)
                op_rec = op if isinstance(op, Opcion) else None
                marca_rec = " ✓ (recomendado)" if (op_rec and op_rec.recomendada) else ""
                print(f"      {n}. {etiqueta}{marca_rec}")
            print("      → responde con el número, texto libre, o 's' para omitir")
        else:
            print("      → responde con texto libre, o 's' para omitir")
    print("=" * 60)


def cmd_clarify_interactivo(args) -> int:
    """Modo visual: muestra TODAS las preguntas pendientes sin límite,
    con múltiple choice numerado (1, 2, 3…) y opción recomendada (primera).
    El humano responde una por una en el mismo chat."""
    raiz = _raiz(args)
    try:
        spec = mod_specify._cargar_spec(raiz, args.texto)
        preguntas, historial = _asegurar_preguntas(
            raiz, spec, mod_enrich._registro_req(raiz)
        )
    except (ClarifyError, SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1

    pendientes = [p for p in preguntas if p.estado == PENDIENTE]
    if not pendientes:
        print(f"🟢 No hay preguntas pendientes para {args.texto}.")
        return cmd_clarify_gate_ns(raiz, spec.spec_id, esencial=True)

    # Siempre escribir la señal para que cualquier extensión de IDE
    # (VS Code, Trae, Cursor, Windsurf) pueda vigilar el archivo y abrir
    # el panel webview automáticamente.
    raiz_path = raiz if isinstance(raiz, pathlib.Path) else pathlib.Path(raiz)
    señal = raiz_path / store.SPECIFY_DIR / ".clarify-panel-request.json"
    señal.parent.mkdir(parents=True, exist_ok=True)
    señal.write_text(
        json.dumps({"spec_id": args.texto, "action": "abrir_panel"},
                   ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Si corre dentro de una terminal integrada de VS Code/Trae/Cursor
    # (VSCODE_PID), no imprimir texto plano ni bloquear con input():
    # solo escribir la señal y salir en silencio. La extensión del IDE
    # vigila el archivo y abre el panel webview automáticamente.
    if os.environ.get("VSCODE_PID"):
        return 0

    # Mostrar TODAS las preguntas de una vez (sin límite de 7)
    _mostrar_todas_preguntas(pendientes)

    # Responder una por una
    for pregunta in pendientes:
        if pregunta.estado != PENDIENTE:
            continue
        try:
            entrada = input(f"\n   Respuesta para {pregunta.id} > ").strip()
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
            print(f"   — {pregunta.id} omitida")
            continue
        if _aplicar_respuesta(raiz, spec, preguntas, historial,
                              pregunta.id, entrada):
            continue
        print(f"   ✓ {pregunta.id} respondida")

    # Re-evaluar qué queda pendiente
    restantes = [p for p in preguntas if p.estado == PENDIENTE]
    if not restantes:
        print(f"\n🟢 Todas las preguntas de {args.texto} han sido respondidas u omitidas.")
        return cmd_clarify_gate_ns(raiz, spec.spec_id, esencial=True)

    print(f"\n⏳ Quedan {len(restantes)} pregunta(s) pendiente(s).")
    print(f"   Puedes volver a ejecutar: clarify {args.texto}")
    print(f"\n¿Qué desea hacer ahora?")
    print(f"[ clarify {args.texto} ]  [ clarify {args.texto} --list ]")
    print(f"[ specify --show {args.texto} ]  [ plan {args.texto} ]")
    return 0


def cmd_clarify_panel(args) -> int:
    """Abre el panel webview visual de clarificaciones para la SPEC."""
    raiz = _raiz(args)
    try:
        spec = mod_specify._cargar_spec(raiz, args.texto)
        preguntas, historial = _asegurar_preguntas(
            raiz, spec, mod_enrich._registro_req(raiz)
        )
    except (ClarifyError, SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1

    pendientes = [p for p in preguntas if p.estado == PENDIENTE]
    if not pendientes:
        print(f"🟢 No hay preguntas pendientes para {args.texto}.")
        return cmd_clarify_gate_ns(raiz, spec.spec_id, esencial=True)

    # Exportar el estado para que el panel webview se abra desde VS Code
    payload = preguntas_para_panel(pendientes)
    print(json.dumps({"comando": "abrir_panel_clarificaciones",
                      "spec_id": spec.spec_id,
                      "preguntas": payload}))
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
    if getattr(args, "panel", False):
        return cmd_clarify_panel(args)
    if getattr(args, "gate", False):
        return cmd_clarify_gate_ns(_raiz(args), args.texto, esencial=False)
    if getattr(args, "answer", None) or getattr(args, "skip", None):
        return cmd_clarify_answer(args)
    if not args.texto:
        print("⛔ indique la SPEC-ID o use --list")
        return 1
    return cmd_clarify_interactivo(args)
