# SDD Visual Toolkit v0.1.4

Versión de mantenimiento. Sin cambios en la CLI, en el motor ni en el formato
de `.specify/`: es compatible con proyectos creados con 0.1.0 a 0.1.3. Lo que
cambia es la verificación del release, el fixture de compatibilidad y el
proceso documentado.

## Añadido

- **`scripts/verificar_release.py --previo`**: comprueba antes de crear el tag
  lo que hasta ahora se revisaba a mano y después de empujar, cuando un tag ya
  es inmutable: tag libre en local y en `origin`, árbol limpio, `HEAD` en
  `origin/main`, versión y primera sección con fecha del CHANGELOG en el
  árbol, `[No publicado]` vacía, enlaces del pie del CHANGELOG a la versión
  nueva, notas con enlaces al tag futuro y versión posterior a la última
  etiquetada.

  ```bash
  python3 scripts/verificar_release.py --previo 0.1.4
  ```

- **Fixture de compatibilidad con pin y snapshots**: el estado de 0.1.0
  incluye ahora la línea base del build y dos instantáneas de `TASK-001`
  escritas por esa versión, así que `validate` y `rollback` se ejercitan con
  estado antiguo y no solo con el actual.

## Corregido

- **El verificador no miraba el cuerpo de la release**: comprobaba que las
  notas existieran en el tag, no que se hubieran publicado. Una release creada
  sin `--notes-file` pasaba en verde con un «What's Changed» autogenerado.
  Ahora compara el cuerpo publicado con `docs/release-notes-vX.Y.Z.md`,
  ignorando los espacios y saltos finales que añade GitHub, y señala el
  comando para corregirlo. Aplicado hacia atrás, v0.1.0 queda marcada: su
  cuerpo tiene enlaces absolutos y el archivo del tag, relativos.
- **`docs/RELEASES.md` describía el orden al revés**: las notas aparecían
  después del tag, la release se creaba sin `--notes-file` y el modo previo no
  estaba en el checklist. Ahora las notas se escriben antes de etiquetar, la
  comprobación previa es el último paso del checklist y la release se crea con
  `--verify-tag` y `--notes-file`.
- **Dos viñetas del CHANGELOG estaban dentro de la sección 0.1.3**, que se
  publicó antes de que existieran: vuelven a la sección que les toca.

## Verificación

- `python3 -m pytest tests/ -q` → 316 passed, 2 subtests passed.
- CI en verde en Python 3.11, 3.12, 3.13 y 3.14, más la instalación editable.
- `python3 scripts/verificar_release.py --previo 0.1.4` en verde antes de
  crear el tag.

## Enlaces

- Changelog completo: [`CHANGELOG.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.4/CHANGELOG.md)
- Proceso de release: [`docs/RELEASES.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.4/docs/RELEASES.md)
- Rama protegida: [`docs/BRANCH_PROTECTION.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.4/docs/BRANCH_PROTECTION.md)
- Contribución: [`CONTRIBUTING.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.4/CONTRIBUTING.md)
