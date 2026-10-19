"""Wallet Monitor 2.1 — private multi-device investment journal."""
import os
from datetime import date, datetime, timedelta
from decimal import Decimal
import pandas as pd
import plotly.express as px
import streamlit as st
from ledger import calculate, LedgerError, D
from storage import initialize, all_transactions, mutate, audit_rows, allocation_targets, save_target

st.set_page_config(page_title='Wallet Monitor 2.2 DEMO', page_icon='📈', layout='wide')


# DEMO PUBBLICA: solo dati fittizi, nessun accesso a Google, Neon o Secrets.
# Ogni sessione browser ha un database SQLite in memoria indipendente.
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

DEMO_PRICES = {'MSFT': (145.0, 'EUR'), 'VWCE.DE': (120.0, 'EUR'),
               'ENI.MI': (16.8, 'EUR'), 'AAPL': (180.0, 'EUR')}
DEMO_YIELDS = {'MSFT': 0.8, 'VWCE.DE': 0.0, 'ENI.MI': 5.5, 'AAPL': 0.5}


def demo_db():
    if 'demo_engine' not in st.session_state:
        eng = create_engine('sqlite://', connect_args={'check_same_thread': False},
                            poolclass=StaticPool)
        initialize(eng)
        example = [
            ('Azioni', 'MSFT', 'Microsoft (esempio)', 'Directa', '2026-01-12', 10, 100),
            ('Azioni', 'MSFT', 'Microsoft (esempio)', 'Directa', '2026-03-16', 5, 130),
            ('Azioni', 'MSFT', 'Microsoft (esempio)', 'Fineco', '2026-04-02', 3, 155),
            ('ETF', 'VWCE.DE', 'ETF globale (esempio)', 'Fineco', '2026-02-04', 12, 110),
            ('Azioni', 'ENI.MI', 'ENI (esempio)', 'Directa', '2026-05-11', 30, 15),
        ]
        for portfolio,ticker,label,broker,day,qty,price in example:
            mutate(eng,'add',dict(portfolio=portfolio,ticker=ticker,label=label,
                broker=broker,kind='BUY',trade_date=day,quantity=qty,unit_price=price,
                currency='EUR',fx_eur=1,fee=0,notes='DATO DIMOSTRATIVO'),actor='demo')
        st.session_state['demo_engine'] = eng
    return st.session_state['demo_engine']

engine = demo_db()
actor = 'demo'
operations = all_transactions(engine, include_deleted=True)
st.warning('🧪 DEMO 2.2 — solo dati fittizi e prezzi simulati. Nessun login, Neon o backup. Modifiche valide soltanto nella sessione corrente.')

def eur(value):
    return f'{float(value):,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.') + ' €'


def quote(ticker):
    if ticker not in DEMO_PRICES:
        raise ValueError('Nessun prezzo simulato per questo ticker: prova MSFT, VWCE.DE, ENI.MI, AAPL')
    return DEMO_PRICES[ticker]


def fx_today(currency):
    if currency != 'EUR':
        raise ValueError('La demo supporta quotazioni simulate solo in EUR')
    return 1.0


def fx_historical(currency, day):
    if currency != 'EUR':
        raise ValueError('La demo supporta solo EUR')
    return 1.0


def historical_value_series(entries):
    # Esempio visivo del grafico; non sono prezzi storici di mercato.
    from datetime import timedelta
    today = date.today()
    dates = [today-timedelta(days=30*i) for i in range(11,-1,-1)] + [today]
    points = []
    for i, day in enumerate(dates):
        subset = [r for r in entries if r['trade_date'] <= day.isoformat()]
        state = calculate(subset)
        total = sum(float(pos['quantity'])*DEMO_PRICES.get(ticker,(0,'EUR'))[0]
                    for (_,ticker,_,_),pos in state['positions'].items()
                    if pos['quantity'] > 0)
        points.append({'Data': day.isoformat(), 'Valore €': round(total*(0.96+i*0.004),2)})
    return points


