# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el versionado [SemVer](https://semver.org/lang/es/).

## [No publicado]

### Añadido

- La matriz de `ide/COMPATIBILIDAD.md` separa extensión y comandos de barra
  por cliente, deja dicho que ninguno está probado dentro del IDE y detalla,
  cliente por cliente, qué hay que abrir y qué anotar para cerrarlo.
- Cada release adjunta `sdd-visual-toolkit-X.Y.Z.vsix`, la extensión del IDE
  empaquetada con `vsce` desde el mismo commit que el tag, y el README
  documenta ese camino de instalación en lugar de la depuración desde el
  código.
- La comprobación previa a etiquetar exige que `ide/vscode/package.json`
  declare la versión del release, para que el `.vsix` no se adjunte con otro
  número.
- `toolkit comandos` escribe los comandos de barra del flujo en la carpeta
  que cada agente lee (`.claude/skills/`, `.cursor/commands/`,
  `.github/prompts/`, `.windsurf/workflows/`, `.agents/skills/`), con la ruta
  absoluta de la CLI adentro: `/sdd-plan-gate` ejecuta `plan --gate SPEC`.
- El verificador posterior exige que el commit etiquetado tenga todos sus
  checks en verde y terminados, para que un tag sobre un commit roto no pase
  por bueno.
- La comprobación previa a etiquetar exige que el commit de `HEAD` tenga
  todos sus checks terminados y en verde: un tag sobre un `main` con el CI
  roto o a medias ya no llega a crearse.
- El fixture de compatibilidad de 0.1.0 incluye ya las aclaraciones, el
  checkpoint de `TASK-001`, el estado del journal y el enriquecimiento del
  que salieron sus 21 requerimientos, así que la prueba ejercita también
  `specify --revise`.

### Corregido

- `build` y su alias `implement` respondían «sin informe para PLAN-999;
  ejecute `analyze PLAN-999` primero» cuando el plan no existía: ahora dicen
  «plan inexistente» y el Quality Gate 4 sigue igual para los planes que sí
  existen.
- `pin --task` decía «línea base registrada» también cuando reutilizaba la
  que ya existía; ahora distingue las dos cosas y, al reutilizarla, aclara
  que no se vuelve a registrar.
- Los comandos de la CLI avisan cuando el ID no existe en vez de morir con un
  traceback: `ast`, `diff`, `historia`, `reporte`, `test`, `validate`,
  `flush`, `pin`, `recover`, `traza` y `clarify` capturaban solo el error de
  su propio módulo, no el de cargar la SPEC, el plan o la tarea.
- `pin --task` guarda la línea base y ya no revienta con `NameError` por una
  llamada a `_guardar_pin` que nadie importaba; tampoco borra las
  desviaciones ya registradas.
- `specify --revise` copiaba la SPEC a `.specify/spec_history/` antes de
  comprobar que su ENR de origen existiera: si faltaba, dejaba una copia
  huérfana y moría con un traceback. Ahora arma la revisión primero y avisa
  con un `⛔` sin escribir nada.
- El verificador solo miraba los enlaces `blob` de las notas y dejaba pasar
  el resto: un relativo o un `/tree/` no lo hacían fallar. Ahora todo enlace
  a un repositorio debe ser `blob` del tag en el repositorio propio, y se
  rechazan los relativos, los `tree` y los que apuntan a otro repositorio.
- Las notas de 0.1.0 enlazaban en relativo y la página de la release los
  resolvía contra la raíz del repo: los cuatro daban 404. Ahora apuntan a
  `blob/v0.1.0`, y el verificador compara esa versión con las notas del árbol
  porque su tag es inmutable.

## [0.1.4] — 2026-11-10

Versión de mantenimiento: sin cambios en la CLI, en el motor ni en el
formato de `.specify/`, así que sigue siendo compatible con proyectos
creados con 0.1.0 a 0.1.3. Es PARCHE por la misma razón que 0.1.3: lo
que cambia son las herramientas de release, las pruebas y la
documentación.

### Añadido

- `scripts/verificar_release.py --previo` comprueba antes de crear el tag
  lo que se revisaba a mano y tarde: tag libre en local y en `origin`, árbol
  limpio, `HEAD` en `origin/main`, versión y CHANGELOG en el árbol,
  `[No publicado]` vacía, enlaces del pie a la versión nueva, notas con
  enlaces al tag futuro y versión posterior a la última etiquetada.
- El fixture de compatibilidad incluye la línea base del pin y dos snapshots
  de `TASK-001` escritos por 0.1.0, y la prueba los ejercita con `validate`
  y `rollback`: restaurar el estado previo deja la validación limpia,
  restaurar el intento fallido la deja en OBSERVADO con un cambio de cuerpo,
  y el estado antiguo se restaura sin tocar nada ajeno.

### Corregido

- `verificar_release.py` daba por buena una release cuyo cuerpo no era el de
  `docs/release-notes-vX.Y.Z.md`: solo miraba que las notas existieran en el
  tag. Ahora compara el cuerpo publicado —sin espacios ni saltos finales— y
  señala el `gh release edit --notes-file` para arreglarlo. Aplicado hacia
  atrás, **v0.1.0 queda marcada**: su cuerpo tiene enlaces absolutos y el
  archivo del tag, relativos.
