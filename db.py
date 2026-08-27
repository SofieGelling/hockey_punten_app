import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).with_name("teamapp_v2_5.db")


@contextmanager
def connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def rows(cur):
    return [dict(r) for r in cur.fetchall()]


def clean_text(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def timestamp_now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def ensure_column(con, table_name, column_name, definition):
    columns = {row["name"] for row in con.execute("PRAGMA table_info(%s)" % table_name)}
    if column_name not in columns:
        con.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table_name, column_name, definition))


def init_db():
    with connection() as con:
        con.executescript(
            """
        CREATE TABLE IF NOT EXISTS players(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'player',
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS activity_types(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            icon TEXT NOT NULL DEFAULT '⭐',
            category TEXT NOT NULL DEFAULT 'team',
            base_points INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS activity_fields(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_type_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            field_type TEXT NOT NULL DEFAULT 'select'
        );
        CREATE TABLE IF NOT EXISTS activity_field_options(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            points INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS activities(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            activity_type_id INTEGER NOT NULL,
            activity_date TEXT NOT NULL,
            description TEXT,
            field_values_json TEXT,
            points INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS activity_change_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            requested_by INTEGER NOT NULL,
            request_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            task_date TEXT NOT NULL,
            task_time TEXT,
            activity_type_id INTEGER,
            category TEXT NOT NULL DEFAULT 'team',
            description TEXT,
            completed INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS task_assignments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            response TEXT NOT NULL DEFAULT 'pending',
            reason TEXT,
            completed INTEGER NOT NULL DEFAULT 0,
            present INTEGER,
            UNIQUE(task_id, player_id)
        );
        CREATE TABLE IF NOT EXISTS brainstorm_folders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            icon TEXT NOT NULL DEFAULT '📁',
            created_by INTEGER
        );
        CREATE TABLE IF NOT EXISTS ideas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            points_suggestion INTEGER,
            status TEXT NOT NULL DEFAULT 'Nieuw idee',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS idea_votes(
            idea_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            vote INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY(idea_id, player_id)
        );
        CREATE TABLE IF NOT EXISTS idea_comments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notifications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS team_transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_type TEXT NOT NULL,
            transaction_date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT,
            description TEXT NOT NULL,
            player_id INTEGER,
            submitted_by INTEGER,
            receipt_status TEXT,
            receipt_name TEXT,
            receipt_data BLOB,
            review_status TEXT NOT NULL DEFAULT 'approved',
            reviewed_by INTEGER,
            reviewed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
        )

        ensure_column(con, "activities", "field_values_json", "TEXT")
        ensure_column(con, "activities", "points", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(con, "tasks", "activity_type_id", "INTEGER")
        ensure_column(con, "tasks", "category", "TEXT NOT NULL DEFAULT 'team'")
        ensure_column(con, "tasks", "description", "TEXT")
        ensure_column(con, "tasks", "completed", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(con, "task_assignments", "reason", "TEXT")
        ensure_column(con, "task_assignments", "completed", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(con, "task_assignments", "present", "INTEGER")
        ensure_column(con, "ideas", "status", "TEXT NOT NULL DEFAULT 'Nieuw idee'")
        ensure_column(con, "idea_votes", "vote", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(con, "team_transactions", "submitted_by", "INTEGER")
        ensure_column(con, "team_transactions", "receipt_status", "TEXT")
        ensure_column(con, "team_transactions", "receipt_name", "TEXT")
        ensure_column(con, "team_transactions", "receipt_data", "BLOB")
        ensure_column(con, "team_transactions", "review_status", "TEXT NOT NULL DEFAULT 'approved'")
        ensure_column(con, "team_transactions", "reviewed_by", "INTEGER")
        ensure_column(con, "team_transactions", "reviewed_at", "TEXT")

        con.execute("UPDATE idea_votes SET vote=1 WHERE vote IS NULL OR vote NOT IN (-1,1)")
        con.execute("UPDATE team_transactions SET submitted_by=COALESCE(submitted_by, player_id)")
        con.execute(
            """
            UPDATE team_transactions
            SET review_status='approved'
            WHERE review_status IS NULL OR review_status=''
            """
        )
        con.execute(
            """
            UPDATE team_transactions
            SET receipt_status=''
            WHERE transaction_type='income' AND receipt_status='none'
            """
        )
        con.execute(
            """
            UPDATE team_transactions
            SET receipt_status='lost'
            WHERE transaction_type='expense' AND (receipt_status IS NULL OR receipt_status='' OR receipt_status='none')
            """
        )

        if con.execute("SELECT COUNT(*) n FROM players").fetchone()["n"] == 0:
            names = [
                "Sofie",
                "Jade",
                "Leanne",
                "Juul",
                "Jasmijn",
                "Anna",
                "Robin",
                "Kieft",
                "Kelsi",
                "Nienke",
                "Melany",
                "Jette",
                "Kathelijn",
                "Klaartje",
            ]
            con.execute("INSERT INTO players(name,role) VALUES(?,?)", ("Beheerder", "admin"))
            con.executemany("INSERT INTO players(name,role) VALUES(?,?)", [(n, "player") for n in names])

        if con.execute("SELECT COUNT(*) n FROM activity_types").fetchone()["n"] == 0:
            con.executemany(
                "INSERT INTO activity_types(name,icon,category,base_points) VALUES(?,?,?,?)",
                [
                    ("Training geven", "🏑", "training", 4),
                    ("Fluiten", "🟨", "fluiten", 3),
                    ("Geld ophalen", "💰", "geld", 2),
                    ("Bardienst", "🍺", "club", 3),
                    ("Sleepover", "🌙", "team", 0),
                ],
            )
            sleep_id = con.execute("SELECT id FROM activity_types WHERE name='Sleepover'").fetchone()["id"]
            cur = con.execute(
                "INSERT INTO activity_fields(activity_type_id,label,field_type) VALUES(?,?,?)",
                (sleep_id, "Aanwezigheid", "select"),
            )
            con.executemany(
                "INSERT INTO activity_field_options(field_id,label,points) VALUES(?,?,?)",
                [
                    (cur.lastrowid, "Halve dag", 3),
                    (cur.lastrowid, "Hele dag", 6),
                    (cur.lastrowid, "Anderhalve dag", 9),
                ],
            )

        if con.execute("SELECT COUNT(*) n FROM activities").fetchone()["n"] == 0:
            players = {r["name"]: r["id"] for r in con.execute("SELECT id,name FROM players")}
            activity_types = {r["name"]: r["id"] for r in con.execute("SELECT id,name FROM activity_types")}
            today = date.today()
            demo = [
                (players["Sofie"], activity_types["Training geven"], str(today - timedelta(days=4)), "Training gegeven", "{}", 4),
                (
                    players["Sofie"],
                    activity_types["Sleepover"],
                    str(today - timedelta(days=3)),
                    "Meegeholpen bij de sleepover",
                    json.dumps({"Aanwezigheid": "Hele dag"}),
                    6,
                ),
                (players["Jade"], activity_types["Geld ophalen"], str(today - timedelta(days=2)), "Sponsoractie · €450 opgehaald", "{}", 8),
                (players["Leanne"], activity_types["Fluiten"], str(today - timedelta(days=6)), "Thuiswedstrijd gefloten", "{}", 3),
                (players["Juul"], activity_types["Bardienst"], str(today - timedelta(days=7)), "Avonddienst", "{}", 3),
                (players["Jasmijn"], activity_types["Training geven"], str(today - timedelta(days=8)), "Jeugdtraining", "{}", 4),
                (players["Anna"], activity_types["Geld ophalen"], str(today - timedelta(days=9)), "Verkoopactie · €180 opgehaald", "{}", 5),
            ]
            con.executemany(
                "INSERT INTO activities(player_id,activity_type_id,activity_date,description,field_values_json,points) VALUES(?,?,?,?,?,?)",
                demo,
            )

        if con.execute("SELECT COUNT(*) n FROM tasks").fetchone()["n"] == 0:
            players = {r["name"]: r["id"] for r in con.execute("SELECT id,name FROM players")}
            activity_types = {r["name"]: r["id"] for r in con.execute("SELECT id,name FROM activity_types")}
            today = date.today()
            task_rows = [
                ("Training jeugd", str(today + timedelta(days=2)), "18:30", activity_types["Training geven"], "training", "Training voor MO12"),
                ("Fluitbeurt thuiswedstrijd", str(today + timedelta(days=4)), "13:00", activity_types["Fluiten"], "fluiten", "Veld 2"),
                ("Sponsoractie centrum", str(today + timedelta(days=7)), "11:00", activity_types["Geld ophalen"], "geld", "Flyers en sponsorwerving"),
                ("Bardienst", str(today + timedelta(days=10)), "20:00", activity_types["Bardienst"], "club", "Clubhuis"),
            ]
            task_ids = []
            for row in task_rows:
                cur = con.execute(
                    "INSERT INTO tasks(title,task_date,task_time,activity_type_id,category,description) VALUES(?,?,?,?,?,?)",
                    row,
                )
                task_ids.append(cur.lastrowid)
            con.executemany(
                "INSERT INTO task_assignments(task_id,player_id,response,reason) VALUES(?,?,?,?)",
                [
                    (task_ids[0], players["Sofie"], "can", ""),
                    (task_ids[1], players["Sofie"], "pending", ""),
                    (task_ids[1], players["Jade"], "cannot", "Werk tot 14:00"),
                    (task_ids[2], players["Leanne"], "pending", ""),
                    (task_ids[3], players["Juul"], "can", ""),
                ],
            )

        if con.execute("SELECT COUNT(*) n FROM brainstorm_folders").fetchone()["n"] == 0:
            admin = con.execute("SELECT id FROM players WHERE name='Beheerder'").fetchone()["id"]
            con.executemany(
                "INSERT INTO brainstorm_folders(name,icon,created_by) VALUES(?,?,?)",
                [("Geld ophalen", "💰", admin), ("Teamactiviteiten", "🎉", admin), ("Trainingen", "🏑", admin)],
            )
            folders = {r["name"]: r["id"] for r in con.execute("SELECT id,name FROM brainstorm_folders")}
            players = {r["name"]: r["id"] for r in con.execute("SELECT id,name FROM players")}
            con.executemany(
                "INSERT INTO ideas(folder_id,author_id,title,description,points_suggestion,status) VALUES(?,?,?,?,?,?)",
                [
                    (folders["Geld ophalen"], players["Sofie"], "Sponsorloop", "Rondjes laten sponsoren door familie en bedrijven.", 8, "In bespreking"),
                    (folders["Geld ophalen"], players["Jade"], "Pubquiz", "Kaartjes verkopen en lokale prijzen regelen.", 6, "Nieuw idee"),
                    (folders["Teamactiviteiten"], players["Leanne"], "Teamdiner", "Gezamenlijk diner organiseren.", 0, "Nieuw idee"),
                ],
            )
            ids = [r["id"] for r in con.execute("SELECT id FROM ideas ORDER BY id")]
            con.executemany(
                "INSERT OR IGNORE INTO idea_votes(idea_id,player_id,vote) VALUES(?,?,?)",
                [(ids[0], players["Jade"], 1), (ids[0], players["Leanne"], 1), (ids[0], players["Juul"], 1), (ids[1], players["Sofie"], 1)],
            )
            con.executemany(
                "INSERT INTO idea_comments(idea_id,player_id,body) VALUES(?,?,?)",
                [
                    (ids[0], players["Jade"], "Misschien kunnen we €5 per ronde laten sponsoren."),
                    (ids[0], players["Leanne"], "8 punten voor de organisatie lijkt mij redelijk."),
                ],
            )

        if con.execute("SELECT COUNT(*) n FROM notifications").fetchone()["n"] == 0:
            sofie = con.execute("SELECT id FROM players WHERE name='Sofie'").fetchone()["id"]
            con.executemany(
                "INSERT INTO notifications(player_id,text) VALUES(?,?)",
                [(sofie, "Je bent ingepland voor Training jeugd."), (sofie, "Jade reageerde op het idee Sponsorloop.")],
            )

        if con.execute("SELECT COUNT(*) n FROM team_transactions").fetchone()["n"] == 0:
            players = {r["name"]: r["id"] for r in con.execute("SELECT id,name FROM players")}
            today = date.today()
            seed_rows = [
                ("income", str(today - timedelta(days=12)), 450.0, "Sponsoractie", "Opbrengst sponsoractie", players["Jade"], players["Jade"], "", None, None, "approved"),
                ("expense", str(today - timedelta(days=9)), 86.40, "Teamactiviteit", "Boodschappen sleepover", players["Sofie"], players["Sofie"], "lost", None, None, "approved"),
                ("income", str(today - timedelta(days=5)), 180.0, "Verkoop", "Verkoopactie", players["Anna"], players["Anna"], "", None, None, "approved"),
                ("expense", str(today - timedelta(days=2)), 42.75, "Materiaal", "Print- en promotiemateriaal", players["Leanne"], players["Leanne"], "lost", None, None, "approved"),
            ]
            con.executemany(
                """
                INSERT INTO team_transactions(
                    transaction_type,transaction_date,amount,category,description,player_id,submitted_by,
                    receipt_status,receipt_name,receipt_data,review_status
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                seed_rows,
            )


def get_players():
    with connection() as con:
        return rows(con.execute("SELECT * FROM players WHERE active=1 ORDER BY CASE WHEN role='admin' THEN 0 ELSE 1 END,name"))


def get_player(pid):
    with connection() as con:
        row = con.execute("SELECT * FROM players WHERE id=?", (pid,)).fetchone()
        return dict(row) if row else None


def get_activity_types():
    with connection() as con:
        return rows(con.execute("SELECT * FROM activity_types WHERE active=1 ORDER BY id"))


def get_fields(tid):
    with connection() as con:
        fields = rows(con.execute("SELECT * FROM activity_fields WHERE activity_type_id=? ORDER BY id", (tid,)))
        for field in fields:
            field["options"] = rows(con.execute("SELECT * FROM activity_field_options WHERE field_id=? ORDER BY id", (field["id"],)))
        return fields


def add_activity(player_id, type_id, activity_date, description, field_values, points):
    with connection() as con:
        con.execute(
            "INSERT INTO activities(player_id,activity_type_id,activity_date,description,field_values_json,points) VALUES(?,?,?,?,?,?)",
            (player_id, type_id, str(activity_date), clean_text(description), json.dumps(field_values, ensure_ascii=False), int(points)),
        )


def get_activities(player_id=None, limit=None):
    filters = []
    params = []
    if player_id:
        filters.append("x.player_id=?")
        params.append(player_id)
    where = " WHERE " + " AND ".join(filters) if filters else ""
    limit_sql = " LIMIT %d" % int(limit) if limit else ""
    sql = """
        SELECT x.*,p.name player_name,a.name activity_name,a.icon,a.category
        FROM activities x
        JOIN players p ON p.id=x.player_id
        JOIN activity_types a ON a.id=x.activity_type_id
        %s
        ORDER BY x.activity_date DESC,x.id DESC%s
    """ % (where, limit_sql)
    with connection() as con:
        return rows(con.execute(sql, params))


def leaderboard():
    with connection() as con:
        return rows(
            con.execute(
                """
                SELECT p.id,p.name,COALESCE(SUM(a.points),0) points,COUNT(a.id) activities
                FROM players p
                LEFT JOIN activities a ON a.player_id=p.id
                WHERE p.active=1 AND p.role='player'
                GROUP BY p.id,p.name
                ORDER BY points DESC,activities DESC,p.name
                """
            )
        )


def breakdown(pid):
    with connection() as con:
        return rows(
            con.execute(
                """
                SELECT t.name,t.icon,COALESCE(SUM(a.points),0) points,COUNT(a.id) count
                FROM activity_types t
                LEFT JOIN activities a ON a.activity_type_id=t.id AND a.player_id=?
                GROUP BY t.id
                ORDER BY points DESC,t.id
                """,
                (pid,),
            )
        )


def request_change(activity_id, player_id, text):
    with connection() as con:
        con.execute(
            "INSERT INTO activity_change_requests(activity_id,requested_by,request_text) VALUES(?,?,?)",
            (activity_id, player_id, clean_text(text)),
        )


def get_change_requests(status="pending"):
    with connection() as con:
        return rows(
            con.execute(
                """
                SELECT r.*,p.name player_name,a.activity_date,t.name activity_name
                FROM activity_change_requests r
                JOIN players p ON p.id=r.requested_by
                JOIN activities a ON a.id=r.activity_id
                JOIN activity_types t ON t.id=a.activity_type_id
                WHERE r.status=?
                ORDER BY r.created_at DESC
                """,
                (status,),
            )
        )


def resolve_change_request(rid, status):
    with connection() as con:
        con.execute("UPDATE activity_change_requests SET status=? WHERE id=?", (status, rid))


def get_tasks(include_past=False):
    where = "" if include_past else "WHERE date(t.task_date)>=date('now') AND t.completed=0"
    with connection() as con:
        tasks = rows(
            con.execute(
                """
                SELECT t.*,a.name activity_name,a.icon
                FROM tasks t
                LEFT JOIN activity_types a ON a.id=t.activity_type_id
                %s
                ORDER BY t.task_date,t.task_time
                """ % where
            )
        )
        for task in tasks:
            task["assignments"] = rows(
                con.execute(
                    """
                    SELECT x.*,p.name
                    FROM task_assignments x
                    JOIN players p ON p.id=x.player_id
                    WHERE x.task_id=?
                    ORDER BY p.name
                    """,
                    (task["id"],),
                )
            )
        return tasks


def tasks_for_player(pid, include_past=False):
    return [task for task in get_tasks(include_past) if any(a["player_id"] == pid for a in task["assignments"])]


def set_task_response(task_id, pid, response, reason=""):
    with connection() as con:
        con.execute(
            "UPDATE task_assignments SET response=?,reason=? WHERE task_id=? AND player_id=?",
            (response, clean_text(reason), task_id, pid),
        )


def set_assignment_completed(task_id, pid, value=True):
    with connection() as con:
        con.execute("UPDATE task_assignments SET completed=? WHERE task_id=? AND player_id=?", (1 if value else 0, task_id, pid))


def add_task(title, task_date, task_time, type_id, category, description, player_ids):
    with connection() as con:
        cur = con.execute(
            "INSERT INTO tasks(title,task_date,task_time,activity_type_id,category,description) VALUES(?,?,?,?,?,?)",
            (clean_text(title), str(task_date), clean_text(task_time), type_id, clean_text(category, "team") or "team", clean_text(description)),
        )
        for pid in player_ids:
            con.execute("INSERT INTO task_assignments(task_id,player_id) VALUES(?,?)", (cur.lastrowid, pid))


def get_folders():
    with connection() as con:
        return rows(
            con.execute(
                """
                SELECT f.*,COUNT(i.id) idea_count,p.name created_by_name
                FROM brainstorm_folders f
                LEFT JOIN ideas i ON i.folder_id=f.id
                LEFT JOIN players p ON p.id=f.created_by
                GROUP BY f.id
                ORDER BY f.id
                """
            )
        )


def add_folder(name, icon, created_by):
    try:
        with connection() as con:
            con.execute(
                "INSERT INTO brainstorm_folders(name,icon,created_by) VALUES(?,?,?)",
                (clean_text(name), clean_text(icon, "📁") or "📁", created_by),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError("Er bestaat al een brainstormmap met deze naam.") from exc


def get_ideas(folder_id, viewer_id=None):
    viewer_id = viewer_id or -1
    with connection() as con:
        ideas = rows(
            con.execute(
                """
                SELECT
                    i.*,
                    p.name author_name,
                    COALESCE(SUM(CASE WHEN v.vote=1 THEN 1 ELSE 0 END),0) likes,
                    COALESCE(SUM(CASE WHEN v.vote=-1 THEN 1 ELSE 0 END),0) dislikes,
                    COALESCE(SUM(v.vote),0) net_score,
                    COALESCE(uv.vote,0) current_vote
                FROM ideas i
                JOIN players p ON p.id=i.author_id
                LEFT JOIN idea_votes v ON v.idea_id=i.id
                LEFT JOIN idea_votes uv ON uv.idea_id=i.id AND uv.player_id=?
                WHERE i.folder_id=?
                GROUP BY i.id
                ORDER BY net_score DESC,likes DESC,i.created_at DESC
                """,
                (viewer_id, folder_id),
            )
        )
        for idea in ideas:
            idea["comments"] = rows(
                con.execute(
                    """
                    SELECT c.*,p.name player_name
                    FROM idea_comments c
                    JOIN players p ON p.id=c.player_id
                    WHERE c.idea_id=?
                    ORDER BY c.id
                    """,
                    (idea["id"],),
                )
            )
        return ideas


def add_idea(folder_id, author_id, title, description, points):
    with connection() as con:
        con.execute(
            "INSERT INTO ideas(folder_id,author_id,title,description,points_suggestion) VALUES(?,?,?,?,?)",
            (folder_id, author_id, clean_text(title), clean_text(description), points),
        )


def cast_idea_vote(idea_id, pid, vote):
    vote = int(vote)
    if vote not in (-1, 1):
        raise ValueError("Ongeldige stem.")
    with connection() as con:
        current = con.execute("SELECT vote FROM idea_votes WHERE idea_id=? AND player_id=?", (idea_id, pid)).fetchone()
        if current and current["vote"] == vote:
            con.execute("DELETE FROM idea_votes WHERE idea_id=? AND player_id=?", (idea_id, pid))
        elif current:
            con.execute("UPDATE idea_votes SET vote=? WHERE idea_id=? AND player_id=?", (vote, idea_id, pid))
        else:
            con.execute("INSERT INTO idea_votes(idea_id,player_id,vote) VALUES(?,?,?)", (idea_id, pid, vote))


def add_comment(idea_id, pid, body):
    with connection() as con:
        con.execute("INSERT INTO idea_comments(idea_id,player_id,body) VALUES(?,?,?)", (idea_id, pid, clean_text(body)))


def set_idea_status(idea_id, status):
    with connection() as con:
        con.execute("UPDATE ideas SET status=? WHERE id=?", (status, idea_id))


def notifications(pid):
    with connection() as con:
        return rows(con.execute("SELECT * FROM notifications WHERE player_id=? ORDER BY id DESC", (pid,)))


def add_activity_type(name, icon, category, base_points):
    try:
        with connection() as con:
            con.execute(
                "INSERT INTO activity_types(name,icon,category,base_points) VALUES(?,?,?,?)",
                (clean_text(name), clean_text(icon, "⭐") or "⭐", clean_text(category, "team") or "team", int(base_points)),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError("Er bestaat al een activiteitstype met deze naam.") from exc


def update_activity_base_points(tid, pts):
    with connection() as con:
        con.execute("UPDATE activity_types SET base_points=? WHERE id=?", (int(pts), tid))


def add_select_field(tid, label, options):
    with connection() as con:
        cur = con.execute("INSERT INTO activity_fields(activity_type_id,label,field_type) VALUES(?,?,?)", (tid, clean_text(label), "select"))
        for name, pts in options:
            con.execute("INSERT INTO activity_field_options(field_id,label,points) VALUES(?,?,?)", (cur.lastrowid, clean_text(name), int(pts)))


def get_transaction(transaction_id, include_receipt_data=False):
    fields = "t.*"
    if not include_receipt_data:
        fields += ", NULL AS receipt_data"
    with connection() as con:
        row = con.execute(
            """
            SELECT %s,
                   paid.name paid_by_name,
                   submitter.name submitted_by_name,
                   reviewer.name reviewer_name
            FROM team_transactions t
            LEFT JOIN players paid ON paid.id=t.player_id
            LEFT JOIN players submitter ON submitter.id=t.submitted_by
            LEFT JOIN players reviewer ON reviewer.id=t.reviewed_by
            WHERE t.id=?
            """
            % fields,
            (transaction_id,),
        ).fetchone()
        return dict(row) if row else None


def add_transaction(
    transaction_type,
    transaction_date,
    amount,
    category,
    description,
    paid_by_player_id,
    submitted_by_player_id=None,
    receipt_status=None,
    receipt_name=None,
    receipt_data=None,
    review_status=None,
):
    submitted_by_player_id = submitted_by_player_id or paid_by_player_id
    if transaction_type == "expense":
        receipt_status = receipt_status or "lost"
        review_status = review_status or "pending"
    else:
        receipt_status = ""
        receipt_name = None
        receipt_data = None
        review_status = review_status or "approved"
    with connection() as con:
        con.execute(
            """
            INSERT INTO team_transactions(
                transaction_type,transaction_date,amount,category,description,player_id,submitted_by,
                receipt_status,receipt_name,receipt_data,review_status,reviewed_by,reviewed_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                transaction_type,
                str(transaction_date),
                float(amount),
                clean_text(category),
                clean_text(description),
                paid_by_player_id,
                submitted_by_player_id,
                receipt_status,
                clean_text(receipt_name, None),
                receipt_data,
                review_status,
                None,
                None,
            ),
        )


def update_transaction(
    transaction_id,
    transaction_date,
    amount,
    category,
    description,
    paid_by_player_id,
    receipt_status=None,
    receipt_name=None,
    receipt_data=None,
    review_status=None,
    reviewer_id=None,
):
    current = get_transaction(transaction_id, include_receipt_data=True)
    if not current:
        raise ValueError("Transactie niet gevonden.")

    final_status = review_status or current["review_status"]
    final_receipt_status = receipt_status if receipt_status is not None else current["receipt_status"]
    final_receipt_name = current["receipt_name"]
    final_receipt_data = current["receipt_data"]

    if current["transaction_type"] == "income":
        final_receipt_status = ""
        final_receipt_name = None
        final_receipt_data = None
    elif final_receipt_status == "uploaded":
        if receipt_data is not None:
            final_receipt_name = clean_text(receipt_name, current["receipt_name"])
            final_receipt_data = receipt_data
        elif not final_receipt_data:
            raise ValueError("Upload een bonnetje of kies 'Bonnetje kwijt'.")
    else:
        final_receipt_status = "lost"
        final_receipt_name = None
        final_receipt_data = None

    reviewed_by = current["reviewed_by"]
    reviewed_at = current["reviewed_at"]
    if final_status in ("approved", "rejected") and reviewer_id:
        reviewed_by = reviewer_id
        reviewed_at = timestamp_now()
    elif final_status == "pending":
        reviewed_by = None
        reviewed_at = None

    with connection() as con:
        con.execute(
            """
            UPDATE team_transactions
            SET transaction_date=?,
                amount=?,
                category=?,
                description=?,
                player_id=?,
                receipt_status=?,
                receipt_name=?,
                receipt_data=?,
                review_status=?,
                reviewed_by=?,
                reviewed_at=?
            WHERE id=?
            """,
            (
                str(transaction_date),
                float(amount),
                clean_text(category),
                clean_text(description),
                paid_by_player_id,
                final_receipt_status,
                final_receipt_name,
                final_receipt_data,
                final_status,
                reviewed_by,
                reviewed_at,
                transaction_id,
            ),
        )


def set_transaction_review(transaction_id, review_status, reviewer_id):
    if review_status not in ("pending", "approved", "rejected"):
        raise ValueError("Ongeldige reviewstatus.")
    reviewed_by = reviewer_id if review_status in ("approved", "rejected") else None
    reviewed_at = timestamp_now() if review_status in ("approved", "rejected") else None
    with connection() as con:
        con.execute(
            "UPDATE team_transactions SET review_status=?, reviewed_by=?, reviewed_at=? WHERE id=?",
            (review_status, reviewed_by, reviewed_at, transaction_id),
        )


def get_transactions(limit=None, transaction_type=None, submitted_by=None, paid_by=None, statuses=None, include_receipt_data=False):
    fields = "t.*"
    if not include_receipt_data:
        fields += ", NULL AS receipt_data"
    filters = []
    params = []
    if transaction_type:
        filters.append("t.transaction_type=?")
        params.append(transaction_type)
    if submitted_by is not None:
        filters.append("COALESCE(t.submitted_by,t.player_id)=?")
        params.append(submitted_by)
    if paid_by is not None:
        filters.append("t.player_id=?")
        params.append(paid_by)
    if statuses:
        placeholders = ",".join(["?"] * len(statuses))
        filters.append("t.review_status IN (%s)" % placeholders)
        params.extend(statuses)
    where = " WHERE " + " AND ".join(filters) if filters else ""
    limit_sql = " LIMIT %d" % int(limit) if limit else ""
    sql = """
        SELECT %s,
               paid.name paid_by_name,
               submitter.name submitted_by_name,
               reviewer.name reviewer_name
        FROM team_transactions t
        LEFT JOIN players paid ON paid.id=t.player_id
        LEFT JOIN players submitter ON submitter.id=t.submitted_by
        LEFT JOIN players reviewer ON reviewer.id=t.reviewed_by
        %s
        ORDER BY t.transaction_date DESC,t.id DESC%s
    """ % (fields, where, limit_sql)
    with connection() as con:
        return rows(con.execute(sql, params))


def money_summary(statuses=None):
    filters = []
    params = []
    if statuses:
        placeholders = ",".join(["?"] * len(statuses))
        filters.append("review_status IN (%s)" % placeholders)
        params.extend(statuses)
    where = " WHERE " + " AND ".join(filters) if filters else ""
    with connection() as con:
        row = con.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN transaction_type='income' THEN amount END),0) income,
                COALESCE(SUM(CASE WHEN transaction_type='expense' THEN amount END),0) expense
            FROM team_transactions
            %s
            """ % where,
            params,
        ).fetchone()
        income = float(row["income"] or 0)
        expense = float(row["expense"] or 0)
        return {"income": income, "expense": expense, "balance": income - expense}


def get_monthly_financials(statuses=None):
    filters = []
    params = []
    if statuses:
        placeholders = ",".join(["?"] * len(statuses))
        filters.append("review_status IN (%s)" % placeholders)
        params.extend(statuses)
    where = " WHERE " + " AND ".join(filters) if filters else ""
    with connection() as con:
        monthly_rows = rows(
            con.execute(
                """
                SELECT
                    substr(transaction_date,1,7) month_key,
                    COALESCE(SUM(CASE WHEN transaction_type='income' THEN amount END),0) income,
                    COALESCE(SUM(CASE WHEN transaction_type='expense' THEN amount END),0) expense
                FROM team_transactions
                %s
                GROUP BY substr(transaction_date,1,7)
                ORDER BY month_key
                """ % where,
                params,
            )
        )
    running = 0.0
    for row in monthly_rows:
        row["income"] = float(row["income"] or 0)
        row["expense"] = float(row["expense"] or 0)
        row["net"] = row["income"] - row["expense"]
        running += row["net"]
        row["balance"] = running
        row["label"] = row["month_key"]
    return monthly_rows


def get_balance_history(statuses=None):
    transactions = get_transactions(statuses=statuses)
    history = []
    running = 0.0
    for transaction in reversed(transactions):
        signed = transaction["amount"] if transaction["transaction_type"] == "income" else -transaction["amount"]
        running += signed
        history.append(
            {
                "transaction_date": transaction["transaction_date"],
                "description": transaction["description"],
                "signed_amount": float(signed),
                "balance": float(running),
                "category": transaction["category"],
                "transaction_type": transaction["transaction_type"],
            }
        )
    return history
