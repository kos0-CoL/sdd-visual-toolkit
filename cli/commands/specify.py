"""Comandos `toolkit specify` — RF-03 (§6)."""

from __future__ import annotations

import pathlib

from cli.commands import enrich as mod_enrich
from core.enrich import VALIDADO
from core.requirements import RegistroRequerimientos
from core.spec import Spec, SpecError, generar_desde_enriquecimiento, render_markdown
from state import store

SPECS_INDEX = "specs.json"
SPEC_HISTORY_DIR = "spec_history"


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def _indice(raiz) -> dict:
    ruta = raiz / store.SPECIFY_DIR / SPECS_INDEX
    if not ruta.exists():
        return {}
    datos = store.leer_json(ruta)
    if not isinstance(datos, dict):
        raise SpecError("el índice de SPECs está corrupto")
    return datos


def _guardar_indice(raiz, indice: dict) -> None:
    store.escribir_json(raiz / store.SPECIFY_DIR / SPECS_INDEX, indice)


def _cargar_spec(raiz, spec_id: str) -> Spec:
    indice = _indice(raiz)
    if spec_id not in indice:
        raise SpecError(f"SPEC inexistente: {spec_id}")
    ruta = raiz / indice[spec_id]["archivo"]
    return Spec.from_dict(store.leer_json(ruta.with_suffix(".json")))


def _persistir_spec(raiz, spec: Spec) -> pathlib.Path:
    """Guarda SPEC como Markdown (legible) + JSON (máquina)."""
    ruta_md = raiz / "specs" / f"{spec.spec_id}.md"
    ruta_md.parent.mkdir(exist_ok=True)
    ruta_md.write_text(render_markdown(spec) + "\n", encoding="utf-8")
    ruta_json = ruta_md.with_suffix(".json")
    store.escribir_json(ruta_json, spec.to_dict())
    return ruta_md


def mostrar_resumen(spec: Spec) -> None:
    print(f"📝 SPEC {spec.spec_id} v{spec.version} [{spec.status}] — {spec.titulo}")
    print(f"  funcionales: {len(spec.funcionales)} | entidades: {len(spec.entidades)}")
    print(f"  criterios: {len(spec.criterios)} | casos: {len(spec.casos)}")
    print(f"  fuera de alcance: {len(spec.fuera_alcance)} | supuestos: {len(spec.supuestos)}")
    if spec.recomienda_dividir():
        print(
            "  ⚠️ §6.4: demasiados flujos independientes; "
            "se recomienda dividir en varias SPEC (no se dividió nada automáticamente)"
        )


def cmd_specify_list(args) -> int:
    for spec_id, info in _indice(_raiz(args)).items():
        print(f"{spec_id} v{info['version']} [{info['status']}] {info['titulo']}")
    return 0


