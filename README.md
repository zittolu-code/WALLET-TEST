# Wallet Monitor 2.2 — DEMO (storico posizioni chiuse e grafica wallet)

**Ambiente dimostrativo indipendente:** soltanto dati fittizi, quotazioni e dividend yield simulati, database SQLite in memoria per sessione del browser. Nessun login Google, Neon, accesso a conti reali, esportazione CSV o backup in esecuzione. Le modifiche si perdono quando termina la sessione o si reimposta la DEMO.

**La versione principale 2.1 NON deve essere modificata.**

## Repository e pubblicazione

- Repository destinazione: `zittolu-code/wallet-demo-22` (solo DEMO), branch `main`.
- Non caricare i file nel repository principale `zittolu-code/wallet` né nella release 2.1.
- Sostituire nella **radice** del repository DEMO i cinque file dello ZIP: `app.py`, `ledger.py`, `storage.py`, `requirements.txt`, `README.md`.
- Eseguire commit su GitHub e controllare la DEMO collegata a Streamlit. Se l'aggiornamento non appare, eseguire «Reboot»/«Rerun» oppure ricaricare la pagina.
- Questa revisione **non forza il reset** delle operazioni già registrate nella sessione DEMO ancora attiva. Per ripristinare i dati iniziali, usare «Ricomincia con i dati di esempio» nel menu laterale.

## Novità della revisione: posizioni chiuse e nuovo stile

1. **Storico sempre consultabile anche dopo la vendita totale.** Una posizione con quantità **0,00** resta nella tabella, contrassegnata **CHIUSA**. Il pulsante a freccia continua ad aprire lo storico completo di acquisti e vendite, con i comandi Modifica ed Elimina.
2. **Riapertura del titolo:** il pulsante **＋ Acquista** rimane abilitato sulla posizione chiusa, e il nuovo acquisto riporta la riga allo stato aperto senza cancellare lo storico precedente. **− Vendi** è disabilitato quando le quote disponibili sono zero.
3. **Calcoli dopo la chiusura:** valore e peso della posizione chiusa sono **0,00**. Il PMC, il P/L percentuale e il rendimento forward risultano non applicabili (—). Il **P/L realizzato** resta visibile nei riepiloghi dei wallet e in quello generale. Gli obiettivi delle posizioni chiuse non sono sommati all'allocazione del portafoglio attivo.
4. **Portafogli separati visivamente:** Directa con intestazione **blu**, Fineco con intestazione **verde**, ciascuno in un proprio riquadro con bordi, titolo e conteggio di posizioni aperte/chiuse. Eventuali wallet aggiunti ricevono colori alternativi. I numeri nei riepiloghi restano compatti e allineati.
5. **TAB rivisti:** fondo grigio chiaro e lieve ombreggiatura; TAB selezionato con sfondo bianco, testo scuro in **grassetto** e bordo discreto **senza evidenziazione rossa**.
6. **Dati invariati:** i dati iniziali restano una società per wallet; non vengono introdotti login Google, Neon, backup, prezzi reali o esportazione CSV.

### Collaudo mirato in Streamlit

- Aprire *I miei portafogli*: verificare riquadri colorati indipendenti Directa (blu) e Fineco (verde), indicatori e tabelle racchiusi dentro ogni wallet.
- Controllare i cinque TAB: quello selezionato deve essere in grassetto con ombra, senza scritte o sottolineature rosse.
- Per Directa / MSFT, vendere tutta la quantità rimasta (`13,00` sui dati iniziali). La riga deve restare **CHIUSA**, a quantità e valore zero. Aprire la freccia e vedere l'intero storico anche quando il portafoglio è vuoto.
- Verificare che il P/L realizzato rimanga nei riepiloghi, che **−** sia disabilitato e che **＋** apra il modulo nello storico. Acquistare nuovamente una quantità: la posizione deve tornare aperta e conservare tutte le operazioni precedenti.
- Chiudere anche Fineco / ENI.MI e controllare che **entrambi** gli storici restino consultabili; la Dashboard generale deve mostrare correttamente solo P/L realizzato e pesi zero.
- Proseguire con Modifica ed Elimina nello storico di un titolo chiuso, verificando il rifiuto contabile delle operazioni incoerenti.

**Test offline eseguiti:** compilazione Python e prove di rendering con oggetto Streamlit simulato (2 wallet iniziali, chiusura di uno o entrambi, storico consultabile, azioni abilitate/disabilitate, riapertura, blocco di vendita scoperta). **Collaudo browser non eseguito:** il pacchetto Streamlit non è disponibile nell'ambiente offline.

## Novità dell’aggiornamento del 24/10/2026

1. **Quantità colorate nello storico:** il numero con il segno **+** è verde negli acquisti; con **−** è rosso nelle vendite. La quantità rimane formattata a due decimali.
2. **Colonna Totale €** fra *Prezzo unitario* e *Commissioni*. Importo lordo dell'operazione = quantità × prezzo unitario × cambio EUR della registrazione. La colonna Totale mostra un importo positivo sia per acquisti sia per vendite; le commissioni sono visualizzate a parte e non sono detratte dal totale lordo.
3. **P/L realizzato:** calcolato con il costo medio ponderato dal registro contabile, includendo le commissioni di acquisto e vendita già presenti nella logica originaria. Sono inclusi anche i risultati delle posizioni **completamente vendute**. Distinzione per wallet e totale generale; si aggiorna quando si acquistano, vendono, modificano, eliminano o ripristinano operazioni.
4. **P/L complessivo = P/L realizzato + P/L non realizzato.** Gli eventuali dividendi incassati sono **esclusi** dal P/L complessivo e la stima dei dividendi annui rimane separata. P/L non realizzato riferito alle posizioni con una quotazione simulata disponibile.
5. Indicatori aggiunti sia ai singoli portafogli sia alla *Dashboard generale*, e totali testuali aggiornati sotto la tabella. Nel caso tutte le posizioni di un wallet siano state chiuse, il risultato realizzato rimane consultabile.

**Esempio di verifica contabile:** due acquisti MSFT (10 × 100 €, 5 × 150 €) e vendita di 5 a 150 €: P/L realizzato **166,67 €**, P/L non realizzato al prezzo DEMO di 145 € **283,33 €**, P/L complessivo **450,00 €**. L'esempio usa commissioni a zero; i dati fittizi iniziali della DEMO sono diversi e producono importi differenti.

## Funzioni introdotte nelle revisioni precedenti

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
- Otto gruppi di verifiche offline della revisione: esempio numerico (166,67 € + 283,33 €), totale lordo storico, aggregazione per wallet, modifica, eliminazione, ripristino e blocco di vendita incoerente, vendite che chiudono interamente una posizione con commissioni, e verifica statica delle colonne/indicatori. La logica preesistente di Acquisto/Vendita/Modifica/Elimina continua a utilizzare il ledger originale.
- **Verifica visiva/interattiva con Streamlit effettivo ancora necessaria:** Streamlit non è installabile nell'ambiente di collaudo offline. Non dichiarare completato il collaudo browser prima di provarlo nella DEMO pubblicata.

## Regole di continuità per le chat temporanee

- Raccogliere note senza modificare alcun file finché l'utente non scrive **ELABORA**.
- Quando l'utente scrive **ELABORA**, modificare solo la DEMO, testarla e consegnare lo ZIP pronto per GitHub.
- Quando l'utente scrive **TERMINA SESSIONE**, preparare uno ZIP di continuità contenente i file più recenti e istruzioni dettagliate per una nuova chat temporanea.
- La versione 2.1 del repository principale deve rimanere intoccata, così come Google, Neon e backup nella DEMO.
