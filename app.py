"""Wallet Monitor 2.2 DEMO - dati fittizi e interfaccia tabellare."""
import hashlib
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


def fmt_quantity(value):
    # Solo presentazione: il registro conserva tutta la precisione originale.
    return f'{float(value):,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def trades_for_position(entries, key):
    # Isolamento rigoroso: portafoglio, ticker, valuta e broker.
    portfolio, ticker, currency, broker = key
    return sorted(
        (r for r in entries
         if not r.get('deleted') and r['kind'] in ('BUY', 'SELL')
         and (r['portfolio'], r['ticker'], r['currency'], r['broker'] or '')
         == (portfolio, ticker, currency, broker)),
        key=lambda r: (str(r['trade_date']), int(r['id'])), reverse=True
    )


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
        quantity = st.number_input('Quantità (0 per dividendi)', min_value=0.0, value=float(initial.get('quantity', 1 if kind != 'DIVIDEND' else 0)), format='%.2f', key=prefix+'qty')
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
 .block-container {padding-top: 1.2rem; max-width: 1750px;}
 /* Schede: compatte, senza pulsanti radio. */
 div[data-testid="stTabs"] button[role="tab"] {font-size: .88rem; padding: .55rem .8rem;}
 /* Riepiloghi: identica altezza e tipografia ridotta anche in presenza del delta. */
 div[data-testid="stMetric"] {
     box-sizing: border-box; height: 104px; padding: 10px 12px;
     border-radius: 5px; border: 1px solid #d7dce3;
     display: flex; flex-direction: column; justify-content: flex-start;
 }
 div[data-testid="stMetricLabel"] {font-size: .78rem; line-height: 1.2;}
 div[data-testid="stMetricValue"] {font-size: 1.45rem; line-height: 1.4;}
 div[data-testid="stMetricDelta"] {font-size: .73rem; line-height: 1.2;}
 div[data-testid="stDataFrame"] {border:1px solid #cbd5e1; border-radius:3px;}
 </style>''', unsafe_allow_html=True)
st.title('Wallet Monitor 2.2 — DEMO · Vista tabellare')
st.caption('Registro dimostrativo · calcoli reali del codice 2.2 · valori di mercato SIMULATI')
with st.sidebar:
    st.success('Ambiente dimostrativo indipendente')
    st.caption('Nessun dato reale. Le modifiche si perdono quando la sessione termina.')
    if st.button('♻️ Ricomincia con i dati di esempio'):
        st.session_state.pop('demo_engine', None)
        st.rerun()

tabs = st.tabs(['I miei portafogli', 'Dashboard generale', 'Nuova operazione',
                'Gestione operazioni', 'Storico operazioni'])
active = [r for r in operations if not r['deleted']]
try:
    ledger = calculate(active)
except LedgerError as exc:
    st.error(f'Incoerenza contabile rilevata: {exc}')
    st.stop()

# TAB nativi Streamlit: nessun selettore radio e nessun cambio pagina.
# Il contenuto rimane separato in schede, con chiavi widget stabili.


def render_portfolios(view):
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
        def fmt_money(value):
            if value is None or pd.isna(value):
                return '—'
            return eur(value)

        def fmt_pct(value):
            if value is None or pd.isna(value):
                return '—'
            return f'{float(value):.2f}'.replace('.', ',') + ' %'

        def action_preset(row, kind, suffix):
            key = row['_key']
            selection = (suffix, key, kind)
            if st.session_state.get('quick_selection') == selection:
                st.session_state.pop('quick_selection', None)
                st.session_state.pop('quick_operation', None)
            else:
                st.session_state['quick_selection'] = selection
                st.session_state['quick_operation'] = {
                    'portfolio': key[0], 'ticker': key[1], 'currency': key[2],
                    'broker': key[3], 'kind': kind, 'quantity': 1.0,
                    'unit_price': 0.0, 'fee': 0.0, 'fx_eur': 1.0,
                    'trade_date': date.today().isoformat(), 'label': '', 'notes': ''
                }

        def stable_id(key):
            # Le chiavi non dipendono dall'ordine: la posizione rimane associata
            # al suo broker anche quando un titolo viene venduto o aggiunto.
            return hashlib.sha256(repr(key).encode('utf-8')).hexdigest()[:16]

        def quick_form(suffix, row):
            preset = st.session_state.get('quick_operation')
            if not preset:
                return
            kind_name = 'ACQUISTO' if preset['kind'] == 'BUY' else 'VENDITA'
            st.info(f"{kind_name} · {preset['ticker']} · {preset['broker'] or 'Senza broker'} — {preset['portfolio']}")
            # ID diverso per ogni titolo/broker/tipo di operazione:
            # non riutilizza campi della posizione precedentemente selezionata.
            form_id = 'quick_form_' + suffix + '_' + stable_id((*row['_key'], preset['kind']))
            with st.container(border=True):
                with st.form(form_id):
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        qty = st.number_input('Quantità', min_value=0.000001, value=1.0, step=1.0, format='%.2f')
                    with c2:
                        price = st.number_input('Prezzo unitario (€)', min_value=0.0, value=0.0, step=0.5, format='%.2f')
                    with c3:
                        fee = st.number_input('Commissioni (€)', min_value=0.0, value=0.0, step=0.5, format='%.2f')
                    with c4:
                        day = st.date_input('Data', value=date.today())
                    save, cancel = st.columns([1, 1])
                    submitted = save.form_submit_button('Salva '+kind_name.lower(), type='primary', use_container_width=True)
                    dismissed = cancel.form_submit_button('Chiudi', use_container_width=True)
                if dismissed:
                    st.session_state.pop('quick_selection', None)
                    st.session_state.pop('quick_operation', None)
                    st.rerun()
                if submitted:
                    if price <= 0:
                        st.error('Indica un prezzo unitario maggiore di zero.')
                        return
                    if preset['kind'] == 'SELL' and qty > float(row['Quantità']) + 1e-8:
                        st.error('La quantità venduta non può superare quella disponibile in questa posizione.')
                        return
                    payload = {**preset, 'trade_date': day.isoformat(), 'quantity': qty,
                               'unit_price': price, 'fee': fee}
                    try:
                        mutate(engine, 'add', payload, actor=actor)
                        st.session_state.pop('quick_selection', None)
                        st.session_state.pop('quick_operation', None)
                        st.rerun()
                    except (LedgerError, ValueError, ArithmeticError) as exc:
                        st.error(str(exc))

        def table(items, suffix, general=False):
            # Una riga Streamlit per ogni posizione permette al form di comparire
            # immediatamente sotto il titolo corretto, cosa impossibile in st.data_editor.
            names = (['Portafoglio'] if general else []) + [
                'Titolo / Broker', 'Quantità', 'PMC', 'Valore', 'P/L', 'P/L %',
                'Peso %', 'Obiettivo %', 'Yield %', 'Dividendi', 'Azioni', '']
            widths = ([1.1] if general else []) + [2.3, 1.1, 1.1, 1.2, 1.2, 0.9, 0.9, 1.15, 0.85, 1.15, 1.5, 0.55]
            header = st.columns(widths, vertical_alignment='center', gap='small')
            for col, name in zip(header, names):
                if name:
                    col.caption('**'+name+'**')
            st.divider()

            def set_target(key, widget_key):
                try:
                    save_target(engine, *key, float(st.session_state[widget_key]))
                except ValueError as exc:
                    st.error(str(exc))

            for index, row in enumerate(items):
                cells = st.columns(widths, vertical_alignment='center', gap='small')
                cell_index = 0
                if general:
                    cells[0].write(row['Portafoglio'])
                    cell_index = 1
                vals = [f"**{row['Ticker']}**  \n{row['Broker']}", fmt_quantity(row['Quantità']),
                        fmt_money(row['PMC €']), fmt_money(row['Valore €']),
                        fmt_money(row['P/L €']), fmt_pct(row['P/L %']),
                        fmt_pct(row['Peso %'])]
                for offset, value in enumerate(vals):
                    cells[cell_index + offset].markdown(value)
                item_id = stable_id(row['_key'])
                target_key = f"target_{suffix}_{item_id}"
                target_col = cells[cell_index + 7]
                target_col.number_input('Obiettivo %', min_value=0.0, max_value=100.0,
                    value=float(row['Obiettivo %'] or 0), step=0.5, format='%.2f',
                    key=target_key, label_visibility='collapsed',
                    on_change=set_target, args=(row['_key'], target_key))
                cells[cell_index + 8].write(fmt_pct(row['Forward Yield %']))
                cells[cell_index + 9].write(fmt_money(row['Dividendo annuo €']))
                actions = cells[cell_index + 10].columns(2, gap='small')
                if actions[0].button('＋', key=f'plus_{suffix}_{item_id}', help='Acquista', use_container_width=True):
                    action_preset(row, 'BUY', suffix)
                    st.rerun()
                if actions[1].button('−', key=f'minus_{suffix}_{item_id}', help='Vendi', use_container_width=True):
                    action_preset(row, 'SELL', suffix)
                    st.rerun()

                history_key = f'history_open_{item_id}'
                is_open = bool(st.session_state.get(history_key, False))
                arrow = '▴' if is_open else '▾'
                if cells[cell_index + 11].button(arrow, key=f'history_{suffix}_{item_id}',
                                                  help='Chiudi storico' if is_open else 'Apri storico acquisti e vendite',
                                                  use_container_width=True):
                    st.session_state[history_key] = not is_open
                    st.rerun()
                if is_open:
                    history = trades_for_position(active, row['_key'])
                    with st.container(border=True):
                        st.caption(f"Storico acquisti e vendite · {row['Ticker']} · {row['Broker']}")
                        if history:
                            detail = pd.DataFrame([{
                                'Data': date.fromisoformat(str(t['trade_date'])).strftime('%d/%m/%Y'),
                                'Operazione': 'Acquisto' if t['kind'] == 'BUY' else 'Vendita',
                                'Quantità': ('+' if t['kind'] == 'BUY' else '−') + fmt_quantity(t['quantity']),
                                'Prezzo unitario': fmt_money(t['unit_price']),
                                'Commissioni': fmt_money(t['fee']),
                            } for t in history])
                            st.dataframe(detail, hide_index=True, use_container_width=True,
                                         height=min(38 * (len(detail) + 1) + 6, 350))
                        else:
                            st.caption('Nessun acquisto o vendita registrato per questa posizione.')

                selection = st.session_state.get('quick_selection')
                if selection and selection[0] == suffix and selection[1] == row['_key']:
                    quick_form(suffix, row)
                st.markdown('<div style="border-bottom:1px solid #e5e7eb;margin:3px 0 9px 0"></div>', unsafe_allow_html=True)

            value_sum = sum((r['Valore €'] or 0) for r in items)
            pnl_sum = sum((r['P/L €'] or 0) for r in items)
            target_sum = sum(float(r['Obiettivo %'] or 0) for r in items)
            div_sum = sum((r['Dividendo annuo €'] or 0) for r in items)
            weights_sum = sum((r['Peso %'] or 0) for r in items)
            st.markdown('**TOTALE PORTAFOGLIO** · Valore: **'+fmt_money(value_sum)+
                        '** · P/L: **'+fmt_money(pnl_sum)+'** · Peso: **'+fmt_pct(weights_sum)+
                        '** · Obiettivi: **'+fmt_pct(target_sum)+'** · Dividendi annui: **'+fmt_money(div_sum)+'**')
            if target_sum > 100.000001:
                st.warning('La somma degli obiettivi supera il 100%.')
            elif target_sum < 99.999999:
                st.caption(f'Obiettivi assegnati: {fmt_pct(target_sum)} (mancano {fmt_pct(100-target_sum)} al 100%)')

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


def render_new_operation():
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


def render_management():
    st.subheader('Modifica, annulla o ripristina')
    if operations:
        frame = pd.DataFrame(operations).sort_values(['trade_date', 'id'], ascending=False)
        frame['Stato'] = frame['deleted'].map({0: 'Attiva', 1: 'Annullata'})
        frame['Tipo'] = frame['kind'].map({'BUY': 'Acquisto', 'SELL': 'Vendita', 'DIVIDEND': 'Dividendo'})
        frame['Quantità'] = frame['quantity'].map(fmt_quantity)
        st.dataframe(frame[['id', 'trade_date', 'portfolio', 'ticker', 'broker', 'Tipo', 'Quantità', 'unit_price', 'currency', 'fee', 'Stato']],
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


def render_operation_history():
    st.subheader('Storico operazioni e revisioni')
    if active:
        df = pd.DataFrame(active)
        df['Quantità'] = df['quantity'].map(fmt_quantity)
        st.dataframe(df[['trade_date', 'portfolio', 'ticker', 'broker', 'kind', 'Quantità', 'unit_price', 'currency', 'fx_eur', 'fee', 'notes']],
                     hide_index=True, use_container_width=True)
    audits = audit_rows(engine)
    st.caption('Le modifiche e gli annullamenti restano nel registro di controllo.')
    if audits:
        st.dataframe(pd.DataFrame(audits), hide_index=True, use_container_width=True)


with tabs[0]:
    render_portfolios('I miei portafogli')
with tabs[1]:
    render_portfolios('Dashboard generale')
with tabs[2]:
    render_new_operation()
with tabs[3]:
    render_management()
with tabs[4]:
    render_operation_history()

st.caption('Solo dimostrazione: prezzi e dividend yield inventati. Nessuna autenticazione, backup, connessione Neon o dato di investimento reale.')
