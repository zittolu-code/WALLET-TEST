# Wallet Monitor 2.2 — DEMO (storico e operazioni unificati)

**Ambiente dimostrativo indipendente:** soltanto dati fittizi, quotazioni e dividend yield simulati, database SQLite in memoria per sessione del browser. Nessun login Google, Neon, accesso a conti reali, esportazione CSV o backup in esecuzione. Le modifiche si perdono quando termina la sessione o si reimposta la DEMO.

**La versione principale 2.1 NON deve essere modificata.**

## Repository e pubblicazione

- Repository destinazione: `zittolu-code/wallet-demo-22` (solo DEMO), branch `main`.
- Non caricare i file nel repository principale `zittolu-code/wallet` né nella release 2.1.
- Sostituire nella **radice** del repository DEMO i cinque file dello ZIP: `app.py`, `ledger.py`, `storage.py`, `requirements.txt`, `README.md`.
- Eseguire commit su GitHub e controllare la DEMO collegata a Streamlit. Se l'aggiornamento non appare, eseguire «Reboot»/«Rerun» oppure ricaricare la pagina.
- La prima apertura di questa revisione rigenera i dati DEMO semplificati; in alternativa, utilizzare «Ricomincia con i dati di esempio» nel menu laterale.

## Novità di questa revisione

1. **Un solo riquadro sotto ogni riga:** la freccia `▾` espande lo storico di acquisti/vendite, distinto per **portafoglio + titolo + valuta + broker**. I pulsanti `＋` / `−` aprono nello **stesso riquadro** i campi per un nuovo acquisto o una nuova vendita. Non si crea più un secondo pannello separato sotto lo storico. Un solo modulo è attivo alla volta.
2. **Modifica e Elimina in ogni riga dello storico:** i pulsanti `✏️` e `🗑️` sono all'estrema destra della transazione. Modifica permette di correggere **data, quantità, prezzo unitario e commissioni**, senza cambiare portafoglio, ticker, broker o tipo di operazione. Elimina richiede conferma. Entrambi agiscono nel riquadro dello storico, senza cambiare schermata.
3. **Contabilità protetta:** ogni salvataggio usa `mutate()` del registro, che ricalcola la cronologia e rifiuta operazioni non coerenti, comprese vendite scoperte o eliminazioni di acquisti indispensabili a coprire vendite. L'eliminazione è **logica**: la transazione sparisce dallo storico attivo, ma resta nel registro di controllo e può essere ripristinata dalla scheda *Gestione operazioni*.
4. **Dati DEMO ridotti a una sola azienda per wallet:**
   - Wallet **Directa** → **MSFT** (Microsoft), due acquisti e una vendita, saldo iniziale **13,00** azioni.
   - Wallet **Fineco** → **ENI.MI** (ENI), due acquisti e una vendita, saldo iniziale **25,00** azioni.
   Questi sono soltanto i dati *iniziali di prova*: la scheda *Nuova operazione* conserva la capacità di inserire altri titoli. Nessun limite viene imposto alla versione definitiva.

## Funzionalità preservate

- Interfaccia compatta, simile a un foglio Excel, con **cinque TAB** orizzontali.
- Quantità **visualizzate con due decimali**, senza perdere precisione nel registro.
- Valori con `€` e percentuali con `%`, Obiettivo % modificabile dalla tabella.
- Totali sotto ogni portafoglio e indicatori riepilogativi di uguale altezza, con testo ridotto.
- Separazione per portafoglio/ticker/broker e rendimenti colorati.
- Schede generali *Nuova operazione*, *Gestione operazioni*, *Storico operazioni* ancora disponibili per operazioni e controllo.

## Verifiche da effettuare in Streamlit

1. Nella scheda *I miei portafogli* devono comparire solo **Directa / MSFT** e **Fineco / ENI.MI**, ciascuno con tre operazioni iniziali.
2. Aprire la freccia sotto MSFT: lo storico con le tre operazioni deve apparire sotto la stessa posizione; poi premere `＋` e `−`: i rispettivi moduli devono comparire **dentro** il riquadro dello storico.
3. Salvare un acquisto e una vendita e verificare variazioni di quantità, PMC, valore, P/L e nuova riga nello storico.
4. Premere `✏️` su un acquisto, modificare prezzo e quantità, salvare e verificare il ricalcolo dei totali.
5. Premere `🗑️`: prima dell'esplicita conferma non deve avvenire alcuna eliminazione. Dopo conferma, la riga sparisce dallo storico attivo; deve essere ancora disponibile per ripristino in *Gestione operazioni*.
6. Provare a eliminare l'unico acquisto che copre una vendita o a vendere più azioni di quelle possedute: l'operazione deve essere respinta senza modificare il registro.
7. Aprire Fineco e verificare che lo storico non contenga operazioni di Directa. Controllare inoltre i cinque TAB, la formattazione con due decimali e gli allineamenti.

## Verifica eseguita offline

- Codice Python compilato senza errori sintattici.
- Test del registro e della logica di interazione (simulazione eventi): acquisto, modifica, cancellazione confermata, cancellazione bloccata per incoerenza, separazione dei wallet e audit.
- **Verifica visiva/interattiva con Streamlit effettivo ancora necessaria:** Streamlit non è installabile nell'ambiente di collaudo offline. Non dichiarare completato il collaudo browser prima di provarlo nella DEMO pubblicata.

## Regole di continuità per le chat temporanee

- Raccogliere note senza modificare alcun file finché l'utente non scrive **ELABORA**.
- Quando l'utente scrive **ELABORA**, modificare solo la DEMO, testarla e consegnare lo ZIP pronto per GitHub.
- Quando l'utente scrive **TERMINA SESSIONE**, preparare uno ZIP di continuità contenente i file più recenti e istruzioni dettagliate per una nuova chat temporanea.
- La versione 2.1 del repository principale deve rimanere intoccata, così come Google, Neon e backup nella DEMO.
