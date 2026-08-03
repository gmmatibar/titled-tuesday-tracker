import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

st.set_page_config(page_title="Titled Tuesday Tracker", page_icon="♟️", layout="wide")

USERNAME = "Matibar"

st.title(f"🏆 Titled Tuesday — Live Tracker: {USERNAME}")
st.caption("Strona odświeża się automatycznie co 20 sekund.")

def get_player_games(username):
    headers = {
        'User-Agent': 'TitledTuesdayTracker/1.0 (contact: contact@example.com)'
    }
    
    # 1. Pobieramy zakończone partie z obecnego miesiąca
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    archive_url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month}"
    
    games = []
    try:
        res = requests.get(archive_url, headers=headers, timeout=5)
        if res.status_code == 200:
            games = res.json().get('games', [])
    except Exception as e:
        st.error(f"Błąd pobierania archiwum: {e}")
        
    return games

def parse_result(result_code):
    win_codes = ['win']
    draw_codes = ['agreed', 'repetition', 'stalemate', 'insufficient', '50move', 'timevsinsufficient']
    if result_code in win_codes:
        return 1.0, "🟢 Wygrana"
    elif result_code in draw_codes:
        return 0.5, "🟡 Remis"
    else:
        return 0.0, "🔴 Przegrana"

# Pobieranie danych
all_games = get_player_games(USERNAME)

if not all_games:
    st.info(f"Brak zarejestrowanych partii dla gracza **{USERNAME}** w tym miesiącu.")
else:
    # Bierzemy ostatnie 15 partii
    recent_games = all_games[-15:]
    
    processed_games = []
    total_score = 0.0

    for idx, game in enumerate(recent_games, start=1):
        white = game['white']['username']
        black = game['black']['username']
        
        is_white = (white.lower() == USERNAME.lower())
        opponent = black if is_white else white
        opp_rating = game['black']['rating'] if is_white else game['white']['rating']
        player_result_code = game['white']['result'] if is_white else game['black']['result']
        
        score_add, result_text = parse_result(player_result_code)
        total_score += score_add

        processed_games.append({
            "Runda / Gra": idx,
            "Przeciwnik": opponent,
            "Ranking Przeciwnika": opp_rating,
            "Kolor": "⚪ Białe" if is_white else "⚫ Czarne",
            "Wynik": result_text,
            "Suma punktów": total_score
        })

    # Metryki na górze strony
    col1, col2, col3 = st.columns(3)
    col1.metric("Gracz", USERNAME)
    col2.metric("Pobrane partie", len(processed_games))
    col3.metric("Zdobyte punkty", f"{total_score} / {len(processed_games)}")

    st.markdown("---")
    st.subheader("📊 Ostatnie partie")

    # Tabela z wynikami
    df = pd.DataFrame(processed_games)
    st.dataframe(df, use_container_width=True, hide_index=True)

# Automatyczne odświeżanie co 20 sekund
time.sleep(20)
st.rerun()
