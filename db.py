import json
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).with_name('teamapp_v2.db')

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

def init_db():
    with connection() as con:
        con.executescript('''
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
            field_type TEXT NOT NULL DEFAULT 'select',
            FOREIGN KEY(activity_type_id) REFERENCES activity_types(id)
        );
        CREATE TABLE IF NOT EXISTS activity_field_options(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            points INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(field_id) REFERENCES activity_fields(id)
        );
        CREATE TABLE IF NOT EXISTS activities(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            activity_type_id INTEGER NOT NULL,
            activity_date TEXT NOT NULL,
            description TEXT,
            field_values_json TEXT,
            points INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(player_id) REFERENCES players(id),
            FOREIGN KEY(activity_type_id) REFERENCES activity_types(id)
        );
        CREATE TABLE IF NOT EXISTS activity_change_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            requested_by INTEGER NOT NULL,
            request_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(activity_id) REFERENCES activities(id),
            FOREIGN KEY(requested_by) REFERENCES players(id)
        );
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            task_date TEXT NOT NULL,
            task_time TEXT,
            activity_type_id INTEGER,
            category TEXT NOT NULL DEFAULT 'team',
            description TEXT,
            completed INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(activity_type_id) REFERENCES activity_types(id)
        );
        CREATE TABLE IF NOT EXISTS task_assignments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            response TEXT NOT NULL DEFAULT 'pending',
            reason TEXT,
            completed INTEGER NOT NULL DEFAULT 0,
            present INTEGER,
            UNIQUE(task_id, player_id),
            FOREIGN KEY(task_id) REFERENCES tasks(id),
            FOREIGN KEY(player_id) REFERENCES players(id)
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
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(folder_id) REFERENCES brainstorm_folders(id),
            FOREIGN KEY(author_id) REFERENCES players(id)
        );
        CREATE TABLE IF NOT EXISTS idea_votes(
            idea_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
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
        ''')

        if con.execute('SELECT COUNT(*) n FROM players').fetchone()['n'] == 0:
            con.executemany('INSERT INTO players(name, role) VALUES(?,?)', [
                ('Beheerder','admin'),('Sofie','player'),('Lisa','player'),('Emma','player'),('Noor','player'),('Anna','player')
            ])

        if con.execute('SELECT COUNT(*) n FROM activity_types').fetchone()['n'] == 0:
            con.executemany('INSERT INTO activity_types(name,icon,category,base_points) VALUES(?,?,?,?)', [
                ('Training geven','🏑','training',4),('Fluiten','🟨','fluiten',3),('Geld ophalen','💰','geld',2),
                ('Bardienst','🍺','club',3),('Sleepover','🌙','team',0)
            ])
            sleep_id = con.execute("SELECT id FROM activity_types WHERE name='Sleepover'").fetchone()['id']
            cur = con.execute('INSERT INTO activity_fields(activity_type_id,label,field_type) VALUES(?,?,?)', (sleep_id,'Aanwezigheid','select'))
            field_id = cur.lastrowid
            con.executemany('INSERT INTO activity_field_options(field_id,label,points) VALUES(?,?,?)', [
                (field_id,'Halve dag',3),(field_id,'Hele dag',6),(field_id,'Anderhalve dag',9)
            ])

        if con.execute('SELECT COUNT(*) n FROM activities').fetchone()['n'] == 0:
            p = {r['name']:r['id'] for r in con.execute('SELECT id,name FROM players')}
            a = {r['name']:r['id'] for r in con.execute('SELECT id,name FROM activity_types')}
            today = date.today()
            demo = [
                (p['Lisa'],a['Training geven'],str(today-timedelta(days=7)),'Training gegeven aan de jeugd','{}',4),
                (p['Emma'],a['Geld ophalen'],str(today-timedelta(days=6)),'Sponsoractie · €450 opgehaald','{}',8),
                (p['Noor'],a['Fluiten'],str(today-timedelta(days=5)),'Thuiswedstrijd gefloten','{}',3),
                (p['Sofie'],a['Training geven'],str(today-timedelta(days=4)),'Training gegeven','{}',4),
                (p['Sofie'],a['Sleepover'],str(today-timedelta(days=3)),'Meegeholpen bij de sleepover',json.dumps({'Aanwezigheid':'Hele dag'}),6),
                (p['Anna'],a['Bardienst'],str(today-timedelta(days=2)),'Avonddienst','{}',3),
            ]
            con.executemany('''INSERT INTO activities(player_id,activity_type_id,activity_date,description,field_values_json,points)
                               VALUES(?,?,?,?,?,?)''', demo)

        if con.execute('SELECT COUNT(*) n FROM tasks').fetchone()['n'] == 0:
            p = {r['name']:r['id'] for r in con.execute('SELECT id,name FROM players')}
            a = {r['name']:r['id'] for r in con.execute('SELECT id,name FROM activity_types')}
            today = date.today()
            tasks = [
                ('Training jeugd',str(today+timedelta(days=2)),'18:30',a['Training geven'],'training','Training voor MO12'),
                ('Fluitbeurt thuiswedstrijd',str(today+timedelta(days=4)),'13:00',a['Fluiten'],'fluiten','Veld 2'),
                ('Sponsoractie centrum',str(today+timedelta(days=7)),'11:00',a['Geld ophalen'],'geld','Flyers en sponsorwerving'),
                ('Bardienst',str(today+timedelta(days=10)),'20:00',a['Bardienst'],'club','Clubhuis'),
            ]
            ids=[]
            for t in tasks:
                cur=con.execute('INSERT INTO tasks(title,task_date,task_time,activity_type_id,category,description) VALUES(?,?,?,?,?,?)',t)
                ids.append(cur.lastrowid)
            con.executemany('INSERT INTO task_assignments(task_id,player_id) VALUES(?,?)', [
                (ids[0],p['Sofie']),(ids[1],p['Sofie']),(ids[1],p['Emma']),(ids[2],p['Noor']),(ids[3],p['Lisa'])
            ])

        if con.execute('SELECT COUNT(*) n FROM brainstorm_folders').fetchone()['n'] == 0:
            admin = con.execute("SELECT id FROM players WHERE name='Beheerder'").fetchone()['id']
            con.executemany('INSERT INTO brainstorm_folders(name,icon,created_by) VALUES(?,?,?)', [
                ('Geld ophalen','💰',admin),('Teamactiviteiten','🎉',admin),('Trainingen','🏑',admin)
            ])
            folders={r['name']:r['id'] for r in con.execute('SELECT id,name FROM brainstorm_folders')}
            p={r['name']:r['id'] for r in con.execute('SELECT id,name FROM players')}
            con.executemany('INSERT INTO ideas(folder_id,author_id,title,description,points_suggestion,status) VALUES(?,?,?,?,?,?)', [
                (folders['Geld ophalen'],p['Sofie'],'Sponsorloop','Rondjes laten sponsoren door familie en bedrijven.',8,'In bespreking'),
                (folders['Geld ophalen'],p['Emma'],'Pubquiz','Kaartjes verkopen en lokale prijzen regelen.',6,'Nieuw idee'),
                (folders['Teamactiviteiten'],p['Lisa'],'Teamdiner','Gezamenlijk diner organiseren.',0,'Nieuw idee')
            ])
            idea_ids=[r['id'] for r in con.execute('SELECT id FROM ideas ORDER BY id')]
            con.executemany('INSERT OR IGNORE INTO idea_votes(idea_id,player_id) VALUES(?,?)', [(idea_ids[0],p['Lisa']),(idea_ids[0],p['Emma']),(idea_ids[0],p['Noor']),(idea_ids[1],p['Sofie'])])
            con.executemany('INSERT INTO idea_comments(idea_id,player_id,body) VALUES(?,?,?)', [
                (idea_ids[0],p['Emma'],'Misschien kunnen we €5 per ronde laten sponsoren.'),
                (idea_ids[0],p['Lisa'],'8 punten voor de organisatie lijkt mij redelijk.')
            ])

        if con.execute('SELECT COUNT(*) n FROM notifications').fetchone()['n'] == 0:
            sofie = con.execute("SELECT id FROM players WHERE name='Sofie'").fetchone()['id']
            con.executemany('INSERT INTO notifications(player_id,text) VALUES(?,?)', [
                (sofie,'Je bent ingepland voor Training jeugd.'),(sofie,'Emma reageerde op het idee Sponsorloop.')
            ])

