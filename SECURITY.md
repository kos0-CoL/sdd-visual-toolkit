# Política de seguridad

## Versiones soportadas

| Versión | Soporte |
| --- | --- |
| 0.1.x | Correcciones de seguridad |
| Anteriores | Sin soporte |

## Cómo reportar una vulnerabilidad

**No abra un issue público.** Use el reporte privado de GitHub:

1. Abra <https://github.com/kos0-CoL/sdd-visual-toolkit/security/advisories/new>.
2. Describa el problema y, si puede, adjunte una prueba de concepto.

Incluya:

- versión o commit (por ejemplo `v0.1.0` o `git rev-parse --short HEAD`),
- sistema operativo y versión de Python,
- comando o flujo afectado,
- impacto que cree que tiene,
- pasos mínimos para reproducir.

No adjunte datos reales de su proyecto ni credenciales; recorte rutas y
contenido cuando sea posible.

## Qué está en alcance

- Ejecución de comandos a partir de datos del proyecto (rutas, hooks,
  runners) que permita salir del repositorio o escalar privilegios.
- Escritura o borrado fuera de `.specify/` por validación de rutas
  insuficiente (rollback, snapshots, checkpoints).
- Inyección en el servidor MCP o en la extensión de VS Code.
- Exposición de secretos en logs, journal, `export` o mensajes de cierre.

## Qué queda fuera de alcance

- Vulnerabilidades en el código del proyecto que usted está desarrollando.
- La ejecución de runners y hooks que usted mismo configuró: es parte del
  diseño (el motor verifica ejecutando pruebas reales).
- Ataques que requieren una cuenta o una máquina ya comprometidas.
- Denegación de servicio por repositorios enormes.

## Expectativas

- Acuse de recibo a la brevedad posible, sin SLA: el proyecto es voluntario.
- Si el reporte es válido, se corrige y se publica un aviso coordinado con
  la versión afectada; se acredita a quien reportó salvo que prefiera el
  anonimato.
- No se toman represalias por reportes de buena fe.
