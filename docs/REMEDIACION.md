# Plan de Remediación — SDD Visual Toolkit

> **Alcance del documento.** Registro del plan ejecutado y cerrado el
> 2026-11-10 en la 0.1.0. Los conteos de pruebas de cada etapa (`238` a `259`
> passed) son los de su momento; el estado vigente está en `README.md` y
> `CHANGELOG.md`.
>
> Derivado de `pre-auditoria.md` (§1–§8) y de la revisión de código hecha
> entonces (`core/`, `cli/`, `state/`, `mcp/`, `ide/`).

## 1. Alcance y metodología

- **Fuentes primarias:** `pre-auditoria.md` (auditoría de producto e ingeniería).
- **Fuentes secundarias:** revisión de código de los módulos señalados
  (`core/build.py`, `core/harness.py`, `core/pin.py`, `core/rollback.py`,
  `core/validate.py`, `core/acceptance.py`, `core/journal.py`, `state/store.py`,
  `mcp/server.py`, `core/plan.py`).
- **Metodología:** cada hallazgo se remedia en una etapa; cada etapa cierra con
  entregables (archivos), cambios concretos y tests correspondientes; la
  verificación de cada etapa usa `python3 -m pytest tests/ -q`.

## 2. Mapa de hallazgos de la auditoría → etapas de remediación

| ID en `pre-auditoria.md` | Severidad | Punto | RF | Etapa |
|---|---|---|---|---|
| Proceso 1 — Cierre sin pruebas | Crítico | `core/build.py::ejecutar_pruebas` → `True` con "sin pruebas ejecutables todavía" | RF-09 / §11, RF-18 / §48 | **E0** |
| Runner del cierre hardcodeado a unittest | Crítico/medio | `registrar_done` → `ejecutar_pruebas` usa unittest fijo | RF-19 / §18, RF-43 / §51 | **E0** |
| Problema 3 — Rollback y validación de rutas | Alto | `Path(raiz) / rel` sin validación | RF-16 / §16 | **E1** |
| Problema 2 — AST demasiado limitado (firma) | Alto | `core/pin.py::_simbolos` no compara cuerpo | RF-10 / §12, RF-34 / §34 | **E2** |
| Problema 5 — MCP solo lectura | Medio | `mcp/server.py`: 3 tools (`exportar_estado`, `siguiente`, `tablero`) | RF-40 / §30 | **E3** |
| Problema 4 — Persistencia/durabilidad | Medio | `state/store.py` sin fsync dir; JSONL sin compaction | RF-11 / §13, RF-13 / §35 | **E5** |
| Problema 3.3 — Análisis repo heurístico | Medio | `core/plan.py` | RF-05 / §8 | **E5** |
| Problema 4 — Optimización testing (proceso por archivo) | Medio | harness/acceptance | RF-19 / §18 | **E5** |
| Sección 5 — Orquestación autónoma de agentes | Medio | humano implementa, motor verifica | RF-09 / §11 | **E4** |
| Sección 6 — Mejoras sugeridas vs requeridas | Medio | no distinguir | RF-07 / §17 | **E4** |
| Sección 7 — Madurez | Medio | CI, licencia, releases | — | **E6** |

## 3. Plan de remediación por etapas

### 3.1 — Etapa 0 — Cierre honesto: `PASSED` / `FAILED` / `NOT_VERIFIED` (Crítico)

**Hallazgo:** `core/build.py::ejecutar_pruebas` devolvía `(True, "sin pruebas ejecutables todavía…")`; `registrar_done` completaba la tarea con `pruebas_ok=True`.

**Entregables:**
1. `core/build.py`: `ejecutar_pruebas` → `(estado, salida)` con `estado ∈ {“pasadas”, “fallidas”, “sin_pruebas”}`; delega a `core.harness.correr_archivos`.
2. `core/harness.py`: nuevo `correr_archivos(raiz, archivos, fase, timeout)` — runner detectado (pytest/unittest; suite npm/go/cargo).

**Tests correspondientes:**
- `tests/test_build.py`: `test_ejecutar_pruebas_solo_declara_sin_pruebas`; `test_done_sin_pruebas_no_cierra` (BuildError, task en curso).
- Verificación: `python3 -m pytest tests/test_build.py tests/test_consolidation.py tests/test_harness.py tests/test_harness_adaptativo.py -q`

**Estado:** IMPLEMENTADA — suite de esos tests en verde (33 passed); suite completa 238 passed.

### 3.2 — Etapa 1 — Seguridad de rutas en rollback (Alto)

**Hallazgo:** `core/rollback.py::restaurar` construye `Path(raiz) / rel` sin
validación; ruta con `../` podía escribir fuera del proyecto.

**Entregable:** `core/rollback.py` — `_copia_segura(raiz, rel)` (resolve +
containment + sin symlink); `restaurar` rechaza rutas inseguras.

