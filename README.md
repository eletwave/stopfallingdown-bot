# stopfallingdown-bot

Automazione gratuita basata su GitHub Actions per preparare e pubblicare post testuali su Instagram per `@stopfallingdown`.

## Flusso

1. Il bot legge `phrases.json` e sceglie una frase non ancora usata nel ciclo corrente.
2. Genera automaticamente un'immagine JPEG 1080×1080 con sfondo nero, testo bianco effetto consumato e firma `@STOPFALLINGDOWN`.
3. Compone la caption e gli hashtag in base alla categoria della frase.
4. Salva l'immagine nel repository pubblico e usa il relativo URL pubblico per la pubblicazione.
5. Pubblica tramite Instagram API.
6. Aggiorna `state.json` e `published.jsonl`, evitando di ripetere una frase finché la banca non è stata completata.
7. Se una pubblicazione fallisce, `pending.json` rimane disponibile e il run successivo ritenta lo stesso post.

## File principali

- `phrases.json` — banca delle frasi.
- `state.json` — ID delle frasi già pubblicate nel ciclo corrente.
- `bot.py` — generatore grafico e client Instagram API.
- `.github/workflows/daily-instagram.yml` — automazione giornaliera.
- `generated/` — immagini create automaticamente.
- `published.jsonl` — storico delle pubblicazioni riuscite.

## Secrets richiesti

Apri il repository su GitHub e vai in:

**Settings → Secrets and variables → Actions → New repository secret**

Aggiungi:

- `IG_USER_ID` — ID dell'account Instagram professionale usato dall'API.
- `IG_ACCESS_TOKEN` — access token con i permessi necessari alla pubblicazione.

Opzionale:

- `META_API_VERSION` — versione della Graph API da usare. Se assente, il codice usa `v23.0` come fallback configurabile.

Non inserire mai token o password direttamente nei file del repository.

## Orario

Il workflow è configurato per partire ogni giorno alle **20:37, fuso Europe/Rome**.

Il workflow può essere avviato anche manualmente dalla scheda **Actions**.

## Primo test senza pubblicazione

1. Apri **Actions**.
2. Seleziona **Daily Instagram Post**.
3. Premi **Run workflow**.
4. Lascia `dry_run` su `true`.
5. Al termine scarica l'artifact `stopfallingdown-preview` per controllare la grafica.

Il dry run non consuma una frase e non pubblica nulla.

## Primo test reale

Dopo aver configurato `IG_USER_ID` e `IG_ACCESS_TOKEN`:

1. Apri **Actions → Daily Instagram Post → Run workflow**.
2. Imposta `dry_run` su `false`.
3. Avvia il workflow.

Se la pubblicazione riesce, il bot registra l'ID della frase in `state.json` e il media ID restituito da Instagram in `published.jsonl`.

## Aggiungere nuove frasi

Aggiungi nuovi oggetti a `phrases.json` mantenendo un `id` numerico univoco, una `category` e un `text` completo.

Esempio:

```json
{"id": 61, "category": "crescita", "text": "Una nuova frase completa."}
```

Le categorie già configurate per gli hashtag sono:

`distacco`, `amore`, `fiducia`, `crescita`, `solitudine`, `ricordi`, `rispetto`, `verita`, `ripartenza`, `confini`.