def get_players():
    with connection() as con: return rows(con.execute('SELECT * FROM players WHERE active=1 ORDER BY role DESC,name'))
def get_player(pid):
    with connection() as con:
        r=con.execute('SELECT * FROM players WHERE id=?',(pid,)).fetchone(); return dict(r) if r else None

def get_activity_types():
    with connection() as con: return rows(con.execute('SELECT * FROM activity_types WHERE active=1 ORDER BY id'))
def get_activity_type(tid):
    with connection() as con:
        r=con.execute('SELECT * FROM activity_types WHERE id=?',(tid,)).fetchone(); return dict(r) if r else None

def get_fields(tid):
    with connection() as con:
        fs=rows(con.execute('SELECT * FROM activity_fields WHERE activity_type_id=? ORDER BY id',(tid,)))
        for f in fs:
            f['options']=rows(con.execute('SELECT * FROM activity_field_options WHERE field_id=? ORDER BY id',(f['id'],)))
        return fs

def add_activity(player_id,type_id,activity_date,description,field_values,points):
    with connection() as con:
        con.execute('INSERT INTO activities(player_id,activity_type_id,activity_date,description,field_values_json,points) VALUES(?,?,?,?,?,?)',
                    (player_id,type_id,str(activity_date),description.strip(),json.dumps(field_values,ensure_ascii=False),int(points)))

