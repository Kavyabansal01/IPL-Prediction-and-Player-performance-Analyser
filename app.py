import json
import pickle
import zipfile
from difflib import SequenceMatcher
from pathlib import Path
from xml.etree import ElementTree as ET

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
CURRENT_SEASON = "2026"


def load_cached_live_matches() -> list[dict]:
    cache_path = BASE_DIR / "api_cache" / "current_matches.json"
    if not cache_path.exists():
        return []
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return payload.get("data", []) if isinstance(payload, dict) else []


def normalize_cached_match(record: dict) -> dict:
    team_info = record.get("teamInfo") or []
    teams = [team.get("name") for team in team_info if isinstance(team, dict) and team.get("name")]
    if len(teams) < 2:
        teams = record.get("teams") or teams
    status = record.get("status", "Status unavailable")
    lowered_status = str(status).lower()
    winner = record.get("winner") or record.get("matchWinner") or record.get("winningTeam") or ""
    if not winner:
        for team in teams:
            if team and team.lower() in lowered_status and "won" in lowered_status:
                winner = team
                break
    score_lines = []
    for innings in record.get("score") or []:
        if not isinstance(innings, dict):
            continue
        inning_name = innings.get("inning") or innings.get("innings") or "Innings"
        runs = innings.get("r")
        wickets = innings.get("w")
        overs = innings.get("o")
        chunk = []
        if runs is not None:
            chunk.append(f"{runs}/{wickets}" if wickets is not None else str(runs))
        if overs is not None:
            chunk.append(f"({overs} ov)")
        if chunk:
            score_lines.append(f"{inning_name}: {' '.join(chunk)}")
    return {
        "teams": teams,
        "status": status,
        "winner": winner,
        "score": " | ".join(score_lines),
    }


def build_today_match_enrichment(today_matches: pd.DataFrame) -> pd.DataFrame:
    enriched = today_matches.copy()
    enriched["live_status"] = "Scheduled"
    enriched["live_score"] = "Local schedule only"

    live_matches = [normalize_cached_match(match) for match in load_cached_live_matches()]
    if not live_matches:
        return enriched
    for idx, row in enriched.iterrows():
        for live in live_matches:
            teams = live.get("teams", [])
            if len(teams) < 2:
                continue
            if {row["team1"], row["team2"]} == {teams[0], teams[1]}:
                enriched.at[idx, "live_status"] = live.get("status") or "Scheduled"
                enriched.at[idx, "live_score"] = live.get("score") or "Score not available"
                if live.get("winner"):
                    enriched.at[idx, "winner"] = live["winner"]
                    enriched.at[idx, "result"] = live.get("status") or "Completed"
                break
    return enriched


