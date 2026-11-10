"""RF-16 — Snapshot Rollback (§16).

Snapshots selectivos por tarea: solo los archivos autorizados de la tarea,
jamás `git checkout` indiscriminado ni tocar trabajo preexistente ajeno.
Ante dos fallos consecutivos con la misma firma: se detiene, se restaura
el último estado seguro, la estrategia queda prohibida y la tarea exige
una solución diferente.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

SNAPSHOTS_DIR = "snapshots"
FORBIDDEN_FILE = "forbidden_strategies.json"


class RollbackError(ValueError):
    """Condición de aceptación violada en el rollback."""


def firma(nota: str) -> str:
    """Firma de error comparable: primera línea, normalizada."""
    primera = (nota or "").strip().splitlines()[0] if (nota or "").strip() else ""
    return " ".join(primera.lower().split())[:120] or "(sin descripción)"


def _copia_segura(raiz, rel: str) -> Path | None:
    """Ruta destino validada: dentro del proyecto y sin symlink (§16)."""
    destino = Path(raiz) / rel
    base = Path(raiz).resolve()
    resuelta = destino.resolve()
    if resuelta != base and base not in resuelta.parents:
        return None
    if destino.is_symlink() or resuelta.is_symlink():
        return None
    return destino


def _dir_tarea(raiz: Path, task_id: str) -> Path:
    ruta = Path(raiz) / ".specify" / SNAPSHOTS_DIR / task_id
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def tomar(raiz, tarea) -> Path:
    """Foto de los archivos de la tarea ANTES de implementarla."""
    destino = _dir_tarea(Path(raiz), tarea.id)
    existentes = sorted(p for p in range(1000)
                        if (destino / str(p)).exists())
    numero = (existentes[-1] + 1) if existentes else 0
    carpeta = destino / str(numero)
    carpeta.mkdir()
    for rel in tarea.archivos:
        origen = Path(raiz) / rel
        if origen.is_file():
            copia = carpeta / rel
            copia.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origen, copia)
    (carpeta / "archivos.txt").write_text("\n".join(tarea.archivos),
                                          encoding="utf-8")
    return carpeta


def ultimos_fallos(eventos: list[dict], task_id: str) -> list[dict]:
    return [e for e in eventos
            if e.get("tarea") == task_id and e.get("evento") == "fallida"][-2:]


def debe_frenar(eventos: list[dict], task_id: str) -> dict | None:
    """Dos fallos consecutivos con la misma firma → frenar (§16)."""
    fallos = ultimos_fallos(eventos, task_id)
    if len(fallos) < 2:
        return None
    firmas = [firma(f.get("nota", "")) for f in fallos]
    if firmas[0] != firmas[1]:
        return None
    return {"firma": firmas[0], "intentos": len(fallos)}


def restaurar(raiz, task_id: str, numero: int | None = None) -> Path:
    """Restaura el último estado seguro. Selectivo: solo archivos de la
    tarea registrados en el snapshot; lo ajeno no se toca (§16)."""
    destino = _dir_tarea(Path(raiz), task_id)
    tomas = sorted(p for p in destino.iterdir()
                   if p.is_dir() and p.name.isdigit())
    if not tomas:
        raise RollbackError(f"sin snapshots para {task_id}: nada que restaurar")
    carpeta = destino / str(numero) if numero is not None else tomas[-1]
    if not carpeta.is_dir():
        raise RollbackError(f"snapshot inexistente: {task_id}/{numero}")
    permitidos = (carpeta / "archivos.txt").read_text(
        encoding="utf-8").splitlines()
    for rel in permitidos:
        copia = carpeta / rel
        destino_final = _copia_segura(raiz, rel)
        if destino_final is None:
            raise RollbackError(f"ruta insegura en snapshot: {rel}")
        if copia.is_file():
            destino_final.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(copia, destino_final)
        elif destino_final.is_file():
            # La creó el intento fallido: se retira para no acumular
            # correcciones sobre lo defectuoso (solo archivos de la tarea).
            destino_final.unlink()
    return carpeta


def prohibir(raiz, task_id: str, estrategia_firma: str, intentos: int) -> dict:
    ruta = Path(raiz) / ".specify" / FORBIDDEN_FILE
    ruta.parent.mkdir(parents=True, exist_ok=True)
    datos = {"forbidden_strategies": []}
    if ruta.exists():
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = {"forbidden_strategies": []}
    registro = {"task_id": task_id, "error_signature": estrategia_firma,
                "strategy": estrategia_firma, "attempts": intentos,
                "reason": "La solución produjo el mismo error"}
    estrategias = datos.setdefault("forbidden_strategies", [])
    if not any(e.get("task_id") == task_id
               and e.get("error_signature") == estrategia_firma
               for e in estrategias):
        estrategias.append(registro)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return registro


def listar(raiz, task_id: str) -> list[str]:
    destino = Path(raiz) / ".specify" / SNAPSHOTS_DIR / task_id
    if not destino.is_dir():
        return []
    return sorted(p.name for p in destino.iterdir()
                  if p.is_dir() and p.name.isdigit())
