"""Persistencia atómica del estado (§13.5, §35).

Todo se guarda bajo `<proyecto>/.specify/`. Las escrituras usan archivo
temporal + renombrado atómico para no dejar JSON a medio escribir.
Solo biblioteca estándar.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

SPECIFY_DIR = ".specify"
REQUERIMIENTOS_FILE = "requerimientos.json"


class StoreError(OSError):
    """El estado persistido no se pudo leer o escribir de forma segura."""


def descubrir_raiz(inicio: Path | None = None) -> Path:
    """Sube desde `inicio` (o cwd) hasta encontrar `.specify/`."""
    actual = (inicio or Path.cwd()).resolve()
    for candidato in (actual, *actual.parents):
        if (candidato / SPECIFY_DIR).is_dir():
            return candidato
    raise StoreError(
        "no hay proyecto toolkit aquí (falta .specify/); ejecute `toolkit init`"
    )


def inicializar_proyecto(raiz: Path) -> Path:
    """Crea la estructura §35 sin tocar nada que ya exista del usuario."""
    raiz = raiz.resolve()
    specify = raiz / SPECIFY_DIR
    (specify / "memory").mkdir(parents=True, exist_ok=True)
    (specify / "checkpoints").mkdir(parents=True, exist_ok=True)
    (raiz / "specs").mkdir(exist_ok=True)
    # Solo donde los comandos escriben de verdad: `specify` deja la SPEC en
    # specs/, y `plan`, `tasks` y `analyze` escriben bajo .specify/. Antes se
    # creaban plans/ y tasks/ en la raíz, que nadie llegaba a usar.
    for sub in ("planes", "tareas", "informes"):
        (specify / sub).mkdir(exist_ok=True)
    # El estado de ejecución y el historial los escribe el journal dentro de
    # `memory/`; antes init dejaba aquí un `current_task.json` y un
    # `execution_history.jsonl` que nadie leía ni actualizaba.
    for nombre, contenido in (
        (REQUERIMIENTOS_FILE, []),
    ):
        destino = specify / nombre
        if not destino.exists():
            _escritura_atomica(destino, contenido, texto=isinstance(contenido, str))
    return raiz


def _fsync_dir(carpeta: Path) -> None:
    """Sincroniza el directorio para que el renombrado sobreviva a un corte.

    Sin este fsync un rename puede perderse aunque el archivo esté completo
    (§13.5, §35). En plataformas sin fsync de directorio (p. ej. Windows)
    se declara no disponible: la escritura atómica sigue siendo válida.
    """
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


def _escritura_atomica(destino: Path, contenido, texto: bool = False) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    fd, temporal = tempfile.mkstemp(
        dir=str(destino.parent), prefix=destino.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            if texto:
                fh.write(contenido)
            else:
                json.dump(contenido, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporal, destino)
        _fsync_dir(destino.parent)
    except BaseException:
        try:
            os.unlink(temporal)
        except OSError:
            pass
        raise


def leer_json(ruta: Path):
    try:
        with open(ruta, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as error:
        raise StoreError(f"archivo de estado inexistente: {ruta}") from error
    except json.JSONDecodeError as error:
        raise StoreError(f"archivo de estado corrupto: {ruta} ({error})") from error


def escribir_json(ruta: Path, contenido) -> None:
    try:
        _escritura_atomica(ruta, contenido)
    except OSError as error:
        raise StoreError(f"no se pudo persistir {ruta}: {error}") from error


def ruta_requerimientos(raiz: Path) -> Path:
    return raiz / SPECIFY_DIR / REQUERIMIENTOS_FILE


MODO_GESTOR = "gestor"
MODO_ORQUESTADOR = "orquestador"
MODO_FILE = "modo.json"


def leer_modo_operacion(raiz: Path) -> str:
    """Lee el modo operativo actual. Default: gestor."""
    ruta = raiz / SPECIFY_DIR / MODO_FILE
    if not ruta.exists():
        return MODO_GESTOR
    try:
        datos = leer_json(ruta)
    except StoreError:
        return MODO_GESTOR
    modo = datos.get("modo")
    if modo not in (MODO_GESTOR, MODO_ORQUESTADOR):
        return MODO_GESTOR
    return modo


def escribir_modo_operacion(raiz: Path, modo: str) -> None:
    """Persiste el modo operativo en `.specify/modo.json`."""
    if modo not in (MODO_GESTOR, MODO_ORQUESTADOR):
        raise StoreError(f"modo inválido: {modo!r} (use {MODO_GESTOR} o {MODO_ORQUESTADOR})")
    escribir_json(raiz / SPECIFY_DIR / MODO_FILE, {"modo": modo})


class TransaccionStore:
    """Almacén transacional para agrupar múltiples escrituras de estado.

    Las escrituras se acumulan en memoria y se confirman como una sola
    unidad atómica con `commit()`. Si alguna escritura falla, las ya
    ejecutadas se deshacen restaurando backups. `rollback()` descarta todo.
    """

    def __init__(self, raiz: Path) -> None:
        self.raiz = raiz
        self._operaciones: list[tuple[Path, object, bool]] = []
        self._backups: dict[Path, object] = {}

    def __enter__(self) -> "TransaccionStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            self.rollback()
        return False

    def escribir(self, ruta: Path, contenido, texto: bool = False) -> None:
        """Acumula una operación de escritura (no se ejecuta hasta commit)."""
        self._operaciones.append((ruta.resolve(), contenido, texto))

    def commit(self) -> None:
        """Ejecuta todas las escrituras atómicamente.

        Si alguna falla, deshace las ya ejecutadas restaurando backups.
        """
        pendientes = list(self._operaciones)
        self._operaciones = []
        self._backups = {}
        for ruta, contenido, texto in pendientes:
            # Hacer backup del archivo existente si lo hay
            if ruta.exists():
                backup = ruta.with_suffix(ruta.suffix + ".bak-trans")
                try:
                    backup.write_bytes(ruta.read_bytes())
                    self._backups[ruta] = backup
                except OSError:
                    pass
            try:
                _escritura_atomica(ruta, contenido, texto=texto)
            except BaseException:
                # Deshacer las ya ejecutadas restaurando backups
                for ruta_hecha, backup in self._backups.items():
                    try:
                        backup.replace(ruta_hecha)
                    except OSError:
                        pass
                self._backups = {}
                raise
        self._backups = {}

    def rollback(self) -> None:
        """Descarta todas las operaciones pendientes sin escribir nada."""
        self._operaciones = []
        self._backups = {}


def transaccion(raiz: Path) -> TransaccionStore:
    """Factory que retorna una TransaccionStore para el proyecto dado."""
    return TransaccionStore(raiz)
