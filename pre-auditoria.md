# Pre-auditoría: SDD Visual Toolkit

> **Alcance del documento.** Inspección estática hecha el 2026-11-10, antes de
> la remediación. Sus cifras, su estado de madurez y su diagnóstico describen
> el repositorio de entonces, no el actual: lo que hoy hay se documenta en
> `README.md`, `CHANGELOG.md` y `docs/REMEDIACION.md`.

Análisis de SDD Visual Toolkit.

Voy a evaluarlo como un producto de ingeniería, no solamente como un repositorio que tiene muchas funcionalidades o una buena presentación.

Hay una distinción importante: que una herramienta declare que controla el desarrollo guiado por especificaciones no significa que realmente pueda garantizarlo. Para comprobar su valor hay que mirar la implementación, las pruebas, los mecanismos de control y lo que sucede cuando un agente intenta saltearse el flujo.

## 1. Primera impresión: qué propone el proyecto

Repositorio: kos0-CoL/sdd-visual-toolkit

El README presenta un orquestador SDD que pretende cubrir el ciclo completo:

- Idea y enriquecimiento
- SPEC y aclaraciones
- Plan técnico y tareas
- Implementación por tareas
- Pruebas, validación y evidencia
- Trazabilidad y recuperación

Lo interesante es que no se limita a generar documentos y tareas. También declara mecanismos de:

- Spec pinning y comparación estructural mediante AST.
- Journal, checkpoints, snapshots y rollback.
- Trazabilidad entre requisitos, pruebas y evidencias.
- CLI, extensión de VS Code y servidor MCP.
- Estado compartido entre interfaces.
- Gates de aprobación humana.

El README declara Python 3.11 o superior, ausencia de dependencias externas y 235 pruebas automatizadas. Son afirmaciones que todavía hay que contrastar con el código.

kos0-CoL/sdd-visual-toolkit · GitHub

Mi primera conclusión: la propuesta tiene un alcance interesante. Su diferenciación potencial no está en generar SPEC o planes —eso ya lo hacen otras herramientas— sino en combinar orquestación, continuidad, inspección de cambios y trazabilidad.

## 2. Comparación con otros toolkits SDD

Tomé como referencias tres proyectos importantes, con filosofías diferentes:

- GitHub Spec Kit: planificación, especificaciones, tareas y convergencia.
- OpenSpec: cambios incrementales y evolución de proyectos existentes.
- BMAD Method: agentes especializados y procesos de desarrollo completos.

También consideré sus repositorios y documentación oficiales.

### Comparación funcional

| Capacidad | SDD Visual | Spec Kit | OpenSpec | BMAD |
|---|---|---|---|---|
| Enriquecimiento de ideas | Sí | Parcial | Explore | Sí |
| Generación de SPEC | Sí | Sí | Sí | Sí |
| Plan técnico | Sí | Sí | Sí | Sí |
| Descomposición en tareas | Sí | Sí | Sí | Sí |
| Gates humanos | Sí | Sí | Revisión flexible | Sí |
| Análisis de consistencia | Sí | Sí | Validación | Sí |
| Verificación posterior | Sí, declarada | Converge | Verify | QA y revisión |
| AST y control estructural | Sí, Python | No es su núcleo | No es su núcleo | No es su núcleo |
| Checkpoints y recuperación | Sí | No es su núcleo | No es su núcleo | Contexto persistente |
| Rollback selectivo | Sí | No es su núcleo | No es su núcleo | No es su núcleo |
| Trazabilidad de evidencia | Sí | Parcial | Historial de cambios | Artefactos y revisión |
| CLI independiente | Sí | Sí | Sí | Sí |
| Integración MCP | Sí, limitada | Ecosistema de integraciones | Integraciones de agentes | Integraciones de agentes |
| Interfaz visual propia | Básica | No es su foco | No es su foco | No es su foco |

Esta tabla compara capacidades declaradas y observables en sus respectivos diseños. No significa que todos los mecanismos tengan el mismo nivel de implementación o garantía.

### ¿Dónde mejora SDD Visual?

1. Control estructural de cambios

Su combinación de pinning, hashes, análisis AST y restricciones por tarea es una diferenciación real respecto de los flujos convencionales de Spec Kit y OpenSpec.

