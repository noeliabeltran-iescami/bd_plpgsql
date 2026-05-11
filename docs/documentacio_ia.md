# Documentació amb IA

Aquesta pàgina descriu com generar documentació automàtica per a objectes PL/pgSQL utilitzant una capa de IA.

## Què fa?

El script `scripts/generate_plpgsql_documentation.py` analitza fitxers SQL amb definicions de funcions, procediments, triggers i altres objectes PL/pgSQL.

Pot crear un arxiu Markdown amb:

- nom de l'objecte
- tipus d'objecte
- signatura
- retorn
- codi SQL
- documentació generada automàticament amb IA si s'activa l'opció `--ai`

## Com utilitzar-lo

1. Instal·la les dependències (opcional si vols activar IA):

```bash
pip install -r requirements.txt
```

2. Executa el script per generar documentació a partir d'una carpeta o fitxer SQL:

```bash
python scripts/generate_plpgsql_documentation.py --src . --output docs/plpgsql_documentation.md
```

3. Per generar descripcions amb IA, defineix la variable d'entorn `OPENAI_API_KEY` i afegeix l'opció `--ai`:

```bash
set OPENAI_API_KEY=tu_api_key
python scripts/generate_plpgsql_documentation.py --src . --output docs/plpgsql_documentation.md --ai
```

## Resultat

El fitxer generat s'emmagatzema per defecte a `docs/plpgsql_documentation.md`. Pots afegir aquest fitxer al teu lloc MkDocs o utilitzar-lo com a documentació complementària.

## Notes

- Si no tens `openai` instal·lat o no tens la clau, el script seguirà generant una documentació bàsica basada en l'extracció d'objectes.
- El script està pensat per funcionar amb fitxers SQL i PL/pgSQL en format estàndard.