def form_fields(prefix, initial=None):
    initial = initial or {}
    types = {'BUY': 'Acquisto', 'SELL': 'Vendita', 'DIVIDEND': 'Dividendo / cedola'}
    current_kind = str(initial.get('kind', 'BUY'))
    kind = st.selectbox('Operazione', list(types), index=list(types).index(current_kind), format_func=lambda x: types[x], key=prefix+'kind')
    c1, c2 = st.columns(2)
    with c1:
        portfolio = st.text_input('Portafoglio', value=str(initial.get('portfolio', 'Principale')), key=prefix+'portfolio')
        ticker = st.text_input('Ticker Yahoo Finance', value=str(initial.get('ticker', '')), placeholder='VWCE.DE, AAPL, ENI.MI', key=prefix+'ticker')
        broker = st.text_input('Broker', value=str(initial.get('broker', '')), placeholder='es. Directa, Fineco', key=prefix+'broker')
        trade_date = st.date_input('Data operazione', value=date.fromisoformat(str(initial.get('trade_date', date.today().isoformat()))), key=prefix+'date')
        quantity = st.number_input('Quantità (0 per dividendi)', min_value=0.0, value=float(initial.get('quantity', 1 if kind != 'DIVIDEND' else 0)), format='%.8f', key=prefix+'qty')
    with c2:
        currency = st.text_input('Valuta ISO del prezzo', value=str(initial.get('currency', 'EUR')), max_chars=3, key=prefix+'currency')
        price_label = 'Dividendo / cedola lordo totale' if kind == 'DIVIDEND' else 'Prezzo unitario'
        price = st.number_input(price_label, min_value=0.0, value=float(initial.get('unit_price', 0)), format='%.6f', key=prefix+'price')
        fee_label = 'Ritenute e spese' if kind == 'DIVIDEND' else 'Commissioni'
        fee = st.number_input(fee_label, min_value=0.0, value=float(initial.get('fee', 0)), format='%.4f', key=prefix+'fee')
        fx = st.number_input('Cambio EUR per 1 unità di valuta', min_value=0.00000001,
                             value=float(initial.get('fx_eur', 1.0)), format='%.8f', key=prefix+'fx',
                             help='Per USD, inserire EUR per 1 USD. Salva il valore storico dell’operazione.')
    label = st.text_input('Nome asset (facoltativo)', value=str(initial.get('label', '')), key=prefix+'label')
    notes = st.text_input('Note', value=str(initial.get('notes', '')), key=prefix+'notes')
    submit = st.form_submit_button('💾 Salva operazione', type='primary', use_container_width=True)
    return submit, dict(kind=kind, portfolio=portfolio, ticker=ticker, trade_date=trade_date.isoformat(),
                        quantity=quantity, unit_price=price, currency=currency, fx_eur=fx, fee=fee,
                        label=label, notes=notes, broker=broker)


def run_change(action, payload=None, row_id=None):
    try:
        mutate(engine, action, payload, row_id, actor)
        st.success('Operazione salvata e portafoglio ricalcolato.')
        st.rerun()
    except (LedgerError, ValueError, ArithmeticError) as exc:
        st.error(str(exc))
    except Exception:
        st.error('Salvataggio non riuscito. Verifica il database e riprova.')

st.markdown('''<style>
 .block-container {padding-top: 1.5rem; max-width: 1500px;}
 div[data-testid="stMetric"] {background:rgba(125,125,125,.065); padding:12px; border-radius:12px; border:1px solid rgba(125,125,125,.14);}
</style>''', unsafe_allow_html=True)
st.title('📈 Wallet Monitor 2.2 — DEMO')
st.caption('Registro dimostrativo · calcoli reali del codice 2.2 · valori di mercato SIMULATI')
with st.sidebar:
    st.success('Ambiente dimostrativo indipendente')
    st.caption('Nessun dato reale. Le modifiche si perdono quando la sessione termina.')
    if st.button('♻️ Ricomincia con i dati di esempio'):
        st.session_state.pop('demo_engine', None)
        st.rerun()

view = st.radio('Sezione', ['I miei portafogli', 'Dashboard generale', 'Nuova operazione',
              'Gestione operazioni', 'Storico operazioni'], horizontal=True)
active = [r for r in operations if not r['deleted']]
try:
    ledger = calculate(active)
except LedgerError as exc:
    st.error(f'Incoerenza contabile rilevata: {exc}')
    st.stop()

if view == 'Nuova operazione':
    st.subheader('Registra acquisto, vendita o dividendo')
    pref = st.session_state.get('buy_again')
    if pref:
        st.info(f"Acquisto aggiuntivo di {pref['ticker']} · {pref['portfolio']} · {pref['broker'] or 'Broker non indicato'}")
    with st.form('create_transaction'):
        submitted, data = form_fields('new_', pref)
        if submitted:
            st.session_state.pop('buy_again', None)
            run_change('add', data)
    st.info('Per un dividendo, inserisci l’importo lordo totale nel campo importo e le ritenute in “Ritenute e spese”. Per valute diverse da EUR usa il cambio storico corretto.')

