import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, time as dtime
import zoneinfo

st.set_page_config(page_title="Titled Tuesday Tracker", page_icon="♟️", layout="wide")

USERNAME = "matibar"

# --- STYLOWANIE CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/comic-sans-ms');
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
    div[data-testid="stTable"] { width: 520px !important; background-color: transparent !important; }
    div[data-testid="stTable"] table { background-color: transparent !important; border-collapse: collapse !important; table-layout: fixed !important; width: 100% !important; border-radius: 6px !important; overflow: hidden !important; }
    div[data-testid="stTable"] td, div[data-testid="stTable"] th { background-color: transparent !important; border-bottom: 1px solid rgba(255, 255, 255, 0.2) !important; padding: 4px 5px !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; color: #D4AF37 !important; text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.9) !important; }
    div[data-testid="stTable"] th { background-color: rgba(0, 0, 0, 0.4) !important; border-bottom: 2px solid #D4AF37 !important; text-align: left !important; }
    div[data-testid="stTable"] table th:nth-child(1), div[data-testid="stTable"] table td:nth-child(1) { width: 35px !important; }
    div[data-testid="stTable"] table th:nth-child(2), div[data-testid="stTable"] table td:nth-child(2) { width: 135px !important; }
    div[data-testid="stTable"] table th:nth-child(3), div[data-testid="stTable"] table td:nth-child(3) { width: 180px !important; }
    div[data-testid="stTable"] table th:nth-child(4), div[data-testid="stTable"] table td:nth-child(4) { width: 65px !important; }
    div[data-testid="stTable"] table th:nth-child(5), div[data-testid="stTable"] table td:nth-child(5) { width: 50px !important; }
    div[data-testid="stTable"] table th:nth-child(6), div[data-testid="stTable"] table td:nth-child(6) { width: 55px !important; }
    div[data-testid="stTable"] td:nth-child(1), div[data-testid="stTable"] th:nth-child(1),
    div[data-testid="stTable"] td:nth-child(5), div[data-testid="stTable"] th:nth-child(5),
    div[data-testid="stTable"] td:nth-child(6), div[data-testid="stTable"] th:nth-child(6) { text-align: center !important; }
    .stCaption { color: #E0E0E0 !important; text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.9) !important; }
    </style>
""", unsafe_allow_html=True)

# --- PANEL STEROWANIA ---
st.sidebar.header("⚙️ Ustawienia Turnieju")

poland_tz = zoneinfo.ZoneInfo("Europe/Warsaw")
now_pl = datetime.now(poland_tz)
st.sidebar.info(f"🕒 **Czas PL:** {now_pl.strftime('%H:%M:%S')}")

selected_date = st.sidebar.date_input("Data turnieju", value=now_pl.date())

is_tuesday = now_pl.weekday() == 1
default_time = dtime(17, 0) if is_tuesday else dtime(0, 0)
selected_time = st.sidebar.time_input("Godzina rozpoczęcia", value=default_time)

selection_mode = st.sidebar.radio(
    "Wybór partii do tabeli:",
    ["Pierwsze 11 od godziny startu", "Ostatnie 11 rozegranych"],
    index=0
)

# Przycisk ręcznego odświeżania zamiast pętli blokującej IP
if st.sidebar.button("🔄 Pobierz najnowsze wyniki"):
    st.rerun()

debug_mode = st.sidebar.checkbox("🐞 Tryb debugowania (status połączenia)", value=True)

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

def fetch_all_possible_sources(username, target_date, cutoff_ts):
    import time
    req_time = int(time.time() * 1000)
    headers = {
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) TrackerBot/{req_time}',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache'
    }

    found_games = {}
    debug_logs = []

    # 1. Archiwum miesięczne
    url_month = f"https://api.chess.com/pub/player/{username.lower()}/games/{target_date.year:04d}/{target_date.month:02d}?cb={req_time}"
    try:
        r1 = requests.get(url_month, headers=headers, timeout=5)
        debug_logs.append(f"Archiwum API status: {r1.status_code}")
        if r1.status_code == 200:
            for g in r1.json().get('games', []):
                if 'url' in g:
                    found_games[g['url']] = g
    except Exception as e:
        debug_logs.append(f"Archiwum błąd: {e}")

    # 2. Live endpoint
    url_live = f"https://api.chess.com/pub/player/{username.lower()}/games?cb={req_time}"
    try:
        r2 = requests.get(url_live, headers=headers, timeout=5)
        debug_logs.append(f"Live API status: {r2.status_code}")
        if r2.status_code == 200:
            for g in r2.json().get('games', []):
                if 'url' in g:
                    found_games[g['url']] = g
    except Exception as e:
        debug_logs.append(f"Live błąd: {e}")

    valid_games = []
    all_today_games = []

    for g in found_games.values():
        end_ts = g.get('end_time')
        if not end_ts:
            continue
        g_date_pl = datetime.fromtimestamp(end_ts, tz=poland_tz).date()
        if g_date_pl == target_date:
            all_today_games.append(g)
            if end_ts >= cutoff_ts:
                valid_games.append(g)

    valid_games.sort(key=lambda x: x.get('end_time', 0))
    all_today_games.sort(key=lambda x: x.get('end_time', 0))
    
    return valid_games, all_today_games, debug_logs

games, all_today_games, logs = fetch_all_possible_sources(USERNAME, selected_date, start_cutoff_dt.timestamp())

if debug_mode:
    st.info(f"**🐞 Status połączenia z API:**\n" + "\n".join([f"- {log}" for log in logs]) + f"\n\nZnaleziono partii z dzisiaj: **{len(all_today_games)}**")

if selection_mode == "Pierwsze 11 od godziny startu":
    tournament_games = games[:11]
else:
    tournament_games = games[-11:] if len(games) >= 11 else games

played_count = len(tournament_games)

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

st.subheader("📊 Wyniki Turnieju")
df = pd.DataFrame(processed_games)
st.table(df)

st.caption(f"🔄 Czas serwera: **{datetime.now(poland_tz).strftime('%H:%M:%S')}** | Zarejestrowanych partii: **{played_count}**")
