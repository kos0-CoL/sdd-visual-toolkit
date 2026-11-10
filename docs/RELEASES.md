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
2. CI en verde en todas las versiones soportadas.
3. `CHANGELOG.md` con la versión publicada y su fecha: las viñetas pasan de
   `[No publicado]` a la sección nueva.
4. `version` de `pyproject.toml` actualizada.
5. Smoke test de la CLI:

   ```bash
   python3 cli/main.py --help
   ```

6. Revisar que no se versionen secretos ni el `.specify/` de un proyecto real.

`[No publicado]` no se borra: se deja arriba y vacía, lista para el ciclo
siguiente, como pide Keep a Changelog. `scripts/verificar_release.py` busca
la primera sección **con fecha**, así que la vacía no lo confunde.

## Verificar antes de etiquetar

El mismo script comprueba, sobre el árbol y los tags, todo lo que se puede
saber antes de crear el tag:

```bash
python3 scripts/verificar_release.py --previo 0.1.3
```

Revisa que el tag esté libre en local y en `origin` (los tags son
inmutables), que el árbol esté limpio, que `HEAD` sea `origin/main`, que
`pyproject.toml` y la primera sección con fecha del CHANGELOG coincidan con
la versión, que `[No publicado]` quede vacía, que los enlaces del pie del
CHANGELOG apunten a la versión nueva, que las notas existan con sus enlaces
al tag y que la versión sea posterior a la última etiquetada.

Este es el momento de corregir: después de `git push origin vX.Y.Z` ya no
se puede, porque los tags `v*` son inmutables.

## Publicar

El tag debe apuntar al commit que ya contiene el CHANGELOG y la versión de
`pyproject.toml`; nunca a un árbol con cambios sin confirmar.

```bash
git tag -a v0.1.0 -m "v0.1.0 — primera versión funcional"
git push origin v0.1.0
```

Luego cree la release en GitHub con las notas del CHANGELOG (borrador en
`docs/release-notes-vX.Y.Z.md`). Una release solo se anuncia cuando CI está
verde y los artefactos corresponden al tag.

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
3. que la release no quedó en borrador ni marcada como previa;
4. que cada enlace `.../blob/<ref>/<ruta>` de `docs/release-notes-vX.Y.Z.md`
   apunta al tag —no a `main`, que sigue avanzando— y que la ruta existe en
   esa ref.

Sale con 0 si todo pasa y con 1 listando los fallos. Si la release quedó
como borrador, publíquela con `gh release edit vX.Y.Z --draft=false`. Un
`404` en un enlace es un enlace roto: corrija las notas y actualícelas con
`gh release edit vX.Y.Z --notes-file docs/release-notes-vX.Y.Z.md`. El tag
no se toca, porque los tags `v*` son inmutables.

## Comunidad

- **Issues**: incluya versión de Python, sistema operativo y el comando
  exacto que falló.
- **Pull requests**: ver `CONTRIBUTING.md`.
- No hay canal de soporte con SLA; el proyecto se mantiene de forma
  voluntaria.
