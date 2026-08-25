import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).with_name("hockey_app.db")


@contextmanager
def connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with connection() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL DEFAULT 'player',
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS activity_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                icon TEXT NOT NULL DEFAULT '⭐',
                points INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                activity_type_id INTEGER NOT NULL,
                activity_date TEXT NOT NULL,
                amount_eur REAL,
                description TEXT,
                points INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT,
                reviewed_by INTEGER,
                FOREIGN KEY(player_id) REFERENCES players(id),
                FOREIGN KEY(activity_type_id) REFERENCES activity_types(id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                task_date TEXT NOT NULL,
                task_time TEXT,
                activity_type_id INTEGER,
                assigned_player_id INTEGER,
                description TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(activity_type_id) REFERENCES activity_types(id),
                FOREIGN KEY(assigned_player_id) REFERENCES players(id)
            );
            """
        )

        player_count = con.execute("SELECT COUNT(*) AS n FROM players").fetchone()["n"]
        if player_count == 0:
            players = [
                ("Beheerder", "admin"),
                ("Lisa", "player"),
                ("Emma", "player"),
                ("Noor", "player"),
                ("Anna", "player"),
            ]
            con.executemany("INSERT INTO players(name, role) VALUES (?, ?)", players)

        type_count = con.execute("SELECT COUNT(*) AS n FROM activity_types").fetchone()["n"]
        if type_count == 0:
            types = [
                ("Training geven", "🏑", 4),
                ("Fluiten", "🟨", 3),
                ("Geld-opbrengende activiteit", "💰", 6),
                ("Bardienst", "🍺", 3),
                ("Sleepover", "🌙", 10),
            ]
            con.executemany("INSERT INTO activity_types(name, icon, points) VALUES (?, ?, ?)", types)

        task_count = con.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"]
        if task_count == 0:
            types = {r["name"]: r["id"] for r in con.execute("SELECT id, name FROM activity_types")}
            con.execute(
                "INSERT INTO tasks(title, task_date, task_time, activity_type_id, description) VALUES (?, ?, ?, ?, ?)",
                ("Fluitbeurt thuiswedstrijd", str(date.today()), "14:30", types.get("Fluiten"), "Nog toe te wijzen"),
            )


def get_players(active_only=True):
    sql = "SELECT * FROM players"
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY CASE WHEN role='admin' THEN 0 ELSE 1 END, name"
    with connection() as con:
        return [dict(r) for r in con.execute(sql).fetchall()]


def get_player(player_id):
    with connection() as con:
        row = con.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
        return dict(row) if row else None


def add_player(name, role="player"):
    with connection() as con:
        con.execute("INSERT INTO players(name, role) VALUES (?, ?)", (name.strip(), role))


def set_player_active(player_id, active):
    with connection() as con:
        con.execute("UPDATE players SET active = ? WHERE id = ?", (1 if active else 0, player_id))


def get_activity_types(active_only=True):
    sql = "SELECT * FROM activity_types"
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY id"
    with connection() as con:
        return [dict(r) for r in con.execute(sql).fetchall()]


def update_activity_points(activity_type_id, points):
    with connection() as con:
        con.execute("UPDATE activity_types SET points = ? WHERE id = ?", (int(points), activity_type_id))


def add_activity_type(name, icon, points):
    with connection() as con:
        con.execute(
            "INSERT INTO activity_types(name, icon, points) VALUES (?, ?, ?)",
            (name.strip(), icon.strip() or "⭐", int(points)),
        )


def submit_activity(player_id, activity_type_id, activity_date, amount_eur, description):
    with connection() as con:
        activity = con.execute("SELECT points FROM activity_types WHERE id = ?", (activity_type_id,)).fetchone()
        points = int(activity["points"])
        con.execute(
            """
            INSERT INTO submissions(player_id, activity_type_id, activity_date, amount_eur, description, points)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (player_id, activity_type_id, str(activity_date), amount_eur, description.strip(), points),
        )


def get_submissions(status=None, player_id=None, limit=None):
    clauses, params = [], []
    if status:
        clauses.append("s.status = ?")
        params.append(status)
    if player_id:
        clauses.append("s.player_id = ?")
        params.append(player_id)

    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    lim = f" LIMIT {int(limit)}" if limit else ""
    sql = f"""
        SELECT s.*, p.name AS player_name, a.name AS activity_name, a.icon AS icon,
               reviewer.name AS reviewer_name
        FROM submissions s
        JOIN players p ON p.id = s.player_id
        JOIN activity_types a ON a.id = s.activity_type_id
        LEFT JOIN players reviewer ON reviewer.id = s.reviewed_by
        {where}
        ORDER BY s.activity_date DESC, s.id DESC
        {lim}
    """
    with connection() as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]


def review_submission(submission_id, admin_id, approved):
    status = "approved" if approved else "rejected"
    with connection() as con:
        con.execute(
            "UPDATE submissions SET status = ?, reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ? WHERE id = ?",
            (status, admin_id, submission_id),
        )


def get_leaderboard():
    sql = """
        SELECT p.id, p.name, p.role,
               COALESCE(SUM(CASE WHEN s.status='approved' THEN s.points ELSE 0 END), 0) AS points,
               COUNT(CASE WHEN s.status='approved' THEN 1 END) AS activities
        FROM players p
        LEFT JOIN submissions s ON s.player_id = p.id
        WHERE p.active = 1 AND p.role != 'admin'
        GROUP BY p.id, p.name, p.role
        ORDER BY points DESC, activities DESC, p.name ASC
    """
    with connection() as con:
        return [dict(r) for r in con.execute(sql).fetchall()]


def get_player_breakdown(player_id):
    sql = """
        SELECT a.name, a.icon, COALESCE(SUM(s.points), 0) AS points, COUNT(s.id) AS count
        FROM activity_types a
        LEFT JOIN submissions s
          ON s.activity_type_id = a.id
         AND s.player_id = ?
         AND s.status = 'approved'
        WHERE a.active = 1
        GROUP BY a.id, a.name, a.icon
        ORDER BY points DESC, a.id
    """
    with connection() as con:
        return [dict(r) for r in con.execute(sql, (player_id,)).fetchall()]


def add_task(title, task_date, task_time, activity_type_id, assigned_player_id, description):
    with connection() as con:
        con.execute(
            """
            INSERT INTO tasks(title, task_date, task_time, activity_type_id, assigned_player_id, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title.strip(), str(task_date), task_time, activity_type_id, assigned_player_id, description.strip()),
        )


def get_upcoming_tasks(limit=8):
    sql = """
        SELECT t.*, a.name AS activity_name, a.icon AS icon, p.name AS assigned_name
        FROM tasks t
        LEFT JOIN activity_types a ON a.id = t.activity_type_id
        LEFT JOIN players p ON p.id = t.assigned_player_id
        WHERE t.completed = 0 AND date(t.task_date) >= date('now', '-1 day')
        ORDER BY t.task_date ASC, COALESCE(t.task_time, '23:59') ASC
        LIMIT ?
    """
    with connection() as con:
        return [dict(r) for r in con.execute(sql, (int(limit),)).fetchall()]
