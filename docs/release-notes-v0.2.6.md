# SDD Visual Toolkit v0.2.6

Versión de corrección del panel integrado. El texto libre de las
clarificaciones se guardaba cortado en palabras cuando no llevaba una «s», y
`clarify SPEC-001` escrito en el chat no abría el panel. Las dos cosas venían
del mismo escape perdido en el script del webview.

Compatible con los proyectos creados con 0.2.1: no cambia el formato de
`.specify/` ni el protocolo MCP.

Cada release adjunta `sdd-visual-toolkit-0.2.6.vsix`, empaquetado con `vsce`
desde el mismo commit que el tag:

```bash
code --install-extension sdd-visual-toolkit-0.2.6.vsix
```

También adjunta el wheel y el sdist. El wheel lleva el `.vsix` en
`share/sdd-toolkit/`, así que `sdd init` puede instalarlo sin bajar nada aparte:

```bash
uv tool install sdd_toolkit-0.2.6-py3-none-any.whl
```

## Corregido

- **El texto libre del panel se guardaba cortado en palabras.** El script del
  webview viaja dentro de un template literal y ahí se pierde la barra
  invertida: el entrecomillado terminaba mirando `/[s"]/` en vez de `/[\s"]/`,
  así que una respuesta con espacios solo se entrecomillaba si contenía una
  «s» —«hola mundo kiosco 1» sobrevivía, «definido en la prueba 1» no—. El
  resto se partía en argumentos sueltos y quedaba guardado como «definido, en,
  la, prueba, 1».
- **`clarify SPEC-001` escrito en el chat no abría el panel** por el mismo
  motivo: el selector llegaba como `/^clarifys+SPEC-d+s*$/i` y la orden caía en
  el camino de «idea», que la enriquecía como si fuera una idea nueva.
- El arnés headless revisa ahora el HTML que se le sirve al webview y falla si
  un escape se vuelve a perder: 47 comprobaciones en verde.

## Verificación

- `python3 -m pytest tests/ -q` → 491 passed, 81 subtests passed, sin fallos.
- El chequeo nuevo del arnés falla con el `chat.js` de 0.2.5 (el HTML servido
  trae `/[s"]/`) y pasa con el corregido.
- Panel probado dentro de VS Code real (perfil aislado, `.vsix` instalado
  desde la release): 25 preguntas pintadas, «Aplicar respuestas» aplicó las 25
  y el texto libre quedó completo («definido en la prueba 1»).
- `sdd --version` → `toolkit 0.2.6`; `ide/vscode/package.json` y `pyproject.toml`
  declaran la misma versión.

## Enlaces

- Changelog completo: [`CHANGELOG.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.6/CHANGELOG.md)
- Proceso de release: [`docs/RELEASES.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.6/docs/RELEASES.md)
- Compatibilidad por entorno: [`ide/COMPATIBILIDAD.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.6/ide/COMPATIBILIDAD.md)
- Checklist de prueba manual: [`ide/PRUEBA-MANUAL.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.6/ide/PRUEBA-MANUAL.md)
- Contribución: [`CONTRIBUTING.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.6/CONTRIBUTING.md)
