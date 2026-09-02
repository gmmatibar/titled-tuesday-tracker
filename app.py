import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, date, time as dtime
import zoneinfo

st.set_page_config(page_title="Titled Tuesday Tracker", page_icon="♟️", layout="wide")

USERNAME = "matibar"

# --- STYLOWANIE CSS (TRANSPARENTNE TŁO) ---
st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/comic-sans-ms');
    
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] {
        background-color: transparent !important;
        background: transparent !important;
    }
    html, body, [class*="css"], .stMarkdown, table {
        font-family: 'Comic Sans MS', 'Comic Sans', cursive, sans-serif !important;
    }
    h3 {
        color: #D4AF37 !important;
        font-family: 'Comic Sans MS', 'Comic Sans', cursive, sans-serif !important;
        font-size: 20px !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.9) !important;
    }
    div[data-testid="stTable"] {
        width: 520px !important;
        background-color: transparent !important;
    }
    div[data-testid="stTable"] table {
        background-color: transparent !important;
        border-collapse: collapse !important;
        table-layout: fixed !important;
        width: 100% !important;
        border-radius: 6px !important;
        overflow: hidden !important;
    }
    div[data-testid="stTable"] td, div[data-testid="stTable"] th {
        background-color: transparent !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.2) !important;
        padding: 4px 5px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        color: #D4AF37 !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.9) !important;
    }
    div[data-testid="stTable"] th {
        background-color: rgba(0, 0, 0, 0.4) !important; 
        border-bottom: 2px solid #D4AF37 !important;
        text-align: left !important;
    }
    div[data-testid="stTable"] table th:nth-child(1),
    div[data-testid="stTable"] table td:nth-child(1) { width: 35px !important; }
    
    div[data-testid="stTable"] table th:nth-child(2),
    div[data-testid="stTable"] table td:nth-child(2) { width: 135px !important; }
    
    div[data-testid="stTable"] table th:nth-child(3),
    div[data-testid="stTable"] table td:nth-child(3) { width: 180px !important; }
    
    div[data-testid="stTable"] table th:nth-child(4),
    div[data-testid="stTable"] table td:nth-child(4) { width: 65px !important; }
    
    div[data-testid="stTable"] table th:nth-child(5),
    div[data-testid="stTable"] table td:nth-child(5) { width: 50px !important; }
    
    div[data-testid="stTable"] table th:nth-child(6),
    div[data-testid="stTable"] table td:nth-child(6) { width: 55px !important; }
    
    div[data-testid="stTable"] td:nth-child(1), div[data-testid="stTable"] th:nth-child(1),
    div[data-testid="stTable"] td:nth-child(5), div[data-testid="stTable"] th:nth-child(5),
    div[data-testid="stTable"] td:nth-child(6), div[data-testid="stTable"] th:nth-child(6) {
        text-align: center !important;
    }
    .stCaption {
        color: #E0E0E0 !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.9) !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- PANEL STEROWANIA ---
st.sidebar.header("⚙️ Ustawienia Turnieju")

poland_tz = zoneinfo.ZoneInfo("Europe/Warsaw")
now_pl = datetime.now(poland_tz)
st.sidebar.info(f"🕒 **Czas PL:** {now_pl.strftime('%H:%M:%S')}")

selected_date = st.sidebar.date_input("Data turnieju", value=now_pl.date())

# We wtorki domyślnie 17:00, w pozostałe dni 00:00 (łapie wszystkie partie od północy)
is_tuesday = now_pl.weekday() == 1
default_time = dtime(17, 0) if is_tuesday else dtime(0, 0)
selected_time = st.sidebar.time_input("Godzina rozpoczęcia", value=default_time)

selection_mode = st.sidebar.radio(
    "Wybór partii do tabeli:",
    ["Pierwsze 11 od godziny startu", "Ostatnie 11 rozegranych"],
    index=0
)

debug_mode = st.sidebar.checkbox("🐞 Tryb debugowania (szczegóły)", value=False)

# Punkt odcięcia czasowego
start_cutoff_dt = datetime.combine(selected_date, selected_time).replace(tzinfo=poland_tz)

def parse_result(result_code):
    win_codes = ['win']
    draw_codes = ['agreed', 'repetition', 'stalemate', 'insufficient', '50move', 'timevsinsufficient']
    if result_code in win_codes:
        return 1.0, "1"
    elif result_code in draw_codes:
        return 0.5, "0,5"
    else:
        return 0.0, "0"

def fetch_all_possible_sources(username, target_date, cutoff_ts):
    req_time = int(time.time() * 1000)
    
    # Nagłówki z pierwszego kodu (sprawdzone omijanie cache)
    headers = {
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) TrackerBot/{req_time}',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache'
    }

    found_games = {}

    # 1. ARCHIWUM MIESIĘCZNE (dla wybranej daty)
    url_month = f"https://api.chess.com/pub/player/{username.lower()}/games/{target_date.year:04d}/{target_date.month:02d}?cb={req_time}"
    try:
        r1 = requests.get(url_month, headers=headers, timeout=5)
        if r1.status_code == 200:
            for g in r1.json().get('games', []):
                if 'url' in g:
                    found_games[g['url']] = g
    except Exception:
        pass

    # 2. PARTIE NA ŻYWO (PRZYWRÓCONE!) - niezbędne do łapania partii z ostatnich kilkunastu minut
    url_live = f"https://api.chess.com/pub/player/{username.lower()}/games?cb={req_time}"
    try:
        r2 = requests.get(url_live, headers=headers, timeout=5)
        if r2.status_code == 200:
            for g in r2.json().get('games', []):
                if 'url' in g:
                    found_games[g['url']] = g
    except Exception:
        pass

    valid_games = []
    all_today_games = [] # Do debugowania

    for g in found_games.values():
        end_ts = g.get('end_time')
        if not end_ts:
            continue # Pomijamy partie, które jeszcze trwają
            
        g_date_pl = datetime.fromtimestamp(end_ts, tz=poland_tz).date()
        
        # Filtrujemy tylko partie z wybranego dnia
        if g_date_pl == target_date:
            all_today_games.append(g)
            # Sprawdzamy czy partia zakończyła się PO wybranej godzinie rozpoczęcia
            if end_ts >= cutoff_ts:
                valid_games.append(g)

    # Sortowanie od najstarszej do najnowszej
    valid_games.sort(key=lambda x: x.get('end_time', 0))
    all_today_games.sort(key=lambda x: x.get('end_time', 0))
    
    return valid_games, all_today_games

