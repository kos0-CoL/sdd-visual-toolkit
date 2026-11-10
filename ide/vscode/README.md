# SDD Visual Toolkit — extensión VS Code (RF-39, §29)

Paleta, vista lateral y barra de estado sobre el **mismo estado central**
que la CLI (`toolkit export`, RF-38). Sin dependencias ni build.

## Probar en desarrollo

1. Abra esta carpeta (`ide/vscode/`) en VS Code.
2. `Ejecutar → Iniciar depuración` (host de extensión).
3. En la ventana nueva, abra un proyecto con `.specify/` y use la
   paleta (`SDD: …`) o la vista `SDD → Fases y tareas`.

## Configuración

- `sddToolkit.python` (defecto `python3`).
- `sddToolkit.cliPath` (defecto `cli/main.py` relativo al proyecto).

Sin `.specify/` la vista lo declara y ofrece `SDD: Inicializar proyecto`.