2. Continuidad de trabajo

Journal, snapshots, historial y recuperación están integrados en el motor. No son simplemente documentos que el agente debe recordar.

3. Trazabilidad operativa

Pretende relacionar SPEC, requerimientos, tareas, archivos modificados, pruebas y evidencias.

4. Estado compartido

CLI, extensión y MCP consultan el mismo estado del proyecto. Esto es especialmente interesante para trabajar con diferentes agentes.

La principal oportunidad es que SDD Visual intenta cubrir un espacio que las herramientas tradicionales no priorizan: controlar lo que efectivamente sucede durante la implementación, no solamente organizar lo que debería suceder.

### ¿Dónde pierde frente a los demás?

| Área | Desventaja |
|---|---|
| Madurez | Los otros proyectos tienen comunidades y trayectoria considerablemente mayores. |
| Ecosistema | Spec Kit y OpenSpec tienen más integraciones de agentes documentadas. |
| Flexibilidad de cambios | OpenSpec tiene un modelo de deltas especialmente adecuado para modificar requisitos existentes. |
| Agentes especializados | BMAD ofrece un ecosistema mucho más desarrollado. |
| Compatibilidad | SDD Visual tiene una cobertura de lenguajes y herramientas de análisis más limitada. |
| Experiencia visual | La extensión actual es bastante más sencilla que una verdadera IDE integrada. |

Por ejemplo, OpenSpec permite expresar cambios como ADDED, MODIFIED y REMOVED, algo muy útil cuando el usuario quiere modificar una funcionalidad sin reconstruir toda la especificación.

GitHub+1

Spec Kit, por su parte, tiene un mecanismo de convergencia que vuelve a contrastar la implementación con los artefactos y puede agregar tareas pendientes.

GitHub+1

Veredicto comparativo: SDD Visual tiene ideas diferenciales interesantes, pero todavía no puede considerarse superior a esos proyectos en términos generales.

## 3. Inspección del código real

Esta parte es más importante que la comparación de funcionalidades.

He consultado el árbol completo del repositorio y examiné archivos de implementación, entre ellos:

- core/build.py
- core/harness.py
- core/astcheck.py
- core/pin.py
- core/journal.py
- core/rollback.py
- core/testguard.py
- core/structure.py
- state/store.py
- mcp/server.py
- ide/vscode/extension.js

También contrasté algunos módulos con sus respectivas pruebas.

### Código real encontrado

Ejecución no verificada

Aclaro algo importante: esta es una inspección estática del código publicado. No he ejecutado el repositorio en un entorno local. Por lo tanto, no voy a presentar los 235 tests declarados como si los hubiera ejecutado y confirmado.

### 3.1. Lo que está realmente implementado

| Subsistema | Evaluación |
|---|---|
| Generación de SPEC | Implementación funcional identificable |
| Enriquecimiento | Implementación propia |
| Planificación | Implementación propia |
| Generación de tareas | Implementación propia |
| Máquina de estados | Implementación propia |
| Persistencia | JSON y JSONL |
| Journaling | Implementado |
| Checkpoints | Implementados |
| Rollback selectivo | Implementado |
| Spec pinning | Implementado para estructura Python |
| AST | Implementación real, con limitaciones |
| Testing Harness | Implementación real, con limitaciones |
| CLI | Implementación propia |
| Extensión VS Code | Implementación básica real |
| Servidor MCP | Implementación real, con herramientas limitadas |

No parece ser simplemente una colección de prompts o documentación.

Tiene un núcleo Python propio, módulos separados y pruebas dirigidas a funcionalidades concretas.

Pero encontré problemas importantes.

### 3.2. Problemas encontrados en el código

#### Problema 1 — Cierre de tareas sin pruebas (Crítico)

Archivo: core/build.py

La función ejecutar_pruebas() contiene esta lógica:

```python
if not objetivos:
    return True, "sin pruebas ejecutables todavía..."
```

Esto significa que una tarea puede superar la comprobación de pruebas aunque no tenga ningún test ejecutable.

Más aún: cuando existen tests, el cierre utiliza directamente unittest, independientemente del runner detectado por el Testing Harness.

Consecuencia: un proyecto JavaScript, Go o Rust puede tener un arnés general que detecta su runner, pero el cierre de tarea no necesariamente utiliza ese mismo mecanismo.

