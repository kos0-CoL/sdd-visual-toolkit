"""Comandos `toolkit instrucciones` — RF-41 (§47, §11.3).

Genera el archivo de instrucciones del agente desde el estado real
(reglas + foto + restricciones + siguiente paso). A stdout por
defecto (solo lectura); con `--guardar` lo persiste en
`.specify/INSTRUCCIONES.md` para cargarlo en cualquier IDE/agente.
"""

from __future__ import annotations

import pathlib

from cli.commands import plan as mod_plan
from cli.commands import restricciones as mod_restr
from cli.commands import specify as mod_specify
from cli.commands import tablero as mod_tablero
from core.instrucciones import documento
from core.navigation import sugerir
from state import store

ARCHIVO = "INSTRUCCIONES.md"


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def _foto(raiz):
    estado = mod_tablero.recopilar(raiz)
    spec_id = estado.get("spec_id")
    if spec_id and "PLAN-" not in str(estado.get("proxima") or ""):
        try:
            planes = [(pid, info)
                      for pid, info in mod_plan._indice(raiz).items()
                      if info.get("spec_id") == spec_id]
            if planes:
                estado["plan_id"] = sorted(p for p, _i in planes)[-1]
        except Exception:  # noqa: BLE001 — sin índice, se declara
            pass
    return estado


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        estado = _foto(raiz)
        secciones: list = []
        spec_id = estado.get("spec_id")
        if spec_id:
            spec = mod_specify._cargar_spec(raiz, spec_id)
            _titulo, secciones = mod_restr._panel_spec(raiz, spec)
        texto = documento(estado, secciones, sugerir(estado))
    except store.StoreError as error:
        print(f"⛔ {error}")
        return 1
    if getattr(args, "guardar", False):
        destino = raiz / store.SPECIFY_DIR / ARCHIVO
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
        print(f"🟢 instrucciones guardadas en {destino}")
        return 0
    print(texto, end="")
    return 0
