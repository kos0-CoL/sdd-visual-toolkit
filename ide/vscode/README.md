# SDD Visual Toolkit — extensión VS Code (RF-39, §29)

Paleta, vista lateral y barra de estado sobre el **mismo estado central**
que la CLI (`toolkit export`, RF-38). Sin dependencias ni build.

## Probar en desarrollo

1. Abra esta carpeta (`ide/vscode/`) en VS Code.
2. `Ejecutar → Iniciar depuración` (host de extensión).
3. En la ventana nueva, abra un proyecto con `.specify/` y use la
   paleta (`SDD: …`) o la vista `SDD → Fases y tareas`.
4. En `SDD → Flujo SDD`, el clic normal ejecuta el comando de la fase y el
   **clic derecho abre el artefacto** que dejó (`.md` en vista previa, JSON
   en el editor, carpetas en el explorador). Si la fase aún no lo escribió,
   avisa en vez de abrir un archivo vacío. En `SDD → Fases y tareas` el mismo
   clic derecho funciona sobre la fase actual y sobre el árbol de estados.

## Configuración

- `sddToolkit.python` (defecto `python3`).
- `sddToolkit.cliPath` (defecto `cli/main.py` relativo al proyecto).
- `sddToolkit.timeoutMinutos` (defecto 5): cuánto se espera a un comando
  antes de cortarlo, junto con sus procesos hijos.

Sin `.specify/` la vista lo declara y ofrece `SDD: Inicializar proyecto`.
