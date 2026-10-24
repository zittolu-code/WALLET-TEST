# Wallet Monitor 2.2 — DEMO tabellare (TAB + storico per posizione)

**Solo ambiente di prova:** dati fittizi, prezzi e dividend yield simulati, SQLite in memoria per sessione. Nessun login Google, Neon, collegamento a portafogli reali, esportazione CSV o backup attivo. Le modifiche svaniscono alla fine della sessione o con il pulsante di reset.

La versione principale **Wallet Monitor 2.1 non va modificata**.

## Dove caricare i file

- Repository della **sola DEMO**: `zittolu-code/wallet-demo-22`
- Branch di pubblicazione DEMO: `main`
- **NON** utilizzare il repository principale `zittolu-code/wallet` né modificare la sua versione 2.1.

## Pubblicazione su GitHub / Streamlit

1. Su GitHub aprire `zittolu-code/wallet-demo-22` e la branch `main`.
2. Caricare **tutti e cinque i file** nella directory radice del repository, sostituendo gli omonimi: `app.py`, `ledger.py`, `storage.py`, `requirements.txt`, `README.md`.
3. Confermare il commit. La DEMO Streamlit collegata al repository eseguirà il deploy; se necessario, utilizzare «Reboot» o «Rerun».
4. Verificare la DEMO nel browser (le modifiche a GitHub **non** sono state eseguite automaticamente dallo ZIP).

## Modifiche presenti

1. **Quantità con due decimali** (es. `15,00`) nelle tabelle delle posizioni e degli storici, oltre che nella visualizzazione degli input. I valori originali del registro NON vengono arrotondati o riscritti soltanto per effetto della formattazione.
2. **Storico per posizione espandibile**: freccia `▾` all'estrema destra della riga; un clic mostra immediatamente sotto la riga gli acquisti e le vendite, un altro clic (`▴`) richiude. Elenco con data, tipo, quantità con segno, prezzo unitario e commissioni, dal più recente al meno recente. Filtri distinti per portafoglio, ticker, valuta **e broker**; operazioni annullate escluse.
3. **Cinque TAB nativi Streamlit** al posto dei cerchietti radio: I miei portafogli, Dashboard generale, Nuova operazione, Gestione operazioni, Storico operazioni. Il resto delle funzioni resta accessibile; le TAB caricano il loro contenuto nell'interfaccia senza cambiare pagina.
4. **Riquadri riepilogativi compatti**: valori ed etichette più piccoli e altezza uniforme; l'indicatore P/L è mantenuto e non altera l'altezza.
5. Restano i **pulsanti + Acquisto e − Vendita** su ogni posizione e il relativo modulo di operazione immediatamente sotto la riga. Restano inoltre gli obiettivi percentuali modificabili e i totali sotto ogni portafoglio.

## Verifiche suggerite nel browser

- I 5 TAB sono orizzontali, non mostrano cerchietti e permettono di visualizzare le sezioni.
- La quantità MSFT Directa si vede come **15,00**, non `15,0000`.
- Aprire `▾` su **MSFT / Directa**: nella DEMO iniziale ci sono due acquisti (10,00 e 5,00) nell'ordine corretto. **MSFT / Fineco** deve mostrare un solo acquisto da 3,00; non devono mescolarsi i broker.
- Provare + Acquisto e − Vendita su MSFT Directa e su MSFT Fineco; dopo il salvataggio verificare i nuovi record in ciascuno storico.
- Tentare una vendita maggiore della quantità disponibile: deve essere bloccata.
- Cambiare un Obiettivo %; verificare il totale e le posizioni distinte.
- I tre riquadri in «Azioni» devono avere identiche dimensioni e testo più contenuto, incluso il riquadro P/L con indicatore verde o rosso.
- Verificare la visualizzazione anche da browser mobile / schermo ristretto: la tabella larga potrebbe richiedere scorrimento.

## Limiti / stato del collaudo

- Controlli di sintassi e test offline del registro e del filtro dello storico eseguibili senza avviare Streamlit.
- **Collaudo visivo e interattivo online ancora necessario** prima di promuovere il codice verso un altro ambiente.
- Nessun dato finanziario reale va inserito nella DEMO.

## Per una futura chat temporanea

Conservare questo ZIP come base; allegarlo alla prossima chat assieme a eventuali nuove indicazioni. La parola **ELABORA** autorizza le modifiche e la generazione di un nuovo ZIP. La parola **TERMINA SESSIONE** richiede uno ZIP di continuità con file e istruzioni aggiornate. **Non modificare mai la 2.1** durante il collaudo della DEMO.