def render_today_matches():
    schedule_df, season_label = load_current_season_schedule()
    st.markdown('<div class="section-title">Today\'s IPL Matches</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-subtitle">Local {season_label} schedule with optional cached live-status enrichment.</div>', unsafe_allow_html=True)

    today = pd.Timestamp.now().normalize()
    today_matches = schedule_df[schedule_df["match_date"].dt.normalize() == today].copy()

    if today_matches.empty:
        st.info("No IPL matches are scheduled for today in the local 2026 schedule.")
        next_matches = schedule_df[schedule_df["match_date"].dt.normalize() > today].copy().head(3)
        if not next_matches.empty:
            st.caption("Next scheduled matches")
            next_matches["fixture"] = next_matches["team1"] + " vs " + next_matches["team2"]
            preview_df = next_matches[["match_date", "fixture", "venue", "city"]].copy()
            preview_df["match_date"] = preview_df["match_date"].dt.strftime("%Y-%m-%d")
            preview_df = preview_df.rename(columns={
                "match_date": "Date",
                "fixture": "Fixture",
                "venue": "Venue",
                "city": "City",
            })
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
        return

    today_matches = build_today_match_enrichment(today_matches)
    today_matches["fixture"] = today_matches["team1"] + " vs " + today_matches["team2"]
    display_df = today_matches[["match_number", "fixture", "venue", "city", "live_status", "live_score"]].copy()
    display_df = display_df.rename(columns={
        "match_number": "Match No.",
        "fixture": "Fixture",
        "venue": "Venue",
        "city": "City",
        "live_status": "Status",
        "live_score": "Score",
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)


st.set_page_config(
    page_title="IPL Analytics",
    page_icon="🏏",
    layout="wide",
)


def inject_styles():
    st.markdown(
        """
        <style>
            .stApp {
                color: #102542;
                background:
                    radial-gradient(circle at top right, rgba(255, 176, 59, 0.18), transparent 26%),
                    radial-gradient(circle at top left, rgba(0, 122, 204, 0.16), transparent 22%),
                    linear-gradient(180deg, #f7f1e3 0%, #fffaf1 45%, #f5f7fb 100%);
            }

            p, label, div, span, .stMarkdown, .stText, .stCaption, .stAlert {
                color: #102542;
            }

            h1, h2, h3 {
                color: #0f3d3e;
            }

            .hero {
                background:
                    radial-gradient(circle at 88% 18%, rgba(255,255,255,0.16), transparent 18%),
                    radial-gradient(circle at 72% 78%, rgba(255,255,255,0.08), transparent 20%),
                    linear-gradient(135deg, #0f3d3e 0%, #145da0 48%, #f28c28 100%);
                color: #ffffff;
                padding: 34px 36px;
                border-radius: 30px;
                box-shadow: 0 26px 60px rgba(15, 61, 62, 0.20);
                margin-bottom: 1.3rem;
                border: 1px solid rgba(255,255,255,0.16);
            }

            .hero-grid {
                display: grid;
                grid-template-columns: 1.8fr 1fr;
                gap: 1.25rem;
                align-items: stretch;
            }

            .hero-copy h1,
            .hero-copy p,
            .hero-panel h3,
            .hero-panel p,
            .hero-kpi-value,
            .hero-kpi-label,
            .hero-eyebrow {
                color: #ffffff;
            }

            .hero-eyebrow {
                text-transform: uppercase;
                letter-spacing: 0.12em;
                font-size: 0.8rem;
                opacity: 0.88;
                margin-bottom: 0.7rem;
            }

            .hero-copy h1 {
                font-size: 2.7rem;
                line-height: 1.05;
                margin: 0 0 0.45rem 0;
                max-width: 10ch;
            }

            .hero-copy p {
                margin: 0;
                font-size: 1.05rem;
                max-width: 58ch;
                opacity: 0.96;
            }

            .hero-badges {
                display: flex;
                gap: 0.55rem;
                flex-wrap: wrap;
                margin-top: 1rem;
            }

            .hero-badge {
                display: inline-block;
                padding: 0.38rem 0.8rem;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.14);
                border: 1px solid rgba(255, 255, 255, 0.20);
                color: #ffffff;
                font-size: 0.92rem;
                backdrop-filter: blur(4px);
            }

            .hero-panel {
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 22px;
                padding: 1rem 1.05rem;
                backdrop-filter: blur(6px);
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }

            .hero-panel h3 {
                margin: 0 0 0.4rem 0;
                font-size: 1rem;
            }

            .hero-panel p {
                margin: 0;
                opacity: 0.92;
                font-size: 0.93rem;
            }

            .hero-kpi-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 0.85rem;
                margin-top: 1rem;
            }

            .hero-kpi {
                background: rgba(255,255,255,0.1);
                border-radius: 16px;
                padding: 0.8rem 0.85rem;
            }

            .hero-kpi-value {
                font-size: 1.2rem;
                font-weight: 700;
                line-height: 1.1;
            }

            .hero-kpi-label {
                font-size: 0.82rem;
                opacity: 0.85;
                margin-top: 0.2rem;
            }

            .section-title {
                font-size: 1.85rem;
                font-weight: 750;
                color: #0f3d3e;
                margin-bottom: 0.2rem;
                line-height: 1.1;
            }

            .section-subtitle {
                color: #5c6b7a;
                margin-bottom: 1rem;
                font-size: 0.98rem;
            }

            .section-card {
                background: rgba(255, 255, 255, 0.97);
                color: #102542;
                border: 1px solid rgba(15, 61, 62, 0.08);
                border-radius: 24px;
                padding: 1.2rem 1.25rem;
                box-shadow: 0 16px 34px rgba(0, 0, 0, 0.06);
            }

            .overview-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 1rem;
                margin: 0.5rem 0 1.35rem 0;
            }

            .overview-card {
                background: rgba(255,255,255,0.88);
                border: 1px solid rgba(15, 61, 62, 0.08);
                border-radius: 22px;
                padding: 1rem 1.1rem;
                box-shadow: 0 14px 28px rgba(16, 37, 66, 0.06);
            }

            .overview-label {
                color: #5c6b7a;
                font-size: 0.84rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }

            .overview-value {
                color: #102542;
                font-size: 2rem;
                font-weight: 750;
                margin-top: 0.35rem;
                line-height: 1.05;
            }

            .overview-note {
                color: #3f556b;
                font-size: 0.92rem;
                margin-top: 0.35rem;
            }

            div[data-testid="stVerticalBlock"] > div:has(> div > .overview-grid) {
                background: transparent !important;
                border: 0 !important;
                box-shadow: none !important;
                padding-top: 0 !important;
            }

            div[data-testid="stVerticalBlock"] > div:has(> div > .overview-grid) + div {
                margin-top: 0.2rem;
            }

            .stRadio > label {
                font-weight: 700 !important;
                color: #0f3d3e !important;
                letter-spacing: 0.02em;
            }

            .stRadio [role="radiogroup"] {
                background: rgba(255,255,255,0.78);
                border: 1px solid rgba(15, 61, 62, 0.08);
                border-radius: 18px;
                padding: 0.45rem 0.45rem 0.2rem 0.45rem;
                box-shadow: 0 12px 24px rgba(16, 37, 66, 0.06);
            }

            .stRadio [role="radiogroup"] label {
                border-radius: 14px;
                padding: 0.55rem 0.65rem;
                margin-bottom: 0.35rem;
                background: transparent;
                transition: background 0.2s ease;
            }

            .stRadio [role="radiogroup"] label:hover {
                background: rgba(20, 93, 160, 0.08);
            }

            .stRadio [role="radiogroup"] p {
                font-weight: 600 !important;
                color: #102542 !important;
            }

            .section-card h1,
            .section-card h2,
            .section-card h3,
            .section-card p,
            .section-card div,
            .section-card span,
            .section-card label,
            .section-card strong {
                color: #102542;
            }

            .insight-card {
                background: linear-gradient(135deg, #fff7e7 0%, #ffffff 100%);
                color: #102542;
                border-left: 5px solid #f28c28;
                border-radius: 18px;
                padding: 1rem 1.1rem;
                margin-top: 1rem;
            }

            .winner-card {
                background: linear-gradient(135deg, #102542 0%, #1b4965 45%, #f28c28 100%);
                color: #ffffff;
                border-radius: 24px;
                padding: 1.4rem;
                text-align: center;
                box-shadow: 0 18px 40px rgba(16, 37, 66, 0.24);
            }

            .winner-card h2,
            .winner-card h1,
            .winner-card p {
                color: #ffffff;
                margin: 0.25rem 0;
            }

            .stSidebar {
                background: linear-gradient(180deg, #fff8ed 0%, #eef4fb 100%);
            }

            .stSidebar,
            .stSidebar p,
            .stSidebar label,
            .stSidebar div,
            .stSidebar span,
            .stSidebar strong {
                color: #102542;
            }

            .stTextInput input,
            .stSelectbox div[data-baseweb="select"] > div,
            .stTextArea textarea {
                color: #102542 !important;
                background-color: #ffffff !important;
            }

            .stTextInput input::placeholder,
            .stTextArea textarea::placeholder {
                color: #5c6b7a !important;
                opacity: 1;
            }

            div[data-baseweb="popover"] div,
            div[data-baseweb="select"] ul,
            div[data-baseweb="select"] li,
            div[role="listbox"] div,
            div[role="option"] {
                color: #102542 !important;
                background: #ffffff !important;
            }

            .stButton > button,
            .stDownloadButton > button {
                background: #145da0 !important;
                color: #ffffff !important;
                border: 1px solid #145da0 !important;
            }

            .stButton > button:hover,
            .stDownloadButton > button:hover {
                background: #0f3d3e !important;
                color: #ffffff !important;
                border-color: #0f3d3e !important;
            }

            div[data-testid="stMetricValue"],
            div[data-testid="stMetricLabel"],
            div[data-testid="stMarkdownContainer"],
            div[data-testid="stCaptionContainer"] {
                color: #102542 !important;
            }

            .stDataFrame,
            .stTable,
            [data-testid="stElementToolbar"],
            [data-testid="stElementToolbar"] button,
            [data-testid="stElementToolbar"] svg,
            [data-testid="stDataFrame"] button,
            [data-testid="stDataFrame"] svg {
                color: #102542 !important;
                fill: #102542 !important;
                opacity: 1 !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource
def load_artifacts():
    with open(BASE_DIR / "model.pkl", "rb") as model_file:
        model = pickle.load(model_file)
    with open(BASE_DIR / "encoders.pkl", "rb") as encoder_file:
        encoders = pickle.load(encoder_file)
    return model, encoders


@st.cache_data
def load_name_map():
    map_path = BASE_DIR / "player_name_map.csv"
    if not map_path.exists():
        return {}
    mapping_df = pd.read_csv(map_path)
    return dict(zip(mapping_df["short_name"], mapping_df["full_name"]))


@st.cache_data
def load_deliveries():
    deliveries_df = pd.read_csv(
        BASE_DIR / "deliveries.csv",
        usecols=["match_id", "ball", "batter", "batsman_runs"],
    )
    name_map = load_name_map()
    if name_map:
        if "batter" in deliveries_df.columns:
            deliveries_df["batter"] = deliveries_df["batter"].replace(name_map)
    return deliveries_df


@st.cache_resource
def load_analytics_cache():
    cache_path = BASE_DIR / "analytics_cache.pkl"
    if not cache_path.exists():
        return None
    with open(cache_path, "rb") as cache_file:
        return pickle.load(cache_file)


@st.cache_data
def load_current_season_teams() -> list[str]:
    mapping_path = BASE_DIR / "player_team_season_mapping.json"
    if mapping_path.exists():
        with open(mapping_path, "r", encoding="utf-8") as mapping_file:
            mapping_data = json.load(mapping_file)
        return sorted([team for team, seasons in mapping_data.items() if CURRENT_SEASON in seasons])

    matches_df = pd.read_csv(BASE_DIR / "ipl.csv", usecols=["season", "team1", "team2"])
    latest_season = matches_df["season"].dropna().max()
    current_teams = sorted(
        set(matches_df.loc[matches_df["season"] == latest_season, "team1"]).union(
            matches_df.loc[matches_df["season"] == latest_season, "team2"]
        )
    )
    replacements = {
        "Delhi Daredevils": "Delhi Capitals",
        "Kings XI Punjab": "Punjab Kings",
        "Rising Pune Supergiants": "Rising Pune Supergiant",
    }
    return [replacements.get(team, team) for team in current_teams]


@st.cache_data
def load_current_season_squads_from_matches() -> dict[str, list[str]]:
    mapping_path = BASE_DIR / "player_team_season_mapping.json"
    if mapping_path.exists():
        with open(mapping_path, "r", encoding="utf-8") as mapping_file:
            mapping_data = json.load(mapping_file)
        return {
            team: sorted(seasons.get(CURRENT_SEASON, []))
            for team, seasons in mapping_data.items()
            if seasons.get(CURRENT_SEASON)
        }

    matches_df = pd.read_csv(
        BASE_DIR / "ipl.csv",
        usecols=["season", "team1", "team2", "team1_players", "team2_players"],
    )
    latest_season = matches_df["season"].dropna().max()
    season_df = matches_df[matches_df["season"] == latest_season].copy()
    name_map = load_name_map()
    replacements = {
        "Delhi Daredevils": "Delhi Capitals",
        "Kings XI Punjab": "Punjab Kings",
        "Rising Pune Supergiants": "Rising Pune Supergiant",
    }

    team_squads: dict[str, set[str]] = {}
    for row in season_df.itertuples(index=False):
        team1 = replacements.get(row.team1, row.team1)
        team2 = replacements.get(row.team2, row.team2)
        team1_players = [
            name_map.get(player.strip(), player.strip())
            for player in str(row.team1_players).split(",")
            if str(player).strip()
        ]
        team2_players = [
            name_map.get(player.strip(), player.strip())
            for player in str(row.team2_players).split(",")
            if str(player).strip()
        ]
        team_squads.setdefault(team1, set()).update(team1_players)
        team_squads.setdefault(team2, set()).update(team2_players)

    return {team: sorted(players) for team, players in team_squads.items()}


@st.cache_data
def load_schedule_from_docx() -> pd.DataFrame | None:
    schedule_path = BASE_DIR / "match.docx"
    if not schedule_path.exists():
        return None

    with zipfile.ZipFile(schedule_path) as docx_file:
        xml_data = docx_file.read("word/document.xml")

    root = ET.fromstring(xml_data)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    lines = []
    for paragraph in root.findall('.//w:p', namespace):
        runs = [node.text for node in paragraph.findall('.//w:t', namespace) if node.text]
        if runs:
            lines.append(''.join(runs))

    csv_lines = [line.strip() for line in lines if "," in line.strip()]
    if not csv_lines:
        return None

    from io import StringIO

    schedule_df = pd.read_csv(StringIO("\n".join(csv_lines)))
    required_columns = {"match_id", "date", "team1", "team2", "venue", "city"}
    if not required_columns.issubset(schedule_df.columns):
        return None

    team_code_map = {
        "CSK": "Chennai Super Kings",
        "DC": "Delhi Capitals",
        "GT": "Gujarat Titans",
        "KKR": "Kolkata Knight Riders",
        "LSG": "Lucknow Super Giants",
        "MI": "Mumbai Indians",
        "PBKS": "Punjab Kings",
        "RCB": "Royal Challengers Bengaluru",
        "RR": "Rajasthan Royals",
        "SRH": "Sunrisers Hyderabad",
    }

    schedule_df["team1"] = schedule_df["team1"].replace(team_code_map)
    schedule_df["team2"] = schedule_df["team2"].replace(team_code_map)
    schedule_df["match_date"] = pd.to_datetime(schedule_df["date"])
    schedule_df["match_number"] = schedule_df["match_id"].apply(lambda value: f"Match {value}")
    schedule_df["winner"] = pd.NA
    schedule_df["result"] = "Scheduled"
    schedule_df["fixture"] = schedule_df["team1"] + " vs " + schedule_df["team2"]
    schedule_df["status"] = "Upcoming"
    schedule_df = schedule_df.sort_values(["match_date", "match_id"])
    return schedule_df


@st.cache_data
def load_current_season_schedule() -> tuple[pd.DataFrame, str]:
    docx_schedule = load_schedule_from_docx()
    if docx_schedule is not None and not docx_schedule.empty:
        return docx_schedule, CURRENT_SEASON

    matches_df = pd.read_csv(
        BASE_DIR / "ipl.csv",
        usecols=[
            "season",
            "match_date",
            "team1",
            "team2",
            "venue",
            "city",
            "winner",
            "match_number",
            "match_type",
            "result",
        ],
    )
    replacements = {
        "Delhi Daredevils": "Delhi Capitals",
        "Kings XI Punjab": "Punjab Kings",
        "Rising Pune Supergiants": "Rising Pune Supergiant",
    }
    for col in ["team1", "team2", "winner"]:
        matches_df[col] = matches_df[col].replace(replacements)

    latest_season = matches_df["season"].dropna().max()
    season_df = matches_df[matches_df["season"] == latest_season].copy()
    season_df["match_date"] = pd.to_datetime(season_df["match_date"])
    season_df = season_df.sort_values("match_date")
    season_df["fixture"] = season_df["team1"] + " vs " + season_df["team2"]
    season_df["status"] = season_df["winner"].fillna("Upcoming")
    return season_df, str(latest_season)


@st.cache_data
def build_player_stats(deliveries_df: pd.DataFrame) -> pd.DataFrame:
    stats = pd.DataFrame(
        {
            "matches": deliveries_df.groupby("batter")["match_id"].nunique(),
            "runs": deliveries_df.groupby("batter")["batsman_runs"].sum(),
            "balls": deliveries_df.groupby("batter")["ball"].count(),
        }
    )
    stats["strike_rate"] = (stats["runs"] / stats["balls"]) * 100
    return stats[stats["balls"] > 100]


@st.cache_data
def build_player_recent_runs(deliveries_df: pd.DataFrame) -> dict[str, pd.Series]:
    runs_per_match = (
        deliveries_df.groupby(["batter", "match_id"], as_index=False)["batsman_runs"]
        .sum()
        .sort_values(["batter", "match_id"])
    )
    recent_runs = {}
    for batter, group in runs_per_match.groupby("batter"):
        recent_runs[batter] = group.set_index("match_id")["batsman_runs"].tail(10)
    return recent_runs


def load_player_analytics(deliveries_df: pd.DataFrame):
    analytics_cache = load_analytics_cache()
    if analytics_cache:
        return (
            analytics_cache["player_stats"],
            analytics_cache["player_recent_runs"],
        )
    return build_player_stats(deliveries_df), build_player_recent_runs(deliveries_df)


@st.cache_data
def load_team_role_lookup() -> dict[str, dict[str, str]]:
    info_path = BASE_DIR / "player_team_season_mapping_info.json"
    if not info_path.exists():
        return {}

    with open(info_path, "r", encoding="utf-8") as info_file:
        info_data = json.load(info_file)

    role_lookup: dict[str, dict[str, str]] = {}
    for team, seasons in info_data.items():
        season_data = seasons.get(CURRENT_SEASON, {})
        players_detail = season_data.get("Players_Detail", {})
        role_lookup[team] = {
            player: details.get("role", "Player")
            for player, details in players_detail.items()
        }
    return role_lookup


def load_team_squads() -> dict[str, list[str]]:
    current_squads = load_current_season_squads_from_matches()
    if current_squads:
        return current_squads

    analytics_cache = load_analytics_cache()
    if analytics_cache and analytics_cache.get("team_squads"):
        return analytics_cache.get("team_squads", {})
    return {}


def format_player_label(team: str, player: str) -> str:
    role = load_team_role_lookup().get(team, {}).get(player)
    if role:
        return f"{player} ({role})"
    return player


def resolve_matchup_pair(batter_query: str, bowler_query: str, matchup_lookup: dict[tuple[str, str], dict[str, float]]):
    batters = sorted({batter for batter, _ in matchup_lookup.keys()})
    bowlers = sorted({bowler for _, bowler in matchup_lookup.keys()})

    batter_suggestions = rank_player_matches(batter_query, batters, limit=8)
    bowler_suggestions = rank_player_matches(bowler_query, bowlers, limit=8)

    for batter in batter_suggestions:
        for bowler in bowler_suggestions:
            matchup = matchup_lookup.get((batter, bowler))
            if matchup:
                return batter, bowler, batter_suggestions, bowler_suggestions, matchup

    batter = batter_suggestions[0] if batter_suggestions else None
    bowler = bowler_suggestions[0] if bowler_suggestions else None
    matchup = matchup_lookup.get((batter, bowler)) if batter and bowler else None
    return batter, bowler, batter_suggestions, bowler_suggestions, matchup


def load_matchup_lookup() -> dict[tuple[str, str], dict[str, float]]:
    analytics_cache = load_analytics_cache()
    if analytics_cache:
        return analytics_cache.get("matchup_lookup", {})
    return {}


def aggregate_selected_xi_features(players: list[str]) -> dict[str, float]:
    analytics_cache = load_analytics_cache() or {}
    lookup = analytics_cache.get("player_feature_lookup", {})
    stats = [lookup.get(player, {"matches": 0.0, "avg_runs": 0.0, "strike_rate": 0.0, "death_strike_rate": 0.0}) for player in players]
    if not stats:
        return {
            "player_avg_matches": 0.0,
            "player_avg_runs": 0.0,
            "player_avg_sr": 0.0,
            "player_avg_death_sr": 0.0,
        }

    return {
        "player_avg_matches": sum(float(item.get("matches", 0.0)) for item in stats) / len(stats),
        "player_avg_runs": sum(float(item.get("avg_runs", 0.0)) for item in stats) / len(stats),
        "player_avg_sr": sum(float(item.get("strike_rate", 0.0)) for item in stats) / len(stats),
        "player_avg_death_sr": sum(float(item.get("death_strike_rate", 0.0)) for item in stats) / len(stats),
    }


def normalize_name(value: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def name_tokens(value: str) -> list[str]:
    return normalize_name(value).split()


def surname_of(value: str) -> str:
    tokens = name_tokens(value)
    return tokens[-1] if tokens else ""


def initials_of(value: str) -> str:
    tokens = name_tokens(value)
    if not tokens:
        return ""
    if len(tokens) == 1:
        return tokens[0][0]
    return "".join(token[0] for token in tokens[:-1])


def rank_player_matches(query: str, player_index, limit: int = 5) -> list[str]:
    normalized_query = normalize_name(query)
    if not normalized_query:
        return []

    query_tokens = normalized_query.split()
    query_surname = surname_of(query)
    query_initials = initials_of(query)
    ranked = []

    for player in player_index:
        normalized_player = normalize_name(player)
        player_tokens = normalized_player.split()
        player_surname = surname_of(player)
        player_initials = initials_of(player)

        score = 0.0

        if normalized_player == normalized_query:
            score += 100
        if normalized_query in normalized_player:
            score += 70
        if player_surname and player_surname == query_surname:
            score += 45
        if query_tokens and player_tokens and query_tokens[0][0] == player_tokens[0][0]:
            score += 30

        token_overlap = len(set(query_tokens) & set(player_tokens))
        score += token_overlap * 18

        if query_initials and player_initials:
            if player_initials == query_initials:
                score += 60
            elif player_initials.startswith(query_initials):
                score += 30
            elif query_initials.startswith(player_initials):
                score += 18
            score += SequenceMatcher(None, query_initials, player_initials).ratio() * 12

        score += SequenceMatcher(None, normalized_query, normalized_player).ratio() * 30

        if score > 20:
            ranked.append((score, player))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [player for _, player in ranked[:limit]]


def resolve_player_name(query: str, player_index):
    matches = rank_player_matches(query, player_index, limit=5)
    if not matches:
        return None, []
    return matches[0], matches


def render_hero():
    st.markdown(
        """
        <div class="hero">
            <div class="hero-grid">
                <div class="hero-copy">
                    <div class="hero-eyebrow">Cricket Intelligence Dashboard</div>
                    <h1>IPL Analytics Platform</h1>
                    <p>Analyze player form, compare performances, and predict match winners in one dashboard.</p>
                    <div class="hero-badges">
                        <span class="hero-badge">2026 Schedule Ready</span>
                        <span class="hero-badge">Current Squad Selection</span>
                        <span class="hero-badge">Local-First Data Flow</span>
                    </div>
                </div>
                <div class="hero-panel">
                    <div>
                        <h3>Matchday Workspace</h3>
                        <p>Explore player trends, review the current fixture list, and generate pre-match predictions from one professional interface.</p>
                    </div>
                    <div class="hero-kpi-grid">
                        <div class="hero-kpi">
                            <div class="hero-kpi-value">70</div>
                            <div class="hero-kpi-label">League Fixtures</div>
                        </div>
                        <div class="hero-kpi">
                            <div class="hero-kpi-value">10</div>
                            <div class="hero-kpi-label">Active Teams</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview(player_stats: pd.DataFrame):
    total_players = len(player_stats)
    total_runs = int(player_stats["runs"].sum())
    avg_strike_rate = player_stats["strike_rate"].mean()

    st.markdown(
        f"""
        <div class="overview-grid">
            <div class="overview-card">
                <div class="overview-label">Tracked Players</div>
                <div class="overview-value">{total_players}</div>
                <div class="overview-note">Qualified batters in the analytics dataset</div>
            </div>
            <div class="overview-card">
                <div class="overview-label">Total Runs</div>
                <div class="overview-value">{total_runs:,}</div>
                <div class="overview-note">Career runs represented in the dashboard</div>
            </div>
            <div class="overview-card">
                <div class="overview-label">Average Strike Rate</div>
                <div class="overview-value">{avg_strike_rate:.2f}</div>
                <div class="overview-note">Across all tracked batting records</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_player_analysis(deliveries_df: pd.DataFrame, player_stats: pd.DataFrame, player_recent_runs: dict[str, pd.Series]):
    st.markdown('<div class="section-title">Player Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Search a batter to review overall numbers and recent form.</div>', unsafe_allow_html=True)
    player_name = st.text_input(
        "Enter Player Name",
        placeholder="Try Virat Kohli, MS Dhoni, Rohit Sharma...",
    )

    if not player_name:
        st.info("Search for a batter to view career numbers and recent form.")
        return

    player, suggestions = resolve_player_name(player_name, player_stats.index.tolist())
    if not player:
        st.error("Player not found.")
        return

    stats = player_stats.loc[player]
    if normalize_name(player_name) != normalize_name(player):
        st.caption(f"Showing stats for dataset match: {player}")
        if len(suggestions) > 1:
            st.caption("Other close matches: " + ", ".join(suggestions[1:]))

    st.markdown(f"### {player}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Matches", int(stats["matches"]))
    col2.metric("Runs", int(stats["runs"]))
    col3.metric("Strike Rate", f"{stats['strike_rate']:.2f}")

    runs_per_match = player_recent_runs.get(player)
    if runs_per_match is None or runs_per_match.empty:
        st.warning("Recent match data is not available for this player.")
        return

    last_matches = runs_per_match.reset_index()
    last_matches["match_no"] = range(1, len(last_matches) + 1)
    last_matches["avg"] = last_matches["batsman_runs"].rolling(3).mean()

    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor("#fffaf1")
    ax.set_facecolor("#fffdf8")
    ax.plot(
        last_matches["match_no"],
        last_matches["batsman_runs"],
        marker="o",
        linewidth=2.5,
        color="#145da0",
        label="Runs",
    )
    ax.plot(
        last_matches["match_no"],
        last_matches["avg"],
        linestyle="--",
        linewidth=2.0,
        color="#f28c28",
        label="3-match average",
    )
    ax.set_title("Last 10 Matches Performance")
    ax.set_xlabel("Recent Matches")
    ax.set_ylabel("Runs")
    ax.legend()
    ax.grid(True, alpha=0.25)
    st.pyplot(fig)

    avg_runs = last_matches["batsman_runs"].mean()
    st.markdown(
        f"""
        <div class="insight-card">
            <strong>Recent Form Snapshot</strong><br>
            Average runs in last 10 matches: <strong>{avg_runs:.2f}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if avg_runs > 30:
        st.success("Player is in good form.")
    elif avg_runs > 15:
        st.warning("Player is in average form.")
    else:
        st.error("Player is struggling.")



def get_team_profile(team_name: str, encoders: dict) -> dict[str, float]:
    profile = encoders.get("team_profiles", {}).get(team_name, {})
    return {
        "recent_avg_runs": float(profile.get("recent_avg_runs", 0.0)),
        "recent_win_rate": float(profile.get("recent_win_rate", 0.0)),
        "player_avg_matches": float(profile.get("player_avg_matches", 0.0)),
        "player_avg_runs": float(profile.get("player_avg_runs", 0.0)),
        "player_avg_sr": float(profile.get("player_avg_sr", 0.0)),
        "player_avg_death_sr": float(profile.get("player_avg_death_sr", 0.0)),
    }


def canonical_team_name(team_name: str) -> str:
    replacements = {
        "Delhi Daredevils": "Delhi Capitals",
        "Kings XI Punjab": "Punjab Kings",
        "Rising Pune Supergiants": "Rising Pune Supergiant",
        "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    }
    return replacements.get(team_name, team_name)


def select_winner_from_selected_teams(model, input_df: pd.DataFrame, encoders: dict, team1: str, team2: str) -> tuple[str, float]:
    probabilities = model.predict_proba(input_df)[0]
    winner_classes = list(encoders["winner"].classes_)
    team_probabilities = {team1: 0.0, team2: 0.0}

    for class_name, probability in zip(winner_classes, probabilities):
        canonical_name = canonical_team_name(class_name)
        if canonical_name in team_probabilities:
            team_probabilities[canonical_name] += float(probability)

    total_selected_probability = team_probabilities[team1] + team_probabilities[team2]
    if total_selected_probability <= 0:
        return team1, 50.0

    normalized_probabilities = {
        team1: team_probabilities[team1] / total_selected_probability,
        team2: team_probabilities[team2] / total_selected_probability,
    }

    winner = max(normalized_probabilities, key=normalized_probabilities.get)
    confidence = normalized_probabilities[winner] * 100
    return winner, confidence


def render_player_comparison(player_stats: pd.DataFrame):
    st.markdown('<div class="section-title">Player Comparison</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Compare two batters side by side on core IPL batting metrics.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        player1 = st.text_input("Enter Player 1", placeholder="Virat Kohli")
    with col2:
        player2 = st.text_input("Enter Player 2", placeholder="Rohit Sharma")

    if not (player1 and player2):
        st.info("Enter both player names to compare them.")
        return

    player1_match, player1_suggestions = resolve_player_name(player1, player_stats.index.tolist())
    player2_match, player2_suggestions = resolve_player_name(player2, player_stats.index.tolist())

    if player1_match is None or player2_match is None:
        st.error("One or both players were not found.")
        return

    if normalize_name(player1) != normalize_name(player1_match):
        st.caption(f"Player 1 matched to: {player1_match}")
        if len(player1_suggestions) > 1:
            st.caption("Other Player 1 matches: " + ", ".join(player1_suggestions[1:]))
    if normalize_name(player2) != normalize_name(player2_match):
        st.caption(f"Player 2 matched to: {player2_match}")
        if len(player2_suggestions) > 1:
            st.caption("Other Player 2 matches: " + ", ".join(player2_suggestions[1:]))

    stats1 = player_stats.loc[player1_match]
    stats2 = player_stats.loc[player2_match]

    comparison = pd.DataFrame(
        {
            "Metric": ["Matches", "Runs", "Balls", "Strike Rate"],
            player1_match: [
                int(stats1["matches"]),
                int(stats1["runs"]),
                int(stats1["balls"]),
                round(stats1["strike_rate"], 2),
            ],
            player2_match: [
                int(stats2["matches"]),
                int(stats2["runs"]),
                int(stats2["balls"]),
                round(stats2["strike_rate"], 2),
            ],
        }
    )

    st.dataframe(comparison, use_container_width=True, hide_index=True)

    chart_df = pd.DataFrame(
        {
            "Metric": ["Matches", "Runs", "Balls", "Strike Rate"],
            player1_match: [
                float(stats1["matches"]),
                float(stats1["runs"]),
                float(stats1["balls"]),
                float(stats1["strike_rate"]),
            ],
            player2_match: [
                float(stats2["matches"]),
                float(stats2["runs"]),
                float(stats2["balls"]),
                float(stats2["strike_rate"]),
            ],
        }
    )

    fig, ax = plt.subplots(figsize=(9, 4.8))
    fig.patch.set_facecolor("#fffaf1")
    ax.set_facecolor("#fffdf8")
    x = range(len(chart_df["Metric"]))
    width = 0.36

    ax.bar(
        [value - width / 2 for value in x],
        chart_df[player1_match],
        width=width,
        color="#145da0",
        label=player1_match,
    )
    ax.bar(
        [value + width / 2 for value in x],
        chart_df[player2_match],
        width=width,
        color="#f28c28",
        label=player2_match,
    )

    ax.set_xticks(list(x))
    ax.set_xticklabels(chart_df["Metric"])
    ax.set_title(f"{player1_match} vs {player2_match}")
    ax.set_ylabel("Value")
    ax.legend()
    ax.grid(axis="y", alpha=0.2)
    st.pyplot(fig)

    better_run_scorer = player1_match if stats1["runs"] > stats2["runs"] else player2_match
    better_strike_rate = player1_match if stats1["strike_rate"] > stats2["strike_rate"] else player2_match
    st.caption(f"Top run scorer: {better_run_scorer} | Better strike rate: {better_strike_rate}")


def render_batter_vs_bowler():
    st.subheader("Batter vs Bowler Analysis")

    matchup_lookup = load_matchup_lookup()
    if not matchup_lookup:
        st.warning("Matchup data is not available.")
        return

    col1, col2 = st.columns(2)
    with col1:
        batter_query = st.text_input("Enter Batter", placeholder="Virat Kohli")
    with col2:
        bowler_query = st.text_input("Enter Bowler", placeholder="Jasprit Bumrah")

    if not batter_query or not bowler_query:
        st.info("Enter both a batter and a bowler to view their detailed head-to-head record.")
        return

    batter, bowler, batter_suggestions, bowler_suggestions, matchup = resolve_matchup_pair(
        batter_query, bowler_query, matchup_lookup
    )

    if not batter or not bowler:
        st.error("Batter or bowler not found.")
        return

    if normalize_name(batter_query) != normalize_name(batter):
        st.caption(f"Batter matched to: {batter}")
        if len(batter_suggestions) > 1:
            st.caption("Other batter matches: " + ", ".join(batter_suggestions[1:]))
    if normalize_name(bowler_query) != normalize_name(bowler):
        st.caption(f"Bowler matched to: {bowler}")
        if len(bowler_suggestions) > 1:
            st.caption("Other bowler matches: " + ", ".join(bowler_suggestions[1:]))

    if not matchup:
        st.warning(f"No recorded head-to-head data found for {batter} vs {bowler}.")
        return

    st.markdown(f"### {batter} vs {bowler}")
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Runs", int(matchup["runs"]))
    metric_col2.metric("Balls", int(matchup["balls"]))
    metric_col3.metric("Strike Rate", f"{matchup['strike_rate']:.2f}")
    metric_col4.metric("Dismissals", int(matchup["dismissals"]))
    st.caption(
        f"Matches faced: {int(matchup['matches'])} | Boundaries: {int(matchup['boundaries'])}"
    )

    chart_df = pd.DataFrame(
        {
            "Metric": ["Runs", "Balls", "Dismissals", "Boundaries"],
            "Value": [
                float(matchup["runs"]),
                float(matchup["balls"]),
                float(matchup["dismissals"]),
                float(matchup["boundaries"]),
            ],
        }
    )

    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_facecolor("#fffaf1")
    ax.set_facecolor("#fffdf8")
    ax.bar(chart_df["Metric"], chart_df["Value"], color=["#145da0", "#1b4965", "#f28c28", "#2a9d8f"])
    ax.set_title(f"{batter} vs {bowler}")
    ax.set_ylabel("Value")
    ax.grid(axis="y", alpha=0.2)
    st.pyplot(fig)

    if matchup["dismissals"] == 0:
        st.success(f"{bowler} has not dismissed {batter} in the recorded data.")
    elif matchup["strike_rate"] >= 140:
        st.success(f"{batter} has scored freely against {bowler}.")
    elif matchup["dismissals"] >= 3:
        st.warning(f"{bowler} has had a strong edge over {batter}.")
    else:
        st.info("This matchup looks fairly balanced based on the available data.")



def render_schedule():
    schedule_df, season_label = load_current_season_schedule()
    st.markdown(f'<div class="section-title">IPL Season {season_label} Schedule</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Full 2026 fixture list sourced from your local schedule document.</div>', unsafe_allow_html=True)

    current_teams = sorted(set(schedule_df["team1"]).union(schedule_df["team2"]))
    filter_options = ["All Teams"] + current_teams
    selected_team = st.selectbox("Filter by Team", filter_options)

    filtered_df = schedule_df
    if selected_team != "All Teams":
        filtered_df = schedule_df[
            (schedule_df["team1"] == selected_team) | (schedule_df["team2"] == selected_team)
        ]

    filtered_df = filtered_df.copy()
    today = pd.Timestamp.now().normalize()
    is_past = filtered_df["match_date"].dt.normalize() < today
    filtered_df.loc[is_past & filtered_df["winner"].isna(), "winner"] = "Completed"
    filtered_df.loc[is_past & filtered_df["result"].isna(), "result"] = "Result not stored in local schedule"
    filtered_df.loc[~is_past & filtered_df["winner"].isna(), "winner"] = "Upcoming"
    filtered_df.loc[~is_past & filtered_df["result"].isna(), "result"] = "Scheduled"

    display_df = filtered_df[
        ["match_date", "match_number", "fixture", "venue", "city", "winner", "result"]
    ].copy()
    display_df["match_date"] = display_df["match_date"].dt.strftime("%Y-%m-%d")
    display_df = display_df.rename(
        columns={
            "match_date": "Date",
            "match_number": "Match No.",
            "fixture": "Fixture",
            "venue": "Venue",
            "city": "City",
            "winner": "Winner",
            "result": "Result Type",
        }
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(display_df)} matches for the {season_label} season from your local match document.")


def render_match_prediction(model, encoders):
    st.markdown('<div class="section-title">Match Winner Prediction</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Select the two teams, set the toss details, choose the playing XIs, and generate a local pre-match prediction.</div>', unsafe_allow_html=True)

    encoded_teams = set(encoders["team1"].classes_)
    teams = [team for team in load_current_season_teams() if team in encoded_teams]
    team_squads = load_team_squads()

    col1, col2 = st.columns(2)
    with col1:
        team1 = st.selectbox("Team 1", teams, index=0)
    with col2:
        default_team2_index = 1 if len(teams) > 1 else 0
        team2 = st.selectbox("Team 2", teams, index=default_team2_index)

    toss_options = [team for team in [team1, team2] if team]
    col3, col4 = st.columns(2)
    with col3:
        toss_winner = st.selectbox("Toss Winner", toss_options)
    with col4:
        toss_decision = st.selectbox("Toss Decision", ["bat", "field"])

    team1_squad = team_squads.get(team1, [])
    team2_squad = team_squads.get(team2, [])

    xi_col1, xi_col2 = st.columns(2)
    with xi_col1:
        team1_selected = st.multiselect(
            f"Select {team1} Playing XI",
            team1_squad,
            default=team1_squad[:11],
            max_selections=11,
            format_func=lambda player: format_player_label(team1, player),
            help="Only current 2026 squad members are shown here.",
        )
    with xi_col2:
        team2_selected = st.multiselect(
            f"Select {team2} Playing XI",
            team2_squad,
            default=team2_squad[:11],
            max_selections=11,
            format_func=lambda player: format_player_label(team2, player),
            help="Only current 2026 squad members are shown here.",
        )

    base_team1_profile = get_team_profile(team1, encoders)
    base_team2_profile = get_team_profile(team2, encoders)
    team1_xi_features = aggregate_selected_xi_features(team1_selected)
    team2_xi_features = aggregate_selected_xi_features(team2_selected)

    team1_profile = {
        **base_team1_profile,
        **team1_xi_features,
    }
    team2_profile = {
        **base_team2_profile,
        **team2_xi_features,
    }

    profile_col1, profile_col2 = st.columns(2)
    with profile_col1:
        st.markdown(f"#### {team1} Profile")
        metrics_col1, metrics_col2 = st.columns(2)
        metrics_col1.metric("Selected XI", f"{len(team1_selected)}/11")
        metrics_col2.metric("Recent Win Rate", f"{team1_profile['recent_win_rate']:.2f}")
        st.metric("Recent Avg Runs", f"{team1_profile['recent_avg_runs']:.2f}")
        if team1_selected:
            st.caption("XI: " + ", ".join(format_player_label(team1, player) for player in team1_selected))
    with profile_col2:
        st.markdown(f"#### {team2} Profile")
        metrics_col3, metrics_col4 = st.columns(2)
        metrics_col3.metric("Selected XI", f"{len(team2_selected)}/11")
        metrics_col4.metric("Recent Win Rate", f"{team2_profile['recent_win_rate']:.2f}")
        st.metric("Recent Avg Runs", f"{team2_profile['recent_avg_runs']:.2f}")
        if team2_selected:
            st.caption("XI: " + ", ".join(format_player_label(team2, player) for player in team2_selected))

    if st.button("Predict Winner", use_container_width=True):
        if team1 == team2:
            st.error("Please select two different teams.")
            return
        if len(team1_selected) != 11 or len(team2_selected) != 11:
            st.error("Please select exactly 11 players for both teams.")
            return

        input_row = {
            "team1": encoders["team1"].transform([team1])[0],
            "team2": encoders["team2"].transform([team2])[0],
            "toss_winner": encoders["toss_winner"].transform([toss_winner])[0],
            "toss_decision": encoders["toss_decision"].transform([toss_decision])[0],
            "team1_recent_avg_runs": team1_profile["recent_avg_runs"],
            "team2_recent_avg_runs": team2_profile["recent_avg_runs"],
            "team1_recent_win_rate": team1_profile["recent_win_rate"],
            "team2_recent_win_rate": team2_profile["recent_win_rate"],
            "team1_player_avg_matches": team1_profile["player_avg_matches"],
            "team2_player_avg_matches": team2_profile["player_avg_matches"],
            "team1_player_avg_runs": team1_profile["player_avg_runs"],
            "team2_player_avg_runs": team2_profile["player_avg_runs"],
            "team1_player_avg_sr": team1_profile["player_avg_sr"],
            "team2_player_avg_sr": team2_profile["player_avg_sr"],
            "team1_player_avg_death_sr": team1_profile["player_avg_death_sr"],
            "team2_player_avg_death_sr": team2_profile["player_avg_death_sr"],
        }

        feature_columns = encoders.get("feature_columns", list(input_row.keys()))
        input_df = pd.DataFrame([[input_row[col] for col in feature_columns]], columns=feature_columns)

        winner, proba = select_winner_from_selected_teams(model, input_df, encoders, team1, team2)

        st.markdown(
            f"""
            <div class="winner-card">
                <h2>Predicted Winner</h2>
                <h1>{winner}</h1>
                <p>Model confidence between selected teams: {proba:.2f}%</p>
            </div>
            """,
            unsafe_allow_html=True,
        )



def main():
    inject_styles()
    render_hero()

    try:
        deliveries_df = load_deliveries()
    except FileNotFoundError as exc:
        st.error(f"Missing required file: {exc.filename}")
        st.info(f"Make sure the file exists inside {BASE_DIR}")
        return

    player_stats, player_recent_runs = load_player_analytics(deliveries_df)
    render_overview(player_stats)

    st.sidebar.title("IPL Control Room")

    page = st.sidebar.radio(
        "Navigate",
        [
            "Predict Match Winner",
            "Player Analysis",
            "Player Comparison",
            "IPL Schedule",
            "Today's IPL Matches",
        ],
    )
    st.sidebar.caption("Professional local-first dashboard using your 2026 schedule and cleaned player data.")
    st.sidebar.caption("Switch sections from the control room below.")

    if page == "Predict Match Winner":
        try:
            with st.spinner("Loading prediction model..."):
                model, encoders = load_artifacts()
            render_match_prediction(model, encoders)
        except FileNotFoundError as exc:
            st.error(f"Missing required file: {exc.filename}")
        except Exception as exc:
            st.error("Prediction model could not be loaded in this environment.")
            st.code(str(exc))
    elif page == "Player Analysis":
        render_player_analysis(deliveries_df, player_stats, player_recent_runs)
    elif page == "IPL Schedule":
        render_schedule()
    elif page == "Today's IPL Matches":
        render_today_matches()
    else:
        render_player_comparison(player_stats)


if __name__ == "__main__":
    main()
