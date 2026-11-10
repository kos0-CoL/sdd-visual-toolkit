# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el versionado [SemVer](https://semver.org/lang/es/).

## [No publicado]

### Corregido

- `pip install -e .` fallaba con «Multiple top-level packages discovered»;
  ahora `pyproject.toml` declara el backend y los paquetes de espacio de
  nombres, y el comando `toolkit` queda disponible tras instalar.

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

[No publicado]: https://github.com/kos0-CoL/sdd-visual-toolkit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.0
