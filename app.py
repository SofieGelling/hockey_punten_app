from datetime import date
import calendar
import altair as alt
import pandas as pd
import streamlit as st
import db

st.set_page_config(page_title='TeamApp', page_icon='🏑', layout='wide', initial_sidebar_state='collapsed')
db.init_db()

CATEGORY = {
    'training': ('#EAF3FF','🔵'), 'fluiten': ('#FFF7D6','🟡'), 'team': ('#FDECF4','🩷'),
    'geld': ('#EAF8EE','🟢'), 'club': ('#F3ECFF','🟣')
}

st.markdown('''
<style>
.stApp{background:linear-gradient(180deg,#F7FBFF 0%,#FFFFFF 38%);color:#13243A}
.block-container{max-width:860px;padding-top:1rem;padding-bottom:7rem}
[data-testid="stSidebar"]{background:#F2F7FE}
.hero{background:linear-gradient(135deg,#2F6FED,#76A9FF);color:white;padding:22px;border-radius:24px;box-shadow:0 10px 30px rgba(47,111,237,.18)}
.hero .eyebrow{font-size:.8rem;letter-spacing:.08em;opacity:.85}.hero .score{font-size:2.35rem;font-weight:850;line-height:1.1;margin:.3rem 0}
.card{background:#fff;border:1px solid #DDE9F7;border-radius:18px;padding:15px 16px;margin:9px 0;box-shadow:0 5px 20px rgba(40,78,120,.055)}
.soft{background:#F5F9FF;border:1px solid #E2ECFA;border-radius:16px;padding:14px;margin:8px 0}
.section{font-size:1.16rem;font-weight:800;margin-top:1.45rem;margin-bottom:.35rem}.muted{color:#718198;font-size:.9rem}
.badge{display:inline-block;background:#EEF5FF;color:#2F6FED;padding:4px 9px;border-radius:999px;font-size:.78rem;font-weight:700}
.task{border-radius:16px;padding:14px;margin:8px 0;border:1px solid rgba(50,80,120,.08)}
.st-key-bottom_nav{position:fixed;left:50%;transform:translateX(-50%);bottom:0;z-index:9999;background:rgba(255,255,255,.96);backdrop-filter:blur(10px);padding:8px 10px 10px;border-top:1px solid #DDE8F6;width:min(860px,100%);box-shadow:0 -5px 18px rgba(40,70,110,.06)}
.st-key-bottom_nav [data-testid="stHorizontalBlock"]{gap:.25rem}.st-key-bottom_nav button{border:none!important;background:transparent!important;font-size:.77rem!important;min-height:48px!important;padding:.2rem!important;color:#31516F!important}
div[data-testid="stButton"]>button, div[data-testid="stFormSubmitButton"]>button{border-radius:14px;min-height:44px;font-weight:700}
.calendar{display:grid;grid-template-columns:repeat(7,1fr);gap:5px}.calhead{text-align:center;font-size:.72rem;color:#7A899C;font-weight:700}.day{min-height:68px;border:1px solid #E4ECF7;border-radius:12px;padding:6px;background:white;font-size:.78rem}.day.empty{background:transparent;border-color:transparent}.dots{font-size:.65rem;line-height:1.2;margin-top:4px}
@media(max-width:700px){.block-container{padding-left:.9rem;padding-right:.9rem;padding-top:.7rem}.hero{padding:18px;border-radius:20px}.hero .score{font-size:2rem}.day{min-height:55px;padding:4px;font-size:.72rem}}
</style>
''', unsafe_allow_html=True)


def goto(page):
    st.session_state.page = page
    st.rerun()

def player_login():
    st.markdown('## 🏑 TeamApp')
    st.caption('Kies je naam om in te loggen.')
    players=db.get_players(); names=[p['name'] for p in players]
    name=st.selectbox('Wie ben je?',names,index=None,placeholder='Kies je naam')
    if st.button('Inloggen',type='primary',use_container_width=True,disabled=name is None):
        st.session_state.player_id=next(p['id'] for p in players if p['name']==name); st.session_state.page='Home'; st.rerun()

