import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, date, timezone

st.set_page_config(page_title="Titled Tuesday Tracker", page_icon="♟️", layout="wide")

USERNAME = "Matibar"

# --- STYLOWANIE CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/comic-sans-ms');
    
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Comic Sans MS', 'Comic Sans', cursive, sans-serif !important;
    }

    h3 {
        color: #D4AF37 !important;
        font-family: 'Comic Sans MS', 'Comic Sans', cursive, sans-serif !important;
        font-size: 20px !important;
    }

    /* Dedykowane style dla własnej tabeli HTML */
    .custom-table {
        font-family: 'Comic Sans MS', 'Comic Sans', cursive, sans-serif !important;
        font-size: 13px !important;
        color: #D4AF37 !important;
        background-color: #1A1A1A;
        border-collapse: collapse;
        table-layout: fixed; /* BARDZO WAŻNE: sztywne wymiary */
        width: 400px; /* Łączna szerokość sumy kolumn */
        border-radius: 6px;
        overflow: hidden;
        border: 1px solid #282828;
    }

    .custom-table th {
        background-color: #141414;
        color: #D4AF37;
        border-bottom: 2px solid #333333;
        padding: 4px 2px;
        text-align: left;
    }

    .custom-table td {
        border-bottom: 1px solid #282828;
        padding: 3px 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Wyśrodkowanie konkretnych kolumn */
    .custom-table .center {
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- PANEL STEROWANIA TURNIEJEM (W panelu bocznym) ---
st.sidebar.header("⚙️ Ustawienia Turnieju")

server_now_utc = datetime.now(timezone.utc)
server_now_local = datetime.now()

st.sidebar.info(
    f"🕒 **Czas serwera:**\n\n"
    f"• **UTC:** {server_now_utc.strftime('%H:%M:%S')}\n"
    f"• **Lokalny serwera:** {server_now_local.strftime('%H:%M:%S')}"
)

selected_date = st.sidebar.date_input("Data turnieju", value=date.today())
selected_time = st.sidebar.time_input("Godzina rozpoczęcia (czas serwera)", value=datetime.strptime("17:00", "%H:%M").time())
start_round = st.sidebar.number_input("Numer pierwszej rundy", min_value=1, value=1, step=1)
filter_blitz = st.sidebar.checkbox("Filtruj tylko partie Blitz", value=True)

start_datetime = datetime.combine(selected_date, selected_time)
start_timestamp = int(start_datetime.timestamp())

@st.cache_data(ttl=3600)
def get_player_name(username):
    headers = {'User-Agent': 'TitledTuesdayTracker/1.0 (contact: contact@example.com)'}
    url = f"https://api.chess.com/pub/player/{username}"
    try:
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200:
            return res.json().get('name', '—')
    except Exception:
        pass
    return '—'

def get_player_games(username):
    headers = {'User-Agent': 'TitledTuesdayTracker/1.0 (contact: contact@example.com)'}
    year = selected_date.strftime("%Y")
    month = selected_date.strftime("%m")
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

all_month_games = get_player_games(USERNAME)

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

# --- GENEROWANIE TABELI HTML ZE SZTYWNYMI SZEROKOŚCIAMI ---
html_table = """
<table class="custom-table">
    <thead>
        <tr>
            <th style="width: 30px;" class="center">Rd.</th>
            <th style="width: 90px;">Przeciwnik</th>
            <th style="width: 130px;">Imię i nazwisko</th>
            <th style="width: 60px;">Ranking</th>
            <th style="width: 45px;" class="center">Kolor</th>
            <th style="width: 45px;" class="center">Wynik</th>
        </tr>
    </thead>
    <tbody>
"""

for row in processed_games:
    html_table += f"""
        <tr>
            <td class="center">{row['Rd.']}</td>
            <td title="{row['Przeciwnik']}">{row['Przeciwnik']}</td>
            <td title="{row['Imię i nazwisko']}">{row['Imię i nazwisko']}</td>
            <td>{row['Ranking']}</td>
            <td class="center">{row['Kolor']}</td>
            <td class="center">{row['Wynik']}</td>
        </tr>
    """

html_table += """
    </tbody>
</table>
"""

st.markdown(html_table, unsafe_allow_html=True)

time.sleep(20)
st.rerun()