Esto es una inconsistencia importante entre dos subsistemas.

Mi recomendación: separar tres resultados:

- PASSED: pruebas ejecutadas y satisfactorias.
- FAILED: pruebas ejecutadas y fallidas.
- NOT_VERIFIED: no existen pruebas ejecutables.

Una tarea no debería declararse verificada en el tercer caso.

#### Problema 2 — AST demasiado limitado (Alto)

Archivo: core/pin.py

El análisis utiliza el AST de Python y registra principalmente:

- Funciones y clases públicas.
- Parámetros.
- Tipos de retorno.
- Imports.
- Variables globales.

No compara de forma semántica el comportamiento interno de las funciones.

Por ejemplo, una función podría conservar exactamente la misma firma y cambiar completamente su comportamiento.

El análisis podría no detectar esa modificación como una desviación estructural.

Tampoco proporciona una protección equivalente para JavaScript, TypeScript, Rust, Go y otros lenguajes.

Consecuencia: el AST es útil como detector de cambios estructurales, pero no demuestra que el código respete la SPEC.

#### Problema 3 — Rollback y validación de rutas (Alto)

Archivo: core/rollback.py

El rollback construye rutas a partir de los archivos registrados en una tarea:

```python
destino_final = Path(raiz) / rel
```

No veo en este módulo una normalización y validación explícita que garantice que las rutas permanezcan dentro del proyecto.

Si se introduye una ruta maliciosa o incorrecta, con componentes ../, existe un riesgo potencial de escritura fuera del repositorio durante la restauración.

Esto requiere comprobar también los puntos de entrada y los controles de rutas de los demás módulos.

Recomendación: resolver las rutas, verificar que pertenezcan a la raíz autorizada y controlar enlaces simbólicos antes de leer, copiar o eliminar archivos.

#### Problema 4 — Persistencia y durabilidad (Medio)

Archivos: state/store.py y core/journal.py.

Hay una buena base: escrituras temporales, renombrado atómico y sincronización del journal.

Sin embargo:

- El almacenamiento general JSON no hace fsync del archivo antes del reemplazo.
- Tampoco sincroniza explícitamente el directorio después del renombrado.
- El historial JSONL crece indefinidamente.
- No hay un almacén transaccional compartido para todas las operaciones.

Esto no significa que el almacenamiento esté roto. Significa que sus garantías de recuperación ante fallos son inferiores a lo que podría ofrecer una persistencia transaccional diseñada para ello.

#### Problema 5 — Integración MCP limitada (Medio)

Archivo: mcp/server.py

Encontré tres herramientas MCP:

- exportar_estado
- siguiente
- tablero

Las tres son de consulta.

Esto permite que un agente conozca el estado del toolkit, pero no le proporciona una interfaz MCP completa para gestionar el ciclo de trabajo.

Consecuencia: la integración existe realmente, pero todavía no equivale a un motor de orquestación accesible completamente desde MCP.

### 3.3. Otro problema importante: el análisis del repositorio

Archivo: core/plan.py.

La investigación del proyecto utiliza recorridos recursivos de archivos, detección de extensiones, lectura de manifiestos y análisis AST de fuentes Python.

Es una solución razonable para repositorios pequeños y medianos.

Sin embargo, hay limitaciones:

- No hay un análisis profundo y equivalente para todos los lenguajes declarados.
- La clasificación de dependencias utiliza reglas heurísticas.
- La selección de componentes relacionados con la SPEC utiliza coincidencias nominales.
- No veo un mecanismo de caché incremental en el análisis mostrado.

Esto puede provocar análisis incompletos y trabajo repetido en repositorios grandes.

## 4. ¿Qué tan optimizado está?

Hay que separar eficiencia de diseño y rendimiento medido.

No tengo benchmarks ejecutados, por lo que no sería serio asignarle milisegundos o porcentajes de rendimiento.

Mi evaluación estática es la siguiente:

| Aspecto | Evaluación |
|---|---|
| Dependencias externas | Muy bueno |
| Modularidad | Buena |
| Simplicidad de instalación | Buena |
| Ejecución de pruebas | Mejorable |
| Persistencia a gran escala | Mejorable |
| Análisis de repositorios grandes | No demostrado |
| Compatibilidad multilenguaje | Limitada |
| Recuperación ante fallos | Parcialmente sólida |