def get_activities(player_id=None,limit=None):
    where=' WHERE x.player_id=?' if player_id else ''
    params=[player_id] if player_id else []
    lim=f' LIMIT {int(limit)}' if limit else ''
    sql=f'''SELECT x.*,p.name player_name,a.name activity_name,a.icon,a.category
            FROM activities x JOIN players p ON p.id=x.player_id JOIN activity_types a ON a.id=x.activity_type_id
            {where} ORDER BY x.activity_date DESC,x.id DESC {lim}'''
    with connection() as con: return rows(con.execute(sql,params))

def leaderboard():
    with connection() as con:
        return rows(con.execute('''SELECT p.id,p.name,COALESCE(SUM(a.points),0) points,COUNT(a.id) activities
            FROM players p LEFT JOIN activities a ON a.player_id=p.id
            WHERE p.active=1 AND p.role='player' GROUP BY p.id,p.name ORDER BY points DESC,activities DESC,p.name'''))

def breakdown(pid):
    with connection() as con:
        return rows(con.execute('''SELECT t.name,t.icon,COALESCE(SUM(a.points),0) points,COUNT(a.id) count
            FROM activity_types t LEFT JOIN activities a ON a.activity_type_id=t.id AND a.player_id=?
            GROUP BY t.id ORDER BY points DESC,t.id''',(pid,)))

def request_change(activity_id,player_id,text):
    with connection() as con:
        con.execute('INSERT INTO activity_change_requests(activity_id,requested_by,request_text) VALUES(?,?,?)',(activity_id,player_id,text.strip()))

def get_change_requests(status='pending'):
    with connection() as con:
        return rows(con.execute('''SELECT r.*,p.name player_name,a.activity_date,t.name activity_name
            FROM activity_change_requests r JOIN players p ON p.id=r.requested_by
            JOIN activities a ON a.id=r.activity_id JOIN activity_types t ON t.id=a.activity_type_id
            WHERE r.status=? ORDER BY r.created_at DESC''',(status,)))

def resolve_change_request(rid,status):
    with connection() as con: con.execute('UPDATE activity_change_requests SET status=? WHERE id=?',(status,rid))

def get_tasks(include_past=False):
    where='' if include_past else "WHERE date(t.task_date)>=date('now') AND t.completed=0"
    with connection() as con:
        tasks=rows(con.execute(f'''SELECT t.*,a.name activity_name,a.icon FROM tasks t LEFT JOIN activity_types a ON a.id=t.activity_type_id
                                  {where} ORDER BY t.task_date,t.task_time'''))
        for t in tasks:
            t['assignments']=rows(con.execute('''SELECT x.*,p.name FROM task_assignments x JOIN players p ON p.id=x.player_id WHERE x.task_id=? ORDER BY p.name''',(t['id'],)))
        return tasks

def tasks_for_player(pid,include_past=False):
    tasks=get_tasks(include_past)
    return [t for t in tasks if any(a['player_id']==pid for a in t['assignments'])]

