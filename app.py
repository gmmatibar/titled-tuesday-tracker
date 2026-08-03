import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, date, timezone

st.set_page_config(page_title="Titled Tuesday Tracker", page_icon="♟️", layout="wide")

USERNAME = "Matibar"

# --- STYLOWANIE CSS (Złoty kolor + Comic Sans + Tło inspirowane grafiką) ---
st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/comic-sans-ms');
    
    /* Ogólna czcionka Comic Sans dla aplikacji */
    html, body, [class*="css"], .stMarkdown, div[data-testid="stTable"], div[data-testid="stDataFrame"] {
        font-family: 'Comic Sans MS', 'Comic Sans', cursive, sans-serif !important;
    }

    /* Złoty kolor tekstu dla tabeli i nagłówka */
    div[data-testid="stDataFrame"] *, h3 {
        color: #D4AF37 !important;
        font-family: 'Comic Sans MS', 'Comic Sans', cursive, sans-serif !important;
    }

    /* Ciemnoszare tło dla całej tabeli (kolor z paska pod kamerką) */
    div[data-testid="stDataFrame"] {
        background-color: #1A1A1A !important;
        border: none !important;
    }

    /* Tło dla pojedynczych komórek oraz nagłówków */
    div[data-testid="stDataFrame"] [role="gridcell"], 
    div[data-testid="stDataFrame"] [role="columnheader"] {
        background-color: #1A1A1A !important;
        border-bottom: 1px solid #282828 !important; /* Dyskretna linia podziału */
    }

    /* Tło dla nagłówków tabeli (nieco ciemniejsza wersja) */
    div[data-testid="stDataFrame"] [role="columnheader"] {
        background-color: #141414 !important;
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
    """Pobiera imię i nazwisko gracza z jego profilu na Chess.com"""
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
        return 1.0, "🟢 Wygrana"
    elif result_code in draw_codes:
        return 0.5, "🟡 Remis"
    else:
        return 0.0, "🔴 Przegrana"

# Pobieranie partii
all_month_games = get_player_games(USERNAME)

filtered_games = []
for game in all_month_games:
    end_time = game.get('end_time', 0)
    time_class = game.get('time_class', '')
    
    if end_time >= start_timestamp:
        if not filter_blitz or time_class == 'blitz':
            filtered_games.append(game)

# Generowanie tabeli na stałe 11 rund
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
            "Ranking": opp_rating,
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

# Tabela z wynikami
st.subheader("📊 Wyniki w Titled Tuesday na żywo")

df = pd.DataFrame(processed_games)

st.dataframe(
    df, 
    use_container_width=False, 
    hide_index=True,
    height=425,
    column_config={
        "Rd.": st.column_config.NumberColumn("Rd.", width=50),
        "Przeciwnik": st.column_config.TextColumn("Przeciwnik", width=160),
        "Imię i nazwisko": st.column_config.TextColumn("Imię i nazwisko", width=200),
        "Ranking": st.column_config.TextColumn("Ranking", width=80),
        "Kolor": st.column_config.TextColumn("Kolor", width=60),
        "Wynik": st.column_config.TextColumn("Wynik", width=120),
    }
)

# Odświeżanie co 20 sekund
time.sleep(20)
st.rerun()