if 'player_id' not in st.session_state:
    player_login(); st.stop()
player=db.get_player(st.session_state.player_id)
st.session_state.setdefault('page','Home')

with st.sidebar:
    st.markdown(f"### 👋 {player['name']}")
    st.caption('Beheerder' if player['role']=='admin' else 'Speler')
    for label,page in [('⭐ Ranglijst','Ranglijst'),('📝 Mijn activiteiten','Mijn activiteiten'),('📊 Statistieken','Statistieken'),('🔔 Meldingen','Meldingen')]:
        if st.button(label,use_container_width=True,key='side_'+page): goto(page)
    st.caption('Later')
    st.button('💰 Geld ophalen',use_container_width=True,disabled=True)
    if player['role']=='admin':
        st.divider(); st.caption('BEHEER')
        if st.button('✅ Wijzigingsverzoeken',use_container_width=True): goto('Wijzigingsverzoeken')
        if st.button('⚙️ Activiteiten instellen',use_container_width=True): goto('Instellingen')
    st.divider()
    if st.button('Uitloggen',use_container_width=True): st.session_state.clear(); st.rerun()

lb=db.leaderboard(); my=next((r for r in lb if r['id']==player['id']),None)

def recommendation():
    if not lb: return 'Nog geen gegevens.'
    low=min(r['points'] for r in lb); names=[r['name'] for r in lb if r['points']==low]
    return f"**{' & '.join(names)}** {'heeft' if len(names)==1 else 'hebben'} nu de minste punten ({low})."

def activity_form():
    types=db.get_activity_types(); labels=[f"{t['icon']} {t['name']}" for t in types]
    choice=st.selectbox('Activiteit',labels); t=types[labels.index(choice)]
    fields=db.get_fields(t['id']); total=t['base_points']; values={}
    st.caption(f"Basispunten: **{t['base_points']}**")
    for f in fields:
        if f['field_type']=='select' and f['options']:
            ol=[f"{o['label']}  ·  +{o['points']} pt" for o in f['options']]
            selected=st.selectbox(f['label'],ol,key=f"field_{f['id']}"); o=f['options'][ol.index(selected)]
            values[f['label']]=o['label']; total+=o['points']
    d=st.date_input('Datum',date.today()); desc=st.text_area('Beschrijving',placeholder='Bijv. sponsoractie · €450 opgehaald')
    st.info(f'Deze activiteit levert **{total} punten** op en staat direct in je overzicht.')
    if st.button('Activiteit opslaan',type='primary',use_container_width=True):
        db.add_activity(player['id'],t['id'],d,desc,values,total); st.success('Opgeslagen!'); st.rerun()


def task_card(t, personal=False):
    bg, dot=CATEGORY.get(t['category'],('#F5F9FF','🔹'))
    ass=t['assignments']; names=', '.join(a['name'] for a in ass) or 'Nog niemand'
    st.markdown(f'''<div class="task" style="background:{bg}"><b>{dot} {t['title']}</b><br><span class="muted">{t['task_date']} {t['task_time'] or ''} · {names}</span><br>{t['description'] or ''}</div>''',unsafe_allow_html=True)
    if personal:
        mine=next((a for a in ass if a['player_id']==player['id']),None)
        if mine:
            if mine['response']=='pending':
                c1,c2=st.columns(2)
                if c1.button('✓ Ik kan',key=f"can{t['id']}",use_container_width=True): db.set_task_response(t['id'],player['id'],'can'); st.rerun()
                if c2.button('✕ Ik kan niet',key=f"cant{t['id']}",use_container_width=True): st.session_state[f"reason_{t['id']}"]=True
                if st.session_state.get(f"reason_{t['id']}"):
                    reason=st.text_input('Reden (zichtbaar voor iedereen)',key=f"reasontext_{t['id']}")
                    if st.button('Reden opslaan',key=f"sreason_{t['id']}",disabled=not reason): db.set_task_response(t['id'],player['id'],'cannot',reason); st.rerun()
            elif mine['response']=='cannot': st.warning(f"Kan niet — {mine['reason']}")
            else:
                st.success('Je hebt aangegeven dat je kunt.')
                if not mine['completed'] and st.button('✓ Mijn deel is klaar',key=f"done{t['id']}"): db.set_assignment_completed(t['id'],player['id']); st.rerun()

