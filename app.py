from datetime import date
import altair as alt
import pandas as pd
import streamlit as st

import db

st.set_page_config(
    page_title="Team Punten",
    page_icon="🏑",
    layout="wide",
    initial_sidebar_state="collapsed",
)

db.init_db()

st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(180deg, #F8FBFF 0%, #FFFFFF 35%); }
    .block-container { max-width: 820px; padding-top: 1.2rem; padding-bottom: 5rem; }
    [data-testid="stSidebar"] { background: #F1F6FF; }
    .hero {
        background: linear-gradient(135deg, #1D4ED8 0%, #3B82F6 100%);
        color: white; padding: 22px; border-radius: 22px; margin-bottom: 14px;
        box-shadow: 0 10px 24px rgba(37, 99, 235, .16);
    }
    .hero .small { opacity:.82; font-size:.86rem; }
    .hero .big { font-size:2.4rem; font-weight:800; line-height:1; margin:.35rem 0; }
    .card {
        background:white; border:1px solid #DDE9FA; border-radius:18px;
        padding:16px; margin-bottom:10px; box-shadow:0 5px 18px rgba(36,71,120,.06);
    }
    .task-card { background:#F8FBFF; border-left:4px solid #60A5FA; border-radius:14px; padding:12px 14px; margin:8px 0; }
    .muted { color:#6B7A90; font-size:.9rem; }
    .rank { font-size:1.05rem; font-weight:700; }
    .section-title { margin-top:1.5rem; margin-bottom:.4rem; font-weight:800; font-size:1.2rem; color:#12233F; }
    div[data-testid="stButton"] > button, div[data-testid="stFormSubmitButton"] > button {
        border-radius:14px; min-height:46px; font-weight:700;
    }
    div[data-baseweb="select"] > div { border-radius:14px; }
    @media (max-width: 700px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; padding-top:.8rem; }
        .hero { padding:18px; border-radius:18px; }
        .hero .big { font-size:2.1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def status_badge(status):
    return {"pending": "⏳ In afwachting", "approved": "✅ Goedgekeurd", "rejected": "❌ Afgewezen"}.get(status, status)


def money_text(value):
    if value is None:
        return ""
    return f" · €{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def login_view():
    st.markdown("## 🏑 Team Punten")
    st.caption("Log in met je naam om jouw bijdrage en de teamstand te bekijken.")
    players = db.get_players()
    names = [p["name"] for p in players]
    selected = st.selectbox("Wie ben je?", names, index=None, placeholder="Kies je naam")
    if st.button("Inloggen", type="primary", use_container_width=True, disabled=selected is None):
        player = next(p for p in players if p["name"] == selected)
        st.session_state.player_id = player["id"]
        st.rerun()
    st.info("Deze versie gebruikt bewust alleen een naam-login. Voor een openbare app is een PIN of echte accountlogin veiliger.")


if "player_id" not in st.session_state:
    login_view()
    st.stop()

player = db.get_player(st.session_state.player_id)
if not player or not player["active"]:
    st.session_state.pop("player_id", None)
    st.rerun()

with st.sidebar:
    st.markdown(f"### 👋 {player['name']}")
    if player["role"] == "admin":
        st.caption("Beheerder")
    section_options = ["Dashboard", "Activiteit indienen", "Komende taken"]
    if player["role"] == "admin":
        section_options += ["Goedkeuren", "Instellingen"]
    section = st.radio("Navigatie", section_options, label_visibility="collapsed")
    st.divider()
    if st.button("Uitloggen", use_container_width=True):
        st.session_state.pop("player_id", None)
        st.rerun()

leaderboard = db.get_leaderboard()
my_row = next((r for r in leaderboard if r["id"] == player["id"]), None)


def recommendation_text():
    if not leaderboard:
        return "Nog onvoldoende gegevens."
    min_points = min(r["points"] for r in leaderboard)
    candidates = [r["name"] for r in leaderboard if r["points"] == min_points]
    if len(candidates) == 1:
        return f"**{candidates[0]}** heeft momenteel de minste punten ({min_points}) en komt als eerste in aanmerking."
    return f"**{' en '.join(candidates)}** hebben momenteel de minste punten ({min_points}) en komen als eerste in aanmerking."


@st.dialog("Activiteit indienen")
def submission_dialog():
    activity_types = db.get_activity_types()
    labels = [f"{a['icon']} {a['name']} · {a['points']} pt" for a in activity_types]
    with st.form("submit_activity_dialog", clear_on_submit=True):
        label = st.selectbox("Activiteit", labels)
        selected_type = activity_types[labels.index(label)]
        activity_date = st.date_input("Datum", value=date.today())
        amount = st.number_input("Opgebracht bedrag (€) — optioneel", min_value=0.0, value=0.0, step=10.0)
        description = st.text_area("Beschrijving", placeholder="Bijv. sponsor X binnengehaald voor €500")
        st.caption(f"Na goedkeuring levert dit **{selected_type['points']} punten** op.")
        submitted = st.form_submit_button("Indienen ter goedkeuring", type="primary", use_container_width=True)
    if submitted:
        db.submit_activity(player["id"], selected_type["id"], activity_date, amount if amount > 0 else None, description)
        st.success("Activiteit ingediend. Een beheerder kan hem nu goedkeuren.")


if section == "Dashboard":
    st.markdown(f"## Goedemorgen, {player['name']} 👋")
    st.caption("Jouw bijdrage aan het team")

    if player["role"] == "admin" and my_row is None:
        hero_points, hero_rank, hero_activities = 0, "—", 0
    else:
        hero_points = my_row["points"] if my_row else 0
        hero_rank = (leaderboard.index(my_row) + 1) if my_row in leaderboard else "—"
        hero_activities = my_row["activities"] if my_row else 0

    st.markdown(
        f"""
        <div class="hero">
            <div class="small">JOUW BIJDRAGE</div>
            <div class="big">{hero_points} punten</div>
            <div>#{hero_rank} van {len(leaderboard)} spelers &nbsp; · &nbsp; {hero_activities} goedgekeurde activiteiten</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("＋ Activiteit toevoegen", type="primary", use_container_width=True):
        submission_dialog()

    st.markdown('<div class="section-title">Teamstand</div>', unsafe_allow_html=True)
    view = st.segmented_control("Weergave", ["Balken", "Spelercards"], default="Balken", label_visibility="collapsed")

    if leaderboard:
        if view == "Balken":
            chart_df = pd.DataFrame(leaderboard)
            chart_df["rank"] = range(1, len(chart_df) + 1)
            chart_df["label"] = chart_df.apply(lambda r: f"{int(r['rank'])}. {r['name']}", axis=1)
            order = chart_df["label"].tolist()
            chart = (
                alt.Chart(chart_df)
                .mark_bar(cornerRadiusEnd=8, height=24)
                .encode(
                    x=alt.X("points:Q", title=None, axis=alt.Axis(grid=False, labels=False, ticks=False)),
                    y=alt.Y("label:N", sort=order, title=None, axis=alt.Axis(labelFontSize=14, labelLimit=160)),
                    tooltip=[alt.Tooltip("name:N", title="Speler"), alt.Tooltip("points:Q", title="Punten"), alt.Tooltip("activities:Q", title="Activiteiten")],
                    color=alt.value("#3B82F6"),
                )
            )
            text = chart.mark_text(align="left", baseline="middle", dx=7, fontWeight="bold").encode(text="points:Q", color=alt.value("#24405F"))
            st.altair_chart((chart + text).properties(height=max(180, len(chart_df) * 42)), use_container_width=True)
        else:
            for idx, row in enumerate(leaderboard, start=1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, f"#{idx}")
                st.markdown(
                    f'<div class="card"><span class="rank">{medal} {row["name"]}</span><br><b>{row["points"]} punten</b> <span class="muted">· {row["activities"]} activiteiten</span></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("Er zijn nog geen spelers in de ranglijst.")

    if player["role"] != "admin":
        st.markdown('<div class="section-title">Waar komen jouw punten vandaan?</div>', unsafe_allow_html=True)
        breakdown = db.get_player_breakdown(player["id"])
        for item in breakdown:
            st.markdown(
                f'<div class="card">{item["icon"]} <b>{item["name"]}</b><span style="float:right"><b>{item["points"]} pt</b></span><br><span class="muted">{item["count"]}× goedgekeurd</span></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="section-title">Wie is als volgende aan de beurt?</div>', unsafe_allow_html=True)
    st.info(recommendation_text())

    st.markdown('<div class="section-title">Komende taken</div>', unsafe_allow_html=True)
    tasks = db.get_upcoming_tasks(4)
    if tasks:
        for task in tasks:
            who = task["assigned_name"] or "Nog niemand"
            when = f"{task['task_date']}" + (f" · {task['task_time']}" if task["task_time"] else "")
            st.markdown(
                f'<div class="task-card"><b>{task["icon"] or "📌"} {task["title"]}</b><br><span class="muted">{when} · {who}</span></div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("Geen komende taken ingevoerd.")

    st.markdown('<div class="section-title">Recente activiteiten</div>', unsafe_allow_html=True)
    recent = db.get_submissions(status="approved", limit=6)
    if recent:
        for s in recent:
            extra = money_text(s["amount_eur"])
            desc = f" · {s['description']}" if s["description"] else ""
            st.markdown(
                f'<div class="card">{s["icon"]} <b>{s["player_name"]}</b> · {s["activity_name"]}<span style="float:right"><b>+{s["points"]}</b></span><br><span class="muted">{s["activity_date"]}{extra}{desc}</span></div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("Nog geen goedgekeurde activiteiten.")

elif section == "Activiteit indienen":
    st.markdown("## ＋ Activiteit indienen")
    st.caption("Jouw punten tellen pas mee nadat een beheerder de activiteit heeft goedgekeurd.")
    activity_types = db.get_activity_types()
    labels = [f"{a['icon']} {a['name']} · {a['points']} pt" for a in activity_types]
    with st.form("submit_activity_page", clear_on_submit=True):
        label = st.selectbox("Wat heb je gedaan?", labels)
        selected_type = activity_types[labels.index(label)]
        activity_date = st.date_input("Datum", value=date.today())
        amount = st.number_input("Opgebracht bedrag (€) — optioneel", min_value=0.0, value=0.0, step=10.0)
        description = st.text_area("Beschrijving", placeholder="Bijv. sponsor X binnengehaald voor €500")
        submitted = st.form_submit_button("Indienen", type="primary", use_container_width=True)
    if submitted:
        db.submit_activity(player["id"], selected_type["id"], activity_date, amount if amount > 0 else None, description)
        st.success("Ingediend! De activiteit staat nu bij de beheerder ter goedkeuring.")

    st.markdown("### Mijn aanvragen")
    mine = db.get_submissions(player_id=player["id"], limit=20)
    if not mine:
        st.caption("Je hebt nog niets ingediend.")
    for s in mine:
        st.markdown(
            f'<div class="card">{s["icon"]} <b>{s["activity_name"]}</b><span style="float:right">{status_badge(s["status"])}</span><br><span class="muted">{s["activity_date"]} · {s["points"]} pt{money_text(s["amount_eur"])}</span></div>',
            unsafe_allow_html=True,
        )

elif section == "Komende taken":
    st.markdown("## 📅 Komende taken")
    st.info(recommendation_text())
    tasks = db.get_upcoming_tasks(20)
    if not tasks:
        st.caption("Er staan nog geen komende taken in de planning.")
    for task in tasks:
        who = task["assigned_name"] or "Nog niet toegewezen"
        st.markdown(
            f'<div class="card"><b>{task["icon"] or "📌"} {task["title"]}</b><br><span class="muted">{task["task_date"]} {task["task_time"] or ""} · {who}</span><br>{task["description"] or ""}</div>',
            unsafe_allow_html=True,
        )

    if player["role"] == "admin":
        st.markdown("### Taak toevoegen")
        types = db.get_activity_types()
        team_players = [p for p in db.get_players() if p["role"] != "admin"]
        with st.form("task_form", clear_on_submit=True):
            title = st.text_input("Titel", placeholder="Bijv. Bardienst zaterdag")
            task_date = st.date_input("Datum", value=date.today())
            task_time = st.text_input("Tijd (optioneel)", placeholder="19:30")
            type_names = [f"{x['icon']} {x['name']}" for x in types]
            type_label = st.selectbox("Type", type_names)
            type_obj = types[type_names.index(type_label)]
            assignee_names = ["Nog niemand"] + [p["name"] for p in team_players]
            assignee = st.selectbox("Toewijzen aan", assignee_names)
            assigned_id = None if assignee == "Nog niemand" else next(p["id"] for p in team_players if p["name"] == assignee)
            description = st.text_area("Beschrijving")
            save = st.form_submit_button("Taak toevoegen", type="primary", use_container_width=True)
        if save and title.strip():
            db.add_task(title, task_date, task_time.strip() or None, type_obj["id"], assigned_id, description)
            st.success("Taak toegevoegd.")
            st.rerun()

elif section == "Goedkeuren" and player["role"] == "admin":
    st.markdown("## ✅ Activiteiten goedkeuren")
    pending = db.get_submissions(status="pending")
    if not pending:
        st.success("Er zijn geen openstaande aanvragen.")
    for s in pending:
        st.markdown(
            f'<div class="card">{s["icon"]} <b>{s["player_name"]} · {s["activity_name"]}</b><br><span class="muted">{s["activity_date"]} · {s["points"]} punten{money_text(s["amount_eur"])}</span><br>{s["description"] or "Geen beschrijving"}</div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        if c1.button("Goedkeuren", key=f"approve_{s['id']}", type="primary", use_container_width=True):
            db.review_submission(s["id"], player["id"], True)
            st.rerun()
        if c2.button("Afwijzen", key=f"reject_{s['id']}", use_container_width=True):
            db.review_submission(s["id"], player["id"], False)
            st.rerun()

elif section == "Instellingen" and player["role"] == "admin":
    st.markdown("## ⚙️ Instellingen")
    tab1, tab2 = st.tabs(["Punten & activiteiten", "Spelers"])

    with tab1:
        st.caption("Aanpassingen gelden voor nieuwe inzendingen. Reeds goedgekeurde activiteiten houden hun oorspronkelijke puntenwaarde.")
        types = db.get_activity_types(active_only=False)
        for a in types:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{a['icon']} {a['name']}**")
                new_points = c2.number_input("Punten", min_value=0, max_value=100, value=int(a["points"]), key=f"points_{a['id']}", label_visibility="collapsed")
                if st.button("Opslaan", key=f"save_points_{a['id']}"):
                    db.update_activity_points(a["id"], new_points)
                    st.success(f"{a['name']} aangepast naar {new_points} punten.")
                    st.rerun()

        st.markdown("### Activiteitstype toevoegen")
        with st.form("new_type", clear_on_submit=True):
            name = st.text_input("Naam")
            icon = st.text_input("Emoji", value="⭐", max_chars=4)
            points = st.number_input("Punten", min_value=0, max_value=100, value=3)
            add = st.form_submit_button("Toevoegen", type="primary")
        if add and name.strip():
            try:
                db.add_activity_type(name, icon, points)
                st.success("Activiteitstype toegevoegd.")
                st.rerun()
            except Exception:
                st.error("Deze activiteit bestaat waarschijnlijk al.")

    with tab2:
        st.caption("De demo bevat voorbeeldspelers. Voeg hier jullie echte teamleden toe.")
        with st.form("new_player", clear_on_submit=True):
            new_name = st.text_input("Naam speler")
            is_admin = st.checkbox("Beheerder")
            add_player = st.form_submit_button("Speler toevoegen", type="primary")
        if add_player and new_name.strip():
            try:
                db.add_player(new_name, "admin" if is_admin else "player")
                st.success("Speler toegevoegd.")
                st.rerun()
            except Exception:
                st.error("Deze naam bestaat al.")

        for p in db.get_players(active_only=False):
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{p['name']}**  \n{p['role']}")
                if p["id"] != player["id"]:
                    label = "Deactiveren" if p["active"] else "Activeren"
                    if c2.button(label, key=f"toggle_player_{p['id']}"):
                        db.set_player_active(p["id"], not bool(p["active"]))
                        st.rerun()
