# stopfallingdown-bot

Automazione basata su GitHub Actions per generare e pubblicare post testuali su Instagram per `@stopfallingdown`.

## Come funziona

1. Il bot legge `phrases.json` e sceglie una frase non ancora usata nel ciclo corrente.
2. Genera automaticamente un'immagine JPEG 1080×1080 con sfondo nero, testo bianco effetto consumato e firma `@STOPFALLINGDOWN`.
3. Compone caption e hashtag in base alla categoria della frase.
4. Salva l'immagine nel repository pubblico, così Meta può leggerla tramite URL.
5. Crea il container multimediale tramite Instagram Graph API su `graph.facebook.com`, attende che il media sia pronto e poi lo pubblica.
6. Aggiorna `state.json` e `published.jsonl`, evitando di ripetere una frase finché la banca non è stata completata.
7. Se una pubblicazione fallisce, `pending.json` rimane disponibile e il run successivo ritenta lo stesso post.

## File principali

- `phrases.json` — banca delle frasi.
- `state.json` — ID delle frasi già pubblicate nel ciclo corrente.
- `bot.py` — generatore grafico e client Instagram Graph API.
- `.github/workflows/daily-instagram.yml` — automazione giornaliera.
- `generated/` — immagini create automaticamente.
- `published.jsonl` — storico delle pubblicazioni riuscite.

## Secrets richiesti

In **Settings → Secrets and variables → Actions**:

- `IG_USER_ID` — ID dell'account Instagram professionale collegato alla Pagina Facebook.
- `IG_ACCESS_TOKEN` — Page Access Token usato per la pubblicazione.

Opzionale:

- `META_API_VERSION` — versione Graph API. Se assente, il bot usa `v25.0`.

Non inserire token o password direttamente nei file del repository.

## Pubblicazione automatica

Il workflow è programmato ogni giorno alle **20:37**, con timezone **Europe/Rome**.

Può anche essere avviato manualmente da **Actions → Daily Instagram Post → Run workflow**.

- `dry_run = true`: genera solo un'anteprima e non pubblica.
- `dry_run = false`: prepara e pubblica il post su Instagram.

## Aggiungere nuove frasi

Aggiungi nuovi oggetti a `phrases.json` mantenendo un `id` numerico univoco, una `category` e un `text` completo.

Esempio:

```json
{"id": 61, "category": "crescita", "text": "Una nuova frase completa."}
```

Categorie hashtag configurate:

`distacco`, `amore`, `fiducia`, `crescita`, `solitudine`, `ricordi`, `rispetto`, `verita`, `ripartenza`, `confini`.
