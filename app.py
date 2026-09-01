import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
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

tournament_input = st.sidebar.text_input(
    "URL lub ID Turnieju Titled Tuesday", 
    placeholder="np. titled-tuesday-blitz-1700-123456"
)

# Wyciąganie czystego ID z URL jeśli wklejono cały link
tournament_id = tournament_input.strip().split("/")[-1] if tournament_input else ""

def parse_result(result_code):
    win_codes = ['win']
    draw_codes = ['agreed', 'repetition', 'stalemate', 'insufficient', '50move', 'timevsinsufficient']
    if result_code in win_codes:
        return 1.0, "1"
    elif result_code in draw_codes:
        return 0.5, "0,5"
    else:
        return 0.0, "0"

def fetch_tournament_games(tourney_id, username):
    """Pobiera gry bezpośrednio z drabinki i rund turniejowych Chess.com"""
    if not tourney_id:
        return {}

    req_time = int(time.time() * 1000)
    headers = {
        'User-Agent': f'TTTrackerBot/{req_time}',
        'Cache-Control': 'no-cache'
    }

    user_games_by_round = {}

    # Pętla po 11 rundach turnieju
    for round_num in range(1, 12):
        url = f"https://api.chess.com/pub/tournament/{tourney_id}/1/{round_num}?cb={req_time}"
        try:
            res = requests.get(url, headers=headers, timeout=3)
            if res.status_code == 200:
                games = res.json().get('games', [])
                for g in games:
                    white = g.get('white', {}).get('username', '').lower()
                    black = g.get('black', {}).get('username', '').lower()
                    
                    if USERNAME.lower() in [white, black]:
                        user_games_by_round[round_num] = g
                        break
            elif res.status_code == 404:
                # Runda jeszcze się nie rozpoczęła
                break
        except Exception:
            pass
            
    return user_games_by_round

# Pobieranie gier z turnieju
tournament_games = fetch_tournament_games(tournament_id, USERNAME) if tournament_id else {}

# Budowanie tabeli na 11 rund
processed_games = []
for rd in range(1, 12):
    if rd in tournament_games:
        game = tournament_games[rd]
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

if not tournament_id:
    st.warning("👈 Wklej link lub ID dzisiejszego turnieju Titled Tuesday w panelu bocznym, aby rozpocząć śledzenie.")

df = pd.DataFrame(processed_games)
st.table(df)

st.caption(f"🔄 Ostatnia aktualizacja: **{datetime.now(poland_tz).strftime('%H:%M:%S')}** | Odnaleziono partii turniejowych: **{len(tournament_games)}/11**")

# Odświeżanie co 10 sekund
time.sleep(10)
st.rerun()