**Tests:** `tests/test_rollback.py::test_restaurar_rechaza_rutas_fuera_del_proyecto`.
**Verificación:** `python3 -m pytest tests/test_rollback.py -q` (7 passed).

### 3.3 — Etapa 2 — Verificación semántica + runner unificado (Alto)

**Hallazgos:** (a) AST solo compara firmas; (b) capa de aceptación fuerza
`unittest` salvo pytest.

**Entregables:**
1. `core/pin.py::verificar_cambios`: al cambiar el hash del archivo sin cambio
   de firma pública → desviación `B` (cuerpo interno, justificar §12.B).
2. `core/acceptance.py::evaluar`: dispatch runner-aware (pytest vs unittest)
   para casos Given-When-Then.

**Tests:** `tests/test_pin.py` (firma cambiada, cuerpo sin firma), `tests/test_acceptance.py`,
`tests/test_harness_adaptativo.py`, `tests/test_validate.py`.
**Verificación:** `python3 -m pytest tests/ -q` (238 passed).

### 3.4 — Etapa 3 — MCP operativo (Medio)

**Hallazgo:** `mcp/server.py` expone solo herramientas de lectura.

**Entregable:** `mcp/server.py` — añadir herramientas operativas
(`asignar_tarea`, `registrar_resultado`, `marcar_completada`) sobre el motor
central; las de lectura siguen disponibles.
**Cambios:** `HERRAMIENTAS_OPERATIVAS`, `_cargar_tarea` (índice de tareas §9),
`_operar` (asignar → `build.marcar_en_curso`; completada → `build.registrar_done`
con gate NOT_VERIFIED; fallida → `build.registrar_fail` + nota) y despacho en
`_llamar`; cada operación persiste con `tasks._persistir`.
**Tests:** `tests/test_mcp.py` (tools/list actualizado; asignar+cerrar con
pruebas reales; `registrar_resultado` fallida; `task_id` ausente y tarea
inexistente declaran error).
**Verificación:** `python3 -m pytest tests/test_mcp.py -q` (6 passed);
suite completa `python3 -m pytest tests/ -q` (242 passed).

**Estado:** IMPLEMENTADA.

### 3.5 — Etapa 4 — Agente/orquestación y mejoras requeridas vs sugeridas (Medio)

**Hallazgo:** flujo humano implementa / motor verifica (intencional, RF-09);
diferenciar cambios requeridos de mejoras sugeridas (RF-07).

**Decisión de alcance:** la orquestación sigue siendo humano-implementa /
motor-verifica; E4 no introduce agentes autónomos. Las herramientas MCP
operativas de E3 cubren recibir tarea, devolver resultado y reportar cambios
sin proveedor concreto.

**Entregables:**
1. `core/plan.py` — `Sugerencia` + registro propio en
   `.specify/sugerencias/<PLAN>.json`: `registrar_sugerencia`,
   `listar_sugerencias`, `decidir_sugerencia` (solo `aprobada`/`descartada`,
   decisión humana explícita). No crea PLAN ni tareas.
2. `core/build.py` — `sugerir(tarea, raiz, plan_id, texto, origen)`: registra
   la mejora y verifica que `archivos`, `dependencias` y `criterio` de la tarea
   quedaron intactos (§40).
3. `core/hooks.py` — nuevo evento `sugerencia` (+ `SDD_SUGERENCIA`) para que
   IDE/agente observen la mejora; un hook que falla se declara, no bloquea.

**Tests:** `tests/test_plan.py` (`TestSugerencias`: registro fuera de plan y
tareas, texto vacío, decisión explícita); `tests/test_hooks.py`
(`TestHookSugerencia`: evento con alcance intacto y hook roto declarado).
**Verificación:** `python3 -m pytest tests/test_plan.py tests/test_hooks.py -q`
(15 passed); suite completa `python3 -m pytest tests/ -q` (247 passed).

**Estado:** IMPLEMENTADA.

### 3.6 — Etapa 5 — Optimización y persistencia (P2)

**Hallazgos:** fsync de directorio, compaction JSONL, caché de análisis,
un solo proceso por suite.

**Entregables:**
1. `state/store.py` — `_escritura_atomica` hace `flush` + `fsync` del archivo
   antes del renombrado y `_fsync_dir` sincroniza el directorio después;
   sin soporte de fsync de directorio (p. ej. Windows) se declara y no rompe.
2. `core/journal.py` — `compactar(raiz, plan_id=None, conservar=200)`:
   conserva los últimos N eventos **por plan**, deja intactos los demás y
   reescribe el JSONL de forma atómica (temp + `fsync` + `os.replace` +
   fsync de directorio). Sin exceso no reescribe; `conservar=0` purga.
