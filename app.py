import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import zoneinfo
import re

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

tournament_input = st.sidebar.text_input(
    "URL lub ID Turnieju Titled Tuesday", 
    value="https://www.chess.com/play/tournament/31074565"
)

def parse_result(result_code):
    win_codes = ['win']
    draw_codes = ['agreed', 'repetition', 'stalemate', 'insufficient', '50move', 'timevsinsufficient']
    if result_code in win_codes:
        return 1.0, "1"
    elif result_code in draw_codes:
        return 0.5, "0,5"
    else:
        return 0.0, "0"

def extract_tournament_id(raw_input):
    """Wyciąga numeryczny lub tekstowy identyfikator turnieju ze ścieżki URL"""
    if not raw_input:
        return ""
    # Szukamy ciągu cyfr lub nazwy po ostatnim slaszu
    match = re.search(r'(?:tournament/|/)([\w-]+)/?$', raw_input.strip())
    if match:
        return match.group(1)
    return raw_input.strip()

def fetch_games_by_tournament(raw_url, username):
    tourney_id = extract_tournament_id(raw_url)
    if not tourney_id:
        return []

    req_time = int(time.time() * 1000)
    headers = {
        'User-Agent': f'TTTrackerBot/{req_time}',
        'Cache-Control': 'no-cache'
    }

    # 1. Próba pobrania jako turniej po ID z wewn. API Chess.com
    games = []
    
    # Odpytujemy do 11 rund
    for round_num in range(1, 12):
        url = f"https://api.chess.com/pub/tournament/{tourney_id}/1/{round_num}?cb={req_time}"
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200:
            round_games = res.json().get('games', [])
            for g in round_games:
                w = g.get('white', {}).get('username', '').lower()
                b = g.get('black', {}).get('username', '').lower()
                if username.lower() in [w, b]:
                    games.append(g)
                    break
        else:
            # Jeśli endpoint zwróci 404, próbujemy alternatywne archiwum miesięczne przefiltrowane pod ten turniej
            break

    # 2. Jeśli API turniejowe zwróciło pusto (częste dla gier w trakcie trwania na żywo):
    if not games:
        now = datetime.now(poland_tz)
        url_archive = f"https://api.chess.com/pub/player/{username.lower()}/games/{now.strftime('%Y')}/{now.strftime('%m')}?cb={req_time}"
        res = requests.get(url_archive, headers=headers, timeout=5)
        if res.status_code == 200:
            month_games = res.json().get('games', [])
            # Filtrujemy partie po URL turnieju lub ID z nagłówka PGN
            for g in month_games:
                pgn = g.get('pgn', '')
                tourney_url_in_g = g.get('tournament', '')
                if tourney_id in pgn or tourney_id in tourney_url_in_g:
                    games.append(g)

    return games

# Pobranie partii
games = fetch_games_by_tournament(tournament_input, USERNAME)
games.sort(key=lambda x: x.get('end_time', 0))

# Budowanie tabeli na 11 rund
processed_games = []
played_count = len(games)

for rd in range(1, 12):
    if (rd - 1) < played_count:
        game = games[rd - 1]
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

st.caption(f"🔄 Ostatnia aktualizacja: **{datetime.now(poland_tz).strftime('%H:%M:%S')}** | Zidentyfikowano partii: **{played_count}/11**")

# Odświeżanie co 10 sekund
time.sleep(10)
st.rerun()
