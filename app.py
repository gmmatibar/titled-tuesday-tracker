import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, date, timezone, timedelta
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Titled Tuesday Tracker", page_icon="♟️", layout="wide")

# Autoodświeżanie co 10 sekund
st_autorefresh(interval=10000, key="datarefresh")

USERNAME = "matibar"

# --- STYLOWANIE CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/comic-sans-ms');
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Comic Sans MS', 'Comic Sans', cursive, sans-serif !important;
    }
    h3 { color: #D4AF37 !important; }
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

start_datetime = datetime.combine(selected_date, selected_time).replace(tzinfo=timezone.utc)
start_timestamp = int(start_datetime.timestamp())

def fetch_games_force_fresh(username, target_date):
    """Pobiera partie z wymuszeniem braku pamięci podręcznej (Cache Busting)"""
    year_str = target_date.strftime("%Y")
    month_str = target_date.strftime("%m")
    
    # Dodanie unikalnego timestampu na końcu URL, by ominąć cache Chess.com
    cache_buster = int(time.time())
    url = f"https://api.chess.com/pub/player/{username}/games/{year_str}/{month_str}?cb={cache_buster}"
    
    headers = {
        'User-Agent': 'TitledTuesdayTracker/1.0 (contact: user@example.com)',
        'Cache-Control': 'no-cache'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.json().get('games', [])
    except Exception as e:
        st.sidebar.error(f"Błąd sieci: {e}")
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

# Pobieranie świeżych gier
all_games = fetch_games_force_fresh(USERNAME, selected_date)

# Filtrowanie partii od wybranego timestampu
filtered_games = []
for game in all_games:
    end_time = game.get('end_time', 0)
    time_class = game.get('time_class', '')
    
    if end_time >= start_timestamp:
        if not filter_blitz or time_class == 'blitz':
            filtered_games.append(game)

# Generowanie tabeli na 11 rund
processed_games = []
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
        
        _, result_text = parse_result(player_result_code)

        processed_games.append({
            "Rd.": current_rd,
            "Przeciwnik": opponent_username,
            "Ranking": str(opp_rating),
            "Kolor": "⚪" if is_white else "⚫",
            "Wynik": result_text
        })
    else:
        processed_games.append({
            "Rd.": current_rd,
            "Przeciwnik": "—",
            "Ranking": "—",
            "Kolor": "—",
            "Wynik": "—"
        })

# Wyświetlanie wyników
st.subheader("📊 Wyniki w Titled Tuesday na żywo")

df = pd.DataFrame(processed_games)
st.dataframe(df, use_container_width=False, height=420)

# Panel diagnostyczny (pomoże od razu zauważyć problem)
st.caption(f"Status: Ostatnia aktualizacja o **{datetime.now().strftime('%H:%M:%S')}**. Znaleziono **{played_games_count}** partii po godzinie {selected_time.strftime('%H:%M')} UTC.")