3. `core/plan.py` — análisis incremental: `_mapa_archivos` (tamaño + mtime),
   `_huella`, caché en `.specify/cache/analisis.json` reutilizada cuando la
   huella no cambió, e `archivos_afectados()` para ver cambiados/eliminados.
   Solo escribe caché si el proyecto ya tiene `.specify/`; una caché corrupta
   se ignora y se recalcula.
4. `core/harness.py` — `correr()` ejecuta todos los objetivos de una fase en
   **una sola invocación** (antes abría un proceso por archivo); conserva el
   marcador `FALLA` para no ocultar rojo.

**Tests:** `tests/test_journal.py` (compaction por plan, plan aislado, no-op,
valor negativo); `tests/test_plan.py` (`TestCacheAnalisis`: reutilización,
invalidación por cambio, sin `.specify`, `usar_cache=False`);
`tests/test_store.py` (fsync de archivo + directorio, sin temporales, texto
atómico, falta de soporte); `tests/test_harness.py` (una sola invocación).
**Verificación:** `python3 -m pytest tests/test_store.py tests/test_journal.py
tests/test_plan.py tests/test_harness.py -q` (33 passed); suite completa
`python3 -m pytest tests/ -q` (259 passed).

**Estado:** IMPLEMENTADA.

### 3.7 — Etapa 6 — Madurez (P2)

**Hallazgos:** CI, licencia, releases, comunidad (pre-auditoría §7: sin
GitHub Actions, sin licencia reconocida, sin releases).

**Entregables:**
1. `.github/workflows/ci.yml` — CI en push a `main` y pull requests;
   matriz Python 3.11–3.14; instala pytest y corre `pytest tests/ -q`
   con `fail-fast: false` y permisos de solo lectura.
2. `LICENSE` — MIT (titular `kos0-CoL`, año 2026); `pyproject.toml`
   declara `license = { text = "MIT" }`.
3. `CHANGELOG.md` — Keep a Changelog + SemVer, con `0.1.0` consolidada
   (etapas E0–E6) y la sección `No publicado` reabierta y vacía.
4. `CONTRIBUTING.md` — entorno, suite, reglas de diseño (solo stdlib,
   no inventar resultados, humano implementa/motor verifica), flujo de PR
   y licencia de las contribuciones.
5. `docs/RELEASES.md` — versionado, checklist previo al tag, publicación y
   expectativas de comunidad.
6. `README.md` — badges de tests y licencia, MCP/hooks actualizados a E3/E4
   y sección «Contribuir».

**Tests:** la etapa no agrega lógica de producto; la verificación es la
suite existente más la validación del workflow.
**Verificación:** YAML del workflow cargado sin errores (4 versiones, 4
pasos); `python3 cli/main.py --help` OK; suite completa
`python3 -m pytest tests/ -q` (259 passed). CI real queda a cargo de GitHub
en el primer push (no ejecutable en este entorno).

**Estado:** IMPLEMENTADA (licencia MIT asumida; cambiar titular/tipo es
editar `LICENSE` y `pyproject.toml`).

## 4. Resumen de entregables por etapa y comandos de verificación

| Etapa | Archivo(s) | Tests | Comando |
|---|---|---|---|
| E0 | `core/build.py`, `core/harness.py` | `tests/test_build.py`, `tests/test_consolidation.py`, `tests/test_harness*.py` | `python3 -m pytest tests/ -q` |
| E1 | `core/rollback.py` | `tests/test_rollback.py` | `python3 -m pytest tests/test_rollback.py -q` |
| E2 | `core/pin.py`, `core/acceptance.py` | `tests/test_pin.py`, `tests/test_acceptance.py`, `tests/test_harness_adaptativo.py`, `tests/test_validate.py` | `python3 -m pytest tests/ -q` |
| E3 | `mcp/server.py` | `tests/test_mcp.py` | `python3 -m pytest tests/test_mcp.py -q` |
| E4 | `core/plan.py`, `core/build.py`, `core/hooks.py` | `tests/test_plan.py`, `tests/test_hooks.py` | `python3 -m pytest tests/ -q` |
| E5 | `state/store.py`, `core/journal.py`, `core/plan.py`, `core/harness.py` | `tests/test_store.py`, `tests/test_journal.py`, `tests/test_plan.py`, `tests/test_harness.py` | `python3 -m pytest tests/ -q` |
| E6 | `LICENSE`, `.github/workflows/ci.yml`, `CHANGELOG.md`, `CONTRIBUTING.md`, `docs/RELEASES.md`, `pyproject.toml`, `README.md` | suite existente | `python3 -m pytest tests/ -q` |

## 5. Fuentes de comparación consultadas

- GitHub Spec Kit (`github/spec-kit`): OK — riguroso, gates, converge.
- OpenSpec (`Fission-AI/OpenSpec`): OK — fluido, deltas ADDED/MODIFIED/REMOVED.
- BMAD (`bmad-code/...`): fetch falló (404) — verificar slug.
