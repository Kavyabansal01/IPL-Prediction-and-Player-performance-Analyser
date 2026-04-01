import pickle
from difflib import SequenceMatcher
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent

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
                background: linear-gradient(135deg, #0f3d3e 0%, #145da0 52%, #f28c28 100%);
                color: #ffffff;
                padding: 28px 32px;
                border-radius: 24px;
                box-shadow: 0 20px 45px rgba(15, 61, 62, 0.22);
                margin-bottom: 1.2rem;
            }

            .hero h1,
            .hero p {
                color: #ffffff;
            }

            .hero h1 {
                font-size: 2.5rem;
                margin: 0 0 0.35rem 0;
            }

            .hero p {
                margin: 0;
                font-size: 1.05rem;
                opacity: 0.95;
            }

            .section-card {
                background: rgba(255, 255, 255, 0.96);
                color: #102542;
                border: 1px solid rgba(15, 61, 62, 0.08);
                border-radius: 22px;
                padding: 1.1rem 1.2rem;
                box-shadow: 0 14px 30px rgba(0, 0, 0, 0.06);
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
    deliveries_df = pd.read_csv(BASE_DIR / "deliveries.csv")
    name_map = load_name_map()
    if name_map:
        for col in ["batter", "bowler", "non_striker", "player_dismissed", "fielder"]:
            if col in deliveries_df.columns:
                deliveries_df[col] = deliveries_df[col].replace(name_map)
    return deliveries_df


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
            <h1>IPL Analytics Platform</h1>
            <p>Analyze player form, compare performances, and predict match winners in one dashboard.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview(player_stats: pd.DataFrame):
    total_players = len(player_stats)
    total_runs = int(player_stats["runs"].sum())
    avg_strike_rate = player_stats["strike_rate"].mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Tracked Players", total_players)
    col2.metric("Total Runs", f"{total_runs:,}")
    col3.metric("Average Strike Rate", f"{avg_strike_rate:.2f}")


def render_player_analysis(deliveries_df: pd.DataFrame, player_stats: pd.DataFrame):
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Player Analysis")
    player_name = st.text_input(
        "Enter Player Name",
        placeholder="Try Virat Kohli, MS Dhoni, Rohit Sharma...",
    )

    if not player_name:
        st.info("Search for a batter to view career numbers and recent form.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    player, suggestions = resolve_player_name(player_name, player_stats.index.tolist())
    if not player:
        st.error("Player not found.")
        st.markdown("</div>", unsafe_allow_html=True)
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

    player_data = deliveries_df[deliveries_df["batter"] == player]
    runs_per_match = (
        player_data.groupby("match_id")["batsman_runs"].sum().sort_index().tail(10)
    )

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

    st.markdown("</div>", unsafe_allow_html=True)


def render_player_comparison(player_stats: pd.DataFrame):
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Player Comparison")

    col1, col2 = st.columns(2)
    with col1:
        player1 = st.text_input("Enter Player 1", placeholder="Virat Kohli")
    with col2:
        player2 = st.text_input("Enter Player 2", placeholder="Rohit Sharma")

    if not (player1 and player2):
        st.info("Enter both player names to compare them.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    player1_match, player1_suggestions = resolve_player_name(player1, player_stats.index.tolist())
    player2_match, player2_suggestions = resolve_player_name(player2, player_stats.index.tolist())

    if player1_match is None or player2_match is None:
        st.error("One or both players were not found.")
        st.markdown("</div>", unsafe_allow_html=True)
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

    better_run_scorer = player1_match if stats1["runs"] > stats2["runs"] else player2_match
    better_strike_rate = player1_match if stats1["strike_rate"] > stats2["strike_rate"] else player2_match
    st.caption(f"Top run scorer: {better_run_scorer} | Better strike rate: {better_strike_rate}")
    st.markdown("</div>", unsafe_allow_html=True)


def render_match_prediction(model, encoders):
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Match Winner Prediction")

    teams = sorted(encoders["team1"].classes_)

    col1, col2 = st.columns(2)
    with col1:
        team1 = st.selectbox("Team 1", teams)
        toss_winner = st.selectbox("Toss Winner", teams)
    with col2:
        team2 = st.selectbox("Team 2", teams)
        toss_decision = st.selectbox("Toss Decision", ["bat", "field"])

    if st.button("Predict Winner", use_container_width=True):
        if team1 == team2:
            st.error("Please select two different teams.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        input_df = pd.DataFrame(
            [
                {
                    "team1": encoders["team1"].transform([team1])[0],
                    "team2": encoders["team2"].transform([team2])[0],
                    "toss_winner": encoders["toss_winner"].transform([toss_winner])[0],
                    "toss_decision": encoders["toss_decision"].transform([toss_decision])[0],
                }
            ]
        )

        prediction = model.predict(input_df)[0]
        winner = encoders["winner"].inverse_transform([prediction])[0]
        proba = model.predict_proba(input_df)[0].max() * 100

        st.markdown(
            f"""
            <div class="winner-card">
                <h2>Predicted Winner</h2>
                <h1>{winner}</h1>
                <p>Model confidence: {proba:.2f}%</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def main():
    inject_styles()
    render_hero()

    try:
        deliveries_df = load_deliveries()
    except FileNotFoundError as exc:
        st.error(f"Missing required file: {exc.filename}")
        st.info(f"Make sure the file exists inside {BASE_DIR}")
        return

    player_stats = build_player_stats(deliveries_df)
    render_overview(player_stats)

    st.sidebar.title("Navigation")

    page = st.sidebar.radio(
        "Choose a section",
        [
            "Predict Match Winner",
            "Player Analysis",
            "Player Comparison",
        ],
    )
    st.sidebar.caption(f"Project folder: {BASE_DIR}")
    st.sidebar.caption("Using player_name_map.csv to expand short player names")

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
        render_player_analysis(deliveries_df, player_stats)
    else:
        render_player_comparison(player_stats)


if __name__ == "__main__":
    main()
