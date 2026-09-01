from datetime import date
import calendar
import io
import json
import mimetypes
import zipfile
from urllib.parse import urlencode

import altair as alt
import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="TeamApp", page_icon="🏑", layout="wide", initial_sidebar_state="auto")
db.init_db()

CATEGORY = {
    "training": ("#EAF3FF", "🔵"),
    "fluiten": ("#FFF7D6", "🟡"),
    "team": ("#FDECF4", "🩷"),
    "geld": ("#EAF8EE", "🟢"),
    "club": ("#F3ECFF", "🟣"),
}

VALID_PAGES = {
    "Home",
    "Teamrekening",
    "Agenda",
    "Ideeën",
    "Ranglijst punten",
    "Activiteiten",
    "Meldingen",
    "Profiel",
    "Toevoegen",
    "Wijzigingsverzoeken",
    "Instellingen",
}

PAGE_ALIASES = {"Ranglijst": "Ranglijst punten"}
ADMIN_PASSWORD = "Beheerder123"

st.markdown(
    """
<style>
.stApp{background:linear-gradient(180deg,#F7FBFF 0%,#FFFFFF 38%);color:#13243A}
.block-container{max-width:900px;padding-top:1.55rem;padding-bottom:2rem}
[data-testid="stSidebar"]{background:#F2F7FE}
.sidebar-name{font-size:1.4rem;font-weight:800;color:#13243A;line-height:1.1;margin:.15rem 0 .85rem}
.sidebar-link{display:block;text-decoration:none!important;color:#18304f!important;background:white;border:1px solid #dfeaf7;border-radius:13px;padding:.72rem .85rem;margin:.35rem 0;font-weight:700}
.sidebar-link.active{background:#eaf3ff;border-color:#a8c9f7;color:#235fae!important}
.sidebar-link.subtle{background:#eef6ff;border-color:#d7e7fb;color:#3567a8!important;margin-top:.75rem}
.card{background:#fff;border:1px solid #DDE9F7;border-radius:18px;padding:15px 16px;margin:9px 0;box-shadow:0 5px 20px rgba(40,78,120,.055)}
.soft{background:#F5F9FF;border:1px solid #E2ECFA;border-radius:16px;padding:14px;margin:8px 0}
.section{font-size:1.12rem;font-weight:800;margin-top:1.35rem;margin-bottom:.4rem}
.subsection-title{font-size:1.02rem;font-weight:800;color:#18304f;margin:.8rem 0 .35rem}
.muted{color:#718198;font-size:.9rem}
.badge{display:inline-block;background:#EEF5FF;color:#2F6FED;padding:4px 9px;border-radius:999px;font-size:.78rem;font-weight:700}
.score-badge{display:inline-block;background:#edf6ff;color:#235fae;padding:4px 10px;border-radius:999px;font-size:.78rem;font-weight:800}
.task{border-radius:16px;padding:14px;margin:8px 0;border:1px solid rgba(50,80,120,.08)}
.metric-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:.65rem 0 1rem}
.mini-metric{background:white;border:1px solid #dfeaf7;border-radius:16px;padding:12px 9px;text-align:center;box-shadow:0 4px 14px rgba(40,78,120,.045)}
.mini-metric .label{font-size:.77rem;color:#718198;margin-bottom:3px}
.mini-metric .value{font-size:1.45rem;font-weight:850;color:#13243A}
.calendar{display:grid;grid-template-columns:repeat(7,1fr);gap:5px}
.calhead{text-align:center;font-size:.72rem;color:#7A899C;font-weight:700}
.day{min-height:68px;border:1px solid #E4ECF7;border-radius:12px;padding:6px;background:white;font-size:.78rem}
.day.empty{background:transparent;border-color:transparent}
.dots{font-size:.65rem;line-height:1.2;margin-top:4px}
.money-positive{color:#14804a;font-weight:800}
.money-negative{color:#b54747;font-weight:800}
.status-pill{display:inline-block;padding:4px 10px;border-radius:999px;font-size:.78rem;font-weight:800}
.status-pill.pending{background:#FFF7D6;color:#8E6700}
.status-pill.approved{background:#EAF8EE;color:#14804A}
.status-pill.rejected{background:#FDECEC;color:#B54747}
.idea-meta{display:flex;gap:.55rem;align-items:center;flex-wrap:wrap}
.page-title{margin:.1rem 0 .7rem;font-size:1.8rem;font-weight:850;color:#13243A}
div[data-testid="stButton"]>button,div[data-testid="stFormSubmitButton"]>button,div[data-testid="stDownloadButton"]>button{border-radius:14px;min-height:42px;font-weight:700}
@media(max-width:700px){
  .block-container{padding-left:.9rem;padding-right:.9rem;padding-top:6.05rem!important}
  .page-title{font-size:1.52rem}
  .metric-row{gap:7px}
  .mini-metric{padding:10px 4px;border-radius:14px}
  .mini-metric .label{font-size:.68rem}
  .mini-metric .value{font-size:1.18rem}
  .day{min-height:52px;padding:4px;font-size:.7rem}
}
</style>
""",
    unsafe_allow_html=True,
)


def q(name, default=None):
    value = st.query_params.get(name, default)
    return value[0] if isinstance(value, list) and value else value


def nav_url(page, **extra):
    params = {"page": page}
    if "player_id" in st.session_state:
        params["user"] = str(st.session_state.player_id)
    params.update({key: str(val) for key, val in extra.items() if val is not None})
    return "?" + urlencode(params)


def goto(page, **extra):
    st.query_params.clear()
    st.query_params["page"] = page
    st.query_params["user"] = str(st.session_state.player_id)
    for key, val in extra.items():
        st.query_params[key] = str(val)
    st.session_state.page = page
    st.rerun()


def is_admin(current_player):
    return current_player.get("role") == "admin"


def is_treasurer(current_player):
    return current_player.get("name") == "Kieft"


def can_review_expenses(current_player):
    return is_admin(current_player) or is_treasurer(current_player)


def format_euro(value):
    return f"€ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_status(status):
    return {
        "pending": "Te controleren",
        "approved": "Goedgekeurd",
        "rejected": "Afgewezen",
    }.get(status, status or "Onbekend")


def receipt_label(status):
    return {
        "uploaded": "Bonnetje aanwezig",
        "lost": "Bonnetje kwijt",
        None: "Geen bonstatus",
        "": "Geen bonstatus",
    }.get(status, "Geen bonstatus")


def badge_status(status):
    return f'<span class="status-pill {status}">{format_status(status)}</span>'


def guess_mime(file_name):
    mime, _ = mimetypes.guess_type(file_name or "")
    return mime or "application/octet-stream"


def render_page_title(text):
    st.markdown(f'<div class="page-title">{text}</div>', unsafe_allow_html=True)


def finish_action(message, page_name=None, **extra):
    st.session_state["flash_message"] = message
    goto(page_name or st.session_state.page, **extra)


def build_transactions_export(transactions):
    if not transactions:
        return pd.DataFrame(
            columns=[
                "Datum",
                "Type",
                "Status",
                "Bedrag",
                "Categorie",
                "Omschrijving",
                "Betaald door",
                "Ingediend door",
                "Bonstatus",
                "Beoordeeld door",
                "Beoordeeld op",
            ]
        )
    rows = []
    for transaction in transactions:
        rows.append(
            {
                "Datum": transaction["transaction_date"],
                "Type": "Inkomst" if transaction["transaction_type"] == "income" else "Uitgave",
                "Status": format_status(transaction.get("review_status") or "approved"),
                "Bedrag": float(transaction["amount"]),
                "Categorie": transaction.get("category") or "",
                "Omschrijving": transaction["description"],
                "Betaald door": transaction.get("paid_by_name") or "",
                "Ingediend door": transaction.get("submitted_by_name") or "",
                "Bonstatus": receipt_label(transaction.get("receipt_status")),
                "Beoordeeld door": transaction.get("reviewer_name") or "",
                "Beoordeeld op": transaction.get("reviewed_at") or "",
            }
        )
    return pd.DataFrame(rows)


def filter_transactions_for_period(transactions, mode, month_key=None, year_value=None):
    if mode == "Totaal":
        return transactions
    if mode == "Jaar" and year_value:
        prefix = str(year_value)
        return [transaction for transaction in transactions if transaction["transaction_date"].startswith(prefix)]
    if mode == "Maand" and month_key:
        return [transaction for transaction in transactions if transaction["transaction_date"].startswith(month_key)]
    return []


