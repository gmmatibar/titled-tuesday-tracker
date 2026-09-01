import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, date
import zoneinfo

st.set_page_config(page_title="Titled Tuesday Tracker", page_icon="♟️", layout="wide")

USERNAME = "matibar"

# --- STYLOWANIE CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/comic-sans-ms');
    
    html, body, [class*="css"], .stMarkdown, table {
        font-family: 'Comic Sans MS', 'Comic Sans', cursive, sans-serif !important;
    }

    div[data-testid="stTable"] table * {
        color: #D4AF37 !important;
        font-family: 'Comic Sans MS', 'Comic Sans', cursive, sans-serif !important;
        font-size: 13px !important;
    }

    h3 {
        color: #D4AF37 !important;
        font-family: 'Comic Sans MS', 'Comic Sans', cursive, sans-serif !important;
        font-size: 20px !important;
    }

    div[data-testid="stTable"] { width: 520px !important; }

    div[data-testid="stTable"] table {
        background-color: #1A1A1A !important;
        border-collapse: collapse !important;
        table-layout: fixed !important;
        width: 100% !important;
        border-radius: 6px !important;
        overflow: hidden !important;
    }

    div[data-testid="stTable"] td, div[data-testid="stTable"] th {
        background-color: #1A1A1A !important;
        border-bottom: 1px solid #282828 !important;
        padding: 4px 5px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    div[data-testid="stTable"] th {
        background-color: #141414 !important;
        border-bottom: 2px solid #333333 !important;
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
    </style>
""", unsafe_allow_html=True)

# --- PANEL STEROWANIA ---
st.sidebar.header("⚙️ Ustawienia Turnieju")

poland_tz = zoneinfo.ZoneInfo("Europe/Warsaw")
st.sidebar.info(f"🕒 **Czas PL:** {datetime.now(poland_tz).strftime('%H:%M:%S')}")

selected_date = st.sidebar.date_input("Data turnieju", value=date.today())

def parse_result(result_code):
    win_codes = ['win']
    draw_codes = ['agreed', 'repetition', 'stalemate', 'insufficient', '50move', 'timevsinsufficient']
    if result_code in win_codes:
        return 1.0, "1"
    elif result_code in draw_codes:
        return 0.5, "0,5"
    else:
        return 0.0, "0"

def fetch_all_possible_sources(username, target_date):
    """Pobiera partie jednocześnie ze wszystkich znanych źródeł API Chess.com"""
    req_time = int(time.time() * 1000)
    headers = {
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) TrackerBot/{req_time}',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache'
    }

    found_games = {}

    # Zapytanie 1: Archwiu miesięczne z bypassem cache
    year_str = target_date.strftime("%Y")
    month_str = target_date.strftime("%m")
    url_month = f"https://api.chess.com/pub/player/{username.lower()}/games/{year_str}/{month_str}?cb={req_time}"
    
    try:
        r1 = requests.get(url_month, headers=headers, timeout=5)
        if r1.status_code == 200:
            for g in r1.json().get('games', []):
                if 'url' in g:
                    found_games[g['url']] = g
    except Exception:
        pass

    # Zapytanie 2: Endpoint gier w trakcie i bezpośrednio zakończonych
    url_live = f"https://api.chess.com/pub/player/{username.lower()}/games?cb={req_time}"
    try:
        r2 = requests.get(url_live, headers=headers, timeout=5)
        if r2.status_code == 200:
            for g in r2.json().get('games', []):
                if 'url' in g:
                    found_games[g['url']] = g
    except Exception:
        pass

    # Przefiltrowanie gier wyłącznie z wybranego dnia (typ blitz)
    today_blitz = []
    for g in found_games.values():
        end_ts = g.get('end_time', 0)
        g_date_pl = datetime.fromtimestamp(end_ts, tz=poland_tz).date()
        
        if g_date_pl == target_date and g.get('time_class') == 'blitz':
            today_blitz.append(g)

    # Sortowanie chronologiczne od 1 rundy do ostatniej
    today_blitz.sort(key=lambda x: x.get('end_time', 0))
    return today_blitz

# Pobieranie gier
games = fetch_all_possible_sources(USERNAME, selected_date)

# Jeśli partii jest więcej niż 11 (np. zagrałeś dzisiaj też inne partie blitz przed turniejem),
# bierzemy OSTATNIE rozegrane partie z dzisiejszego dnia
if len(games) > 11:
    tournament_games = games[-11:]
else:
    tournament_games = games

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
st.subheader("📊 Wyniki w Titled Tuesday")

df = pd.DataFrame(processed_games)
st.table(df)

st.caption(f"🔄 Czas serwera: **{datetime.now(poland_tz).strftime('%H:%M:%S')}** | Wykryto dzisiejszych partii: **{played_count}**")

# Odświeżanie co 5 sekund
time.sleep(5)
st.rerun()