### Cuellos de botella que conviene investigar

1. Procesos de testing: ejecutar cada archivo de pruebas en un proceso separado puede incrementar el tiempo total considerablemente.
2. Recorrido del repositorio: volver a recorrer y calcular hashes de muchos archivos en cada verificación puede resultar costoso.
3. Historial: almacenar todos los eventos sin compactación puede degradar progresivamente la consulta.
4. Análisis AST: volver a parsear archivos sin caché desperdicia trabajo cuando hay pocos cambios.
5. CLI y extensión: la extensión consulta el estado mediante procesos externos. No es necesariamente malo, pero puede generar latencia y consultas repetidas.

No recomiendo introducir Redis, bases de datos externas o infraestructura adicional solamente para resolver estos puntos. Primero mediría los problemas reales.

## 5. ¿El proyecto es realmente un orquestador de IA?

Esta es una distinción fundamental.

El código implementa un motor que organiza fases, administra tareas, conserva el estado y verifica resultados.

Pero el flujo de implementación descrito en core/build.py dice expresamente:

El humano implementa, el motor verifica.

Es decir, el sistema puede preparar el trabajo para un agente y controlar sus resultados, pero no encontré evidencia suficiente de un motor propio que dirija autónomamente la ejecución de los agentes.

La diferencia es importante:

| Capacidad | Estado observado |
|---|---|
| Preparar instrucciones para agentes | Sí |
| Generar contexto de implementación | Sí |
| Administrar tareas | Sí |
| Verificar cambios | Parcial |
| Ejecutar pruebas | Sí, con limitaciones |
| Conectarse mediante MCP | Sí |
| Invocar agentes y coordinar su ejecución | No demostrado |
| Interceptar todas las escrituras de los agentes | No demostrado |
| Impedir cambios fuera de alcance en tiempo real | No demostrado |

Esto no invalida el proyecto. Pero sí cambia su definición actual.

Hoy es principalmente un gestor y verificador de flujos SDD con integraciones para agentes, no un orquestador autónomo completo.

Y conviene que esa distinción esté claramente reflejada en la documentación.

## 6. Características que tiene y oportunidades de mejora

Esta es la extracción funcional consolidada. Distingo lo que ya aparece en el código de lo que todavía es una oportunidad.

| Característica | Estado | Evolución recomendada |
|---|---|---|
| Enriquecimiento de ideas | Implementada | Mejorar calidad y validación |
| Gestión de requerimientos | Implementada | Versionado y evolución |
| SPEC | Implementada | Comparación entre versiones |
| Clarify | Implementada | Preguntas adaptativas |
| Investigación de repositorios | Implementada | Análisis semántico multilenguaje |
| Plan técnico | Implementado | Planificación incremental |
| Tareas y dependencias | Implementadas | Dependencias más flexibles |
| Spec pinning | Parcial | AST y análisis semántico |
| Testing Harness | Parcial | Runner unificado |
| Trazabilidad | Parcial | Evidencia verificable por criterio |
| Checkpoints | Implementados | Consistencia transaccional |
| Recuperación | Implementada | Pruebas de interrupciones reales |
| Rollback | Implementado | Seguridad de rutas y archivos |
| Extensión VS Code | Básica | Interfaz interactiva |
| MCP | Básico | Herramientas operativas |
| Adaptadores de agentes | Parciales | Integraciones específicas |
| Colaboración entre agentes | No demostrada | Coordinación y concurrencia |

### Las 10 mejoras que considero más valiosas

Las ordenaría así:

### P0

1. Corregir la validación de pruebas

El cierre debe distinguir entre pruebas satisfactorias, fallidas y no ejecutadas. Un resultado no verificado nunca debe convertirse en éxito.

2. Seguridad de ejecución y archivos

Validar rutas, enlaces simbólicos y argumentos de comandos. La extensión debería ejecutar procesos con argumentos separados, no construir comandos de terminal concatenando entradas.

3. Verificación real de implementaciones

Comprobar cambios de comportamiento, no solamente firmas AST. Incorporar evidencia vinculada a criterios de aceptación.

### P1