- `docs/RELEASES.md` describía el orden al revés: las notas aparecían
  después del tag, la release se creaba sin `--notes-file` —GitHub autogenera
  el «What's Changed»— y el modo `--previo` quedaba fuera del checklist, así
  que se podía etiquetar sin haberlo ejecutado. Ahora las notas se escriben
  antes de etiquetar, el último paso del checklist es
  `verificar_release.py --previo X.Y.Z` y la release se crea con
  `--verify-tag` y `--notes-file`.

## [0.1.3] — 2026-11-10

Versión de mantenimiento: documentación, pruebas y herramientas. Sin cambios
en el motor ni en el formato de `.specify/`: es compatible con proyectos
creados con 0.1.0 a 0.1.2.

### Añadido

- `tests/test_compatibilidad_formato.py` abre con la CLI actual un estado
  real creado por 0.1.0 (fixture sin regenerar, con su procedencia
  documentada) y comprueba que se lee, que leer no lo reescribe y que
  escribir conserva lo anterior. Así el CI avisa si el formato deja de ser
  compatible, sin depender del juicio de quien publica.
- `docs/RELEASES.md` incluye el paso posterior a publicar: comprobar que el
  tag anotado existe en el remoto y apunta al commit con la versión, que la
  release no quedó en borrador y que los enlaces de las notas resuelven en
  la ref del tag.
- El workflow de CI acepta `workflow_dispatch`, para arrancar los checks
  sobre una rama cuando GitHub tarda en crear el run del PR, sin duplicar
  runs cerrando y reabriendo, y solo si no existe ya uno para ese commit.
  `CONTRIBUTING.md` y `docs/BRANCH_PROTECTION.md` lo explican.
- `scripts/verificar_release.py` hace esas comprobaciones en un solo
  comando: tag anotado local y remoto, versión en `pyproject.toml` y
  CHANGELOG dentro del tag, release publicada y enlaces de las notas
  resueltos en la ref del tag. Sin dependencias: solo usa `git` y `gh`.

### Corregido

- `status` y `siguiente` avisaban «Pruebas con rojo: corrija y repita el
  test» aunque la última corrida estuviera en verde: `core/navigation.py`
  no consultaba el resultado. Ahora recomienda cerrar la tarea en curso o
  seguir con la próxima, y solo habla de rojo cuando lo hay.
- `pre-auditoria.md` y `docs/REMEDIACION.md` se leían como el estado actual:
  ninguno estaba fechado y el segundo decía «revisión en curso». Ahora abren
  con una nota de alcance que los sitúa en el 2026-11-10 y remite al estado
  vigente, y la frase sobre la falta de CI pasa al tiempo de entonces.
- `docs/RELEASES.md` pedía el CHANGELOG «sin dejar `No publicado`», lo que
  se lee como borrar la sección; ahora dice que las viñetas pasan a la
  sección nueva y que `[No publicado]` queda arriba, vacía.
- `CONTRIBUTING.md` seguía recomendando `--upgrade pip` al preparar el
  entorno, cuando el README y la CI no lo hacen y las notas de 0.1.2
  registran haberlo retirado por coste (4,0 s → 2,0 s de mediana por job).
- `ide/COMPATIBILIDAD.md` describía el MCP con tres herramientas de solo
  lectura y citaba como evidencia `tests/test_mcp.py`, que exige las seis:
  las tres de lectura y las tres operativas.
- `docs/BRANCH_PROTECTION.md` atribuía la espera del CI a GitHub en general.
  La medición de 31 runs de `push` (3–4 s, salvo un commit empujado diez
  minutos después de crearse) frente a 20 de `pull_request` (4 s a 447 s)
  sitúa la demora en el evento del PR, no en la cola de runners.
- El README anunciaba 269 pruebas en dos frases mientras su badge y la
  suite tenían 284. Los conteos se escriben a mano y solo el badge tenía
  prueba; ahora `tests/test_readme.py` compara también las menciones
  «N tests» de la prosa.

## [0.1.2] — 2026-11-10

Versión de mantenimiento y herramientas: sin cambios en el motor ni en el
formato de `.specify/`.

### Añadido

- `toolkit --version` imprime la versión, tomada de `pyproject.toml` en el
  árbol de fuentes y de los metadatos del paquete en una instalación normal.
  El servidor MCP declara esa misma versión en lugar de una constante.
- `docs/BRANCH_PROTECTION.md` describe las reglas de `main`, el motivo de
  cada una y cómo replicarlas; enlazado desde `CONTRIBUTING.md`.
- Caché de las dependencias de pip en la CI, con clave por versión de Python
  y hash de `requirements-dev.txt`.
- Pruebas que mantienen alineadas la versión de `pyproject.toml` con la
  primera entrada del CHANGELOG y el badge de tests del README con la suite.
- Los tags `v*` son inmutables: un ruleset impide moverlos o borrarlos una
  vez publicados. Los releases nuevos se siguen creando igual; detalles en
  `docs/BRANCH_PROTECTION.md`.

