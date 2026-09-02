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
    
    /* Pełna przezroczystość tła Streamlit */
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

    /* Przezroczystość dla tabeli */
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
        background-color: rgba(0, 0, 0, 0.4) !important; /* Lekkie przyciemnienie nagłówka dla czytelności */
        border-bottom: 2px solid #D4AF37 !important;
        text-align: left !important;
    }

    /* Szerokości kolumn */
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

selected_date = st.sidebar.date_input("Data turnieju", value=date.today())
selected_time = st.sidebar.time_input("Godzina rozpoczęcia", value=dtime(17, 0))

selection_mode = st.sidebar.radio(
    "Wybiór partii do tabeli:",
    ["Pierwsze 11 od godziny startu", "Ostatnie 11 rozegranych"],
    index=0
)

# Punkt odcięcia czasowego w strefie czasowej Polski
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

def fetch_games_for_month(username, year, month, headers):
    """Pobiera archiwum gier z danego miesiąca z obsługą błędów 404"""
    url = f"https://api.chess.com/pub/player/{username.lower()}/games/{year:04d}/{month:02d}"
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json().get('games', [])
    except Exception:
        pass
    return []

def fetch_all_possible_sources(username, start_dt):
    """Pobiera partie z obecnego i poprzedniego miesiąca oraz z live endpointu"""
    headers = {
        'User-Agent': f'ChessTournamentTracker/2.0 (user: {username})',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache'
    }

    found_games = {}

    # 1. Pobierz gry z obecnego miesiąca wyznaczonej daty
    g1 = fetch_games_for_month(username, start_dt.year, start_dt.month, headers)
    for g in g1:
        if 'url' in g:
            found_games[g['url']] = g

    # 2. Pobierz gry z poprzedniego miesiąca (na wypadek przełomu miesięcy/stref czasowych)
    prev_month_date = start_dt - timedelta(days=15)
    g2 = fetch_games_for_month(username, prev_month_date.year, prev_month_date.month, headers)
    for g in g2:
        if 'url' in g:
            found_games[g['url']] = g

    # 3. Endpoint z najnowszymi/aktywnymi grami
    url_live = f"https://api.chess.com/pub/player/{username.lower()}/games"
    try:
        r_live = requests.get(url_live, headers=headers, timeout=5)
        if r_live.status_code == 200:
            for g in r_live.json().get('games', []):
                if 'url' in g:
                    found_games[g['url']] = g
    except Exception:
        pass

    # Przefiltruj partie: wyłącznie blitz/bullet/rapid zakończone PO ustalonej godzinie rozpoczęcia
    cutoff_ts = start_dt.timestamp()
    valid_games = []

    for g in found_games.values():
        end_ts = g.get('end_time', 0)
        if end_ts >= cutoff_ts:
            valid_games.append(g)

    # Sortowanie chronologiczne
    valid_games.sort(key=lambda x: x.get('end_time', 0))
    return valid_games

# Pobranie przefiltrowanych partii
games = fetch_all_possible_sources(USERNAME, start_cutoff_dt)

# Wybór 11 partii zależnie od ustawienia w Sidebarze
if selection_mode == "Pierwsze 11 od godziny startu":
    tournament_games = games[:11]
else:
    tournament_games = games[-11:] if len(games) >= 11 else games

played_count = len(tournament_games)

# Budowanie tabeli na 11 rund
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

# Wyświetlanie tabeli
st.subheader("📊 Wyniki Turnieju")

df = pd.DataFrame(processed_games)
st.table(df)

st.caption(f"🔄 Czas serwera: **{datetime.now(poland_tz).strftime('%H:%M:%S')}** | Zarejestrowanych partii: **{played_count}**")

# Automatyczne odświeżanie co 5 sekund
time.sleep(5)
st.rerun()