def set_task_response(task_id,pid,response,reason=''):
    with connection() as con: con.execute('UPDATE task_assignments SET response=?,reason=? WHERE task_id=? AND player_id=?',(response,reason.strip(),task_id,pid))

def set_assignment_completed(task_id,pid,value=True):
    with connection() as con: con.execute('UPDATE task_assignments SET completed=? WHERE task_id=? AND player_id=?',(1 if value else 0,task_id,pid))

def add_task(title,task_date,task_time,type_id,category,description,player_ids):
    with connection() as con:
        cur=con.execute('INSERT INTO tasks(title,task_date,task_time,activity_type_id,category,description) VALUES(?,?,?,?,?,?)',(title,str(task_date),task_time,type_id,category,description.strip()))
        for pid in player_ids: con.execute('INSERT INTO task_assignments(task_id,player_id) VALUES(?,?)',(cur.lastrowid,pid))

def get_folders():
    with connection() as con:
        fs=rows(con.execute('''SELECT f.*,COUNT(i.id) idea_count FROM brainstorm_folders f LEFT JOIN ideas i ON i.folder_id=f.id GROUP BY f.id ORDER BY f.id'''))
        return fs

def add_folder(name,icon,created_by):
    with connection() as con: con.execute('INSERT INTO brainstorm_folders(name,icon,created_by) VALUES(?,?,?)',(name.strip(),icon.strip() or '📁',created_by))

def get_ideas(folder_id):
    with connection() as con:
        ideas=rows(con.execute('''SELECT i.*,p.name author_name,COUNT(DISTINCT v.player_id) votes
            FROM ideas i JOIN players p ON p.id=i.author_id LEFT JOIN idea_votes v ON v.idea_id=i.id
            WHERE i.folder_id=? GROUP BY i.id ORDER BY votes DESC,i.created_at DESC''',(folder_id,)))
        for i in ideas:
            i['comments']=rows(con.execute('''SELECT c.*,p.name player_name FROM idea_comments c JOIN players p ON p.id=c.player_id WHERE c.idea_id=? ORDER BY c.id''',(i['id'],)))
        return ideas

def add_idea(folder_id,author_id,title,description,points):
    with connection() as con: con.execute('INSERT INTO ideas(folder_id,author_id,title,description,points_suggestion) VALUES(?,?,?,?,?)',(folder_id,author_id,title.strip(),description.strip(),points))
def toggle_vote(idea_id,pid):
    with connection() as con:
        exists=con.execute('SELECT 1 FROM idea_votes WHERE idea_id=? AND player_id=?',(idea_id,pid)).fetchone()
        if exists: con.execute('DELETE FROM idea_votes WHERE idea_id=? AND player_id=?',(idea_id,pid))
        else: con.execute('INSERT INTO idea_votes(idea_id,player_id) VALUES(?,?)',(idea_id,pid))
def add_comment(idea_id,pid,body):
    with connection() as con: con.execute('INSERT INTO idea_comments(idea_id,player_id,body) VALUES(?,?,?)',(idea_id,pid,body.strip()))
def set_idea_status(idea_id,status):
    with connection() as con: con.execute('UPDATE ideas SET status=? WHERE id=?',(status,idea_id))

def notifications(pid):
    with connection() as con: return rows(con.execute('SELECT * FROM notifications WHERE player_id=? ORDER BY id DESC',(pid,)))

def add_activity_type(name,icon,category,base_points):
    with connection() as con: con.execute('INSERT INTO activity_types(name,icon,category,base_points) VALUES(?,?,?,?)',(name.strip(),icon.strip() or '⭐',category,int(base_points)))
def update_activity_base_points(tid,pts):
    with connection() as con: con.execute('UPDATE activity_types SET base_points=? WHERE id=?',(int(pts),tid))
def add_select_field(tid,label,options):
    with connection() as con:
        cur=con.execute('INSERT INTO activity_fields(activity_type_id,label,field_type) VALUES(?,?,?)',(tid,label.strip(),'select'))
        for name,pts in options: con.execute('INSERT INTO activity_field_options(field_id,label,points) VALUES(?,?,?)',(cur.lastrowid,name.strip(),int(pts)))
