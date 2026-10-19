# Wallet Monitor 2.2 DEMO - azioni integrate nelle righe

Versione dimostrativa con dati inventati, senza login, Neon o backup.

## Aggiornare Streamlit
Carica `app.py`, `ledger.py`, `storage.py` e `requirements.txt` nel repository pubblico `wallet-demo-22` su branch `main`. I file esistenti vengono aggiornati; Streamlit effettua il redeploy.

## Tabella
- Ogni posizione ha i pulsanti `+` (acquisto) e `-` (vendita) sulla stessa riga.
- Cliccando si apre un modulo **direttamente sotto quella posizione**, senza cambiare pagina.
- Il modulo mostra il ticker e broker corretti; richiede data, quantita, prezzo e commissioni. Conferma o Chiudi.
- La vendita verifica la quantita disponibile.
- La percentuale obiettivo si modifica direttamente nella colonna e i totali sono sotto la tabella.

I dati sono dimostrativi e temporanei; non inserire dati finanziari personali.
