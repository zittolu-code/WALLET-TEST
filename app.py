"""Wallet Monitor 2.2 DEMO - dati fittizi e interfaccia tabellare."""
import hashlib
from html import escape
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
DEMO_SEED_ID = 'demo-22-uno-per-wallet-v1'


def demo_db():
    # Al primo caricamento di questa revisione, sostituisci i soli vecchi dati
    # DEMO in memoria; la release principale 2.1 non viene mai coinvolta.
    if st.session_state.get('_demo_seed_id') != DEMO_SEED_ID:
        st.session_state.pop('demo_engine', None)
        st.session_state.pop('inline_action', None)
        st.session_state['_demo_seed_id'] = DEMO_SEED_ID
    if 'demo_engine' not in st.session_state:
        eng = create_engine('sqlite://', connect_args={'check_same_thread': False},
                            poolclass=StaticPool)
        initialize(eng)
        # Una sola azienda per wallet DEMO. Ogni azienda ha acquisti e vendite
        # per provare storico, modifica ed eliminazione senza dati reali.
        example = [
            ('Directa', 'MSFT', 'Microsoft (esempio)', 'Directa', '2026-01-12', 'BUY', 10, 100),
            ('Directa', 'MSFT', 'Microsoft (esempio)', 'Directa', '2026-03-16', 'BUY', 5, 130),
            ('Directa', 'MSFT', 'Microsoft (esempio)', 'Directa', '2026-06-15', 'SELL', 2, 140),
            ('Fineco', 'ENI.MI', 'ENI (esempio)', 'Fineco', '2026-02-03', 'BUY', 20, 15),
            ('Fineco', 'ENI.MI', 'ENI (esempio)', 'Fineco', '2026-04-08', 'BUY', 10, 16),
            ('Fineco', 'ENI.MI', 'ENI (esempio)', 'Fineco', '2026-07-10', 'SELL', 5, 17),
        ]
        for portfolio,ticker,label,broker,day,kind,qty,price in example:
            mutate(eng,'add',dict(portfolio=portfolio,ticker=ticker,label=label,
                broker=broker,kind=kind,trade_date=day,quantity=qty,unit_price=price,
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
 /* Navigation: spreadsheet-style tabs with a neutral bold selected tab. */
 div[data-testid="stTabs"] [data-baseweb="tab-list"] {gap: .38rem; padding-top:.3rem;}
 div[data-testid="stTabs"] button[role="tab"] {
     font-size: .89rem !important; padding: .55rem .88rem !important;
     color: #455469 !important; font-weight: 550 !important;
     background: #f1f4f8 !important;
     border: 1px solid #d8e0e9 !important;
     border-bottom: 1px solid #c8d2dd !important;
     border-radius: 9px 9px 0 0 !important;
     box-shadow: 0 2px 5px rgba(26,43,67,.075);
     transition: background-color .15s, box-shadow .15s;
 }
 div[data-testid="stTabs"] button[role="tab"]:hover {
     color: #24384f !important; background: #e9eef5 !important;
 }
 div[data-testid="stTabs"] button[role="tab"] p {
     color: inherit !important; font-weight: inherit !important;
 }
 div[data-testid="stTabs"] button[role="tab"]:focus-visible {
     outline: 2px solid #768ba4 !important; outline-offset: 1px;
 }
 div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
     color: #1c304b !important; font-weight: 750 !important;
     background: #fff !important; border-bottom: 2px solid #475569 !important;
     box-shadow: 0 3px 9px rgba(26,43,67,.15);
 }
 div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
     background: transparent !important; height: 0 !important;
 }
 div[data-testid="stTabs"] [data-baseweb="tab-border"] {background: #d9e1eb !important;}
 /* Same compact metrics irrespective of delta badges. */
 div[data-testid="stMetric"] {
     box-sizing: border-box; height: 104px; padding: 10px 12px;
     border-radius: 7px; border: 1px solid #d7dce3;
     display: flex; flex-direction: column; justify-content: flex-start;
     background: #fff;
 }
 div[data-testid="stMetricLabel"] {font-size: .78rem; line-height: 1.2;}
 div[data-testid="stMetricValue"] {font-size: 1.45rem; line-height: 1.4;}
 div[data-testid="stMetricDelta"] {font-size: .73rem; line-height: 1.2;}
 div[data-testid="stDataFrame"] {border:1px solid #cbd5e1; border-radius:3px;}
 .wallet-history-separator {border-top:1px solid #e5e7eb; margin:.6rem 0;}
 /* Wallet card header clearly separates independent portfolios. */
 .wallet-banner {
     display:flex; align-items:center; justify-content:space-between;
     gap: 1rem; flex-wrap:wrap;
     border: 1px solid var(--wallet-border);
     border-left: 5px solid var(--wallet-accent);
     background: var(--wallet-background);
     border-radius: 8px; padding: .7rem 1rem; margin-bottom: .5rem;
 }
 .wallet-banner-title {font-size: 1.25rem; color: #1e293b; font-weight: 750; line-height:1.3;}
 .wallet-banner-sub {font-size: .73rem; color: #64748b; letter-spacing:.045em; font-weight:600;}
 .wallet-banner-summary {font-size: .8rem; color:#46566d; font-weight:600;}
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

# Il P/L realizzato include anche titoli interamente venduti: il ledger mantiene
# la voce contabile per ogni combinazione portafoglio/titolo/valuta/broker.
realized_by_portfolio = {}
for (portfolio_name, _, _, _), accounting_position in ledger['positions'].items():
    realized_by_portfolio[portfolio_name] = (
        realized_by_portfolio.get(portfolio_name, D(0)) + accounting_position['realized']
    )

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
    # The accounting ledger keeps sold-out positions. Keep their rows visible too,
    # so users can open the full trade history or reopen the position via Buy.
    traded_keys = {(r['portfolio'], r['ticker'], r['currency'], r['broker'] or '')
                   for r in active if r['kind'] in ('BUY', 'SELL')}
    for (portfolio, ticker, currency, broker), pos in ledger['positions'].items():
        key = (portfolio, ticker, currency, broker)
        closed = pos['quantity'] <= 0
        if closed and key not in traded_keys:
            continue  # A dividend-only record is not a former position.
        row = {'Portafoglio': portfolio, 'Ticker': ticker, 'Broker': broker or 'Non specificato',
               'Quantità': 0.0 if closed else float(pos['quantity']),
               'PMC €': None if closed else float(pos['cost']/pos['quantity']),
               'Costo €': 0.0 if closed else float(pos['cost']),
               'Valuta': currency, 'Prezzo attuale': None,
               'Valore €': 0.0 if closed else None,
               'P/L €': 0.0 if closed else None, 'P/L %': None,
               'Peso %': 0.0 if closed else None,
               'Obiettivo %': targets.get(key),
               'Scostamento pp': None, 'Forward Yield %': None,
               'Dividendo annuo €': 0.0 if closed else None,
               'Chiusa': closed, '_key': key}
        if not closed:
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
        # Nessuna posizione negoziata attiva o storica: in tal caso rimangono
        # consultabili soltanto eventuali valori contabili (es. dividendi).
        if view == 'Dashboard generale':
            a, b = st.columns(2)
            a.metric('P/L realizzato', eur(ledger['realized']), delta=eur(ledger['realized']))
            b.metric('P/L complessivo', eur(ledger['realized']), delta=eur(ledger['realized']))
        else:
            for wallet, wallet_realized in sorted(realized_by_portfolio.items()):
                st.markdown('### ' + wallet)
                a, b = st.columns(2)
                a.metric('P/L realizzato', eur(wallet_realized), delta=eur(wallet_realized))
                b.metric('P/L complessivo', eur(wallet_realized), delta=eur(wallet_realized))
    else:
        def fmt_money(value):
            if value is None or pd.isna(value):
                return '—'
            return eur(value)

        def fmt_pct(value):
            if value is None or pd.isna(value):
                return '—'
            return f'{float(value):.2f}'.replace('.', ',') + ' %'

        def stable_id(key):
            # Le chiavi non dipendono dall'ordine delle posizioni e isolano il broker.
            return hashlib.sha256(repr(key).encode('utf-8')).hexdigest()[:16]

        def set_inline_action(row, mode, entry_id=None):
            """Un solo pannello attivo alla volta, sempre dentro lo storico."""
            key = row['_key']
            selection = {'key': key, 'mode': mode, 'entry_id': entry_id}
            if st.session_state.get('inline_action') == selection:
                st.session_state.pop('inline_action', None)
            else:
                st.session_state['inline_action'] = selection
            st.session_state[f'history_open_{stable_id(key)}'] = True

        def commit_inline(action, payload=None, row_id=None):
            """Il ledger controlla l'intera cronologia prima di scrivere."""
            try:
                mutate(engine, action, payload, row_id, actor)
                st.session_state.pop('inline_action', None)
                st.rerun()
            except (LedgerError, ValueError, ArithmeticError) as exc:
                st.error(str(exc))
            except Exception:
                st.error('Salvataggio non riuscito. Riprova o verifica i dati.')

        def render_inline_panel(row, suffix, item_id):
            """Un unico riquadro per storico e acquisto, vendita, modifica, elimina."""
            key = row['_key']
            history = trades_for_position(active, key)
            action = st.session_state.get('inline_action')
            selected = action if action and action.get('key') == key else None

            with st.container(border=True):
                st.markdown(f"**Storico acquisti e vendite** · {row['Ticker']} · {row['Broker']}")
                if history:
                    widths_history = [1.0, 1.05, .82, 1.07, 1.07, 1.0, .53, .53]
                    header = st.columns(widths_history, vertical_alignment='center', gap='small')
                    for col, name in zip(header, ['Data', 'Operazione', 'Quantità', 'Prezzo unitario',
                                                  'Totale €', 'Commissioni', 'Modifica', 'Elimina']):
                        col.caption('**' + name + '**')
                    for transaction in history:
                        transaction_id = int(transaction['id'])
                        cells = st.columns(widths_history, vertical_alignment='center', gap='small')
                        trade_day = date.fromisoformat(str(transaction['trade_date'])).strftime('%d/%m/%Y')
                        cells[0].markdown(trade_day)
                        kind = transaction['kind']
                        cells[1].markdown(':green[Acquisto]' if kind == 'BUY' else ':red[Vendita]')
                        qty_prefix = '+' if kind == 'BUY' else '−'
                        quantity_display = qty_prefix + fmt_quantity(transaction['quantity'])
                        cells[2].markdown(':green[' + quantity_display + ']' if kind == 'BUY'
                                          else ':red[' + quantity_display + ']')
                        cells[3].markdown(fmt_money(transaction['unit_price']))
                        # Totale lordo espresso in EUR al cambio storico, senza commissioni.
                        # Resta positivo sia per acquisti sia per vendite; il segno e il
                        # colore della quantità identificano la direzione del movimento.
                        gross_total = (D(transaction['quantity']) *
                                       D(transaction['unit_price']) * D(transaction['fx_eur']))
                        cells[4].markdown(eur(gross_total))
                        cells[5].markdown(fmt_money(transaction['fee']))
                        if cells[6].button('✏️', key=f'edit_{suffix}_{item_id}_{transaction_id}',
                                           help=f'Modifica operazione del {trade_day}', use_container_width=True):
                            set_inline_action(row, 'EDIT', transaction_id)
                            st.rerun()
                        if cells[7].button('🗑️', key=f'delete_{suffix}_{item_id}_{transaction_id}',
                                           help=f'Elimina operazione del {trade_day}', use_container_width=True):
                            set_inline_action(row, 'DELETE', transaction_id)
                            st.rerun()
                    st.caption('Totale € = quantità × prezzo unitario × cambio storico EUR; commissioni escluse.')
                else:
                    st.caption('Nessuna operazione registrata per questa posizione.')

                # I moduli compaiono QUI, mai in un secondo riquadro sotto lo storico.
                if not selected:
                    return

                mode = selected['mode']
                original = next((t for t in history if int(t['id']) == selected.get('entry_id')), None)
                if mode in ('EDIT', 'DELETE') and original is None:
                    st.warning('Operazione non più disponibile. Apri nuovamente lo storico.')
                    return

                st.markdown('<div class="wallet-history-separator"></div>', unsafe_allow_html=True)
                if mode == 'DELETE':
                    trade_date = date.fromisoformat(str(original['trade_date'])).strftime('%d/%m/%Y')
                    st.warning(f"Eliminare l'operazione #{original['id']} del {trade_date}? "
                               'Scomparirà dallo storico attivo, ma resterà nel registro di controllo.')
                    confirm_key = f'inline_confirm_{suffix}_{item_id}_{original["id"]}'
                    confirmed = st.checkbox('Confermo l’eliminazione di questa operazione', key=confirm_key)
                    yes, no = st.columns(2)
                    if yes.button('Elimina operazione', type='primary', disabled=not confirmed,
                                  key=f'inline_delete_yes_{suffix}_{item_id}', use_container_width=True):
                        commit_inline('delete', row_id=original['id'])
                    if no.button('Annulla', key=f'inline_delete_no_{suffix}_{item_id}', use_container_width=True):
                        st.session_state.pop('inline_action', None)
                        st.rerun()
                    return

                if mode == 'EDIT':
                    original_kind = original['kind']
                    mode_title = 'Modifica acquisto' if original_kind == 'BUY' else 'Modifica vendita'
                    default_qty = float(original['quantity'])
                    default_price = float(original['unit_price'])
                    default_fee = float(original['fee'])
                    default_date = date.fromisoformat(str(original['trade_date']))
                else:
                    original_kind = mode
                    mode_title = 'Nuovo acquisto' if mode == 'BUY' else 'Nuova vendita'
                    default_qty, default_price, default_fee, default_date = 1.0, 0.0, 0.0, date.today()

                st.markdown('**' + mode_title + '**')
                form_id = f'inline_{suffix}_{item_id}_{mode}_{selected.get("entry_id") or "new"}'
                with st.form(form_id):
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        qty = st.number_input('Quantità', min_value=0.01, value=default_qty,
                                              step=1.0, format='%.2f')
                    with c2:
                        price = st.number_input('Prezzo unitario (€)', min_value=0.0,
                                                value=default_price, step=0.5, format='%.2f')
                    with c3:
                        fee = st.number_input('Commissioni (€)', min_value=0.0,
                                              value=default_fee, step=0.5, format='%.2f')
                    with c4:
                        day = st.date_input('Data', value=default_date)
                    save, cancel = st.columns(2)
                    submitted = save.form_submit_button('Salva ' + ('modifica' if mode == 'EDIT'
                                                                    else mode_title.lower()),
                                                        type='primary', use_container_width=True)
                    dismissed = cancel.form_submit_button('Chiudi', use_container_width=True)
                if dismissed:
                    st.session_state.pop('inline_action', None)
                    st.rerun()
                if submitted:
                    if price <= 0:
                        st.error('Indica un prezzo unitario maggiore di zero.')
                        return
                    if mode == 'SELL' and qty > row['Quantità'] + 1e-8:
                        st.error('La quantità venduta supera quella disponibile in questa posizione.')
                        return
                    if mode == 'EDIT':
                        # Non permettiamo di spostare una transazione su un altro asset/broker.
                        # Manteniamo anche note, cambio storico e altri dati originali.
                        payload = {field: original[field] for field in (
                            'portfolio', 'ticker', 'label', 'kind', 'trade_date', 'quantity',
                            'unit_price', 'currency', 'fx_eur', 'fee', 'notes', 'broker')}
                        payload.update(trade_date=day.isoformat(), quantity=qty,
                                       unit_price=price, fee=fee)
                        commit_inline('edit', payload, original['id'])
                    else:
                        previous = history[0] if history else None
                        payload = dict(portfolio=key[0], ticker=key[1], currency=key[2], broker=key[3],
                                       kind=mode, trade_date=day.isoformat(), quantity=qty,
                                       unit_price=price, fee=fee, fx_eur=1.0,
                                       label=previous['label'] if previous else '', notes='')
                        commit_inline('add', payload)

        def table(items, suffix, general=False, realized_override=None):
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
                status = ' · :gray[CHIUSA]' if row['Chiusa'] else ''
                vals = [f"**{row['Ticker']}**{status}  \n{row['Broker']}", fmt_quantity(row['Quantità']),
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
                    key=target_key, label_visibility='collapsed', disabled=row['Chiusa'],
                    on_change=set_target, args=(row['_key'], target_key))
                cells[cell_index + 8].write(fmt_pct(row['Forward Yield %']))
                cells[cell_index + 9].write(fmt_money(row['Dividendo annuo €']))
                actions = cells[cell_index + 10].columns(2, gap='small')
                if actions[0].button('＋', key=f'plus_{suffix}_{item_id}', help='Acquista', use_container_width=True):
                    set_inline_action(row, 'BUY')
                    st.rerun()
                if actions[1].button('−', key=f'minus_{suffix}_{item_id}', help='Vendi',
                                     use_container_width=True, disabled=row['Chiusa']):
                    set_inline_action(row, 'SELL')
                    st.rerun()

                history_key = f'history_open_{item_id}'
                is_open = bool(st.session_state.get(history_key, False))
                arrow = '▴' if is_open else '▾'
                if cells[cell_index + 11].button(arrow, key=f'history_{suffix}_{item_id}',
                                                  help='Chiudi storico' if is_open else 'Apri storico acquisti e vendite',
                                                  use_container_width=True):
                    st.session_state[history_key] = not is_open
                    if is_open and st.session_state.get('inline_action', {}).get('key') == row['_key']:
                        st.session_state.pop('inline_action', None)
                    st.rerun()
                if is_open:
                    render_inline_panel(row, suffix, item_id)
                st.markdown('<div style="border-bottom:1px solid #e5e7eb;margin:3px 0 9px 0"></div>', unsafe_allow_html=True)

            value_sum = sum((r['Valore €'] or 0) for r in items)
            pnl_sum = sum((r['P/L €'] or 0) for r in items)
            target_sum = sum(float(r['Obiettivo %'] or 0) for r in items if not r['Chiusa'])
            div_sum = sum((r['Dividendo annuo €'] or 0) for r in items)
            weights_sum = sum((r['Peso %'] or 0) for r in items)
            # Nella vista aggregata includiamo il P/L dei titoli totalmente venduti.
            portfolios_in_table = {r['Portafoglio'] for r in items}
            realized_sum = (realized_override if realized_override is not None else
                            sum((realized_by_portfolio.get(p, D(0)) for p in portfolios_in_table), D(0)))
            total_pnl = D(str(pnl_sum)) + realized_sum
            st.markdown('**TOTALE PORTAFOGLIO** · Valore: **'+fmt_money(value_sum)+
                        '** · P/L non realizzato: **'+fmt_money(pnl_sum)+
                        '** · P/L realizzato: **'+fmt_money(realized_sum)+
                        '** · P/L complessivo: **'+fmt_money(total_pnl)+
                        '** · Peso: **'+fmt_pct(weights_sum)+
                        '** · Obiettivi: **'+fmt_pct(target_sum)+
                        '** · Dividendi annui: **'+fmt_money(div_sum)+'**')
            if target_sum > 100.000001:
                st.warning('La somma degli obiettivi supera il 100%.')
            elif target_sum < 99.999999:
                st.caption(f'Obiettivi assegnati: {fmt_pct(target_sum)} (mancano {fmt_pct(100-target_sum)} al 100%)')

        if view == 'Dashboard generale':
            unrealized = D(str(total_value)) - D(str(priced_cost))
            realized = ledger['realized']
            a,b,c,d,e = st.columns(5)
            a.metric('Valore valorizzato', eur(total_value))
            b.metric('P/L non realizzato*', eur(unrealized), delta=eur(unrealized))
            c.metric('P/L realizzato', eur(realized), delta=eur(realized))
            d.metric('P/L complessivo*', eur(unrealized + realized),
                     delta=eur(unrealized + realized))
            e.metric('Dividendi annui stimati', eur(estimated_div))
            st.caption('Costo posizioni: ' + eur(total_cost) +
                       '. *P/L non realizzato solo su titoli quotati; P/L complessivo = realizzato + non realizzato, '
                       'esclusi i dividendi. Dividendi annui: stima lorda, non incassi effettivi.')
            pie_df = pd.DataFrame([{'Portafoglio':k,'Valore €':v} for k,v in totals_by_portfolio.items() if v>0])
            if not pie_df.empty:
                st.plotly_chart(px.pie(pie_df, names='Portafoglio', values='Valore €', hole=.5), use_container_width=True)
            st.markdown('#### Tutti i titoli — inclusi quelli chiusi')
            table(positions, 'generale', general=True, realized_override=ledger['realized'])
        else:
            wallet_names = sorted({r['Portafoglio'] for r in positions} | set(realized_by_portfolio))
            palette = [('#3172bc', '#edf5ff', '#c9ddf5'),
                       ('#16836b', '#edfaf5', '#c4e9db'),
                       ('#7c64ac', '#f5f1fb', '#e0d5f0'),
                       ('#b4792a', '#fcf5e9', '#efddbd')]
            for wallet_index, portfolio in enumerate(wallet_names):
                part = sorted((r for r in positions if r['Portafoglio'] == portfolio),
                              key=lambda r: (r['Chiusa'], r['Ticker'], r['Broker']))
                open_count = sum(not r['Chiusa'] for r in part)
                closed_count = sum(r['Chiusa'] for r in part)
                accent, bg, border = palette[wallet_index % len(palette)]
                p_value = sum(x['Valore €'] or 0 for x in part)
                p_cost = sum(x['Costo €'] for x in part if x['Valore €'] is not None)
                p_div = sum(x['Dividendo annuo €'] or 0 for x in part)
                unrealized = D(str(p_value)) - D(str(p_cost))
                realized = realized_by_portfolio.get(portfolio, D(0))
                # Border encloses header, KPIs, all position rows and expanded histories.
                with st.container(border=True):
                    safe_name = escape(str(portfolio))
                    status_summary = f'{open_count} aperte · {closed_count} chiuse'
                    st.markdown(
                        f'<div class="wallet-banner" style="--wallet-accent:{accent};'
                        f'--wallet-background:{bg};--wallet-border:{border}">'
                        f'<div><div class="wallet-banner-sub">PORTAFOGLIO {wallet_index + 1:02d}</div>'
                        f'<div class="wallet-banner-title">▣ {safe_name}</div></div>'
                        f'<div class="wallet-banner-summary">{status_summary}</div></div>',
                        unsafe_allow_html=True)
                    a,b,c,d,e = st.columns(5)
                    a.metric('Valore portafoglio', eur(p_value))
                    b.metric('P/L non realizzato', eur(unrealized), delta=eur(unrealized))
                    c.metric('P/L realizzato', eur(realized), delta=eur(realized))
                    d.metric('P/L complessivo', eur(unrealized + realized), delta=eur(unrealized + realized))
                    e.metric('Dividendi annui stimati', eur(p_div))
                    if open_count == 0 and closed_count:
                        st.caption('Posizioni chiuse: apri la freccia per consultare lo storico, oppure usa ＋ per riacquistare.')
                    if part:
                        table(part, f'port_{wallet_index}', realized_override=realized)
                    else:
                        st.caption('Nessuna posizione da mostrare per questo portafoglio.')
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
