import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, date, timezone

st.set_page_config(page_title="Titled Tuesday Tracker", page_icon="♟️", layout="wide")

USERNAME = "Matibar"

st.title(f"🏆 Titled Tuesday — Live Tracker: {USERNAME}")

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

st.caption(f"Śledzenie partii od: **{start_datetime.strftime('%Y-%m-%d %H:%M')}**. Strona odświeża się automatycznie co 20 sekund.")

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

if not filtered_games:
    st.info(f"Brak partii dla gracza **{USERNAME}** rozegranych po {start_datetime.strftime('%Y-%m-%d %H:%M')}.")
else:
    processed_games = []
    total_score = 0.0

    for idx, game in enumerate(filtered_games, start=int(start_round)):
        white = game['white']['username']
        black = game['black']['username']
        
        is_white = (white.lower() == USERNAME.lower())
        opponent_username = black if is_white else white
        opp_rating = game['black']['rating'] if is_white else game['white']['rating']
        player_result_code = game['white']['result'] if is_white else game['black']['result']
        
        # Pobieranie Imienia i Nazwiska przeciwnika
        opp_real_name = get_player_name(opponent_username)
        
        score_add, result_text = parse_result(player_result_code)
        total_score += score_add

        processed_games.append({
            "Rd.": idx,
            "Przeciwnik": opponent_username,
            "Imię i nazwisko": opp_real_name,
            "Ranking": opp_rating,
            "Kolor": "⚪" if is_white else "⚫",
            "Wynik": result_text
        })

    # Metryki na górze strony
    col1, col2, col3 = st.columns(3)
    col1.metric("Gracz", USERNAME)
    col2.metric("Rozegrane rundy", len(processed_games))
    col3.metric("Zdobyte punkty", f"{total_score} / {len(processed_games)}")

    st.markdown("---")
    st.subheader("📊 Wyniki w Titled Tuesday na żywo")

    # Tabela z wynikami i konfiguracją dopasowania szerokości
    df = pd.DataFrame(processed_games)
    
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Rd.": st.column_config.Column(width="small"),
            "Kolor": st.column_config.Column(width="small"),
            "Ranking": st.column_config.Column(width="small"),
        }
    )

    # --- PODSUMOWANIE / WYNIK POD TABELĄ ---
    st.markdown("---")
    st.markdown(f"### Wynik {total_score}/{len(processed_games)}")

# Odświeżanie co 20 sekund
time.sleep(20)
st.rerun()