page=st.session_state.page

if page=='Home':
    st.markdown(f"## Hoi {player['name']} 👋")
    pts=my['points'] if my else 0; rank=(lb.index(my)+1) if my in lb else '—'; acts=my['activities'] if my else 0
    st.markdown(f'''<div class="hero"><div class="eyebrow">JOUW BIJDRAGE</div><div class="score">{pts} punten</div><div>#{rank} van {len(lb)} · {acts} activiteiten</div></div>''',unsafe_allow_html=True)
    st.markdown('<div class="section">Komende taken voor jou</div>',unsafe_allow_html=True)
    mine=db.tasks_for_player(player['id'])[:3]
    if mine:
        for t in mine: task_card(t,personal=True)
    else: st.caption('Je hebt op dit moment geen komende taken.')
    st.markdown('<div class="section">Teamstand</div>',unsafe_allow_html=True)
    for i,r in enumerate(lb[:5],1):
        st.markdown(f'<div class="card"><b>#{i} {r["name"]}</b><span style="float:right"><b>{r["points"]} pt</b></span><br><span class="muted">{r["activities"]} activiteiten</span></div>',unsafe_allow_html=True)
    st.info(+recommendation())
    st.markdown('<div class="section">Recent</div>',unsafe_allow_html=True)
    for a in db.get_activities(limit=4):
        st.markdown(f'<div class="card">{a["icon"]} <b>{a["player_name"]}</b> · {a["activity_name"]}<span style="float:right"><b>+{a["points"]}</b></span><br><span class="muted">{a["activity_date"]} · {a["description"] or ""}</span></div>',unsafe_allow_html=True)

elif page=='Toevoegen':
    st.markdown('## ➕ Toevoegen')
    tab1,tab2,tab3,tab4=st.tabs(['Activiteit','Taak','Idee','Map'])
    with tab1: activity_form()
    with tab2:
        types=db.get_activity_types(); players=[p for p in db.get_players() if p['role']=='player']
        title=st.text_input('Taaknaam'); d=st.date_input('Datum',date.today()); tm=st.text_input('Tijd',placeholder='18:30')
        typelabel=st.selectbox('Activiteitstype',[f"{t['icon']} {t['name']}" for t in types]); t=types[[f"{x['icon']} {x['name']}" for x in types].index(typelabel)]
        people=st.multiselect('Toewijzen aan',[p['name'] for p in players]); desc=st.text_area('Beschrijving',key='taskdesc')
        st.caption(f"Punten volgen automatisch het activiteitstype. Basispunten: {t['base_points']}.")
        if st.button('Taak toevoegen',type='primary',disabled=not title): db.add_task(title,d,tm,t['id'],t['category'],desc,[p['id'] for p in players if p['name'] in people]); st.success('Taak toegevoegd.'); st.rerun()
    with tab3:
        folders=db.get_folders(); folder=st.selectbox('Map',[f"{f['icon']} {f['name']}" for f in folders]); f=folders[[f"{x['icon']} {x['name']}" for x in folders].index(folder)]
        title=st.text_input('Idee'); desc=st.text_area('Uitleg'); pts=st.number_input('Voorstel voor punten',min_value=0,value=0)
        if st.button('Idee plaatsen',type='primary',disabled=not title): db.add_idea(f['id'],player['id'],title,desc,pts); st.success('Idee toegevoegd.'); st.rerun()
    with tab4:
        name=st.text_input('Naam brainstormmap'); icon=st.text_input('Icoon',value='📁')
        if st.button('Map maken',type='primary',disabled=not name): db.add_folder(name,icon,player['id']); st.success('Map gemaakt.'); st.rerun()

