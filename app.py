import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timezone

st.set_page_config(page_title="Titled Tuesday Tracker", page_icon="♟️", layout="wide")

USERNAME = "Matibar"

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
    div[data-testid="stTable"] table th:nth-child(1), div[data-testid="stTable"] table td:nth-child(1) { width: 35px !important; }
    div[data-testid="stTable"] table th:nth-child(2), div[data-testid="stTable"] table td:nth-child(2) { width: 135px !important; }
    div[data-testid="stTable"] table th:nth-child(3), div[data-testid="stTable"] table td:nth-child(3) { width: 180px !important; }
    div[data-testid="stTable"] table th:nth-child(4), div[data-testid="stTable"] table td:nth-child(4) { width: 65px !important; }
    div[data-testid="stTable"] table th:nth-child(5), div[data-testid="stTable"] table td:nth-child(5) { width: 50px !important; }
    div[data-testid="stTable"] table th:nth-child(6), div[data-testid="stTable"] table td:nth-child(6) { width: 55px !important; }

    div[data-testid="stTable"] td:nth-child(1), div[data-testid="stTable"] th:nth-child(1),
    div[data-testid="stTable"] td:nth-child(5), div[data-testid="stTable"] th:nth-child(5),
    div[data-testid="stTable"] td:nth-child(6), div[data-testid="stTable"] th:nth-child(6) {
        text-align: center !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- PANEL STEROWANIA ---
st.sidebar.header("⚙️ Ustawienia Turnieju")

server_now_utc = datetime.now(timezone.utc)
st.sidebar.info(f"🕒 **Aktualny czas UTC:** {server_now_utc.strftime('%H:%M:%S')}")

selected_date = st.sidebar.date_input("Data turnieju", value=date.today())
selected_time = st.sidebar.time_input("Godzina rozpoczęcia (UTC)", value=datetime.strptime("17:00", "%H:%M").time())
start_round = st.sidebar.number_input("Numer pierwszej rundy", min_value=1, value=1, step=1)
filter_blitz = st.sidebar.checkbox("Filtruj tylko partie Blitz", value=True)

# POPRAWKA 1: Jawną deklaracja strefy UTC dla start_datetime
start_datetime = datetime.combine(selected_date, selected_time).replace(tzinfo=timezone.utc)
start_timestamp = int(start_datetime.timestamp())

@st.cache_data(ttl=86400)
def get_player_name(username):
    headers = {'User-Agent': 'TitledTuesdayTracker/1.0 (contact: email@example.com)'}
    url = f"https://api.chess.com/pub/player/{username}"
    try:
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200:
            return res.json().get('name', '—')
    except Exception:
        pass
    return '—'

@st.cache_data(ttl=15)
def get_player_games(username, year, month):
    headers = {'User-Agent': 'TitledTuesdayTracker/1.0 (contact: email@example.com)'}
    archive_url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month}"
    try:
        res = requests.get(archive_url, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.json().get('games', [])
    except Exception as e:
        st.error(f"Błąd pobierania danych z Chess.com: {e}")
    return []

def parse_result(result_code):
    win_codes = ['win']
    draw_codes = ['agreed', 'repetition', 'stalemate', 'insufficient', '50move', 'timevsinsufficient']
    if result_code in win_codes:
        return 1.0, "1"
    elif result_code in draw_codes:
        return 0.5, "0,5"
    else:
        return 0.0, "0"

# Pobieranie partii z krótkim ttl w cache
year_str = selected_date.strftime("%Y")
month_str = selected_date.strftime("%m")
all_month_games = get_player_games(USERNAME, year_str, month_str)

filtered_games = []
for game in all_month_games:
    end_time = game.get('end_time', 0)
    time_class = game.get('time_class', '')
    
    if end_time >= start_timestamp:
        if not filter_blitz or time_class == 'blitz':
            filtered_games.append(game)

processed_games = []
total_score = 0.0
played_games_count = len(filtered_games)
start_rd = int(start_round)

for i in range(11):
    current_rd = start_rd + i
    
    if i < played_games_count:
        game = filtered_games[i]
        white = game['white']['username']
        black = game['black']['username']
        
        is_white = (white.lower() == USERNAME.lower())
        opponent_username = black if is_white else white
        opp_rating = game['black']['rating'] if is_white else game['white']['rating']
        player_result_code = game['white']['result'] if is_white else game['black']['result']
        
        opp_real_name = get_player_name(opponent_username)
        score_add, result_text = parse_result(player_result_code)
        total_score += score_add

        processed_games.append({
            "Rd.": current_rd,
            "Przeciwnik": opponent_username,
            "Imię i nazwisko": opp_real_name,
            "Ranking": str(opp_rating),
            "Kolor": "⚪" if is_white else "⚫",
            "Wynik": result_text
        })
    else:
        processed_games.append({
            "Rd.": current_rd,
            "Przeciwnik": "—",
            "Imię i nazwisko": "—",
            "Ranking": "—",
            "Kolor": "—",
            "Wynik": "—"
        })

st.subheader("📊 Wyniki w Titled Tuesday na żywo")
df = pd.DataFrame(processed_games)
st.table(df)