elif view == 'Gestione operazioni':
    st.subheader('Modifica, annulla o ripristina')
    if operations:
        frame = pd.DataFrame(operations).sort_values(['trade_date', 'id'], ascending=False)
        frame['Stato'] = frame['deleted'].map({0: 'Attiva', 1: 'Annullata'})
        frame['Tipo'] = frame['kind'].map({'BUY': 'Acquisto', 'SELL': 'Vendita', 'DIVIDEND': 'Dividendo'})
        st.dataframe(frame[['id', 'trade_date', 'portfolio', 'ticker', 'broker', 'Tipo', 'quantity', 'unit_price', 'currency', 'fee', 'Stato']],
                     hide_index=True, use_container_width=True)
        ids = {f"#{r['id']} · {r['trade_date']} · {r['portfolio']} · {r['ticker']} · {r['kind']} · {'Annullata' if r['deleted'] else 'Attiva'}": r for r in operations}
        choice = st.selectbox('Seleziona la registrazione', list(ids), index=len(ids)-1)
        row = ids[choice]
        if row['deleted']:
            if st.button('↩️ Ripristina registrazione'):
                run_change('restore', row_id=row['id'])
        else:
            with st.expander('✏️ Modifica questa operazione'):
                # Key ties the widgets to selected record; prevents stale values when selection changes.
                with st.form('edit_'+str(row['id'])):
                    submitted, data = form_fields('edit_'+str(row['id'])+'_', row)
                    if submitted:
                        run_change('edit', data, row['id'])
            confirm = st.checkbox('Confermo l’annullamento della registrazione selezionata', key=f'confirm_{row["id"]}')
            if st.button('🗑️ Annulla operazione', disabled=not confirm):
                run_change('delete', row_id=row['id'])
    else:
        st.info('Non ci sono ancora operazioni.')

