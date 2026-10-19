# Wallet Monitor 2.2 — DEMO autonoma

Questa è una **dimostrazione pubblicabile solo con dati fittizi** della UI e della logica di Wallet Monitor 2.2. Non è una versione sicura per dati personali.

## Cosa contiene
- `app.py`: interfaccia Streamlit e dati dimostrativi in memoria
- `ledger.py`: calcoli di portafoglio originali 2.2
- `storage.py`: logica originale 2.2 utilizzata con SQLite in memoria
- `requirements.txt`: dipendenze minime

## Avvio Streamlit Cloud
Crea un **nuovo repository GitHub pubblico**, carica **solo questi quattro file**, poi crea una nuova app Streamlit con branch `main` e main file `app.py`. Non usare il repository privato reale `wallet` per la demo. Non inserire Secrets.

## Limitazioni e sicurezza
- Nessun Google login, Neon, Secrets o workflow GitHub Actions.
- La demo può essere accessibile a chiunque abbia il link. **Non inserire dati personali o reali**.
- Ogni sessione del browser ha un database SQLite in memoria; modifiche e obiettivi scompaiono quando la sessione termina o il servizio si riavvia.
- Prezzi, valute e rendimenti sono **solo simulazioni** e non sono consigli finanziari. Sono disponibili quotazioni simulate per MSFT, VWCE.DE, ENI.MI e AAPL (EUR). Grafico storico solo illustrativo.
- Non sono presenti funzioni di backup o ripristino. Le funzioni contabili rimangono quelle del codice 2.2.