4. Testing multilenguaje unificado

Un mismo contrato para pytest, unittest, npm, Go, Rust y otros runners, tanto en ejecución como en cierre de tareas.

5. Integración efectiva con agentes

Permitir que diferentes agentes reciban tareas, devuelvan resultados y reporten cambios sin depender de un proveedor concreto.

6. MCP operativo

Ampliar las herramientas MCP para consultar, preparar y gestionar tareas mediante las mismas reglas del motor central.

7. Diferenciación entre cambios requeridos y mejoras sugeridas

Detectar oportunidades de mejora durante la implementación sin incorporarlas automáticamente a la tarea actual.

### P2

8. Análisis incremental

Caché de análisis, hashes reutilizables y detección de archivos afectados para reducir trabajo repetido.

9. Interfaz visual de verdad

Visualizar cambios, dependencias, pruebas, restricciones y trazabilidad sin depender constantemente de la terminal.

10. Persistencia escalable

Consolidar operaciones de estado, recuperación, integridad y compactación del historial.

## 7. Madurez del proyecto

Hay un dato que no conviene pasar por alto.

En la consulta del repositorio, GitHub mostraba:

- 2 commits.
- 0 estrellas.
- 0 forks.
- Sin releases publicadas.
- Sin licencia reconocida por los metadatos del repositorio.
- Fecha de creación: 10 de noviembre UTC, correspondiente todavía al 9 de noviembre en Argentina.

kos0-CoL/sdd-visual-toolkit · GitHub

Esto indica que estamos ante un proyecto muy reciente.

No significa que el código sea malo. Significa que todavía no tiene evidencia de uso prolongado, compatibilidad en distintos entornos ni madurez comunitaria.

Tampoco encontré una configuración de GitHub Actions en el árbol consultado. Por lo tanto, en esa instantánea no había evidencia de una integración continua que ejecutase automáticamente esos tests ante cada modificación.

### Mi valoración técnica

Evaluación cualitativa de la inspección estática, no métricas de benchmark.

| Dimensión | Valoración |
|---|---|
| Idea y diferenciación | Alta |
| Modularidad | Buena |
| Cobertura funcional | Amplia |
| Calidad de implementación | Irregular |
| Seguridad | Necesita correcciones |
| Optimización | Razonable para prototipo |
| Madurez | Muy temprana |
| Preparación para producción | Insuficiente |
| Potencial de evolución | Alto |

## 8. Mi conclusión: ¿hay una mejora real frente al resto?

Sí, hay una oportunidad de mejora real, pero todavía no hay una superioridad técnica demostrada.

La característica más interesante de SDD Visual no es la generación de especificaciones.

Eso ya está bastante cubierto por los competidores.

Su verdadero valor potencial es la integración de cuatro capacidades:

1. Intención: qué pidió el usuario y qué se aprobó.
2. Implementación: qué modificó realmente el agente.
3. Verificación: qué se probó y qué resultados obtuvo.
4. Continuidad: cómo recuperar y continuar el trabajo.

El resultado: que el usuario pueda trabajar con cualquier agente y saber qué se hizo, por qué se hizo, qué funciona y qué falta.

Lo que yo haría con este proyecto:

No intentaría convertirlo en otro Spec Kit ni en otro BMAD.

Tampoco agregaría más gates, más aprobaciones o más documentos porque sí.

Lo desarrollaría alrededor de tres objetivos:

1. Mejorar la experiencia: que el toolkit ayude a trabajar con IA de manera más cómoda y eficiente.
2. Verificar lo que realmente programa: evidencia de código, pruebas, cambios y cumplimiento de requisitos.
3. Mantener continuidad y compatibilidad: distintos IDE, agentes y modelos compartiendo un único estado.

La recuperación, el pinning y la trazabilidad ya proporcionan una base interesante para eso.

Mi recomendación final: conservar la arquitectura actual, corregir primero los defectos de verificación y seguridad encontrados, y después concentrar el desarrollo en la integración real con agentes y la experiencia visual.

No hace falta agregar veinte funcionalidades nuevas. Hace falta conseguir que las que ya existen funcionen correctamente y se integren como un producto coherente.

Ese es el camino que podría convertir a SDD Visual Toolkit en algo verdaderamente diferente de los demás.
