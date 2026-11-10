"""RF-11 — State Journaling (§13).

Memoria operativa persistente: historial de eventos (JSONL) + estado
actual (JSON con escritura atómica). Ningún avance existe si no está
registrado; ningún registro parcial cuenta como estado.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

MEMORY_DIR = "memory"
STATE_FILE = "current_task.json"
HISTORY_FILE = "execution_history.jsonl"
STATE_BACKUP = "current_task.json.bak"
COMPACTAR_POR_DEFECTO = 200

CLAVES_ESTADO = {
    "plan_id", "spec_id", "fase", "total_tareas", "ultimo_exito_indice",
    "tarea_en_curso", "fallos_consecutivos", "ultimo_checkpoint",
    "run_id", "actualizado_en",
}


class JournalError(ValueError):
    """Condición de aceptación violada en el journaling."""


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _memoria(raiz: Path) -> Path:
    ruta = Path(raiz) / ".specify" / MEMORY_DIR
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def nuevo_run_id() -> str:
    return uuid.uuid4().hex[:12]


def registrar(raiz, plan_id: str, evento: dict) -> dict:
    """Agrega un evento al historial. Escritura por agregado (una línea
    completa o nada), nunca reescribe el pasado."""
    if not evento.get("evento") or not evento.get("tarea"):
        raise JournalError("el evento requiere 'evento' y 'tarea'")
    registro = {"fecha": _ahora(), "plan": plan_id, **evento}
    ruta = _memoria(Path(raiz)) / HISTORY_FILE
    linea = json.dumps(registro, ensure_ascii=False)
    with open(ruta, "a", encoding="utf-8") as fh:
        fh.write(linea + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return registro


def actualizar_estado(raiz, estado: dict) -> dict:
    """Escritura atómica con validación de esquema y copia de recuperación
    (§13.5). Un corte de luz deja el estado viejo intacto, jamás un JSON
    a medias."""
    faltantes = CLAVES_ESTADO - set(estado)
    if faltantes:
        raise JournalError(f"estado incompleto, faltan: {sorted(faltantes)}")
    memoria = _memoria(Path(raiz))
    destino = memoria / STATE_FILE
    estado = {**estado, "actualizado_en": _ahora()}
    texto = json.dumps(estado, ensure_ascii=False, indent=2)
    if destino.exists():
        destino.replace(memoria / STATE_BACKUP)
    fd, tmp = tempfile.mkstemp(dir=str(memoria), prefix=".estado-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(texto)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, destino)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return estado


def leer_estado(raiz) -> dict | None:
    ruta = _memoria(Path(raiz)) / STATE_FILE
    if not ruta.exists():
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise JournalError(f"estado ilegible: {error}") from error
    faltantes = CLAVES_ESTADO - set(datos)
    if faltantes:
        raise JournalError(f"estado corrupto, faltan: {sorted(faltantes)}")
    return datos


def historial(raiz, plan_id: str | None = None, ultimos: int = 0) -> list[dict]:
    ruta = _memoria(Path(raiz)) / HISTORY_FILE
    if not ruta.exists():
        return []
    eventos = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            eventos.append(json.loads(linea))
        except json.JSONDecodeError:
            continue  # línea parcial de un corte: se ignora, no se inventa
    if plan_id is not None:
        eventos = [e for e in eventos if e.get("plan") == plan_id]
    return eventos[-ultimos:] if ultimos > 0 else eventos


def _fsync_dir(carpeta: Path) -> None:
    """Sincroniza el directorio del journal tras el renombrado atómico."""
    try:
        fd = os.open(str(carpeta), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _reescribir_atomico(ruta: Path, texto: str) -> None:
    """Reescribe el historial completo o nada: nunca deja JSONL a medias."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(ruta.parent), prefix=".historial-",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(texto)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, ruta)
        _fsync_dir(ruta.parent)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def compactar(raiz, plan_id: str | None = None,
              conservar: int = COMPACTAR_POR_DEFECTO) -> dict:
    """Compacta el JSONL conservando los últimos N eventos por plan (§13).

    Los eventos recientes son la memoria operativa; el historial completo
    crecía sin límite y degradaba la consulta. Con `plan_id` solo se compacta
    ese plan; los demás quedan intactos. La reescritura es atómica: un corte
    deja el historial anterior completo, no uno truncado.
    """
    if conservar < 0:
        raise JournalError("conservar debe ser >= 0")
    ruta = _memoria(Path(raiz)) / HISTORY_FILE
    eventos = historial(raiz)
    if conservar == 0 and plan_id is None:
        conservados = []
    else:
        indices: dict[str, list[int]] = {}
        for posicion, evento in enumerate(eventos):
            indices.setdefault(str(evento.get("plan")), []).append(posicion)
        mantener: set[int] = set()
        for plan, posiciones in indices.items():
            if plan_id is not None and plan != plan_id:
                mantener.update(posiciones)
            else:
                mantener.update(posiciones[-conservar:] if conservar else [])
        conservados = [e for i, e in enumerate(eventos) if i in mantener]
    descartados = len(eventos) - len(conservados)
    if descartados:
        texto = "".join(json.dumps(e, ensure_ascii=False) + "\n"
                        for e in conservados)
        _reescribir_atomico(ruta, texto)
    return {"antes": len(eventos), "despues": len(conservados),
            "descartados": descartados}


def checkpoint(raiz, plan_id: str, spec_id: str, tarea, proxima_id: str | None,
               pruebas: str, pruebas_ok: bool, nota: str = "") -> dict:
    """Checkpoint semántico §13.4: qué quedó hecho y qué sigue, con hashes."""
    from core.pin import snapshot_archivo  # noqa: PLC0415

    archivos, hashes = [], {}
    for rel in tarea.archivos:
        ruta = Path(raiz) / rel
        if ruta.is_file():
            archivos.append(rel)
            snap = snapshot_archivo(ruta)
            if snap is not None:
                hashes[rel] = snap["sha"][:16]
    return registrar(raiz, plan_id, {
        "evento": "checkpoint",
        "tarea": tarea.id,
        "spec": spec_id,
        "fase": "implement",
        "proxima": proxima_id,
        "archivos": archivos,
        "hashes": hashes,
        "pruebas": pruebas,
        "pruebas_ok": pruebas_ok,
        "decisiones": nota,
    })


def estado_inicial(plan_id: str, spec_id: str, total: int, run_id: str) -> dict:
    return {
        "plan_id": plan_id, "spec_id": spec_id, "fase": "implement",
        "total_tareas": total, "ultimo_exito_indice": -1,
        "tarea_en_curso": None, "fallos_consecutivos": 0,
        "ultimo_checkpoint": None, "run_id": run_id,
        "actualizado_en": _ahora(),
    }


def resumen(raiz, plan_id: str) -> str:
    eventos = historial(raiz, plan_id)
    hechas = [e for e in eventos if e.get("evento") == "completada"]
    fallidas = [e for e in eventos if e.get("evento") == "fallida"]
    en_curso = [e for e in eventos if e.get("evento") == "en_curso"]
    lineas = [
        f"📓 Journal {plan_id}: {len(eventos)} evento(s) — "
        f"{len(hechas)} completada(s), {len(fallidas)} fallida(s).",
        f"Última en curso: {en_curso[-1]['tarea'] if en_curso else 'ninguna'}.",
        "Últimos eventos:",
    ]
    for e in eventos[-5:]:
        lineas.append(f"  {e.get('fecha')} [{e.get('evento')}] {e.get('tarea')}")
    return "\n".join(lineas)
