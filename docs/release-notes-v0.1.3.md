# SDD Visual Toolkit v0.1.3

Versión de mantenimiento. Sin cambios en el motor ni en el formato de
`.specify/`: es compatible con proyectos creados con 0.1.0 a 0.1.2. Todo lo
que cambia está en documentación, pruebas y herramientas.

## Añadido

- **`scripts/verificar_release.py`**: comprueba de una vez que el tag existe
  en local y en `origin`, que es anotado y apunta al mismo objeto, que dentro
  del tag están la versión de `pyproject.toml` y la primera entrada con fecha
  del CHANGELOG, que la release está publicada y no en borrador, y que cada
  enlace de las notas resuelve en la ref del tag. Sin dependencias: usa `git`
  y `gh`.

  ```bash
  python3 scripts/verificar_release.py          # versión de pyproject.toml
  python3 scripts/verificar_release.py 0.1.3    # o una versión concreta
  ```

- **Disparo manual del CI** (`workflow_dispatch`) para cuando GitHub tarda en
  crear el run de un PR. Es un respaldo, no un reflejo: la comprobación previa
  evita duplicar runs, y el coste de duplicarlos está documentado.

## Corregido

- **El README anunciaba 269 pruebas** en dos frases mientras su badge y la
  suite tenían 284. Los conteos se escriben a mano y solo el badge tenía
  prueba; ahora `tests/test_readme.py` compara también las menciones
  «N tests» de la prosa.
- **`ide/COMPATIBILIDAD.md` describía el MCP con tres herramientas** de solo
  lectura y citaba como evidencia `tests/test_mcp.py`, que exige las seis: las
  tres de lectura y las tres operativas.
- **`CONTRIBUTING.md` recomendaba `--upgrade pip`** al preparar el entorno,
  cuando el README y la CI no lo hacen y la 0.1.2 registró su retirada por
  coste (4,0 s → 2,0 s de mediana por job).
- **`docs/RELEASES.md` pedía el CHANGELOG «sin dejar `No publicado`»**, lo que
  se lee como borrar la sección. Ahora dice que las viñetas pasan a la sección
  nueva y que `[No publicado]` queda arriba, vacía.
- **La latencia del CI estaba atribuida a GitHub en general.** La medición de
  31 runs de `push` (3–4 s) frente a 20 de `pull_request` (4 s a 447 s) la
  sitúa en el evento del PR, no en la cola de runners.
- **`pre-auditoria.md` y `docs/REMEDIACION.md` se leían como el estado
  actual**: ninguno estaba fechado y el segundo hablaba de trabajo «en curso».
  Ahora abren con una nota de alcance que los sitúa en el 2026-11-10 y remite
  al estado vigente.

## Verificación

- `python3 -m pytest tests/ -q` → 285 passed.
- CI en verde en Python 3.11, 3.12, 3.13 y 3.14, más la instalación editable.

## Enlaces

- Changelog completo: [`CHANGELOG.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.3/CHANGELOG.md)
- Proceso de release: [`docs/RELEASES.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.3/docs/RELEASES.md)
- Rama protegida: [`docs/BRANCH_PROTECTION.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.3/docs/BRANCH_PROTECTION.md)
- Contribución: [`CONTRIBUTING.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.3/CONTRIBUTING.md)