def cmd_specify_show(args) -> int:
    try:
        mostrar_resumen(_cargar_spec(_raiz(args), args.show))
    except (SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0


def cmd_specify(args) -> int:
    raiz = _raiz(args)
    try:
        enr = mod_enrich._registro(raiz).obtener(args.texto)
        if enr.estado != VALIDADO:
            raise SpecError(
                f"{enr.id} no está validado; ejecute `enrich --accept {enr.id}` primero"
            )
        reqs = mod_enrich._registro_req(raiz).listar()
        indice = _indice(raiz)
        spec_id = f"SPEC-{len(indice) + 1:03d}"
        spec = generar_desde_enriquecimiento(enr, reqs, spec_id, titulo=args.titulo)
        ruta = _persistir_spec(raiz, spec)
        # Vincular REQ→SPEC (§39 trazabilidad).
        registro_req = mod_enrich._registro_req(raiz)
        for req in registro_req.listar():
            if req.origen == enr.id:
                req.spec_id = spec_id
        store.escribir_json(
            store.ruta_requerimientos(raiz), registro_req.to_list()
        )
        indice[spec_id] = {
            "spec_id": spec_id,
            "titulo": spec.titulo,
            "archivo": str(ruta.relative_to(raiz)),
            "version": spec.version,
            "status": spec.status,
            "enr_origen": enr.id,
            "created_at": spec.created_at,
            "updated_at": spec.updated_at,
            "approved_at": spec.approved_at,
            "historial": [],
        }
        _guardar_indice(raiz, indice)
    except (SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    mostrar_resumen(spec)
    print("\n🟢 FASE COMPLETADA: SPECIFY")
    print(f"Archivo generado: {ruta.relative_to(raiz)} (+ JSON máquina)")
    print("Validaciones: 15 secciones §6.2; metadatos en estado real (draft, sin aprobar).")
    print(f"Problemas pendientes: {len(spec.supuestos)} supuesto(s) para clarify.")
    print("Estado persistido: sí (REQ vinculados a la SPEC).")
    print("¿Qué desea hacer ahora?")
    print(f"[ specify --show {spec_id} ]  [ req list ]")
    return 0


def cmd_specify_approve(args) -> int:
    raiz = _raiz(args)
    try:
        spec = _cargar_spec(raiz, args.approve)
        spec.aprobar()  # camino exclusivamente humano (§6.3)
        _persistir_spec(raiz, spec)
        indice = _indice(raiz)
        indice[spec.spec_id]["status"] = spec.status
        indice[spec.spec_id]["updated_at"] = spec.updated_at
        indice[spec.spec_id]["approved_at"] = spec.approved_at
        _guardar_indice(raiz, indice)
    except (SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    print(f"🟢 SPEC APROBADA por validación humana: {spec.spec_id} v{spec.version}")
    return 0


def cmd_specify_revise(args) -> int:
    raiz = _raiz(args)
    try:
        if not args.motivo:
            raise SpecError("indique --motivo de la revisión (§6.6)")
        spec = _cargar_spec(raiz, args.revise)
        # §6.6: conservar historial antes de modificar.
        from core.spec import _subir_version  # noqa: PLC0415

        previa = (raiz / "specs" / f"{spec.spec_id}.md").read_text(encoding="utf-8")
        snap_dir = raiz / store.SPECIFY_DIR / SPEC_HISTORY_DIR
        snap_dir.mkdir(parents=True, exist_ok=True)
        (snap_dir / f"{spec.spec_id}_v{spec.version}.md").write_text(
            previa, encoding="utf-8"
        )
        refs_previas = set(spec.referencias)
        enr = mod_enrich._registro(raiz).obtener(spec.enr_origen)
        reqs = mod_enrich._registro_req(raiz).listar()
        nueva = generar_desde_enriquecimiento(enr, reqs, spec.spec_id, titulo=spec.titulo)
        nueva.version = _subir_version(spec.version)
        nueva.status = spec.status
        nueva.created_at = spec.created_at
        nueva.approved_at = spec.approved_at
        refs_nuevas = set(nueva.referencias)
        _persistir_spec(raiz, nueva)
        indice = _indice(raiz)
        indice[nueva.spec_id]["version"] = nueva.version
        indice[nueva.spec_id]["updated_at"] = nueva.updated_at
        indice[nueva.spec_id]["historial"].append(
            {
                "version": nueva.version,
                "fecha": nueva.updated_at,
                "motivo": args.motivo,
                "agregados": sorted(refs_nuevas - refs_previas),
                "quitados": sorted(refs_previas - refs_nuevas),
            }
        )
        _guardar_indice(raiz, indice)
        spec = nueva
    except (SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    mostrar_resumen(spec)
    print(f"Historial conservado en .specify/{SPEC_HISTORY_DIR}/ (§6.6)")
    return 0


def despachar(args) -> int:
    if args.list:
        return cmd_specify_list(args)
    if args.show:
        return cmd_specify_show(args)
    if args.approve:
        return cmd_specify_approve(args)
    if args.revise:
        return cmd_specify_revise(args)
    if not args.texto:
        print("⛔ indique el ENR-ID o use --list/--show/--revise/--approve")
        return 1
    return cmd_specify(args)