elif page=='Mijn activiteiten':
    st.markdown('## 📝 Mijn activiteiten')
    st.caption('Nieuwe activiteiten staan direct in dit overzicht en tellen direct mee.')
    for a in db.get_activities(player_id=player['id']):
        st.markdown(f'<div class="card">{a["icon"]} <b>{a["activity_name"]}</b><span style="float:right"><b>+{a["points"]} pt</b></span><br><span class="muted">{a["activity_date"]}</span><br>{a["description"] or ""}</div>',unsafe_allow_html=True)
        with st.expander('Wijziging aanvragen'):
            text=st.text_area('Wat wil je wijzigen?',key=f"chg{a['id']}",placeholder='Bijv. aanwezigheid moet Hele dag zijn in plaats van Halve dag')
            if st.button('Wijzigen',key=f"chgb{a['id']}",disabled=not text): db.request_change(a['id'],player['id'],text); st.success('Verzoek naar beheerder gestuurd.')

elif page=='Agenda':
    st.markdown('## 📅 Agenda')
    who=st.segmented_control('Agenda',['Mijn agenda','Hele team'],default='Mijn agenda')
    mode=st.segmented_control('Weergave',['Lijst','Kalender'],default='Lijst')
    tasks=db.tasks_for_player(player['id']) if who=='Mijn agenda' else db.get_tasks()
    if mode=='Lijst':
        for t in tasks: task_card(t,personal=(who=='Mijn agenda'))
    else:
        st.session_state.setdefault('cal_month',date.today().month); st.session_state.setdefault('cal_year',date.today().year)
        c1,c2,c3=st.columns([1,3,1])
        if c1.button('‹',use_container_width=True):
            m=st.session_state.cal_month-1; y=st.session_state.cal_year
            if m==0: m=12; y-=1
            st.session_state.cal_month=m; st.session_state.cal_year=y; st.rerun()
        c2.markdown(f"<h4 style='text-align:center'>{calendar.month_name[st.session_state.cal_month]} {st.session_state.cal_year}</h4>",unsafe_allow_html=True)
        if c3.button('›',use_container_width=True):
            m=st.session_state.cal_month+1; y=st.session_state.cal_year
            if m==13: m=1; y+=1
            st.session_state.cal_month=m; st.session_state.cal_year=y; st.rerun()
        cal=calendar.Calendar(firstweekday=0); days=list(cal.itermonthdays(st.session_state.cal_year,st.session_state.cal_month))
        html='<div class="calendar">'+''.join(f'<div class="calhead">{d}</div>' for d in ['Ma','Di','Wo','Do','Vr','Za','Zo'])
        for day in days:
            if day==0: html+='<div class="day empty"></div>'; continue
            ds=f"{st.session_state.cal_year:04d}-{st.session_state.cal_month:02d}-{day:02d}"
            todays=[t for t in tasks if t['task_date']==ds]
            dots=' '.join(CATEGORY.get(t['category'],('', '🔹'))[1] for t in todays[:4])
            html+=f'<div class="day"><b>{day}</b><div class="dots">{dots}</div></div>'
        html+='</div>'; st.markdown(html,unsafe_allow_html=True)
        st.markdown('<div class="section">Taken deze maand</div>',unsafe_allow_html=True)
        for t in tasks:
            if t['task_date'].startswith(f"{st.session_state.cal_year:04d}-{st.session_state.cal_month:02d}"): task_card(t,personal=(who=='Mijn agenda'))