### Cambiado

- La CI ejecuta la suite en paralelo con `pytest-xdist -n 2` (16,1 s → 10,0 s
  por job en la medición); `pytest-xdist` queda como dependencia de
  desarrollo en `CONTRIBUTING.md`.
- La protección de `main` usa un ruleset de repositorio en vez de la
  protección clásica: todo cambio debe entrar por pull request, sin exención
  para administradores. Detalles en `docs/BRANCH_PROTECTION.md`.
- Las dependencias de desarrollo (`pytest`, `pytest-xdist`) se declaran en
  `requirements-dev.txt`; la CI y `CONTRIBUTING.md` instalan desde ahí en vez
  de repetir la lista, y la caché de pip usa esa clave.
- La CI ya no actualiza pip antes de instalar: el paso de instalación baja de
  4,0 s a 2,0 s de mediana por job (24 jobs antes, 20 después).

### Corregido

- El tablero buscaba el estado `"en curso"`, pero `build` marca `en_curso`:
  la «Tarea actual» nunca aparecía. `status`, `tablero` y `siguiente` usan
  ahora la constante del motor, con una prueba de regresión.
- El servidor MCP informaba `0.1.0` después de publicar la 0.1.1.
- El badge de tests del README anunciaba 259 pruebas frente a una suite
  mayor.
- `README.md`: las instrucciones ejecutaban `pytest` sin instalarlo (un
  entorno limpio fallaba en ese paso), decían 259 pruebas, el ejemplo
  de sesión mostraba un formato de salida que ya no existe y el rango de RF
  omitía las primeras.

## [0.1.1] — 2026-11-10

Versión de mantenimiento: no cambia el comportamiento del motor ni el
formato de `.specify/`.

### Añadido

- Código de conducta (Contributor Covenant 2.1, español) con el canal
  privado de reporte y enlaces desde `README.md` y `CONTRIBUTING.md`.
- Plantillas de issues para errores y propuestas, con selector que enlaza la
  guía de contribución y la SPEC.
- Plantilla de pull request con tipo, alcance, checklist de verificación y
  evidencia.
- `SECURITY.md` con versiones soportadas, alcance y expectativas; el reporte
  privado de vulnerabilidades queda habilitado en el repositorio.
- `CODEOWNERS` para solicitar revisión automática al dueño en PR de terceros.
- Job de CI `instalación editable`: instala el paquete y ejecuta `toolkit`
  fuera del árbol del repositorio. Queda exigido en `main` junto con la suite
  en las cuatro versiones soportadas.

### Corregido

- `pip install -e .` fallaba con «Multiple top-level packages discovered»;
  ahora `pyproject.toml` declara el backend y los paquetes de espacio de
  nombres, y el comando `toolkit` queda disponible tras instalar.
- `.gitignore` cubre los artefactos de empaquetado (`*.egg-info/`, `build/`,
  `dist/`).

## [0.1.0] — 2026-11-10

Primera versión funcional: ciclo SDD completo desde una idea hasta código
verificado, con gates humanos y estado recuperable.

### Añadido

- Fases `enrich`, `specify`, `clarify` (Quality Gate 1), `plan`
  (Quality Gate 2), `tasks` (Quality Gate 3), `analyze` (Quality Gate 4)
  e implementación incremental supervisada.
- Verificación real de cierre: una tarea no se completa sin archivos
  objetivo y pruebas ejecutables (`PASSED` / `FAILED` / `NOT_VERIFIED`).
- Spec pinning con AST diff, detección de cambios de cuerpo y validación
  estructural.
- Testing harness por capas (unitarios, integración, regresión,
  aceptación, estructural) y testing adaptativo multi-lenguaje
  (pytest/unittest, npm, Go, Rust).
- Journal, checkpoints semánticos, snapshots por tarea y rollback con
  validación de rutas.
- Trazabilidad SPEC → tarea → test → evidencia, tablero, árbol de
  estados, píldoras de navegación y mensajes de cierre.
- Sugerencias de mejora separadas del alcance de la tarea (evento
  `sugerencia` y registro en `.specify/sugerencias/`).
- CLI completa, extensión de VS Code, servidor MCP stdio con
  herramientas de lectura y operativas, y hooks propios por evento.
- Integración continua en GitHub Actions: suite completa en Python
  3.11, 3.12, 3.13 y 3.14 para cada push a `main` y cada pull request.
- Licencia MIT (`LICENSE`), `CONTRIBUTING.md` y `docs/RELEASES.md` con el
  flujo de contribución y el proceso de release.
- Cero dependencias externas en tiempo de ejecución.

### Cambiado

- Persistencia más durable: `fsync` de archivo y directorio tras el
  renombrado atómico, y compactación del historial JSONL.
- Análisis de repositorio con caché incremental y detección de archivos
  afectados.
- Cada fase de testing se ejecuta en una sola invocación del runner.

[No publicado]: https://github.com/kos0-CoL/sdd-visual-toolkit/compare/v0.1.4...HEAD
[0.1.4]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.4
[0.1.3]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.3
[0.1.2]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.2
[0.1.1]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.1
[0.1.0]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.0