def build_receipts_zip(transactions):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        added = 0
        for transaction in transactions:
            if not transaction.get("receipt_data"):
                continue
            file_name = transaction.get("receipt_name") or f"bonnetje-{transaction['id']}.bin"
            archive_name = f"{transaction['transaction_date']}_{transaction.get('paid_by_name') or 'team'}_{transaction['id']}_{file_name}"
            archive.writestr(archive_name, transaction["receipt_data"])
            added += 1
    if buffer.getbuffer().nbytes == 0:
        return None
    buffer.seek(0)
    return buffer.getvalue()


def metric_strip(points, rank, activities):
    st.markdown(
        f"""
        <div class="metric-row">
          <div class="mini-metric"><div class="label">Punten</div><div class="value">{points}</div></div>
          <div class="mini-metric"><div class="label">Rang</div><div class="value">#{rank}</div></div>
          <div class="mini-metric"><div class="label">Activiteiten</div><div class="value">{activities}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def finance_metric_strip(balance, income, expense):
    st.markdown(
        f"""
        <div class="metric-row">
          <div class="mini-metric"><div class="label">Saldo</div><div class="value">{balance}</div></div>
          <div class="mini-metric"><div class="label">Inkomsten</div><div class="value">{income}</div></div>
          <div class="mini-metric"><div class="label">Uitgaven</div><div class="value">{expense}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def recommendation(leaderboard_rows):
    if not leaderboard_rows:
        return "Nog geen gegevens."
    lowest = min(row["points"] for row in leaderboard_rows)
    names = [row["name"] for row in leaderboard_rows if row["points"] == lowest]
    verb = "heeft" if len(names) == 1 else "hebben"
    return f"**{' & '.join(names)}** {verb} nu de minste punten ({lowest})."


def money_line_chart(dataframe, x_field, series_field, value_field, tooltip_fields):
    return (
        alt.Chart(dataframe)
        .mark_line(interpolate="monotone", point=True, strokeWidth=3)
        .encode(
            x=alt.X(x_field, title=None),
            y=alt.Y(value_field, title="Bedrag"),
            color=alt.Color(
                series_field,
                scale=alt.Scale(domain=["Inkomsten", "Uitgaven", "Saldo"], range=["#2F6FED", "#D96B6B", "#14804A"]),
                title=None,
            ),
            tooltip=tooltip_fields,
        )
        .properties(height=280)
        .interactive()
    )


def single_line_chart(dataframe, x_field, y_field, color="#2F6FED", tooltip_fields=None):
    tooltip_fields = tooltip_fields or [x_field, y_field]
    return (
        alt.Chart(dataframe)
        .mark_line(interpolate="monotone", point=True, strokeWidth=3, color=color)
        .encode(x=alt.X(x_field, title=None), y=alt.Y(y_field, title="Saldo"), tooltip=tooltip_fields)
        .properties(height=280)
        .interactive()
    )


def render_transaction_card(transaction, show_receipt=False, receipt_key_prefix="receipt"):
    amount_class = "money-positive" if transaction["transaction_type"] == "income" else "money-negative"
    sign = "+" if transaction["transaction_type"] == "income" else "−"
    meta = [
        transaction["transaction_date"],
        transaction.get("category") or "Overig",
        transaction.get("paid_by_name") or "Team",
    ]
    if transaction.get("submitted_by_name"):
        meta.append(f"Ingediend door {transaction['submitted_by_name']}")
    st.markdown(
        (
            f'<div class="card"><b>{transaction["description"]}</b>'
            f'<span class="{amount_class}" style="float:right">{sign} {format_euro(transaction["amount"])}</span>'
            f'<br><span class="muted">{" · ".join(meta)}</span>'
            f'<br><span class="muted">{receipt_label(transaction.get("receipt_status"))}</span>'
            f'<br>{badge_status(transaction.get("review_status") or "approved")}</div>'
        ),
        unsafe_allow_html=True,
    )
    if show_receipt and transaction.get("receipt_data"):
        st.download_button(
            "Bonnetje bekijken",
            data=transaction["receipt_data"],
            file_name=transaction.get("receipt_name") or f"bonnetje-{transaction['id']}",
            mime=guess_mime(transaction.get("receipt_name")),
            key=f"{receipt_key_prefix}_{transaction['id']}",
            use_container_width=True,
        )


def player_card(row, rank, prefix):
    if st.button(
        f"#{rank}  {row['name']}   ·   {row['points']} pt\n{row['activities']} activiteiten  ›",
        key=f"{prefix}_{row['id']}",
        use_container_width=True,
    ):
        player_dialog(row["id"])


@st.dialog("Spelerdetails")
def player_dialog(player_id):
    selected = db.get_player(player_id)
    row = next((entry for entry in lb if entry["id"] == player_id), None)
    if not selected or not row:
        st.warning("Speler niet gevonden.")
        return
    rank = lb.index(row) + 1
    st.markdown(f"### 👤 {selected['name']}")
    metric_strip(row["points"], rank, row["activities"])
    st.markdown("#### Punten per activiteit")
    for breakdown_row in db.breakdown(player_id):
        if breakdown_row["count"]:
            st.markdown(
                f'<div class="card">{breakdown_row["icon"]} <b>{breakdown_row["name"]}</b>'
                f'<span style="float:right"><b>{breakdown_row["points"]} pt</b></span>'
                f'<br><span class="muted">{breakdown_row["count"]}× gedaan</span></div>',
                unsafe_allow_html=True,
            )
    st.markdown("#### Activiteiten")
    activities = db.get_activities(player_id=player_id)
    if not activities:
        st.caption("Nog geen activiteiten.")
    for activity in activities[:12]:
        try:
            values = json.loads(activity.get("field_values_json") or "{}")
        except Exception:
            values = {}
        details = " · ".join(f"{key}: {value}" for key, value in values.items())
        extra = " · ".join(part for part in [details, activity.get("description") or ""] if part)
        st.markdown(
            f'<div class="card">{activity["icon"]} <b>{activity["activity_name"]}</b>'
            f'<span style="float:right"><b>+{activity["points"]}</b></span>'
            f'<br><span class="muted">{activity["activity_date"]}{" · " + extra if extra else ""}</span></div>',
            unsafe_allow_html=True,
        )


def activity_form():
    types = db.get_activity_types()
    if not types:
        st.warning("Er zijn nog geen activiteitstypes ingesteld.")
        return
    labels = [f"{row['icon']} {row['name']}" for row in types]
    choice = st.selectbox("Activiteit", labels, key="activity_type")
    activity_type = types[labels.index(choice)]
    total = activity_type["base_points"]
    values = {}
    if activity_type["base_points"]:
        st.caption(f"Basispunten: **{activity_type['base_points']}**")
    for field in db.get_fields(activity_type["id"]):
        if field["field_type"] == "select" and field["options"]:
            options = [f"{option['label']} · +{option['points']} pt" for option in field["options"]]
            selected = st.selectbox(field["label"], options, key=f"activity_field_{field['id']}")
            option = field["options"][options.index(selected)]
            values[field["label"]] = option["label"]
            total += option["points"]
    activity_date = st.date_input("Datum", date.today(), key="activity_date")
    description = st.text_area("Beschrijving", placeholder="Bijv. sponsoractie · €450 opgehaald", key="activity_desc")
    st.info(f"Deze activiteit levert **{total} punten** op en staat direct in je overzicht.")
    if st.button("Activiteit opslaan", type="primary", use_container_width=True, key="activity_save"):
        db.add_activity(player["id"], activity_type["id"], activity_date, description, values, total)
        finish_action("Activiteit opgeslagen.", "Toevoegen")


def task_card(task, personal=False):
    bg_color, dot = CATEGORY.get(task["category"], ("#F5F9FF", "🔹"))
    assignees = task["assignments"]
    names = ", ".join(assignment["name"] for assignment in assignees) or "Nog niemand"
    st.markdown(
        f'<div class="task" style="background:{bg_color}"><b>{dot} {task["title"]}</b>'
        f'<br><span class="muted">{task["task_date"]} {task["task_time"] or ""} · {names}</span>'
        f'<br>{task["description"] or ""}</div>',
        unsafe_allow_html=True,
    )
    if not personal:
        return
    mine = next((assignment for assignment in assignees if assignment["player_id"] == player["id"]), None)
    if not mine:
        return
    response = mine["response"]
    if response == "pending":
        col1, col2 = st.columns(2)
        if col1.button("✓ Ik kan", key=f"can_{task['id']}", use_container_width=True):
            db.set_task_response(task["id"], player["id"], "can")
            finish_action("Antwoord opgeslagen.")
        if col2.button("✕ Ik kan niet", key=f"cant_{task['id']}", use_container_width=True):
            st.session_state[f"cant_reason_{task['id']}"] = True
        if st.session_state.get(f"cant_reason_{task['id']}"):
            reason = st.text_input("Reden", key=f"cant_reason_text_{task['id']}")
            if st.button("Opslaan", key=f"cant_reason_save_{task['id']}", disabled=not reason):
                db.set_task_response(task["id"], player["id"], "cannot", reason)
                finish_action("Antwoord opgeslagen.")
    elif response == "cannot":
        st.warning(f"Kan niet — {mine['reason']}")
        col1, col2 = st.columns(2)
        if col1.button("✓ Toch wel kunnen", key=f"switch_can_{task['id']}", use_container_width=True):
            db.set_task_response(task["id"], player["id"], "can", "")
            finish_action("Antwoord opgeslagen.")
        if col2.button("✏️ Reden wijzigen", key=f"edit_reason_{task['id']}", use_container_width=True):
            st.session_state[f"edit_cant_{task['id']}"] = True
        if st.session_state.get(f"edit_cant_{task['id']}"):
            reason = st.text_input("Reden aanpassen", value=mine["reason"] or "", key=f"edit_cant_text_{task['id']}")
            if st.button("Wijziging opslaan", key=f"edit_cant_save_{task['id']}", disabled=not reason):
                db.set_task_response(task["id"], player["id"], "cannot", reason)
                finish_action("Wijziging opgeslagen.")
    else:
        st.success("Je hebt aangegeven dat je kunt.")
        col1, col2 = st.columns(2)
        if col1.button("✏️ Antwoord wijzigen", key=f"change_can_{task['id']}", use_container_width=True):
            st.session_state[f"change_can_{task['id']}"] = True
        if not mine["completed"] and col2.button("✓ Mijn deel klaar", key=f"done_{task['id']}", use_container_width=True):
            db.set_assignment_completed(task["id"], player["id"])
            finish_action("Taak afgerond opgeslagen.")
        if st.session_state.get(f"change_can_{task['id']}"):
            reason = st.text_input("Waarom kun je toch niet?", key=f"change_can_reason_{task['id']}")
            col3, col4 = st.columns(2)
            if col3.button("Opslaan als kan niet", key=f"change_can_save_{task['id']}", disabled=not reason, use_container_width=True):
                db.set_task_response(task["id"], player["id"], "cannot", reason)
                finish_action("Antwoord opgeslagen.")
            if col4.button("Annuleren", key=f"change_can_cancel_{task['id']}", use_container_width=True):
                st.session_state.pop(f"change_can_{task['id']}", None)
                st.rerun()


def login():
    render_page_title("TeamApp")
    st.caption("Kies je naam om in te loggen.")
    players = db.get_players()
    names = [entry["name"] for entry in players]
    name = st.selectbox("Wie ben je?", names, index=None, placeholder="Kies je naam", key="login_name")
    password = ""
    if name == "Beheerder":
        password = st.text_input("Wachtwoord beheerder", type="password", key="login_admin_password")
    if st.button("Inloggen", type="primary", use_container_width=True, disabled=name is None):
        if name == "Beheerder" and password != ADMIN_PASSWORD:
            st.error("Onjuist wachtwoord voor Beheerder.")
        else:
            st.session_state.player_id = next(entry["id"] for entry in players if entry["name"] == name)
            goto("Home")


if "player_id" not in st.session_state:
    try:
        saved = int(q("user")) if q("user") else None
    except Exception:
        saved = None
    if saved and db.get_player(saved):
        st.session_state.player_id = saved

if "player_id" not in st.session_state:
    login()
    st.stop()

player = db.get_player(st.session_state.player_id)
if not player:
    st.session_state.clear()
    st.query_params.clear()
    login()
    st.stop()

page = PAGE_ALIASES.get(q("page", "Home"), q("page", "Home"))
if page not in VALID_PAGES:
    page = "Home"
st.session_state.page = page

flash_message = st.session_state.pop("flash_message", None)
if flash_message:
    st.success(flash_message)

with st.sidebar:
    st.markdown(f'<div class="sidebar-name">{player["name"]}</div>', unsafe_allow_html=True)
    menu_items = [
        ("Home", "Home"),
        ("Teamrekening", "Teamrekening"),
        ("Agenda", "Agenda"),
        ("Ideeën", "Ideeën"),
        ("Ranglijst punten", "Ranglijst punten"),
        ("Activiteiten", "Activiteiten"),
        ("Meldingen", "Meldingen"),
    ]
    for label, page_name in menu_items:
        css_class = "sidebar-link active" if page == page_name else "sidebar-link"
        st.markdown(f'<a class="{css_class}" href="{nav_url(page_name)}" target="_self">{label}</a>', unsafe_allow_html=True)
    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
    subtle_class = "sidebar-link subtle active" if page == "Toevoegen" else "sidebar-link subtle"
    st.markdown(f'<a class="{subtle_class}" href="{nav_url("Toevoegen")}" target="_self">+ Activiteit toevoegen</a>', unsafe_allow_html=True)
    if is_admin(player):
        st.divider()
        for label, page_name in [("Wijzigingsverzoeken", "Wijzigingsverzoeken"), ("Instellingen", "Instellingen")]:
            css_class = "sidebar-link active" if page == page_name else "sidebar-link"
            st.markdown(f'<a class="{css_class}" href="{nav_url(page_name)}" target="_self">{label}</a>', unsafe_allow_html=True)
    st.divider()
    if st.button("Uitloggen", use_container_width=True, key="logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

lb = db.leaderboard()
my = next((entry for entry in lb if entry["id"] == player["id"]), None)
players = db.get_players()
player_names = [entry["name"] for entry in players]
player_name_to_id = {entry["name"]: entry["id"] for entry in players}

if page == "Home":
    render_page_title(f"Hoi {player['name']}")
    st.markdown('<div class="section">Komende taken voor jou</div>', unsafe_allow_html=True)
    mine_tasks = db.tasks_for_player(player["id"])[:3]
    if mine_tasks:
        for task in mine_tasks:
            task_card(task, personal=True)
    else:
        st.caption("Je hebt op dit moment geen komende taken.")

    st.markdown('<div class="section">Teaminfo</div>', unsafe_allow_html=True)
    money = db.money_summary(statuses=["approved"])
    st.markdown(
        f'<div class="soft"><b>Teamrekening</b><br><span class="muted">Huidig saldo</span><br><b>{format_euro(money["balance"])}</b></div>',
        unsafe_allow_html=True,
    )
    st.info("Volgende voor een verplichting: " + recommendation(lb))

    st.markdown('<div class="section">Teamstand</div>', unsafe_allow_html=True)
    for index, row in enumerate(lb[:5], 1):
        player_card(row, index, "home_player")

    col1, col2 = st.columns([3, 1])
    col1.markdown('<div class="section">Recente activiteiten</div>', unsafe_allow_html=True)
    if col2.button("Bekijk alles", key="recent_all", use_container_width=True):
        goto("Activiteiten", view="team")
    for activity in db.get_activities(limit=4):
        st.markdown(
            f'<div class="card">{activity["icon"]} <b>{activity["player_name"]}</b> · {activity["activity_name"]}'
            f'<span style="float:right"><b>+{activity["points"]}</b></span>'
            f'<br><span class="muted">{activity["activity_date"]} · {activity["description"] or ""}</span></div>',
            unsafe_allow_html=True,
        )

elif page == "Toevoegen":
    render_page_title("+ Activiteit toevoegen")
    tab_activity, tab_task, tab_idea, tab_folder = st.tabs(["Activiteit", "Taak", "Idee", "Map"])
    with tab_activity:
        activity_form()
    with tab_task:
        activity_types = db.get_activity_types()
        team_players = [entry for entry in players if entry["role"] == "player"]
        if not activity_types:
            st.warning("Er zijn nog geen activiteitstypes ingesteld voor taken.")
        else:
            title = st.text_input("Taaknaam", key="task_title")
            task_date = st.date_input("Datum", date.today(), key="task_date")
            task_time = st.text_input("Tijd", placeholder="18:30", key="task_time")
            labels = [f"{entry['icon']} {entry['name']}" for entry in activity_types]
            selected_label = st.selectbox("Activiteitstype", labels, key="task_type")
            activity_type = activity_types[labels.index(selected_label)]
            selected_people = st.multiselect("Toewijzen aan", [entry["name"] for entry in team_players], key="task_people")
            description = st.text_area("Beschrijving", key="task_desc")
            st.caption(f"Punten volgen automatisch het activiteitstype. Basispunten: {activity_type['base_points']}.")
            if st.button("Taak toevoegen", type="primary", disabled=not title, key="task_save"):
                db.add_task(
                    title,
                    task_date,
                    task_time,
                    activity_type["id"],
                    activity_type["category"],
                    description,
                    [entry["id"] for entry in team_players if entry["name"] in selected_people],
                )
                finish_action("Taak toegevoegd.", "Toevoegen")
    with tab_idea:
        folders = db.get_folders()
        if not folders:
            st.info("Maak eerst een brainstormmap aan via het tabblad Map.")
        else:
            labels = [f"{folder['icon']} {folder['name']}" for folder in folders]
            selected = st.selectbox("Map", labels, key="idea_folder")
            folder = folders[labels.index(selected)]
            title = st.text_input("Idee", key="idea_title")
            description = st.text_area("Uitleg", key="idea_desc")
            points = st.number_input("Voorstel voor punten", min_value=0.0, value=0.0, step=0.1, format="%.1f", key="idea_pts")
            if st.button("Idee plaatsen", type="primary", disabled=not title, key="idea_save"):
                db.add_idea(folder["id"], player["id"], title, description, points)
                finish_action("Idee toegevoegd.", "Toevoegen")
    with tab_folder:
        name = st.text_input("Naam brainstormmap", key="folder_name")
        icon = st.text_input("Icoon", value="📁", key="folder_icon")
        if st.button("Map maken", type="primary", disabled=not name, key="folder_save"):
            try:
                db.add_folder(name, icon, player["id"])
            except ValueError as exc:
                st.error(str(exc))
            else:
                finish_action("Map gemaakt.", "Toevoegen")

elif page == "Activiteiten":
    render_page_title("Activiteiten")
    default_scope = "Alle recente" if q("view") == "team" else "Mijn activiteiten"
    scope = st.segmented_control("Overzicht", ["Mijn activiteiten", "Alle recente"], default=default_scope, key="activity_scope")
    if scope == "Mijn activiteiten":
        st.caption("Nieuwe activiteiten staan direct in je overzicht en tellen direct mee.")
        activities = db.get_activities(player_id=player["id"])
        if not activities:
            st.info("Je hebt nog geen activiteiten toegevoegd.")
        for activity in activities:
            st.markdown(
                f'<div class="card">{activity["icon"]} <b>{activity["activity_name"]}</b>'
                f'<span style="float:right"><b>+{activity["points"]} pt</b></span>'
                f'<br><span class="muted">{activity["activity_date"]}</span><br>{activity["description"] or ""}</div>',
                unsafe_allow_html=True,
            )
            if st.button("Activiteit verwijderen", key=f"delete_own_activity_{activity['id']}", use_container_width=True):
                db.delete_activity(activity["id"])
                finish_action("Activiteit verwijderd.", "Activiteiten")
            with st.expander("Wijziging aanvragen"):
                text = st.text_area(
                    "Wat wil je wijzigen?",
                    key=f"chg_{activity['id']}",
                    placeholder="Bijv. aanwezigheid moet Hele dag zijn in plaats van Halve dag",
                )
                if st.button("Verzoek versturen", key=f"chg_btn_{activity['id']}", disabled=not text):
                    db.request_change(activity["id"], player["id"], text)
                    finish_action("Wijzigingsverzoek verstuurd.", "Activiteiten")
    else:
        st.caption("Alle recente activiteiten van het team.")
        team_activities = db.get_activities()
        for activity in team_activities:
            st.markdown(
                f'<div class="card">{activity["icon"]} <b>{activity["player_name"]}</b> · {activity["activity_name"]}'
                f'<span style="float:right"><b>+{activity["points"]}</b></span>'
                f'<br><span class="muted">{activity["activity_date"]}</span><br>{activity["description"] or ""}</div>',
                unsafe_allow_html=True,
            )
        if is_admin(player):
            st.markdown('<div class="section">Beheer alle activiteiten</div>', unsafe_allow_html=True)
            activity_types = db.get_activity_types(include_inactive=True)
            type_by_id = {entry["id"]: entry for entry in activity_types}
            type_labels = []
            for entry in activity_types:
                suffix = "" if entry["active"] else " (verborgen)"
                type_labels.append(f"{entry['icon']} {entry['name']}{suffix}")
            if not team_activities:
                st.caption("Er zijn nog geen activiteiten toegevoegd.")
            for activity in team_activities:
                current_values = json.loads(activity.get("field_values_json") or "{}")
                current_type_id = activity["activity_type_id"] if activity["activity_type_id"] in type_by_id else activity_types[0]["id"]
                current_index = next(index for index, entry in enumerate(activity_types) if entry["id"] == current_type_id)
                with st.expander(f"{activity['player_name']} · {activity['activity_name']} · {activity['activity_date']}", expanded=False):
                    selected_player = st.selectbox(
                        "Speler",
                        player_names,
                        index=player_names.index(activity["player_name"]) if activity["player_name"] in player_names else 0,
                        key=f"manage_activity_player_{activity['id']}",
                    )
                    selected_label = st.selectbox(
                        "Activiteitstype",
                        type_labels,
                        index=current_index,
                        key=f"manage_activity_type_{activity['id']}",
                    )
                    selected_type = activity_types[type_labels.index(selected_label)]
                    selected_fields = db.get_fields(selected_type["id"])
                    values = {}
                    computed_points = float(selected_type["base_points"])
                    for field in selected_fields:
                        options = field["options"]
                        option_labels = [f"{option['label']} · +{option['points']} pt" for option in options]
                        default_index = 0
                        for index, option in enumerate(options):
                            if current_values.get(field["label"]) == option["label"]:
                                default_index = index
                                break
                        chosen_label = st.selectbox(
                            field["label"],
                            option_labels,
                            index=default_index,
                            key=f"manage_activity_field_{activity['id']}_{field['id']}",
                        )
                        chosen_option = options[option_labels.index(chosen_label)]
                        values[field["label"]] = chosen_option["label"]
                        computed_points += float(chosen_option["points"])
                    activity_date = st.date_input(
                        "Datum",
                        value=pd.to_datetime(activity["activity_date"]).date(),
                        key=f"manage_activity_date_{activity['id']}",
                    )
                    description = st.text_area(
                        "Beschrijving",
                        value=activity["description"] or "",
                        key=f"manage_activity_desc_{activity['id']}",
                    )
                    points = st.number_input(
                        "Punten",
                        min_value=0.0,
                        value=float(activity["points"]),
                        step=0.1,
                        format="%.1f",
                        key=f"manage_activity_points_{activity['id']}",
                        help=f"Automatische berekening op basis van type en keuzes: {computed_points:.1f} punten",
                    )
                    if st.button("Activiteit opslaan", key=f"manage_activity_save_{activity['id']}", type="primary", use_container_width=True):
                        db.update_activity(
                            activity["id"],
                            player_name_to_id[selected_player],
                            selected_type["id"],
                            activity_date,
                            description,
                            values,
                            points,
                        )
                        finish_action("Activiteit bijgewerkt.", "Activiteiten", view="team")
                    if st.button("Activiteit verwijderen", key=f"manage_activity_delete_{activity['id']}", use_container_width=True):
                        db.delete_activity(activity["id"])
                        finish_action("Activiteit verwijderd.", "Activiteiten", view="team")

elif page == "Agenda":
    render_page_title("Agenda")
    who = st.segmented_control("Agenda", ["Mijn agenda", "Hele team"], default="Mijn agenda", key="agenda_scope")
    mode = st.segmented_control("Weergave", ["Lijst", "Kalender"], default="Lijst", key="agenda_mode")
    tasks = db.tasks_for_player(player["id"]) if who == "Mijn agenda" else db.get_tasks()
    if mode == "Lijst":
        if not tasks:
            st.info("Geen komende taken.")
        for task in tasks:
            task_card(task, personal=(who == "Mijn agenda"))
    else:
        st.session_state.setdefault("cal_month", date.today().month)
        st.session_state.setdefault("cal_year", date.today().year)
        col1, col2, col3 = st.columns([1, 3, 1])
        if col1.button("‹", key="cal_prev", use_container_width=True):
            month = st.session_state.cal_month - 1
            year = st.session_state.cal_year
            if month == 0:
                month = 12
                year -= 1
            st.session_state.cal_month = month
            st.session_state.cal_year = year
            st.rerun()
        col2.markdown(
            f"<h4 style='text-align:center'>{calendar.month_name[st.session_state.cal_month]} {st.session_state.cal_year}</h4>",
            unsafe_allow_html=True,
        )
        if col3.button("›", key="cal_next", use_container_width=True):
            month = st.session_state.cal_month + 1
            year = st.session_state.cal_year
            if month == 13:
                month = 1
                year += 1
            st.session_state.cal_month = month
            st.session_state.cal_year = year
            st.rerun()
        days = list(calendar.Calendar(firstweekday=0).itermonthdays(st.session_state.cal_year, st.session_state.cal_month))
        html = '<div class="calendar">' + "".join(f'<div class="calhead">{day}</div>' for day in ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"])
        for day in days:
            if day == 0:
                html += '<div class="day empty"></div>'
                continue
            day_string = f"{st.session_state.cal_year:04d}-{st.session_state.cal_month:02d}-{day:02d}"
            today_tasks = [task for task in tasks if task["task_date"] == day_string]
            dots = " ".join(CATEGORY.get(task["category"], ("", "🔹"))[1] for task in today_tasks[:4])
            html += f'<div class="day"><b>{day}</b><div class="dots">{dots}</div></div>'
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
        st.markdown('<div class="section">Taken deze maand</div>', unsafe_allow_html=True)
        for task in tasks:
            if task["task_date"].startswith(f"{st.session_state.cal_year:04d}-{st.session_state.cal_month:02d}"):
                task_card(task, personal=(who == "Mijn agenda"))

elif page == "Ideeën":
    render_page_title("Ideeën")
    folders = db.get_folders()
    folder_id = q("folder")
    if not folder_id:
        for folder in folders:
            if st.button(
                f"{folder['icon']} {folder['name']} · {folder['idea_count']} ideeën",
                use_container_width=True,
                key=f"folder_{folder['id']}",
            ):
                goto("Ideeën", folder=folder["id"])
        if st.button("+ Nieuwe map", key="show_new_folder", use_container_width=True):
            st.session_state["show_new_folder_form"] = not st.session_state.get("show_new_folder_form", False)
        if st.session_state.get("show_new_folder_form"):
            st.markdown('<div class="soft">', unsafe_allow_html=True)
            new_name = st.text_input("Naam van de nieuwe map", key="new_folder_name_inline")
            new_icon = st.text_input("Icoon", value="📁", key="new_folder_icon_inline")
            col1, col2 = st.columns(2)
            if col1.button("Map opslaan", key="new_folder_save_inline", disabled=not new_name, use_container_width=True):
                try:
                    db.add_folder(new_name, new_icon, player["id"])
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state["show_new_folder_form"] = False
                    finish_action("Map gemaakt.", "Ideeën")
            if col2.button("Annuleren", key="new_folder_cancel_inline", use_container_width=True):
                st.session_state["show_new_folder_form"] = False
                st.rerun()
    else:
        try:
            current_folder_id = int(folder_id)
        except Exception:
            current_folder_id = None
        folder = next((entry for entry in folders if entry["id"] == current_folder_id), None)
        if not folder:
            goto("Ideeën")
        if st.button("← Alle mappen", key="back_folders"):
            goto("Ideeën")
        st.markdown(f"### {folder['icon']} {folder['name']}")
        st.caption("Ideeën zijn standaard ingeklapt. Open een idee voor details, stemmen en reacties.")
        for idea in db.get_ideas(folder["id"], viewer_id=player["id"]):
            label = f"{idea['title']}   ·   Score {idea['net_score']}   ·   👍 {idea['likes']}   ·   👎 {idea['dislikes']}   ·   💬 {len(idea['comments'])}"
            with st.expander(label, expanded=False):
                st.markdown(
                    f'<div class="idea-meta"><span class="badge">{idea["status"]}</span><span class="score-badge">Score {idea["net_score"]}</span></div>',
                    unsafe_allow_html=True,
                )
                st.caption(f"door {idea['author_name']}")
                if idea["description"]:
                    st.write(idea["description"])
                col1, col2 = st.columns(2)
                up_type = "primary" if idea["current_vote"] == 1 else "secondary"
                down_type = "primary" if idea["current_vote"] == -1 else "secondary"
                if col1.button(f"👍 {idea['likes']}", key=f"vote_up_{idea['id']}", type=up_type, use_container_width=True):
                    db.cast_idea_vote(idea["id"], player["id"], 1)
                    finish_action("Stem opgeslagen.", "Ideeën", folder=folder["id"])
                if col2.button(f"👎 {idea['dislikes']}", key=f"vote_down_{idea['id']}", type=down_type, use_container_width=True):
                    db.cast_idea_vote(idea["id"], player["id"], -1)
                    finish_action("Stem opgeslagen.", "Ideeën", folder=folder["id"])
                st.markdown(f"**Puntenvoorstel:** {idea['points_suggestion'] or 0}")
                st.markdown('<div class="subsection-title">Reacties</div>', unsafe_allow_html=True)
                if not idea["comments"]:
                    st.caption("Nog geen reacties.")
                for comment in idea["comments"]:
                    st.markdown(f"**{comment['player_name']}**  \n{comment['body']}")
                body = st.text_input("Reageer", key=f"comment_{idea['id']}")
                if st.button("Plaatsen", key=f"comment_btn_{idea['id']}", disabled=not body):
                    db.add_comment(idea["id"], player["id"], body)
                    finish_action("Reactie geplaatst.", "Ideeën", folder=folder["id"])
                if is_admin(player):
                    statuses = ["Nieuw idee", "In bespreking", "Gekozen", "Uitgevoerd", "Geparkeerd", "Niet uitvoeren"]
                    current_index = statuses.index(idea["status"]) if idea["status"] in statuses else 0
                    status = st.selectbox("Status", statuses, index=current_index, key=f"status_{idea['id']}")
                    if st.button("Status opslaan", key=f"status_btn_{idea['id']}"):
                        db.set_idea_status(idea["id"], status)
                        finish_action("Ideestatus opgeslagen.", "Ideeën", folder=folder["id"])

        if st.button("+ Idee toevoegen", key=f"show_add_idea_{folder['id']}", use_container_width=True):
            state_key = f"show_add_idea_form_{folder['id']}"
            st.session_state[state_key] = not st.session_state.get(state_key, False)
        if st.session_state.get(f"show_add_idea_form_{folder['id']}"):
            title = st.text_input("Titel van het idee", key=f"folder_idea_title_{folder['id']}")
            description = st.text_area("Beschrijving", key=f"folder_idea_desc_{folder['id']}")
            points = st.number_input( "Voorstel voor punten", min_value=0.0, value=0.0, step=0.1, format="%.1f", key=f"folder_idea_points_{folder['id']}")
            col1, col2 = st.columns(2)
            if col1.button("Idee opslaan", key=f"folder_idea_save_{folder['id']}", disabled=not title, use_container_width=True):
                db.add_idea(folder["id"], player["id"], title, description, points)
                st.session_state[f"show_add_idea_form_{folder['id']}"] = False
                finish_action("Idee toegevoegd.", "Ideeën", folder=folder["id"])
            if col2.button("Annuleren", key=f"folder_idea_cancel_{folder['id']}", use_container_width=True):
                st.session_state[f"show_add_idea_form_{folder['id']}"] = False
                st.rerun()

elif page == "Ranglijst punten":
    render_page_title("Ranglijst punten")
    view = st.segmented_control("Weergave", ["Balken", "Spelercards"], default="Balken", key="rank_view")
    if view == "Balken" and lb:
        dataframe = pd.DataFrame(lb)
        dataframe["label"] = [f"{idx}. {name}" for idx, name in enumerate(dataframe.name, 1)]
        bars = (
            alt.Chart(dataframe)
            .mark_bar(cornerRadiusEnd=8, height=25)
            .encode(
                x=alt.X("points:Q", axis=None, title=None),
                y=alt.Y("label:N", sort=dataframe.label.tolist(), title=None),
                color=alt.value("#6EA6F8"),
                tooltip=["name", "points", "activities"],
            )
        )
        text = bars.mark_text(align="left", dx=7, fontWeight="bold").encode(text="points:Q", color=alt.value("#254360"))
        st.altair_chart((bars + text).properties(height=max(180, len(dataframe) * 40)), use_container_width=True)
        st.caption("Kies Spelercards om op een speler te kunnen tikken.")
    else:
        st.caption("Tik op een speler voor een popup met de punten en activiteiten.")
        for index, row in enumerate(lb, 1):
            player_card(row, index, "rank_player")
    st.info(recommendation(lb))

elif page == "Profiel":
    render_page_title(player["name"])
    points = my["points"] if my else 0
    rank = lb.index(my) + 1 if my in lb else "—"
    activities = my["activities"] if my else 0
    metric_strip(points, rank, activities)
    st.markdown('<div class="section">Mijn bijdrage</div>', unsafe_allow_html=True)
    for row in db.breakdown(player["id"]):
        if row["count"]:
            st.markdown(
                f'<div class="card">{row["icon"]} <b>{row["name"]}</b><span style="float:right"><b>{row["points"]} pt</b></span>'
                f'<br><span class="muted">{row["count"]}×</span></div>',
                unsafe_allow_html=True,
            )
    st.markdown('<div class="section">Taakhistorie</div>', unsafe_allow_html=True)
    for task in db.tasks_for_player(player["id"], include_past=True)[:8]:
        task_card(task)

elif page == "Meldingen":
    render_page_title("Meldingen")
    notices = db.notifications(player["id"])
    if not notices:
        st.info("Geen meldingen.")
    for notice in notices:
        st.markdown(
            f'<div class="card"><b>{notice["text"]}</b><br><span class="muted">{notice["created_at"]}</span></div>',
            unsafe_allow_html=True,
        )

elif page == "Teamrekening":
    render_page_title("Teamrekening")
    approved_summary = db.money_summary(statuses=["approved"])
    monthly_rows = db.get_monthly_financials(statuses=["approved"])
    balance_history = db.get_balance_history(statuses=["approved"])
    tab_names = ["Overzicht", "Uitgave toevoegen", "Inkomst toevoegen"]
    if can_review_expenses(player):
        tab_names.extend(["Financieel beheer", "Te controleren uitgaven"])
    tabs = st.tabs(tab_names)

    with tabs[0]:
        view = st.segmented_control("Overzicht", ["Maandelijks", "Totaal"], default="Maandelijks", key="money_view_mode")
        if view == "Maandelijks":
            if monthly_rows:
                options = list(reversed([row["month_key"] for row in monthly_rows]))
                selected_month = st.selectbox("Maand", options, key="money_month_select")
                current = next(row for row in monthly_rows if row["month_key"] == selected_month)
                finance_metric_strip(format_euro(current["balance"]), format_euro(current["income"]), format_euro(current["expense"]))
                monthly_frame = pd.DataFrame(monthly_rows)
                monthly_frame["month"] = pd.to_datetime(monthly_frame["month_key"] + "-01")
                chart_frame = monthly_frame.rename(
                    columns={"income": "Inkomsten", "expense": "Uitgaven", "balance": "Saldo"}
                )[["month", "Inkomsten", "Uitgaven", "Saldo"]]
                chart_frame = chart_frame.melt("month", var_name="Serie", value_name="Bedrag")
                st.altair_chart(
                    money_line_chart(
                        chart_frame,
                        "month:T",
                        "Serie:N",
                        "Bedrag:Q",
                        [alt.Tooltip("month:T", title="Maand"), "Serie:N", alt.Tooltip("Bedrag:Q", format=".2f")],
                    ),
                    use_container_width=True,
                )
            else:
                st.info("Er zijn nog geen goedgekeurde transacties om een maandoverzicht te tonen.")
        else:
            finance_metric_strip(format_euro(approved_summary["balance"]), format_euro(approved_summary["income"]), format_euro(approved_summary["expense"]))
            if balance_history:
                history_frame = pd.DataFrame(balance_history)
                history_frame["transaction_date"] = pd.to_datetime(history_frame["transaction_date"])
                st.altair_chart(
                    single_line_chart(
                        history_frame,
                        "transaction_date:T",
                        "balance:Q",
                        color="#2F6FED",
                        tooltip_fields=[
                            alt.Tooltip("transaction_date:T", title="Datum"),
                            "description:N",
                            alt.Tooltip("signed_amount:Q", title="Mutatie", format=".2f"),
                            alt.Tooltip("balance:Q", title="Saldo", format=".2f"),
                        ],
                    ),
                    use_container_width=True,
                )
            else:
                st.info("Er zijn nog geen goedgekeurde transacties om een totaaloverzicht te tonen.")

        st.markdown('<div class="section">Recente goedgekeurde transacties</div>', unsafe_allow_html=True)
        approved_transactions = db.get_transactions(limit=8, statuses=["approved"])
        if not approved_transactions:
            st.caption("Nog geen goedgekeurde transacties.")
        for transaction in approved_transactions:
            render_transaction_card(transaction, show_receipt=False)

        st.markdown('<div class="section">Mijn ingediende uitgaven</div>', unsafe_allow_html=True)
        own_expenses = db.get_transactions(transaction_type="expense", submitted_by=player["id"], statuses=["pending", "approved"])
        if not own_expenses:
            st.caption("Je hebt nog geen uitgaven ingediend.")
        for transaction in own_expenses:
            render_transaction_card(transaction, show_receipt=False)
            if st.button("Uitgave verwijderen", key=f"delete_own_expense_{transaction['id']}", use_container_width=True):
                db.delete_transaction(transaction["id"])
                finish_action("Uitgave verwijderd.", "Teamrekening")

    with tabs[1]:
        expense_date = st.date_input("Datum", date.today(), key="money_expense_date")
        amount = st.number_input("Bedrag (€)", min_value=0.0, step=1.0, key="money_expense_amount")
        description = st.text_input("Omschrijving", key="money_expense_desc")
        category = st.text_input("Categorie", placeholder="Bijv. boodschappen, materiaal, teamactiviteit", key="money_expense_category")
        default_index = player_names.index(player["name"]) if player["name"] in player_names else 0
        paid_by_name = st.selectbox("Betaald door", player_names, index=default_index, key="money_expense_paid_by")
        receipt_choice = st.radio("Bonnetje", ["Ik heb een bonnetje", "Bonnetje kwijt"], horizontal=True, key="money_expense_receipt")
        upload = None
        if receipt_choice == "Ik heb een bonnetje":
            upload = st.file_uploader("Upload bonnetje", type=["png", "jpg", "jpeg", "pdf"], key="money_expense_upload")
        if st.button("Uitgave indienen", type="primary", use_container_width=True, key="money_expense_save"):
            if amount <= 0 or not description or not category:
                st.error("Vul datum, bedrag, omschrijving en categorie in.")
            elif receipt_choice == "Ik heb een bonnetje" and upload is None:
                st.error("Upload een bonnetje of kies 'Bonnetje kwijt'.")
            else:
                receipt_status = "uploaded" if receipt_choice == "Ik heb een bonnetje" else "lost"
                db.add_transaction(
                    "expense",
                    expense_date,
                    amount,
                    category,
                    description,
                    player_name_to_id[paid_by_name],
                    submitted_by_player_id=player["id"],
                    receipt_status=receipt_status,
                    receipt_name=upload.name if upload else None,
                    receipt_data=upload.getvalue() if upload else None,
                    review_status="pending",
                )
                finish_action("Uitgave ingediend. Kieft of Beheerder kan deze nu controleren.", "Teamrekening")

    with tabs[2]:
        income_date = st.date_input("Datum", date.today(), key="money_income_date")
        amount = st.number_input("Bedrag (€)", min_value=0.0, step=1.0, key="money_income_amount")
        category = st.text_input("Categorie", placeholder="Bijv. sponsor, verkoop, actie", key="money_income_category")
        description = st.text_input("Waar komt het bedrag vandaan?", key="money_income_desc")
        paid_by_name = st.selectbox("Ontvangen door", player_names, index=0, key="money_income_paid_by")
        if st.button("Inkomst opslaan", type="primary", use_container_width=True, key="money_income_save"):
            if amount <= 0 or not description:
                st.error("Vul minimaal bedrag en omschrijving in.")
            else:
                db.add_transaction(
                    "income",
                    income_date,
                    amount,
                    category,
                    description,
                    player_name_to_id[paid_by_name],
                    submitted_by_player_id=player["id"],
                    review_status="approved",
                )
                finish_action("Inkomst opgeslagen.", "Teamrekening")

    if can_review_expenses(player):
        with tabs[3]:
            all_finance_rows = db.get_transactions(statuses=["pending", "approved"], include_receipt_data=True)
            export_modes = ["Maand", "Jaar", "Totaal"]
            month_options = sorted({row["transaction_date"][:7] for row in all_finance_rows}, reverse=True)
            year_options = sorted({row["transaction_date"][:4] for row in all_finance_rows}, reverse=True)
            st.markdown('<div class="section">Downloads en bonnetjes</div>', unsafe_allow_html=True)
            export_mode = st.segmented_control("Download overzicht", export_modes, default="Maand", key="finance_export_mode")
            selected_month = None
            selected_year = None
            if export_mode == "Maand":
                if month_options:
                    selected_month = st.selectbox("Maand", month_options, key="finance_export_month")
                else:
                    st.caption("Nog geen transacties om per maand te downloaden.")
            elif export_mode == "Jaar":
                if year_options:
                    selected_year = st.selectbox("Jaar", year_options, key="finance_export_year")
                else:
                    st.caption("Nog geen transacties om per jaar te downloaden.")
            filtered_rows = filter_transactions_for_period(all_finance_rows, export_mode, selected_month, selected_year)
            export_frame = build_transactions_export(filtered_rows)
            file_suffix = selected_month or selected_year or "totaal"
            if not export_frame.empty:
                st.download_button(
                    "Download overzicht (CSV)",
                    data=export_frame.to_csv(index=False).encode("utf-8"),
                    file_name=f"teamrekening_overzicht_{file_suffix}.csv",
                    mime="text/csv",
                    key="finance_export_csv",
                    use_container_width=True,
                )
                receipts_zip = build_receipts_zip(filtered_rows)
                if receipts_zip:
                    st.download_button(
                        "Download bonnetjes (ZIP)",
                        data=receipts_zip,
                        file_name=f"teamrekening_bonnetjes_{file_suffix}.zip",
                        mime="application/zip",
                        key="finance_export_zip",
                        use_container_width=True,
                    )
                else:
                    st.caption("Geen bonnetjes beschikbaar in deze selectie.")
                st.dataframe(export_frame, use_container_width=True, hide_index=True)
            else:
                st.info("Geen transacties in deze selectie.")

            st.markdown('<div class="section">Alle bonnetjes</div>', unsafe_allow_html=True)
            receipt_rows = [row for row in all_finance_rows if row["transaction_type"] == "expense"]
            if not receipt_rows:
                st.caption("Er zijn nog geen uitgaven toegevoegd.")
            for transaction in receipt_rows:
                st.markdown(
                    f'<div class="card"><b>{transaction["description"]}</b>'
                    f'<span style="float:right"><b>{format_euro(transaction["amount"])}</b></span>'
                    f'<br><span class="muted">{transaction["transaction_date"]} · {transaction.get("category") or "Overig"} · {transaction.get("paid_by_name") or "Onbekend"}</span>'
                    f'<br><span class="muted">{receipt_label(transaction.get("receipt_status"))}</span>'
                    f'<br>{badge_status(transaction.get("review_status") or "approved")}</div>',
                    unsafe_allow_html=True,
                )
                if transaction.get("receipt_data"):
                    st.download_button(
                        "Bonnetje bekijken",
                        data=transaction["receipt_data"],
                        file_name=transaction.get("receipt_name") or f"bonnetje-{transaction['id']}",
                        mime=guess_mime(transaction.get("receipt_name")),
                        key=f"receipt_overview_{transaction['id']}",
                        use_container_width=True,
                    )
                else:
                    st.caption("Geen bestand geüpload.")

        with tabs[4]:
            st.markdown('<div class="section">Te controleren uitgaven</div>', unsafe_allow_html=True)
            filter_choice = st.segmented_control("Controlelijst", ["Te controleren", "Alles"], default="Te controleren", key="review_filter")
            statuses = ["pending"] if filter_choice == "Te controleren" else ["pending", "approved"]
            review_items = db.get_transactions(transaction_type="expense", statuses=statuses, include_receipt_data=True)
            if not review_items:
                st.info("Geen uitgaven in deze lijst.")
            for transaction in review_items:
                st.markdown(
                    (
                        f'<div class="card"><b>{transaction["submitted_by_name"] or transaction["paid_by_name"]}</b>'
                        f' · {transaction["description"]}'
                        f'<span style="float:right"><b>{format_euro(transaction["amount"])}</b></span>'
                        f'<br><span class="muted">{transaction["transaction_date"]} · {transaction["category"] or "Overig"} · betaald door {transaction["paid_by_name"] or "Onbekend"}</span>'
                        f'<br><span class="muted">{receipt_label(transaction.get("receipt_status"))}</span>'
                        f'<br>{badge_status(transaction["review_status"])}</div>'
                    ),
                    unsafe_allow_html=True,
                )
                if transaction.get("receipt_data"):
                    st.download_button(
                        "Bonnetje openen",
                        data=transaction["receipt_data"],
                        file_name=transaction.get("receipt_name") or f"bonnetje-{transaction['id']}",
                        mime=guess_mime(transaction.get("receipt_name")),
                        key=f"review_receipt_open_{transaction['id']}",
                        use_container_width=True,
                    )
                col1, col2 = st.columns(2)
                if col1.button("Accepteren", key=f"approve_tx_{transaction['id']}", use_container_width=True):
                    db.set_transaction_review(transaction["id"], "approved", player["id"])
                    finish_action("Uitgave goedgekeurd.", "Teamrekening")
                if col2.button("Afwijzen", key=f"reject_tx_{transaction['id']}", use_container_width=True):
                    db.set_transaction_review(transaction["id"], "rejected", player["id"])
                    finish_action("Uitgave afgewezen.", "Teamrekening")
                with st.expander(f"Bewerken · {transaction['description']}", expanded=False):
                    review_date = st.date_input("Datum", value=pd.to_datetime(transaction["transaction_date"]).date(), key=f"review_date_{transaction['id']}")
                    review_amount = st.number_input("Bedrag (€)", min_value=0.0, value=float(transaction["amount"]), key=f"review_amount_{transaction['id']}")
                    review_description = st.text_input("Omschrijving", value=transaction["description"], key=f"review_desc_{transaction['id']}")
                    review_category = st.text_input("Categorie", value=transaction["category"] or "", key=f"review_cat_{transaction['id']}")
                    current_paid_by = transaction["paid_by_name"] if transaction["paid_by_name"] in player_names else player_names[0]
                    review_paid_by = st.selectbox("Betaald door", player_names, index=player_names.index(current_paid_by), key=f"review_paid_{transaction['id']}")
                    receipt_default = "Ik heb een bonnetje" if transaction.get("receipt_status") == "uploaded" else "Bonnetje kwijt"
                    review_receipt_choice = st.radio(
                        "Bonnetje",
                        ["Ik heb een bonnetje", "Bonnetje kwijt"],
                        horizontal=True,
                        index=0 if receipt_default == "Ik heb een bonnetje" else 1,
                        key=f"review_receipt_{transaction['id']}",
                    )
                    if transaction.get("receipt_data"):
                        st.download_button(
                            "Bonnetje bekijken",
                            data=transaction["receipt_data"],
                            file_name=transaction.get("receipt_name") or f"bonnetje-{transaction['id']}",
                            mime=guess_mime(transaction.get("receipt_name")),
                            key=f"review_receipt_download_{transaction['id']}",
                            use_container_width=True,
                        )
                    replacement_upload = None
                    if review_receipt_choice == "Ik heb een bonnetje":
                        replacement_upload = st.file_uploader(
                            "Nieuw bonnetje uploaden (optioneel)",
                            type=["png", "jpg", "jpeg", "pdf"],
                            key=f"review_upload_{transaction['id']}",
                        )
                    review_status = st.selectbox(
                        "Status",
                        ["pending", "approved", "rejected"],
                        index=["pending", "approved", "rejected"].index(transaction["review_status"]),
                        format_func=format_status,
                        key=f"review_status_{transaction['id']}",
                    )
                    if st.button("Wijzigingen opslaan", key=f"review_save_{transaction['id']}", type="primary", use_container_width=True):
                        try:
                            db.update_transaction(
                                transaction["id"],
                                review_date,
                                review_amount,
                                review_category,
                                review_description,
                                player_name_to_id[review_paid_by],
                                receipt_status="uploaded" if review_receipt_choice == "Ik heb een bonnetje" else "lost",
                                receipt_name=replacement_upload.name if replacement_upload else None,
                                receipt_data=replacement_upload.getvalue() if replacement_upload else None,
                                review_status=review_status,
                                reviewer_id=player["id"],
                            )
                        except ValueError as exc:
                            st.error(str(exc))
                        else:
                            finish_action("Uitgave bijgewerkt.", "Teamrekening")

elif page == "Wijzigingsverzoeken" and is_admin(player):
    render_page_title("Wijzigingsverzoeken")
    requests = db.get_change_requests()
    if not requests:
        st.info("Geen openstaande verzoeken.")
    for request in requests:
        st.markdown(
            f'<div class="card"><b>{request["player_name"]}</b> · {request["activity_name"]}'
            f'<br><span class="muted">{request["activity_date"]}</span><p>{request["request_text"]}</p></div>',
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        if col1.button("Goedkeuren", key=f"approve_{request['id']}", use_container_width=True):
            db.resolve_change_request(request["id"], "approved")
            finish_action("Wijzigingsverzoek goedgekeurd.", "Wijzigingsverzoeken")
        if col2.button("Afwijzen", key=f"reject_{request['id']}", use_container_width=True):
            db.resolve_change_request(request["id"], "rejected")
            finish_action("Wijzigingsverzoek afgewezen.", "Wijzigingsverzoeken")

elif page == "Instellingen" and is_admin(player):
    render_page_title("Activiteiten instellen")
    st.caption("Een activiteit kan alleen basispunten hebben, of één of meerdere zelfgemaakte keuzevelden met extra punten.")
    for activity_type in db.get_activity_types():
        with st.expander(f"{activity_type['icon']} {activity_type['name']} · {activity_type['base_points']} basispunten"):
            points = st.number_input("Basispunten", min_value=0.0, value=float(activity_type["base_points"]),step=0.1,format="%.1f",key=f"base_{activity_type['id']}")
            if st.button("Basispunten opslaan", key=f"base_save_{activity_type['id']}"):
                db.update_activity_base_points(activity_type["id"], points)
                finish_action("Basispunten opgeslagen.", "Instellingen")
            fields = db.get_fields(activity_type["id"])
            for field in fields:
                st.markdown(f"**{field['label']}**")
                edit_label = st.text_input("Veldnaam", value=field["label"], key=f"edit_field_label_{field['id']}")
                option_rows = []
                existing_options = field["options"] or []
                option_count = max(1, len(existing_options))
                for index in range(option_count):
                    option = existing_options[index] if index < len(existing_options) else {"label": "", "points": 0}
                    col1, col2 = st.columns([2, 1])
                    option_name = col1.text_input(
                        f"Optie {index + 1}",
                        value=option["label"],
                        key=f"edit_field_option_name_{field['id']}_{index}",
                    )
                    option_points = col2.number_input(
                        "Punten",
                        min_value=0.0,
                        value=float(option["points"]),
                        step=0.1,
                        format="%.1f",
                        key=f"edit_field_option_points_{field['id']}_{index}",
                    )
                    option_rows.append((option_name, option_points))
                col1, col2 = st.columns(2)
                if col1.button("Keuzeveld opslaan", key=f"save_field_{field['id']}", use_container_width=True):
                    valid_options = [(name, points) for name, points in option_rows if str(name).strip()]
                    if not edit_label or not valid_options:
                        st.error("Vul een veldnaam en minimaal één optie in.")
                    else:
                        db.update_select_field(field["id"], edit_label, valid_options)
                        finish_action("Keuzeveld bijgewerkt.", "Instellingen")
                if col2.button("Keuzeveld verwijderen", key=f"delete_field_{field['id']}", use_container_width=True):
                    db.delete_select_field(field["id"])
                    finish_action("Keuzeveld verwijderd.", "Instellingen")
            st.markdown("**+ Eigen keuzeveld toevoegen**")
            label = st.text_input("Onderwerp / veldnaam", placeholder="Bijv. Aanwezigheid", key=f"new_field_{activity_type['id']}")
            count = st.number_input("Aantal opties", min_value=1, max_value=6, value=2, key=f"opt_count_{activity_type['id']}")
            options = []
            for index in range(int(count)):
                col1, col2 = st.columns([2, 1])
                name = col1.text_input(f"Optie {index + 1}", key=f"opt_name_{activity_type['id']}_{index}")
                option_points = col2.number_input( "Punten", min_value=0.0, value=0.0, step=0.1, format="%.1f", key=f"opt_pts_{activity_type['id']}_{index}")
                options.append((name, option_points))
            if st.button(
                "Veld toevoegen",
                key=f"field_add_{activity_type['id']}",
                disabled=not label or any(not name for name, _ in options),
            ):
                db.add_select_field(activity_type["id"], label, options)
                finish_action("Keuzeveld toegevoegd.", "Instellingen")
            if st.button("Activiteitstype verwijderen", key=f"delete_type_{activity_type['id']}", use_container_width=True):
                try:
                    db.delete_activity_type(activity_type["id"])
                except Exception as exc:
                    st.error(f"Verwijderen mislukt: {exc}")
                else:
                    finish_action("Activiteitstype verwijderd.", "Instellingen")
    st.divider()
    st.markdown("### Nieuw activiteitstype")
    name = st.text_input("Naam", key="new_type_name")
    icon = st.text_input("Icoon", value="⭐", key="new_type_icon")
    category = st.selectbox("Categorie", ["training", "fluiten", "team", "geld", "club"], key="new_type_category")
    base = st.number_input("Basispunten", min_value=0.0, value=0.0, step=0.1, format="%.1f",key="new_type_base")
    if st.button("Activiteitstype toevoegen", type="primary", disabled=not name, key="new_type_save"):
        try:
            db.add_activity_type(name, icon, category, base)
        except ValueError as exc:
            st.error(str(exc))
        else:
            finish_action("Activiteitstype toegevoegd.", "Instellingen")
    st.divider()
    st.markdown("### Taken beheren")
    activity_types = db.get_activity_types()
    task_types = {entry["id"]: entry for entry in activity_types}
    team_players = [entry for entry in players if entry["role"] == "player"]
    tasks = db.get_tasks(include_past=True)
    if not tasks:
        st.caption("Er zijn nog geen taken toegevoegd.")
    for task in tasks:
        assigned_names = [assignment["name"] for assignment in task["assignments"]]
        with st.expander(f"{task['title']} · {task['task_date']} · {', '.join(assigned_names) or 'Geen spelers'}", expanded=False):
            title = st.text_input("Taaknaam", value=task["title"], key=f"manage_task_title_{task['id']}")
            task_date = st.date_input("Datum", value=pd.to_datetime(task["task_date"]).date(), key=f"manage_task_date_{task['id']}")
            task_time = st.text_input("Tijd", value=task["task_time"] or "", key=f"manage_task_time_{task['id']}")
            if activity_types:
                type_labels = [f"{entry['icon']} {entry['name']}" for entry in activity_types]
                current_type_id = task["activity_type_id"] if task["activity_type_id"] in task_types else activity_types[0]["id"]
                current_index = next(index for index, entry in enumerate(activity_types) if entry["id"] == current_type_id)
                selected_label = st.selectbox("Activiteitstype", type_labels, index=current_index, key=f"manage_task_type_{task['id']}")
                selected_type = activity_types[type_labels.index(selected_label)]
                category = selected_type["category"]
                type_id = selected_type["id"]
            else:
                st.warning("Er zijn geen activiteitstypes beschikbaar.")
                category = task["category"]
                type_id = task["activity_type_id"]
            selected_people = st.multiselect(
                "Toewijzen aan",
                [entry["name"] for entry in team_players],
                default=assigned_names,
                key=f"manage_task_people_{task['id']}",
            )
            description = st.text_area("Beschrijving", value=task["description"] or "", key=f"manage_task_desc_{task['id']}")
            col1, col2 = st.columns(2)
            if col1.button("Taak opslaan", key=f"manage_task_save_{task['id']}", type="primary", use_container_width=True):
                db.update_task(
                    task["id"],
                    title,
                    task_date,
                    task_time,
                    type_id,
                    category,
                    description,
                    [entry["id"] for entry in team_players if entry["name"] in selected_people],
                )
                finish_action("Taak bijgewerkt.", "Instellingen")
            if col2.button("Taak verwijderen", key=f"manage_task_delete_{task['id']}", use_container_width=True):
                db.delete_task(task["id"])
                finish_action("Taak verwijderd.", "Instellingen")