elif page=='Ideeën':
    st.markdown('## 💡 Brainstorm')
    folders=db.get_folders()
    if 'folder_id' not in st.session_state:
        for f in folders:
            if st.button(f"{f['icon']} {f['name']}  ·  {f['idea_count']} ideeën",use_container_width=True,key=f"folder{f['id']}"): st.session_state.folder_id=f['id']; st.rerun()
        st.caption('Iedereen kan via ➕ een nieuwe brainstormmap toevoegen.')
    else:
        f=next((x for x in folders if x['id']==st.session_state.folder_id),None)
        if st.button('← Alle mappen'): st.session_state.pop('folder_id',None); st.rerun()
        st.markdown(f"### {f['icon']} {f['name']}")
        for idea in db.get_ideas(f['id']):
            st.markdown(f'<div class="card"><span class="badge">{idea["status"]}</span><h4>{idea["title"]}</h4><span class="muted">door {idea["author_name"]}</span><p>{idea["description"] or ""}</p><b>Puntenvoorstel: {idea["points_suggestion"] or 0}</b> · 👍 {idea["votes"]} · 💬 {len(idea["comments"])}</div>',unsafe_allow_html=True)
            cols=st.columns([1,3])
            if cols[0].button('👍 Stem',key=f"vote{idea['id']}"): db.toggle_vote(idea['id'],player['id']); st.rerun()
            with st.expander(f"Reacties ({len(idea['comments'])})"):
                for c in idea['comments']: st.markdown(f"**{c['player_name']}**  \n{c['body']}")
                body=st.text_input('Reageer',key=f"comment{idea['id']}")
                if st.button('Plaatsen',key=f"commentbtn{idea['id']}",disabled=not body): db.add_comment(idea['id'],player['id'],body); st.rerun()
            if player['role']=='admin':
                status=st.selectbox('Status',['Nieuw idee','In bespreking','Gekozen','Uitgevoerd','Geparkeerd','Niet uitvoeren'],index=['Nieuw idee','In bespreking','Gekozen','Uitgevoerd','Geparkeerd','Niet uitvoeren'].index(idea['status']) if idea['status'] in ['Nieuw idee','In bespreking','Gekozen','Uitgevoerd','Geparkeerd','Niet uitvoeren'] else 0,key=f"status{idea['id']}")
                if st.button('Status opslaan',key=f"statusbtn{idea['id']}"): db.set_idea_status(idea['id'],status); st.rerun()

elif page=='Profiel':
    st.markdown(f"## 👤 {player['name']}")
    pts=my['points'] if my else 0; rank=(lb.index(my)+1) if my in lb else '—'
    c1,c2,c3=st.columns(3); c1.metric('Punten',pts); c2.metric('Rang',f'#{rank}'); c3.metric('Activiteiten',my['activities'] if my else 0)
    st.markdown('<div class="section">Mijn bijdrage</div>',unsafe_allow_html=True)
    for b in db.breakdown(player['id']):
        if b['count']: st.markdown(f'<div class="card">{b["icon"]} <b>{b["name"]}</b><span style="float:right"><b>{b["points"]} pt</b></span><br><span class="muted">{b["count"]}×</span></div>',unsafe_allow_html=True)
    st.markdown('<div class="section">Taakhistorie</div>',unsafe_allow_html=True)
    for t in db.tasks_for_player(player['id'],include_past=True)[:6]: task_card(t)

elif page=='Ranglijst':
    st.markdown('## ⭐ Ranglijst')
    view=st.segmented_control('Weergave',['Balken','Spelercards'],default='Balken')
    if view=='Balken' and lb:
        df=pd.DataFrame(lb); df['label']=[f"{i}. {n}" for i,n in enumerate(df.name,1)]
        bars=alt.Chart(df).mark_bar(cornerRadiusEnd=8,height=26).encode(x=alt.X('points:Q',axis=None,title=None),y=alt.Y('label:N',sort=df.label.tolist(),title=None),color=alt.value('#6EA6F8'),tooltip=['name','points','activities'])
        txt=bars.mark_text(align='left',dx=7,fontWeight='bold').encode(text='points:Q',color=alt.value('#254360'))
        st.altair_chart((bars+txt).properties(height=max(180,len(df)*43)),use_container_width=True)
    else:
        for i,r in enumerate(lb,1): st.markdown(f'<div class="card"><b>#{i} {r["name"]}</b><span style="float:right"><b>{r["points"]} pt</b></span><br><span class="muted">{r["activities"]} activiteiten</span></div>',unsafe_allow_html=True)
    st.info(recommendation())

