# Wallet Monitor 2.2 DEMO - moduli integrati nelle righe

Demo indipendente basata esclusivamente su dati fittizi e quotazioni simulate.
Nessun login Google, database Neon, connessione a dati finanziari reali o backup attivo.
La versione principale Wallet Monitor 2.1 non deve essere modificata.

## Pubblicazione demo su GitHub / Streamlit

Repository destinazione: `zittolu-code/wallet-demo-22`, branch `main`.

1. Su GitHub aprire il repository *della DEMO*, NON `zittolu-code/wallet`.
2. Sostituire nella root `app.py`, `ledger.py`, `storage.py`, `requirements.txt`, `README.md`
   con gli omonimi file contenuti in questo ZIP.
3. Confermare il commit sulla branch `main` della DEMO.
4. Aprire l'app Streamlit collegata al repository; se necessario usare "Reboot"/"Rerun".
5. Provare `+` e `-` per MSFT su Directa, MSFT su Fineco e VWCE.DE su Fineco.
   Verificare che il form compaia immediatamente sotto la posizione scelta.

## Funzioni e limiti

- Acquisto e vendita in linea sotto ogni riga, con prezzo, quantità, commissioni e data.
- Verifica delle quantità disponibili in caso di vendita.
- Obiettivi percentuali modificabili sulla posizione (titolo, broker, portafoglio, valuta).
- Totali sotto ciascuna tabella, valori monetari con euro e percentuali formattate.
- Nessuna esportazione CSV nella DEMO.
- Dati temporanei in memoria: si azzerano alla fine della sessione o usando il reset.
- Non inserire informazioni finanziarie personali.

## Stato dei test

Controllo sintattico e test delle funzioni di registro possono essere eseguiti offline.
Il rendering visivo va verificato nell'app Streamlit online.
