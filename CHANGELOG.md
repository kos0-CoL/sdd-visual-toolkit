# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el versionado [SemVer](https://semver.org/lang/es/).

## [No publicado]

Sin cambios pendientes de publicar.

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

[No publicado]: https://github.com/kos0-CoL/sdd-visual-toolkit/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.1
[0.1.0]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.0
