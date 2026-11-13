# Plan de Mejoras — SDD Visual Toolkit

**Origen:** Auditoría técnica entregada al usuario (debILidades y recomendaciones).
**Fecha:** 13 de noviembre de 2026
**Versión base:** 0.2.1
**Alcance:** Solo las 6 áreas seleccionadas por el usuario (no todas las del reporte).

---

## 0. Resumen de áreas a intervenir

| ID | Área | Prioridad | Archivos principales | Qué se va a hacer |
|----|------|-----------|---------------------|-------------------|
| A1 | Verificación semántica (más allá de firmas AST) | Alta | `core/pin.py` | Detectar cambios de cuerpo interno con hash + AST profundo, no solo firma pública |
| A2 | Runners multilenguaje (npm/go/cargo) | Alta | `core/harness.py`, `core/build.py` | Que el cierre de tarea use el runner detectado del repo, no solo unittest para Python |
| A3 | Compatibilidad IDEs no VS Code | Alta | `ide/COMPATIBILIDAD.md`, `cli/commands/comandos.py` | Documentar estado real, añadir verificaciones y fallbacks para Cursor/Windsurf/Cline/Kilo/Claude/Antigravity |
| A4 | Compactación automática del journal | Media | `core/journal.py`, `core/build.py` | Ejecutar `compactar()` al cerrar plan o por umbral de eventos |
| A5 | Persistencia transaccional compartida | Media | `state/store.py` | Almacén transacional para operaciones de estado (commit/rollback de múltiples escrituras) |
| A6 | Modo gestor vs orquestador autónomo configurable | Alta | `core/build.py`, `state/store.py`, `cli/main.py` | Alternativa configurable para variar entre "humano implementa / motor verifica" y "orquestador autónomo" |

---

## 1. Área A1 — Verificación semántica en core/pin.py

### Problema actual
`core/pin.py::_simbolos` extrae solo firmas públicas, imports, globales y retornos. No compara el comportamiento interno de las funciones. Una función puede conservar su firma y cambiar completamente su lógica sin ser detectada como desviación.

### Objetivo
Añadir detección de cambios de cuerpo interno (código entre la firma y el `return`/bloque) para marcar desviación clase B con mayor precisión.

### Cambios en `core/pin.py`

1. **Nueva función `_cuerpo_funcion(nodo)`**: extrae el AST del cuerpo de una función/clase (sin la firma) y devuelve su hash.
2. **Ampliar `snapshot_archivo`**: incluir `cuerpos` (dict nombre → hash del cuerpo) además de `publicas`, `imports`, etc.
3. **Ampliar `verificar_cambios`**: cuando `actual["sha"] != anterior["sha"]` pero las firmas públicas son iguales, comparar hashes de cuerpos. Si difieren, desviación B con detalle "cuerpo interno modificado".
4. **Ampliar `asegurar_baseline`**: guardar `cuerpos` en el baseline.

### Tests nuevos
- `tests/test_pin.py::test_cambio_de_cuerpo_sin_firma_es_B` — función con misma firma pero cuerpo distinto → desviación B.
- `tests/test_pin.py::test_sin_cambios_no_hay_desviaciones` — mismo cuerpo y firma → sin desviación.

---

## 2. Área A2 — Runners multilenguaje (npm/go/cargo)

### Problema actual
`core/build.py::ejecutar_pruebas` usa `core.harness.correr_archivos` que ya detecta runners (pytest/unittest/npm/go/cargo), pero `registrar_done` en `core/build.py` solo verifica que haya archivos `tests/` y llama a `correr_archivos`. Para repos no-Python, los archivos de test de Python no existen y el cierre devuelve `sin_pruebas` (NOT_VERIFIED), bloqueando el cierre aunque el repo use npm/go/cargo con tests en otro lenguaje.

### Objetivo
Que el cierre de tarea respete el runner detectado del repo: si es npm/go/cargo, buscar archivos de test según la convención de ese lenguaje (`*.test.js`, `*_test.go`, `*_test.rs`) y ejecutar con el runner correspondiente antes de permitir el cierre.

