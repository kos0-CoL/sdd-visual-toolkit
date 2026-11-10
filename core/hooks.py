"""RF-42 — Hooks de agente (§47).

Ganchos propios del usuario/IDE ante eventos del ciclo de tarea:
`tarea_abierta` (build pone una tarea en curso) y `tarea_cerrada`
(build registra done/fail). Viven en `.specify/hooks/<evento>/` como
archivos ejecutables; reciben SDD_EVENTO/PLAN/TAREA/RESULTADO/ROOT.
Un hook que falla se declara y se registra, nunca bloquea en silencio
(§47: degradar funcionalmente).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from state.store import SPECIFY_DIR

EVENTOS = ("tarea_abierta", "tarea_cerrada")
TIMEOUT_S = 60


def dir_evento(raiz, evento: str) -> Path:
    return Path(raiz) / SPECIFY_DIR / "hooks" / evento


def listar(raiz) -> dict:
    """{evento: [{nombre, ejecutable}]} con lo que hay en disco."""
    visto = {}
    for evento in EVENTOS:
        carpeta = dir_evento(raiz, evento)
        hooks = []
        if carpeta.is_dir():
            for ruta in sorted(carpeta.iterdir()):
                if ruta.is_file():
                    hooks.append({"nombre": ruta.name,
                                  "ejecutable": os.access(ruta, os.X_OK)})
        visto[evento] = hooks
    return visto


def disparar(raiz, evento: str, entorno: dict) -> list:
    """Ejecuta los hooks ejecutables del evento. Nunca lanza excepción."""
    resultados = []
    for ruta in sorted(dir_evento(raiz, evento).glob("*")):
        if not (ruta.is_file() and os.access(ruta, os.X_OK)):
            continue
        env = {**os.environ,
               "SDD_EVENTO": evento,
               "SDD_ROOT": str(raiz),
               "SDD_PLAN": str(entorno.get("plan", "")),
               "SDD_TAREA": str(entorno.get("tarea", "")),
               "SDD_RESULTADO": str(entorno.get("resultado", ""))}
        try:
            corrido = subprocess.run(
                [str(ruta)], cwd=str(raiz), env=env, capture_output=True,
                text=True, timeout=TIMEOUT_S)
            resultados.append({
                "hook": ruta.name, "ok": corrido.returncode == 0,
                "codigo": corrido.returncode,
                "salida": (corrido.stdout + corrido.stderr).strip()[:2000]})
        except Exception as error:  # noqa: BLE001 — se declara, no se rompe
            resultados.append({"hook": ruta.name, "ok": False,
                               "codigo": -1, "salida": str(error)[:500]})
    return resultados
