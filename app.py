import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, date, time as dtime, timedelta
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

# Automatyczna godzina (we wtorki domyślnie 17:00, w pozostałe dni 00:00)
is_tuesday = now_pl.weekday() == 1
default_time = dtime(17, 0) if is_tuesday else dtime(0, 0)
selected_time = st.sidebar.time_input("Godzina rozpoczęcia", value=default_time)

selection_mode = st.sidebar.radio(
    "Wybór partii do tabeli:",
    ["Pierwsze 11 od godziny startu", "Ostatnie 11 rozegranych"],
    index=0
)

debug_mode = st.sidebar.checkbox("🐞 Tryb debugowania (pokaż dane)", value=False)

# Punkt odcięcia
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

def fetch_games_for_month(username, year, month, headers, req_time):
    # Dodałem z powrotem ?cb= aby omijać cache na serwerach Chess.com
    url = f"https://api.chess.com/pub/player/{username.lower()}/games/{year:04d}/{month:02d}?cb={req_time}"
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json().get('games', [])
    except Exception:
        pass
    return []

def fetch_all_possible_sources(username, start_dt):
    req_time = int(time.time() * 1000)
    
    # Agresywne nagłówki blokujące zapisywanie w pamięci podręcznej (cache)
    headers = {
        'User-Agent': f'ChessTournamentTracker/3.0 (user: {username}) ts={req_time}',
        'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

    found_games = {}

    # 1. Obecny miesiąc
    g1 = fetch_games_for_month(username, start_dt.year, start_dt.month, headers, req_time)
    for g in g1:
        if 'url' in g:
            found_games[g['url']] = g

    # 2. Poprzedni miesiąc (zabezpieczenie stref czasowych)
    prev_month_date = start_dt - timedelta(days=15)
    g2 = fetch_games_for_month(username, prev_month_date.year, prev_month_date.month, headers, req_time)
    for g in g2:
        if 'url' in g:
            found_games[g['url']] = g

    # Filtracja po dacie/czasie (odrzucamy partie zakończone przed ustaloną godziną)
    cutoff_ts = start_dt.timestamp()
    valid_games = []

    for g in found_games.values():
        end_ts = g.get('end_time', 0)
        if end_ts >= cutoff_ts:
            valid_games.append(g)

    # Sortowanie od najstarszej do najnowszej
    valid_games.sort(key=lambda x: x.get('end_time', 0))
    return valid_games, found_games

# Pobieranie gier
games, all_raw_games = fetch_all_possible_sources(USERNAME, start_cutoff_dt)

# Wyświetlanie danych dla trybu debugowania
if debug_mode:
    st.info(f"**🐞 Tryb debugowania**\nGodzina odcięcia (Unix timestamp): {start_cutoff_dt.timestamp()}")
    all_sorted = sorted(all_raw_games.values(), key=lambda x: x.get('end_time', 0))
    if all_sorted:
        last_raw_game = all_sorted[-1]
        last_time_pl = datetime.fromtimestamp(last_raw_game['end_time'], tz=poland_tz)
        st.warning(f"Najnowsza gra pobrana z API Chess.com zakończyła się: **{last_time_pl.strftime('%Y-%m-%d %H:%M:%S')}**. Została rozegrana z przeciwnikiem: **{last_raw_game.get('black', {}).get('username') if last_raw_game.get('white', {}).get('username').lower() == USERNAME.lower() else last_raw_game.get('white', {}).get('username')}**.")
    else:
        st.error("API Chess.com aktualnie nie zwraca ŻADNYCH gier w tym i poprzednim miesiącu (błąd API).")

# Wybór 11 partii zależnie od opcji
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

# Ważne: co 5 sekund to bardzo szybko, jeśli problem z banem IP od Chess.com by się pojawił, zmień to na 10
time.sleep(5)
st.rerun()