### Cambios

**`core/harness.py`**:
1. Nueva función `archivos_test_por_runner(raiz, archivos_tarea)` que mapea extensiones de test por runner:
   - npm: `*.test.js`, `*.test.ts`, `*.spec.js`, `*.spec.ts`
   - go: `*_test.go`
   - cargo: cualquier `*.rs` bajo `tests/`
   - pytest/unittest: `tests/*.py`

**`core/build.py`**:
1. Modificar `ejecutar_pruebas` para usar `archivos_test_por_runner` en lugar de filtrar solo `tests/*.py`.
2. El timeout para runners externos (npm/go/cargo) se ajusta a 180s.

### Tests nuevos
- `tests/test_build.py::test_ejecutar_pruebas_solo_declara_sin_pruebas` — verifica que no hay tests sin runner.
- `tests/test_harness.py::test_detecta_unittest_y_respeta_pytest_del_repo` — mapeo de runner del repo.

---

## 3. Área A3 — Compatibilidad IDEs no VS Code

### Problema actual
`ide/COMPATIBILIDAD.md` marca Cursor, Windsurf, Antigravity, Cline, Kilo y Claude Code como "sin probar". Los comandos de barra se generan pero no se verifica que funcionen dentro de cada cliente.

### Objetivo
Documentar el estado real, añadir verificaciones automáticas de generación de comandos por cliente, y proveer fallbacks cuando un cliente no soporte una superficie específica.

### Cambios

**`ide/COMPATIBILIDAD.md`**:
1. Añadir columna "Estado real" con fecha de verificación o "pendiente".
2. Añadir notas específicas por cliente (Cursor: `$ARGUMENTS` vs prompt, Windsurf: Cascade, etc.).

**`cli/commands/comandos.py`**:
1. Nueva opción `--verificar-cliente <cliente>` que compruebe que los archivos generados para ese cliente existen y tienen la ruta absoluta correcta.
2. Mejorar el mensaje de error cuando un cliente no está soportado.

### Tests nuevos
- `tests/test_compatibilidad_formato.py::test_las_rutas_de_lo_incluido_existen` — genera comandos para cada cliente y verifica que existan.
- `tests/test_compatibilidad_formato.py::test_tablero_lee_el_estado_antiguo` — `--verificar-cliente` detecta rutas muertas.

---

## 4. Área A4 — Compactación automática del journal

### Problema actual
`core/journal.py::compactar` existe pero se invoca manualmente. El historial JSONL crece indefinidamente si no se compacta periódicamente.

### Objetivo
Ejecutar compactación automática al cerrar un plan (`cierre`) o cuando el historial supera un umbral (por defecto 500 eventos).

### Cambios

**`core/journal.py`**:
1. Nueva función `debe_compactar(raiz, umbral=500)` que retorna True si el historial supera el umbral.
2. Nueva función `compactar_si_necesario(raiz, plan_id=None, umbral=500)` que ejecuta `compactar` solo si supera el umbral.

**`core/build.py`**:
1. En `registrar_done` y `registrar_fail`, después de registrar el evento, llamar a `compactar_si_necesario` con el `plan_id` de la tarea.

### Tests nuevos
- `tests/test_journal.py::test_compactar_conserva_ultimos_por_plan` — con menos de 500 eventos no compacta; con más sí.
- `tests/test_build.py::test_done_y_fail_registran_en_diario` — verificar que registrar_done déclenche compactación.

---

## 5. Área A5 — Persistencia transaccional compartida

### Problema actual
`state/store.py::_escritura_atomica` escribe un archivo de forma atómica, pero no hay un almacén transacional que agrupe múltiples escrituras (commit/rollback de varias operaciones de estado como una sola unidad).

### Objetivo
Agregar `TransaccionStore` que permita agrupar múltiples escrituras y confirmarlas o revertirlas como una sola unidad atómica.

### Cambios en `state/store.py`

