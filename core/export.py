"""RF-38 — Capa de integración IDE (§29-30, §32).

Documento JSON máquina con el mismo estado central que la CLI:
tablero, árbol, navegación y píldoras. Lo consumen adaptadores
externos (VS Code, Antigravity, Cursor, MCP) sin duplicar estado.
Render puro; la CLI lo rellena con artefactos reales.
"""

from __future__ import annotations

import json

VERSION = "1.0"


def documento(estado: dict, nodos: list, transiciones: list,
              navegacion: dict, flujo: list | None = None,
              skills: dict | None = None) -> dict:
    """Foto máquina del proyecto. Todo sale de artefactos reales.

    `skills` es el mapa ruta muerta → cuántos archivos la usan; se publica para
    que el IDE avise sin tener que leer los archivos generados por su cuenta.
    """
    errores = estado.get("errores") or []
    muertas = skills or {}
    return {
        "toolkit": "sdd-visual-toolkit",
        "api": VERSION,
        "proyecto": estado.get("proyecto", "?"),
        "spec_id": estado.get("spec_id"),
        "spec_status": estado.get("spec_status"),
        "fase": estado.get("fase", "sin SPEC"),
        "progreso": {
            "hechas": estado.get("hechas", 0),
            "total": estado.get("total", 0),
            "pendientes": estado.get("pendientes", 0),
        },
        "tarea_actual": estado.get("tarea_actual"),
        "ultima_completada": estado.get("ultima_completada"),
        "pruebas": estado.get("pruebas", "sin corridas"),
        "errores": list(errores),
        "proxima": estado.get("proxima", "—"),
        "arbol": [{"fase": fase, "estado": est} for fase, est in (nodos or [])],
        # Fase → artefacto → skill: es lo que pinta el panel de flujo del IDE.
        "flujo": list(flujo or []),
        "transiciones": list(transiciones or [])[-12:],
        "navegacion": {
            "recomendada": (navegacion.get("recomendada") or {}).get("comando"),
            "pildoras": [
                {"etiqueta": p.get("etiqueta"), "comando": p.get("comando"),
                 "recomendada": bool(p.get("recomendada")),
                 "bloqueada": bool(p.get("bloqueada")),
                 "motivo": p.get("motivo", "")}
                for p in (navegacion.get("pills") or [])],
            "bloqueos": list(navegacion.get("bloqueos") or []),
            "requiere_aprobacion": bool(
                navegacion.get("requiere_aprobacion")),
        },
        "avisos": {
            "skills": {
                "total": sum(muertas.values()),
                "rutas": [{"ruta": ruta, "archivos": cuantos}
                          for ruta, cuantos in sorted(muertas.items())],
            },
        },
    }


def render(doc: dict) -> str:
    """JSON legible para adaptadores externos."""
    return json.dumps(doc, ensure_ascii=False, indent=2)
