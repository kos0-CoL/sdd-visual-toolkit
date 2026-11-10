# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el versionado [SemVer](https://semver.org/lang/es/).

## [No publicado]

### Añadido

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

[No publicado]: https://github.com/kos0-CoL/sdd-visual-toolkit/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.2
[0.1.1]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.1
[0.1.0]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.0
