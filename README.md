# SDD Visual Toolkit — SPEC v0.1

Herramienta de orquestación del Desarrollo Guiado por Especificaciones.
SPEC de producto: `docs/SPEC-v0.1.md`.

Entrega por requisitos funcionales (§44), uno a uno:

- [x] RF-01 Gestión de requerimientos
- [x] RF-02 Enriquecimiento inicial
- [x] RF-03 Generación de SPEC
- [x] RF-04 Clarificación interactiva
- [x] RF-05 Plan de implementación
- [x] RF-06 Desglose en tareas
- [x] RF-07 Análisis de consistencia
- [x] RF-08 Investigación del repositorio
- [x] RF-09 Ejecución de implementación
- [x] RF-10 Spec Pinning
- [x] RF-11 State Journaling
- [x] RF-12 Checkpoints
- [x] RF-14 Context Split-Streaming
- [x] RF-15 Context Flush
- [x] RF-16 Snapshot Rollback
- [x] RF-17 Análisis AST
- [x] RF-18 Validación de cambios
- [x] RF-19 Testing Harness
- [x] RF-20 Tests unitarios
- [x] RF-21 Tests de integración
- [x] RF-22 Tests generales y de regresión
- [x] RF-23 Tests de aceptación
- [x] RF-24 Validación estructural
- [x] RF-25 Cobertura de tests
- [x] RF-26 Resultados visibles y comparación
- [x] RF-27 Consolidación y cierre de tarea
- [x] RF-28 Protección de pruebas
- [x] RF-29 Trazabilidad SPEC→tests
- [x] RF-30 Historial y trazabilidad
- [x] RF-31 Interfaz visual (tablero)
- [x] RF-32 Árbol de estados
- [x] RF-33 Panel de restricciones
- [x] RF-13 Recuperación de sesiones
- [x] RF-34 Visual AST Diff
- [x] RF-35 Navegación mediante píldoras
- [x] RF-36 CLI independiente (status/implement/history/specs)
- [x] RF-37 Mensajes finales de fase
- [x] RF-38 Capa de integración IDE (export JSON)
- [x] RF-39 Integración con VS Code (paleta + vista + estado)
- [x] RF-40 Adaptadores §30 (servidor MCP + matriz de compatibilidad)
- [x] RF-41 Archivo de instrucciones del agente (§47)
- [x] RF-42 Hooks de agente por evento (§47)
- [x] RF-43 Testing adaptativo multi-lenguaje (§51)

Uso:

```bash
toolkit init
toolkit req add "El dashboard muestra el inventario" --procedencia explicito
toolkit req list
toolkit req show REQ-001
toolkit req set REQ-001 --estado aceptado
```