elif page=='Statistieken':
    st.markdown('## 📊 Statistieken')
    st.segmented_control('Periode',['Deze maand','Dit seizoen','Alles'],default='Dit seizoen')
    st.caption('Eerste opzet — filters en uitgebreidere grafieken kunnen we hierna toevoegen.')
    df=pd.DataFrame(lb)
    if not df.empty: st.bar_chart(df.set_index('name')['points'])

elif page=='Meldingen':
    st.markdown('## 🔔 Meldingen')
    for n in db.notifications(player['id']): st.markdown(f'<div class="card"><b>{n["text"]}</b><br><span class="muted">{n["created_at"]}</span></div>',unsafe_allow_html=True)

elif page=='Wijzigingsverzoeken' and player['role']=='admin':
    st.markdown('## ✅ Wijzigingsverzoeken')
    reqs=db.get_change_requests()
    if not reqs: st.info('Geen openstaande verzoeken.')
    for r in reqs:
        st.markdown(f'<div class="card"><b>{r["player_name"]}</b> · {r["activity_name"]}<br><span class="muted">{r["activity_date"]}</span><p>{r["request_text"]}</p></div>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        if c1.button('Goedkeuren',key=f"approve{r['id']}",use_container_width=True): db.resolve_change_request(r['id'],'approved'); st.rerun()
        if c2.button('Afwijzen',key=f"reject{r['id']}",use_container_width=True): db.resolve_change_request(r['id'],'rejected'); st.rerun()
    st.caption('In deze visuele V2 markeert goedkeuren het verzoek als akkoord. De volgende stap is het daadwerkelijke wijzigingsformulier voor de beheerder.')

elif page=='Instellingen' and player['role']=='admin':
    st.markdown('## ⚙️ Activiteiten instellen')
    st.caption('Hier zie je het flexibele model: standaardpunten zijn optioneel en je kunt zelf velden met opties + punten toevoegen.')
    for t in db.get_activity_types():
        with st.expander(f"{t['icon']} {t['name']} · basis {t['base_points']} pt"):
            pts=st.number_input('Basispunten',min_value=0,value=t['base_points'],key=f"bp{t['id']}")
            if st.button('Basispunten opslaan',key=f"bps{t['id']}"): db.update_activity_base_points(t['id'],pts); st.rerun()
            for f in db.get_fields(t['id']):
                st.markdown(f"**{f['label']}**")
                for o in f['options']: st.caption(f"• {o['label']} → +{o['points']} punten")
            st.markdown('**＋ Eigen veld toevoegen**')
            label=st.text_input('Naam veld',placeholder='Bijv. Aanwezigheid, Uren, Dagen',key=f"fld{t['id']}")
            raw=st.text_area('Opties + punten',placeholder='Halve dag = 3\nHele dag = 6\nAnderhalve dag = 9',key=f"opts{t['id']}")
            if st.button('＋ Veld toevoegen',key=f"addfld{t['id']}",disabled=not label or not raw):
                opts=[]
                for line in raw.splitlines():
                    if '=' in line:
                        n,p=line.rsplit('=',1)
                        try: opts.append((n.strip(),int(p.strip())))
                        except ValueError: pass
                if opts: db.add_select_field(t['id'],label,opts); st.success('Veld toegevoegd.'); st.rerun()
    st.divider(); st.markdown('### Nieuw activiteitstype')
    n=st.text_input('Naam'); icon=st.text_input('Icoon',value='⭐'); cat=st.selectbox('Categorie',['training','fluiten','team','geld','club']); bp=st.number_input('Standaardpunten',min_value=0,value=0,key='newbp')
    if st.button('Activiteitstype maken',type='primary',disabled=not n): db.add_activity_type(n,icon,cat,bp); st.success('Aangemaakt.'); st.rerun()

# Fixed mobile-style bottom nav
with st.container(key='bottom_nav'):
    cols=st.columns(5)
    nav=[('🏠\nHome','Home'),('📅\nAgenda','Agenda'),('➕\nToevoegen','Toevoegen'),('💡\nIdeeën','Ideeën'),('👤\nProfiel','Profiel')]
    for c,(label,p) in zip(cols,nav):
        if c.button(label,key='nav_'+p,use_container_width=True): goto(p)
