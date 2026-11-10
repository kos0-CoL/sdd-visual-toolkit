# SDD Visual Toolkit v0.1.0

Primera versión funcional del orquestador de Desarrollo Guiado por
Especificaciones: convierte una idea en SPEC, plan, tareas, código verificado
y evidencia trazable, con gates humanos y estado recuperable.

## Destacados

- **Ciclo completo**: `enrich` → `specify` → `clarify` (Gate 1) → `plan`
  (Gate 2) → `tasks` (Gate 3) → `analyze` (Gate 4) → implementación
  incremental supervisada.
- **Cierre honesto**: una tarea no se marca completada sin archivos objetivo
  y pruebas ejecutables. El resultado es `PASSED`, `FAILED` o
  `NOT_VERIFIED`; nunca se asume verde.
- **Spec pinning y AST diff**: congela firmas e interfaces y delata cambios
  estructurales no autorizados.
- **Testing adaptativo**: pytest/unittest, npm, Go y Rust, por capas
  (unitarios, integración, regresión, aceptación y estructural).
- **Estado recuperable**: journal, checkpoints semánticos, snapshots por
  tarea y rollback con validación de rutas.
- **Trazabilidad**: SPEC → tarea → test → evidencia, con tablero, árbol de
  estados y píldoras de navegación.
- **Integraciones**: CLI completa, extensión de VS Code, servidor MCP stdio
  con herramientas de lectura y operativas, y hooks por evento
  (`tarea_abierta`, `tarea_cerrada`, `sugerencia`).

## Instalación

Requisitos: **Python ≥ 3.11** y Git. Cero dependencias en tiempo de
ejecución.

```bash
git clone https://github.com/kos0-CoL/sdd-visual-toolkit.git
cd sdd-visual-toolkit
python3 cli/main.py --help
```

## Primeros pasos

```bash
python3 cli/main.py init
python3 cli/main.py enrich "Quiero un dashboard para gestionar un kiosco"
python3 cli/main.py siguiente
```

## Cambios

### Añadido

- Fases `enrich`, `specify`, `clarify`, `plan`, `tasks`, `analyze` e
  implementación incremental supervisada.
- Verificación real de cierre (`PASSED` / `FAILED` / `NOT_VERIFIED`).
- Spec pinning con AST diff y validación estructural.
- Testing harness por capas y testing adaptativo multi-lenguaje.
- Journal, checkpoints, snapshots, rollback y validación de rutas.
- Trazabilidad SPEC → tarea → test → evidencia, tablero y árbol de estados.
- Sugerencias de mejora separadas del alcance de la tarea.
- CLI, extensión de VS Code, servidor MCP stdio y hooks por evento.
- Integración continua en Python 3.11–3.14, licencia MIT, `CONTRIBUTING.md`
  y proceso de release documentado.

### Cambiado

- Persistencia durable con `fsync` de archivo y directorio.
- Compactación del historial JSONL.
- Análisis de repositorio con caché incremental.
- Una sola invocación del runner por fase de testing.

## Limitaciones conocidas

- El ciclo es **humano-implementa / motor-verifica**: la herramienta no
  escribe código de forma autónoma.
- La verificación manual en Antigravity y VS Code sigue pendiente en sus
  entornos reales.
- `pytest` es la única dependencia, y solo para la suite de desarrollo.

## Enlaces

- Changelog completo: [`CHANGELOG.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.0/CHANGELOG.md)
- Contribución: [`CONTRIBUTING.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.0/CONTRIBUTING.md)
- Proceso de release: [`docs/RELEASES.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.0/docs/RELEASES.md)
- SPEC de producto: [`docs/SPEC-v0.1.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.0/docs/SPEC-v0.1.md)

**Full Changelog**: https://github.com/kos0-CoL/sdd-visual-toolkit/commits/v0.1.0

Licencia: MIT.