elif view in ('I miei portafogli', 'Dashboard generale'):
    @st.cache_data(ttl=3600, show_spinner=False)
    def forward_yield(ticker):
        return DEMO_YIELDS.get(ticker)

    st.subheader('Portafogli separati' if view == 'I miei portafogli' else 'Dashboard generale')
    st.caption('P/L positivo in verde, negativo in rosso. Prezzi e dividend yield sono simulati, non sono dati di mercato.')
    targets = {(x['portfolio'], x['ticker'], x['currency'], x['broker']): float(x['target_pct']) for x in allocation_targets(engine)}
    positions = []
    warnings = []
    for (portfolio, ticker, currency, broker), pos in ledger['positions'].items():
        if pos['quantity'] <= 0:
            continue
        row = {'Portafoglio': portfolio, 'Ticker': ticker, 'Broker': broker or 'Non specificato',
               'Quantità': float(pos['quantity']), 'PMC €': float(pos['cost']/pos['quantity']),
               'Costo €': float(pos['cost']), 'Valuta': currency, 'Prezzo attuale': None,
               'Valore €': None, 'P/L €': None, 'P/L %': None,
               'Peso %': None, 'Obiettivo %': targets.get((portfolio,ticker,currency,broker)),
               'Scostamento pp': None, 'Forward Yield %': None, 'Dividendo annuo €': None,
               '_key': (portfolio,ticker,currency,broker)}
        try:
            price, found_currency = quote(ticker)
            if found_currency != currency:
                raise ValueError(f'Valuta Yahoo {found_currency} diversa da {currency}')
            current_fx = fx_today(currency)
            market_value = float(pos['quantity'] * D(price) * D(current_fx))
            pnl = market_value - row['Costo €']
            row.update({'Prezzo attuale': price, 'Valore €': market_value,
                        'P/L €': pnl, 'P/L %': pnl / row['Costo €'] * 100 if row['Costo €'] else 0})
            try:
                yield_pct = forward_yield(ticker)
                row['Forward Yield %'] = yield_pct
                if yield_pct is not None:
                    row['Dividendo annuo €'] = market_value * yield_pct / 100
            except Exception:
                pass
        except Exception as exc:
            warnings.append(f'{portfolio} / {ticker} / {broker or "Broker non specificato"}: {exc}')
        positions.append(row)
    total_value = sum(x['Valore €'] or 0 for x in positions)
    priced_cost = sum(x['Costo €'] for x in positions if x['Valore €'] is not None)
    total_cost = sum(x['Costo €'] for x in positions)
    estimated_div = sum(x['Dividendo annuo €'] or 0 for x in positions)
    totals_by_portfolio = {}
    for row in positions:
        key = row['Portafoglio']
        totals_by_portfolio[key] = totals_by_portfolio.get(key,0)+(row['Valore €'] or 0)
    for row in positions:
        base = totals_by_portfolio[row['Portafoglio']]
        if row['Valore €'] is not None and base:
            row['Peso %'] = row['Valore €']/base*100
            if row['Obiettivo %'] is not None:
                row['Scostamento pp'] = row['Peso %'] - row['Obiettivo %']
    if warnings:
        with st.expander(f'⚠️ {len(warnings)} posizioni senza quotazione', expanded=True):
            for warning in warnings:
                st.warning(warning)
    if not positions:
        st.info('Nessuna posizione aperta. Vai su Nuova operazione per registrare un acquisto.')
    else:
        DISPLAY = ['Portafoglio','Ticker','Broker','Quantità','Valuta','PMC €','Prezzo attuale',
                   'Costo €','Valore €','P/L €','P/L %','Peso %','Obiettivo %',
                   'Scostamento pp','Forward Yield %','Dividendo annuo €']
        def table(items, suffix, general=False):
            default = ['Portafoglio','Ticker','Broker','Quantità','PMC €','Valore €','P/L €',
                       'P/L %','Peso %','Obiettivo %','Forward Yield %','Dividendo annuo €'] if general else \
                      ['Ticker','Broker','Quantità','PMC €','Valore €','P/L €','P/L %','Peso %',
                       'Obiettivo %','Forward Yield %','Dividendo annuo €']
            with st.expander('⚙️ Mostra / nascondi colonne', expanded=False):
                selected = st.multiselect('Colonne visibili', DISPLAY, default=default, key='columns_'+suffix)
            if not selected:
                st.info('Scegli almeno una colonna per visualizzare la tabella.')
                return
            frame = pd.DataFrame([{k:r.get(k) for k in selected} for r in items])
            styler = frame.style
            colorcols = [c for c in ('P/L €','P/L %','Scostamento pp') if c in frame]
            if colorcols:
                def color_pnl(v):
                    if pd.isna(v): return ''
                    return 'color:#168344;font-weight:700' if v>0 else 'color:#d83a45;font-weight:700' if v<0 else ''
                styler = styler.map(color_pnl, subset=colorcols)
            formats = {c:'{:,.2f}' for c in selected if c in ('PMC €','Prezzo attuale','Costo €','Valore €','P/L €','P/L %','Peso %','Obiettivo %','Scostamento pp','Forward Yield %','Dividendo annuo €')}
            if formats:
                styler = styler.format(formats, na_rep='N/D', decimal=',', thousands='.')
            st.dataframe(styler, hide_index=True, use_container_width=True)
            st.download_button('⬇️ Esporta CSV', frame.to_csv(index=False).encode('utf-8-sig'),
                               file_name='wallet_'+suffix+'.csv', key='csv_'+suffix)

        if view == 'Dashboard generale':
            a,b,c,d = st.columns(4)
            a.metric('Valore valorizzato', eur(total_value))
            b.metric('Costo posizioni', eur(total_cost))
            c.metric('P/L non realizzato*', eur(total_value-priced_cost), delta=eur(total_value-priced_cost))
            d.metric('Dividendi annui stimati', eur(estimated_div))
            st.caption('*P/L calcolato soltanto sulle posizioni con quotazione. Stima dividendi lorda: non sono incassi effettivi.')
            pie_df = pd.DataFrame([{'Portafoglio':k,'Valore €':v} for k,v in totals_by_portfolio.items() if v>0])
            if not pie_df.empty:
                st.plotly_chart(px.pie(pie_df, names='Portafoglio', values='Valore €', hole=.5), use_container_width=True)
            st.markdown('#### Tutti i titoli — tutti i portafogli')
            table(positions, 'generale', general=True)
        else:
            for portfolio in sorted({r['Portafoglio'] for r in positions}):
                part = [r for r in positions if r['Portafoglio']==portfolio]
                st.divider()
                st.markdown('### '+portfolio)
                p_value = sum(x['Valore €'] or 0 for x in part)
                p_cost = sum(x['Costo €'] for x in part if x['Valore €'] is not None)
                p_div = sum(x['Dividendo annuo €'] or 0 for x in part)
                a,b,c = st.columns(3)
                a.metric('Valore portafoglio', eur(p_value))
                b.metric('P/L non realizzato', eur(p_value-p_cost), delta=eur(p_value-p_cost))
                c.metric('Dividendi annui stimati', eur(p_div))
                table(part, 'port_'+str(sorted({r['Portafoglio'] for r in positions}).index(portfolio)))
                with st.expander('🎯 Modifica obiettivi dei titoli'):
                    keys = [(r['Ticker'],r['Valuta'],r['_key'][3]) for r in part]
                    picker = st.selectbox('Titolo e broker', range(len(keys)),
                        format_func=lambda i:f'{keys[i][0]} · {keys[i][2] or "Broker non indicato"}', key='targetpick_'+portfolio)
                    chosen = part[picker]
                    target = st.number_input('Peso obiettivo (%)', min_value=0.0, max_value=100.0,
                        value=float(chosen['Obiettivo %'] or 0), step=0.5, key='targetval_'+portfolio)
                    if st.button('Salva obiettivo', key='targetsave_'+portfolio):
                        save_target(engine, *chosen['_key'], target)
                        st.rerun()
                with st.expander('➕ Acquista ancora una posizione esistente'):
                    keys = [r['_key'] for r in part]
                    selected_pos = st.selectbox('Posizione', range(len(keys)),
                        format_func=lambda i:f'{keys[i][1]} · {keys[i][3] or "Broker non specificato"}', key='purchase_'+portfolio)
                    if st.button('Prepara nuovo acquisto',key='purchasego_'+portfolio):
                        chosen = keys[selected_pos]
                        st.session_state['buy_again'] = dict(portfolio=chosen[0],ticker=chosen[1],
                            currency=chosen[2],broker=chosen[3], kind='BUY', quantity=1,
                            unit_price=0, fx_eur=1, fee=0, trade_date=date.today().isoformat())
                        # Streamlit widget keys retain values between forms unless explicitly reset.
                        preset = st.session_state['buy_again']
                        for field in ('portfolio','ticker','broker','currency','kind'):
                            st.session_state['new_'+field] = preset[field]
                        st.session_state['new_date'] = date.today()
                        st.session_state['new_qty'] = 1.0
                        st.session_state['new_price'] = 0.0
                        st.session_state['new_fee'] = 0.0
                        st.session_state['new_fx'] = 1.0
                        st.session_state['new_label'] = ''
                        st.session_state['new_notes'] = ''
                        st.info('Posizione selezionata. Apri la sezione “Nuova operazione” in alto: i dati del titolo saranno precompilati.')

        if active and view == 'Dashboard generale':
            with st.expander('📉 Storico indicativo — valore del portafoglio'):
                st.caption('Non è un grafico del rendimento: include variazioni dovute ad acquisti e vendite.')
                if st.button('Calcola andamento storico'):
                    try:
                        st.session_state['portfolio_history'] = historical_value_series(active)
                    except Exception as exc:
                        st.warning(f'Storico non disponibile: {exc}')
                if st.session_state.get('portfolio_history'):
                    st.line_chart(pd.DataFrame(st.session_state['portfolio_history']).set_index('Data'))

elif view == 'Storico operazioni':
    st.subheader('Storico operazioni e revisioni')
    if active:
        df = pd.DataFrame(active)
        st.dataframe(df[['trade_date', 'portfolio', 'ticker', 'broker', 'kind', 'quantity', 'unit_price', 'currency', 'fx_eur', 'fee', 'notes']],
                     hide_index=True, use_container_width=True)
        st.download_button('Esporta registro CSV', df.to_csv(index=False).encode('utf-8-sig'), file_name='wallet_transazioni.csv')
    audits = audit_rows(engine)
    st.caption('Le modifiche e gli annullamenti restano nel registro di controllo.')
    if audits:
        st.dataframe(pd.DataFrame(audits), hide_index=True, use_container_width=True)

st.caption('Solo dimostrazione: prezzi e dividend yield inventati. Nessuna autenticazione, backup, connessione Neon o dato di investimento reale.')
