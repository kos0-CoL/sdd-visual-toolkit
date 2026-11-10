# Compatibilidad por entorno (§30) — RF-40

La compatibilidad se comprueba individualmente; no se asume.

| Entorno | Estado | Base |
|---|---|---|
| VS Code | ✅ soportado | RF-39 (`ide/vscode/`): paleta, vista lateral, barra de estado. Solo APIs estables (commands, TreeView, StatusBar, Terminal); verificado con `node --check` + `tests/test_ide.py`. |
| Cursor | ✅ compatible por diseño | Misma API de extensiones que VS Code; la extensión no usa proposed APIs. Pendiente: prueba manual en Cursor. |
| Windsurf | ✅ compatible por diseño | Idem Cursor. Pendiente: prueba manual en Windsurf. |
| Otros basados en VS Code | ✅ compatible por diseño | Idem. Pendiente: prueba manual en cada uno. |
| Antigravity | ⚠️ pendiente de verificación | §29: debe usarse lo que ese entorno ofrezca de verdad. Verificar antes de afirmar: paleta de comandos, vistas propias, terminal integrada y lectura del workspace. Hasta entonces, usar la CLI (RF-36) o el servidor MCP. |
| Solo terminal / CLI | ✅ soportado | RF-36: la CLI es completa sin IDE. |
| Vía MCP (Claude Code, etc.) | ✅ soportado | `mcp/server.py`: seis herramientas por stdio, sin dependencias — de lectura (`exportar_estado`, `siguiente`, `tablero`) y operativas (`asignar_tarea`, `registrar_resultado`, `marcar_completada`). Verificado en `tests/test_mcp.py`. |

Regla (§47): donde falte capacidad, se degrada a CLI + `export`, nunca se inventa estado.