1. **Clase `TransaccionStore`**:
   - `__enter__` / `__exit__` (context manager).
   - `escribir(ruta, contenido)` — acumula operaciones en memoria.
   - `commit()` — ejecuta todas las escrituras atómicamente (si una falla, deshace las ya hechas restaurando backups).
   - `rollback()` — descarta todas las operaciones pendientes.

2. **Función `transaccion(raiz)`** — factory que retorna una `TransaccionStore`.

### Tests nuevos
- `tests/test_store.py::test_escritura_atomica_no_deja_temporales` — múltiples escrituras en un commit.
- `tests/test_store.py::test_escritura_texto_atomica` — rollback no escribe nada.
- `tests/test_store.py::test_fsync_dir_no_falla_sin_soporte` — si una escritura falla, las anteriores se deshacen.

---

## 6. Área A6 — Modo gestor vs orquestador autónomo configurable

### Problema actual
El flujo es rígidamente "humano implementa, motor verifica" (RF-09). No hay alternativa para equipos que quieran un comportamiento más autónomo donde el motor sugiera o ejecute cambios directamente.

### Objetivo
Agregar una configuración `modo_operacion` con dos valores:
- `gestor` (por defecto): humano implementa, motor verifica.
- `orquestador`: el motor puede sugerir cambios de implementación y el agente puede aplicarlos con aprobación explícita.

### Cambios

**`state/store.py`**:
1. Agregar `MODO_GESTOR = "gestor"` y `MODO_ORQUESTADOR = "orquestador"`.
2. Agregar `leer_modo_operacion(raiz)` y `escribir_modo_operacion(raiz, modo)` que persistan el modo en el estado del proyecto.

**`core/build.py`**:
1. `registrar_done` acepta parámetro opcional `modo`. Si es `orquestador`, permite cierre con `sin_pruebas` solo si hay una nota de justificación (no bloquea, pero advierte).
2. `sugerir` ya existe; en modo `orquestador` las sugerencias pueden incluir un parche propuesto (diff) que el agente puede aplicar.

**`cli/main.py`**:
1. Nuevo subcomando `modo [gestor|orquestador]` para consultar/cambiar el modo actual.

### Tests nuevos
- `tests/test_store.py::test_escribir_json_sincroniza_archivo_y_directorio` — persistencia del modo.
- `tests/test_build.py::test_done_sin_pruebas_no_cierra` — permite cierre con nota en modo orquestador.
- `tests/test_mcp.py::test_registrar_resultado_fallida` — `modo gestor` / `modo orquestador` / `modo` (consulta).

---

## 7. Cronograma de ejecución

| Paso | Área | Acción | Criterio de aceptación |
|------|------|--------|------------------------|
| 1 | A1 | Modificar `core/pin.py` (hash de cuerpo) | Tests nuevos pasan |
| 2 | A2 | Modificar `core/harness.py` y `core/build.py` (runners) | Tests nuevos pasan |
| 3 | A3 | Actualizar `ide/COMPATIBILIDAD.md` y `cli/commands/comandos.py` | Tests nuevos pasan |
| 4 | A4 | Modificar `core/journal.py` y `core/build.py` (compactación) | Tests nuevos pasan |
| 5 | A5 | Agregar `TransaccionStore` en `state/store.py` | Tests nuevos pasan |
| 6 | A6 | Agregar modo operativo configurable | Tests nuevos pasan |
| 7 | Todas | Ejecutar suite completa `pytest tests/ -q` | 484+ tests pasando, 0 fallos |

---

## 8. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Cambios en `core/pin.py` rompen tests existentes de pinning | Alto | Ejecutar `tests/test_pin.py` antes y después de cada cambio |
| Runners npm/go/cargo no disponibles en entorno de prueba | Medio | Mockear `detectar_runner` en tests; no instalar lenguajes reales |
| Transacción parcial deja estado inconsistente | Alto | `commit()` con deshace automático de escrituras previas si falla |
| Cambio de modo operativo afecta flujos existentes | Medio | `gestor` es el valor por defecto; no cambia comportamiento actual |

---

**Siguiente paso:** Ejecutar el área A1 (verificación semántica en `core/pin.py`).
