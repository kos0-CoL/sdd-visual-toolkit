# SDD Visual Toolkit v0.2.1

Versión corta sobre la 0.2.0: `init` puede dejar el `.gitignore` como está y la
vista lateral explica qué hacer cuando la ventana no tiene carpeta abierta.
Compatible con los proyectos creados con 0.2.0: no cambia el formato de
`.specify/` ni el protocolo MCP.

Cada release adjunta `sdd-visual-toolkit-0.2.1.vsix`, empaquetado con `vsce`
desde el mismo commit que el tag:

```bash
code --install-extension sdd-visual-toolkit-0.2.1.vsix
```

## Añadido

- **`init --sin-gitignore`.** Inicializa el proyecto sin escribir el
  `.gitignore` ni añadirle reglas: para quien ya lleva ese archivo como quiere.
  El resto de `init` —`.specify/`, `specs/` y los ajustes del IDE— queda igual.
- **La vista lateral dice cómo aparecer.** La extensión se instala una vez,
  pero las vistas leen el estado de una carpeta concreta. Con la ventana vacía
  ahora muestran «Abrir carpeta» (y, si es nueva, «inicializa el proyecto»), y
  el aviso de la paleta trae ese botón en vez de «abra una carpeta primero» a
  secas.

## Documentación

- **`docs/TUTORIAL.md`**: el recorrido de cero, con un ejemplo real. Instalar el
  comando, instalar la extensión, `init`, abrir el panel y el primer prompt;
  después cada fase con su salida y una tabla con lo que muestra la vista.
  Incluye los errores frecuentes (`abra una carpeta primero`, `Orden «sdd» no
  encontrada`, gates bloqueados) con su solución.

## Verificación

- `python3 -m pytest tests/ -q` → 481 passed, 81 subtests passed.
- CI en verde en Python 3.11, 3.12, 3.13 y 3.14, más la instalación editable.
- `python3 scripts/verificar_release.py --previo 0.2.1` en verde antes del tag.
- `sdd init --sin-gitignore` en una carpeta vacía dejó `.specify/`, `.vscode/`
  y `specs/` sin crear `.gitignore`, y con un `.gitignore` previo lo dejó byte
  a byte igual.
- El `.vsix` 0.2.1 declara la misma versión que `pyproject.toml` y su
  `package.json` trae `viewsWelcome` para las dos vistas.

## Enlaces

- Changelog completo: [`CHANGELOG.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.1/CHANGELOG.md)
- Proceso de release: [`docs/RELEASES.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.1/docs/RELEASES.md)
- Compatibilidad por entorno: [`ide/COMPATIBILIDAD.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.1/ide/COMPATIBILIDAD.md)
- Checklist de prueba manual: [`ide/PRUEBA-MANUAL.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.1/ide/PRUEBA-MANUAL.md)
- Contribución: [`CONTRIBUTING.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.1/CONTRIBUTING.md)