# Pobieranie gier
games, all_today_games = fetch_all_possible_sources(USERNAME, selected_date, start_cutoff_dt.timestamp())

# Wyświetlanie danych dla trybu debugowania
if debug_mode:
    st.info(f"**🐞 Tryb debugowania** - Godzina odcięcia: {start_cutoff_dt.strftime('%H:%M:%S')}")
    if not all_today_games:
        st.error(f"API Chess.com aktualnie nie zwraca ŻADNYCH zakończonych partii dla dnia {selected_date}.")
    else:
        debug_data = []
        for g in all_today_games:
            dt_pl = datetime.fromtimestamp(g['end_time'], tz=poland_tz)
            is_white = (g['white']['username'].lower() == USERNAME.lower())
            opp = g['black']['username'] if is_white else g['white']['username']
            status = "✅ POKAZANA" if g['end_time'] >= start_cutoff_dt.timestamp() else "❌ ODRZUCONA (przed czasem)"
            debug_data.append({
                "Godzina (PL)": dt_pl.strftime('%H:%M:%S'),
                "Przeciwnik": opp,
                "Status filtra": status
            })
        st.write("Wszystkie dzisiejsze partie znalezione w API:")
        st.dataframe(pd.DataFrame(debug_data))

# Wybór 11 partii
if selection_mode == "Pierwsze 11 od godziny startu":
    tournament_games = games[:11]
else:
    tournament_games = games[-11:] if len(games) >= 11 else games

played_count = len(tournament_games)

# Budowa struktury tabeli
processed_games = []
for rd in range(1, 12):
    if (rd - 1) < played_count:
        game = tournament_games[rd - 1]
        white = game['white']['username']
        black = game['black']['username']
        
        is_white = (white.lower() == USERNAME.lower())
        opponent_username = black if is_white else white
        opp_rating = game['black']['rating'] if is_white else game['white']['rating']
        player_result_code = game['white']['result'] if is_white else game['black']['result']
        
        _, result_text = parse_result(player_result_code)

        processed_games.append({
            "Rd.": rd,
            "Przeciwnik": opponent_username,
            "Ranking": str(opp_rating),
            "Kolor": "⚪" if is_white else "⚫",
            "Wynik": result_text
        })
    else:
        processed_games.append({
            "Rd.": rd,
            "Przeciwnik": "—",
            "Ranking": "—",
            "Kolor": "—",
            "Wynik": "—"
        })

# Wyświetlanie
st.subheader("📊 Wyniki Turnieju")

df = pd.DataFrame(processed_games)
st.table(df)

st.caption(f"🔄 Czas serwera: **{datetime.now(poland_tz).strftime('%H:%M:%S')}** | Zarejestrowanych partii: **{played_count}**")

# Automatyczne odświeżanie
time.sleep(5)
st.rerun()
