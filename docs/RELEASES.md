# Proceso de release

## Versionado

SemVer `MAYOR.MENOR.PARCHE`:

- **MAYOR**: cambios incompatibles en la CLI, en el formato de `.specify/`
  o en el protocolo MCP.
- **MENOR**: capacidad nueva compatible.
- **PARCHE**: correcciones y documentación.

`pyproject.toml` es la fuente de la versión; `CHANGELOG.md` la fuente de
las notas.

## Checklist antes de etiquetar

1. `python3 -m pytest tests/ -q` en verde.
2. CI en verde en todas las versiones soportadas, sobre el commit que se va
   a etiquetar.
3. `version` de `pyproject.toml` actualizada.
4. `CHANGELOG.md` con la versión publicada y su fecha: las viñetas pasan de
   `[No publicado]` a la sección nueva.
5. `docs/release-notes-vX.Y.Z.md` escrito, con sus enlaces apuntando ya al
   tag `vX.Y.Z`.
6. Smoke test de la CLI:

   ```bash
   python3 cli/main.py --help
   ```

7. Revisar que no se versionen secretos ni el `.specify/` de un proyecto real.
8. Mergeado en `main`, con el árbol limpio y al día:

   ```bash
   git status --short      # sin salida
   git pull --ff-only
   ```

9. La comprobación previa, que es la puerta del proceso:

   ```bash
   python3 scripts/verificar_release.py --previo X.Y.Z   # sin la "v"
   ```

   Revisa que el tag esté libre en local y en `origin` (son inmutables), que
   el árbol esté limpio, que `HEAD` sea `origin/main`, que `pyproject.toml` y
   la primera sección con fecha del CHANGELOG coincidan con la versión, que
   `[No publicado]` quede vacía, que los enlaces del pie del CHANGELOG
   apunten a la versión nueva, que las notas existan con enlaces al tag y que
   la versión sea posterior a la última etiquetada.

   Este es el momento de corregir: después de `git push origin vX.Y.Z` ya no
   se puede, porque los tags `v*` son inmutables.

Las notas se escriben **antes** de etiquetar, no después: el paso 9 las
comprueba y la release publica ese mismo archivo tal cual. `[No publicado]`
no se borra: se deja arriba y vacía, lista para el ciclo siguiente, como pide
Keep a Changelog. `scripts/verificar_release.py` busca la primera sección
**con fecha**, así que la vacía no lo confunde.

## Publicar

El tag debe apuntar al commit que ya contiene el CHANGELOG, la versión de
`pyproject.toml` y las notas; nunca a un árbol con cambios sin confirmar.

```bash
git tag -a vX.Y.Z -m "vX.Y.Z — resumen de la versión"
git push origin vX.Y.Z
gh release create vX.Y.Z --title "vX.Y.Z" --verify-tag \
  --notes-file docs/release-notes-vX.Y.Z.md
```

`--notes-file` no es opcional: sin él GitHub autogenera un «What's Changed»,
las notas del repo no se publican y la verificación posterior lo marca como
fallo. `--verify-tag` impide que `gh` cree el tag por su cuenta si no se
empujó: la release cuelga del tag ya verificado. Una release solo se anuncia
cuando CI está verde y los artefactos corresponden al tag.

## Verificar tras publicar

Crear el tag no termina la release. El script del repo lo comprueba todo de
una vez, sin instalar nada y sin modificar nada (sin `--previo`, que es el
modo de antes de etiquetar):

```bash
python3 scripts/verificar_release.py          # versión de pyproject.toml
python3 scripts/verificar_release.py 0.1.2    # o una versión concreta
```

Revisa, para `vX.Y.Z`:

1. que el tag existe en local y en `origin`, que es anotado y que ambos
   apuntan al mismo objeto;
2. que ese tag contiene la versión en `pyproject.toml` y como primera
   entrada con fecha del CHANGELOG;
3. que el commit etiquetado tiene todos sus checks en verde y terminados: un
   tag sobre un commit con el CI rojo no pasa, y tampoco uno sin checks;
4. que la release no quedó en borrador ni marcada como previa;
5. que el cuerpo publicado es el de `docs/release-notes-vX.Y.Z.md`, sin
   contar espacios ni saltos finales: si se creó sin `--notes-file`, GitHub
   autogenera un «What's Changed» y las notas del repo no se leen;
6. que todo enlace de `docs/release-notes-vX.Y.Z.md` a un repositorio sea
   `.../blob/<tag>/<ruta>` en este mismo repositorio, con la ruta existente
   en esa ref —no en `main`, que sigue avanzando—: se rechazan los relativos,
   los `/tree/`, otras refs y los enlaces a otro repositorio. Sin `blob` solo
   pasan las páginas de GitHub que no son ficheros (`compare`, `commits`,
   `releases`, `tags`) y el `git clone` de un bloque de código.

`v0.1.0` es la excepción documentada: sus notas enlazaban en relativo, GitHub
las resolvía contra la raíz del repo y las cuatro daban 404, y su tag no se
puede corregir. Para esa versión el script compara el cuerpo con
`docs/release-notes-v0.1.0.md` del árbol, ya arreglado, en lugar de con la
copia del tag (`NOTAS_DEL_ARBOL` en `scripts/verificar_release.py`). Las
notas se escriben con enlaces absolutos desde 0.1.1 justamente por esto.

Sale con 0 si todo pasa y con 1 listando los fallos. Si la release quedó
como borrador, publíquela con `gh release edit vX.Y.Z --draft=false`. Si el
cuerpo no coincide, actualícelo con `gh release edit vX.Y.Z --notes-file
docs/release-notes-vX.Y.Z.md`. Un `404` en un enlace es un enlace roto:
corrija las notas y actualícelas igual. El tag no se toca, porque los tags
`v*` son inmutables.

## Comunidad

- **Issues**: incluya versión de Python, sistema operativo y el comando
  exacto que falló.
- **Pull requests**: ver `CONTRIBUTING.md`.
- No hay canal de soporte con SLA; el proyecto se mantiene de forma
  voluntaria.
