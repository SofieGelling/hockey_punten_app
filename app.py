from datetime import date
import calendar
import json
from urllib.parse import urlencode

import altair as alt
import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title='TeamApp', page_icon='🏑', layout='wide', initial_sidebar_state='auto')
db.init_db()

CATEGORY = {
    'training': ('#EAF3FF','🔵'), 'fluiten': ('#FFF7D6','🟡'), 'team': ('#FDECF4','🩷'),
    'geld': ('#EAF8EE','🟢'), 'club': ('#F3ECFF','🟣')
}

st.markdown('''
<style>
.stApp{background:linear-gradient(180deg,#F7FBFF 0%,#FFFFFF 38%);color:#13243A}
.block-container{max-width:860px;padding-top:1.1rem;padding-bottom:2rem}
[data-testid="stSidebar"]{background:#F2F7FE}
.sidebar-link{display:block;text-decoration:none!important;color:#18304f!important;background:white;border:1px solid #dfeaf7;border-radius:13px;padding:.7rem .85rem;margin:.35rem 0;font-weight:700}
.sidebar-link.active{background:#eaf3ff;border-color:#a8c9f7;color:#235fae!important}
.hero{background:linear-gradient(135deg,#2F6FED,#76A9FF);color:white;padding:20px;border-radius:22px;box-shadow:0 10px 30px rgba(47,111,237,.18)}
.card{background:#fff;border:1px solid #DDE9F7;border-radius:18px;padding:15px 16px;margin:9px 0;box-shadow:0 5px 20px rgba(40,78,120,.055)}
.soft{background:#F5F9FF;border:1px solid #E2ECFA;border-radius:16px;padding:14px;margin:8px 0}
.section{font-size:1.16rem;font-weight:800;margin-top:1.45rem;margin-bottom:.35rem}.muted{color:#718198;font-size:.9rem}
.badge{display:inline-block;background:#EEF5FF;color:#2F6FED;padding:4px 9px;border-radius:999px;font-size:.78rem;font-weight:700}
.task{border-radius:16px;padding:14px;margin:8px 0;border:1px solid rgba(50,80,120,.08)}
.metric-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:.65rem 0 1rem}
.mini-metric{background:white;border:1px solid #dfeaf7;border-radius:16px;padding:12px 9px;text-align:center;box-shadow:0 4px 14px rgba(40,78,120,.045)}
.mini-metric .label{font-size:.77rem;color:#718198;margin-bottom:3px}.mini-metric .value{font-size:1.55rem;font-weight:850;color:#13243A}
.calendar{display:grid;grid-template-columns:repeat(7,1fr);gap:5px}.calhead{text-align:center;font-size:.72rem;color:#7A899C;font-weight:700}.day{min-height:68px;border:1px solid #E4ECF7;border-radius:12px;padding:6px;background:white;font-size:.78rem}.day.empty{background:transparent;border-color:transparent}.dots{font-size:.65rem;line-height:1.2;margin-top:4px}
.money-positive{color:#14804a;font-weight:800}.money-negative{color:#b54747;font-weight:800}
div[data-testid="stButton"]>button,div[data-testid="stFormSubmitButton"]>button{border-radius:14px;min-height:42px;font-weight:700}
@media(max-width:700px){
  .block-container{padding-left:.85rem;padding-right:.85rem;padding-top:5.3rem!important}
  .hero{padding:17px;border-radius:19px}
  .metric-row{gap:7px}.mini-metric{padding:10px 4px;border-radius:14px}.mini-metric .label{font-size:.68rem}.mini-metric .value{font-size:1.25rem}
  .day{min-height:52px;padding:4px;font-size:.7rem}
}
</style>
''', unsafe_allow_html=True)

VALID_PAGES = {'Home','Agenda','Toevoegen','Ideeën','Ranglijst','Activiteiten','Meldingen','Profiel','Teamrekening','Wijzigingsverzoeken','Instellingen'}

def q(name, default=None):
    v=st.query_params.get(name,default)
    return v[0] if isinstance(v,list) and v else v

def nav_url(page, **extra):
    params={'page':page}
    if 'player_id' in st.session_state: params['user']=str(st.session_state.player_id)
    params.update({k:str(v) for k,v in extra.items() if v is not None})
    return '?' + urlencode(params)

def goto(page, **extra):
    st.query_params.clear()
    st.query_params['page']=page
    st.query_params['user']=str(st.session_state.player_id)
    for k,v in extra.items(): st.query_params[k]=str(v)
    st.session_state.page=page
    st.rerun()

def login():
    st.markdown('## 🏑 TeamApp')
    st.caption('Kies je naam om in te loggen.')
    players=db.get_players(); names=[p['name'] for p in players]
    name=st.selectbox('Wie ben je?',names,index=None,placeholder='Kies je naam',key='login_name')
    if st.button('Inloggen',type='primary',use_container_width=True,disabled=name is None):
        st.session_state.player_id=next(p['id'] for p in players if p['name']==name)
        goto('Home')

if 'player_id' not in st.session_state:
    try:
        saved=int(q('user')) if q('user') else None
    except Exception:
        saved=None
    if saved and db.get_player(saved): st.session_state.player_id=saved
if 'player_id' not in st.session_state:
    login(); st.stop()

player=db.get_player(st.session_state.player_id)
page=q('page','Home')
if page not in VALID_PAGES: page='Home'
st.session_state.page=page

with st.sidebar:
    st.markdown(f"### 👋 {player['name']}")
    st.caption('Beheerder' if player['role']=='admin' else 'Speler')
    st.caption('MENU')
    nav=[('🏠 Home','Home'),('📅 Agenda','Agenda'),('➕ Toevoegen','Toevoegen'),('💡 Ideeën','Ideeën'),('⭐ Ranglijst','Ranglijst'),('📝 Activiteiten','Activiteiten'),('🔔 Meldingen','Meldingen'),('👤 Profiel','Profiel'),('💰 Teamrekening','Teamrekening')]
    for label,p in nav:
        cls='sidebar-link active' if page==p else 'sidebar-link'
        st.markdown(f'<a class="{cls}" href="{nav_url(p)}" target="_self">{label}</a>',unsafe_allow_html=True)
    if player['role']=='admin':
        st.divider(); st.caption('BEHEER')
        for label,p in [('✅ Wijzigingsverzoeken','Wijzigingsverzoeken'),('⚙️ Activiteiten instellen','Instellingen')]:
            cls='sidebar-link active' if page==p else 'sidebar-link'
            st.markdown(f'<a class="{cls}" href="{nav_url(p)}" target="_self">{label}</a>',unsafe_allow_html=True)
    st.divider()
    if st.button('🚪 Uitloggen',use_container_width=True,key='logout'):
        st.session_state.clear(); st.query_params.clear(); st.rerun()

lb=db.leaderboard(); my=next((r for r in lb if r['id']==player['id']),None)

def metric_strip(points,rank,activities):
    st.markdown(f'''<div class="metric-row">
      <div class="mini-metric"><div class="label">Punten</div><div class="value">{points}</div></div>
      <div class="mini-metric"><div class="label">Rang</div><div class="value">#{rank}</div></div>
      <div class="mini-metric"><div class="label">Activiteiten</div><div class="value">{activities}</div></div>
    </div>''',unsafe_allow_html=True)

def recommendation():
    if not lb: return 'Nog geen gegevens.'
    low=min(r['points'] for r in lb); names=[r['name'] for r in lb if r['points']==low]
    return f"**{' & '.join(names)}** {'heeft' if len(names)==1 else 'hebben'} nu de minste punten ({low})."

@st.dialog('Spelerdetails')
def player_dialog(player_id):
    selected=db.get_player(player_id); row=next((r for r in lb if r['id']==player_id),None)
    if not selected or not row:
        st.warning('Speler niet gevonden.'); return
    rank=lb.index(row)+1
    st.markdown(f"### 👤 {selected['name']}")
    metric_strip(row['points'],rank,row['activities'])
    st.markdown('#### Punten per activiteit')
    for b in db.breakdown(player_id):
        if b['count']:
            st.markdown(f'<div class="card">{b["icon"]} <b>{b["name"]}</b><span style="float:right"><b>{b["points"]} pt</b></span><br><span class="muted">{b["count"]}× gedaan</span></div>',unsafe_allow_html=True)
    st.markdown('#### Activiteiten')
    acts=db.get_activities(player_id=player_id)
    if not acts: st.caption('Nog geen activiteiten.')
    for a in acts[:12]:
        try: vals=json.loads(a.get('field_values_json') or '{}')
        except Exception: vals={}
        details=' · '.join(f'{k}: {v}' for k,v in vals.items())
        extra=' · '.join(x for x in [details,a.get('description') or ''] if x)
        st.markdown(f'<div class="card">{a["icon"]} <b>{a["activity_name"]}</b><span style="float:right"><b>+{a["points"]}</b></span><br><span class="muted">{a["activity_date"]}{" · "+extra if extra else ""}</span></div>',unsafe_allow_html=True)

def player_card(r, rank, prefix):
    if st.button(f"#{rank}  {r['name']}   ·   {r['points']} pt\n{r['activities']} activiteiten  ›",key=f'{prefix}_{r["id"]}',use_container_width=True):
        player_dialog(r['id'])

def activity_form():
    types=db.get_activity_types(); labels=[f"{t['icon']} {t['name']}" for t in types]
    choice=st.selectbox('Activiteit',labels,key='activity_type'); t=types[labels.index(choice)]
    total=t['base_points']; values={}
    if t['base_points']: st.caption(f"Basispunten: **{t['base_points']}**")
    for f in db.get_fields(t['id']):
        if f['field_type']=='select' and f['options']:
            opts=[f"{o['label']} · +{o['points']} pt" for o in f['options']]
            sel=st.selectbox(f['label'],opts,key=f"activity_field_{f['id']}"); o=f['options'][opts.index(sel)]
            values[f['label']]=o['label']; total+=o['points']
    d=st.date_input('Datum',date.today(),key='activity_date')
    desc=st.text_area('Beschrijving',placeholder='Bijv. sponsoractie · €450 opgehaald',key='activity_desc')
    st.info(f'Deze activiteit levert **{total} punten** op en staat direct in je overzicht.')
    if st.button('Activiteit opslaan',type='primary',use_container_width=True,key='activity_save'):
        db.add_activity(player['id'],t['id'],d,desc,values,total); st.success('Opgeslagen!'); st.rerun()

def task_card(t, personal=False):
    bg,dot=CATEGORY.get(t['category'],('#F5F9FF','🔹')); ass=t['assignments']; names=', '.join(a['name'] for a in ass) or 'Nog niemand'
    st.markdown(f'''<div class="task" style="background:{bg}"><b>{dot} {t['title']}</b><br><span class="muted">{t['task_date']} {t['task_time'] or ''} · {names}</span><br>{t['description'] or ''}</div>''',unsafe_allow_html=True)
    if not personal: return
    mine=next((a for a in ass if a['player_id']==player['id']),None)
    if not mine: return
    response=mine['response']
    if response=='pending':
        c1,c2=st.columns(2)
        if c1.button('✓ Ik kan',key=f'can_{t["id"]}',use_container_width=True): db.set_task_response(t['id'],player['id'],'can'); st.rerun()
        if c2.button('✕ Ik kan niet',key=f'cant_{t["id"]}',use_container_width=True): st.session_state[f'cant_reason_{t["id"]}']=True
        if st.session_state.get(f'cant_reason_{t["id"]}'):
            reason=st.text_input('Reden',key=f'cant_reason_text_{t["id"]}')
            if st.button('Opslaan',key=f'cant_reason_save_{t["id"]}',disabled=not reason): db.set_task_response(t['id'],player['id'],'cannot',reason); st.rerun()
    elif response=='cannot':
        st.warning(f"Kan niet — {mine['reason']}")
        c1,c2=st.columns(2)
        if c1.button('✓ Toch wel kunnen',key=f'switch_can_{t["id"]}',use_container_width=True): db.set_task_response(t['id'],player['id'],'can',''); st.rerun()
        if c2.button('✏️ Reden wijzigen',key=f'edit_reason_{t["id"]}',use_container_width=True): st.session_state[f'edit_cant_{t["id"]}']=True
        if st.session_state.get(f'edit_cant_{t["id"]}'):
            reason=st.text_input('Reden aanpassen',value=mine['reason'] or '',key=f'edit_cant_text_{t["id"]}')
            if st.button('Wijziging opslaan',key=f'edit_cant_save_{t["id"]}',disabled=not reason): db.set_task_response(t['id'],player['id'],'cannot',reason); st.rerun()
    else:
        st.success('Je hebt aangegeven dat je kunt.')
        c1,c2=st.columns(2)
        if c1.button('✏️ Antwoord wijzigen',key=f'change_can_{t["id"]}',use_container_width=True): st.session_state[f'change_can_{t["id"]}']=True
        if not mine['completed'] and c2.button('✓ Mijn deel klaar',key=f'done_{t["id"]}',use_container_width=True): db.set_assignment_completed(t['id'],player['id']); st.rerun()
        if st.session_state.get(f'change_can_{t["id"]}'):
            reason=st.text_input('Waarom kun je toch niet?',key=f'change_can_reason_{t["id"]}')
            c3,c4=st.columns(2)
            if c3.button('Opslaan als kan niet',key=f'change_can_save_{t["id"]}',disabled=not reason,use_container_width=True): db.set_task_response(t['id'],player['id'],'cannot',reason); st.rerun()
            if c4.button('Annuleren',key=f'change_can_cancel_{t["id"]}',use_container_width=True): st.session_state.pop(f'change_can_{t["id"]}',None); st.rerun()

if page=='Home':
    st.markdown(f"## Hoi {player['name']} 👋")
    pts=my['points'] if my else 0; rank=lb.index(my)+1 if my in lb else '—'; acts=my['activities'] if my else 0
    metric_strip(pts,rank,acts)
    st.markdown('<div class="section">Komende taken voor jou</div>',unsafe_allow_html=True)
    mine_tasks=db.tasks_for_player(player['id'])[:3]
    if mine_tasks:
        for t in mine_tasks: task_card(t,personal=True)
    else: st.caption('Je hebt op dit moment geen komende taken.')
    st.markdown('<div class="section">Teamstand</div>',unsafe_allow_html=True)
    for i,r in enumerate(lb[:5],1): player_card(r,i,'home_player')
    st.info('Volgende voor een verplichting: '+recommendation())
    c1,c2=st.columns([3,1])
    c1.markdown('<div class="section">Recent</div>',unsafe_allow_html=True)
    if c2.button('Bekijk alles',key='recent_all',use_container_width=True): goto('Activiteiten',view='team')
    for a in db.get_activities(limit=4):
        st.markdown(f'<div class="card">{a["icon"]} <b>{a["player_name"]}</b> · {a["activity_name"]}<span style="float:right"><b>+{a["points"]}</b></span><br><span class="muted">{a["activity_date"]} · {a["description"] or ""}</span></div>',unsafe_allow_html=True)

elif page=='Toevoegen':
    st.markdown('## ➕ Toevoegen')
    tab1,tab2,tab3,tab4=st.tabs(['Activiteit','Taak','Idee','Map'])
    with tab1: activity_form()
    with tab2:
        types=db.get_activity_types(); players=[p for p in db.get_players() if p['role']=='player']
        title=st.text_input('Taaknaam',key='task_title'); d=st.date_input('Datum',date.today(),key='task_date'); tm=st.text_input('Tijd',placeholder='18:30',key='task_time')
        type_labels=[f"{t['icon']} {t['name']}" for t in types]; label=st.selectbox('Activiteitstype',type_labels,key='task_type'); t=types[type_labels.index(label)]
        people=st.multiselect('Toewijzen aan',[p['name'] for p in players],key='task_people'); desc=st.text_area('Beschrijving',key='task_desc')
        st.caption(f"Punten volgen automatisch het activiteitstype. Basispunten: {t['base_points']}.")
        if st.button('Taak toevoegen',type='primary',disabled=not title,key='task_save'):
            db.add_task(title,d,tm,t['id'],t['category'],desc,[p['id'] for p in players if p['name'] in people]); st.success('Taak toegevoegd.'); st.rerun()
    with tab3:
        folders=db.get_folders(); labels=[f"{f['icon']} {f['name']}" for f in folders]; label=st.selectbox('Map',labels,key='idea_folder'); f=folders[labels.index(label)]
        title=st.text_input('Idee',key='idea_title'); desc=st.text_area('Uitleg',key='idea_desc'); pts=st.number_input('Voorstel voor punten',min_value=0,value=0,key='idea_pts')
        if st.button('Idee plaatsen',type='primary',disabled=not title,key='idea_save'): db.add_idea(f['id'],player['id'],title,desc,pts); st.success('Idee toegevoegd.'); st.rerun()
    with tab4:
        name=st.text_input('Naam brainstormmap',key='folder_name'); icon=st.text_input('Icoon',value='📁',key='folder_icon')
        if st.button('Map maken',type='primary',disabled=not name,key='folder_save'): db.add_folder(name,icon,player['id']); st.success('Map gemaakt.'); st.rerun()

elif page=='Activiteiten':
    st.markdown('## 📝 Activiteiten')
    default='Alle recente' if q('view')=='team' else 'Mijn activiteiten'
    scope=st.segmented_control('Overzicht',['Mijn activiteiten','Alle recente'],default=default,key='activity_scope')
    if scope=='Mijn activiteiten':
        st.caption('Nieuwe activiteiten staan direct in je overzicht en tellen direct mee.')
        activities=db.get_activities(player_id=player['id'])
        if not activities: st.info('Je hebt nog geen activiteiten toegevoegd.')
        for a in activities:
            st.markdown(f'<div class="card">{a["icon"]} <b>{a["activity_name"]}</b><span style="float:right"><b>+{a["points"]} pt</b></span><br><span class="muted">{a["activity_date"]}</span><br>{a["description"] or ""}</div>',unsafe_allow_html=True)
            with st.expander('Wijziging aanvragen'):
                text=st.text_area('Wat wil je wijzigen?',key=f'chg_{a["id"]}',placeholder='Bijv. aanwezigheid moet Hele dag zijn in plaats van Halve dag')
                if st.button('Verzoek versturen',key=f'chg_btn_{a["id"]}',disabled=not text): db.request_change(a['id'],player['id'],text); st.success('Verzoek verstuurd.')
    else:
        st.caption('Alle recente activiteiten van het team.')
        for a in db.get_activities():
            st.markdown(f'<div class="card">{a["icon"]} <b>{a["player_name"]}</b> · {a["activity_name"]}<span style="float:right"><b>+{a["points"]}</b></span><br><span class="muted">{a["activity_date"]}</span><br>{a["description"] or ""}</div>',unsafe_allow_html=True)

elif page=='Agenda':
    st.markdown('## 📅 Agenda')
    who=st.segmented_control('Agenda',['Mijn agenda','Hele team'],default='Mijn agenda',key='agenda_scope')
    mode=st.segmented_control('Weergave',['Lijst','Kalender'],default='Lijst',key='agenda_mode')
    tasks=db.tasks_for_player(player['id']) if who=='Mijn agenda' else db.get_tasks()
    if mode=='Lijst':
        if not tasks: st.info('Geen komende taken.')
        for t in tasks: task_card(t,personal=(who=='Mijn agenda'))
    else:
        st.session_state.setdefault('cal_month',date.today().month); st.session_state.setdefault('cal_year',date.today().year)
        c1,c2,c3=st.columns([1,3,1])
        if c1.button('‹',key='cal_prev',use_container_width=True):
            m=st.session_state.cal_month-1; y=st.session_state.cal_year
            if m==0: m=12; y-=1
            st.session_state.cal_month=m; st.session_state.cal_year=y; st.rerun()
        c2.markdown(f"<h4 style='text-align:center'>{calendar.month_name[st.session_state.cal_month]} {st.session_state.cal_year}</h4>",unsafe_allow_html=True)
        if c3.button('›',key='cal_next',use_container_width=True):
            m=st.session_state.cal_month+1; y=st.session_state.cal_year
            if m==13: m=1; y+=1
            st.session_state.cal_month=m; st.session_state.cal_year=y; st.rerun()
        days=list(calendar.Calendar(firstweekday=0).itermonthdays(st.session_state.cal_year,st.session_state.cal_month))
        html='<div class="calendar">'+''.join(f'<div class="calhead">{d}</div>' for d in ['Ma','Di','Wo','Do','Vr','Za','Zo'])
        for day in days:
            if day==0: html+='<div class="day empty"></div>'; continue
            ds=f'{st.session_state.cal_year:04d}-{st.session_state.cal_month:02d}-{day:02d}'; todays=[t for t in tasks if t['task_date']==ds]
            dots=' '.join(CATEGORY.get(t['category'],('', '🔹'))[1] for t in todays[:4]); html+=f'<div class="day"><b>{day}</b><div class="dots">{dots}</div></div>'
        html+='</div>'; st.markdown(html,unsafe_allow_html=True)
        st.markdown('<div class="section">Taken deze maand</div>',unsafe_allow_html=True)
        for t in tasks:
            if t['task_date'].startswith(f'{st.session_state.cal_year:04d}-{st.session_state.cal_month:02d}'): task_card(t,personal=(who=='Mijn agenda'))

elif page=='Ideeën':
    st.markdown('## 💡 Brainstorm')
    folders=db.get_folders(); folder_id=q('folder')
    if not folder_id:
        for f in folders:
            if st.button(f"{f['icon']} {f['name']} · {f['idea_count']} ideeën",use_container_width=True,key=f'folder_{f["id"]}'):
                goto('Ideeën',folder=f['id'])
        st.caption('Iedereen kan via ➕ een nieuwe brainstormmap toevoegen.')
    else:
        try: fid=int(folder_id)
        except Exception: fid=None
        f=next((x for x in folders if x['id']==fid),None)
        if not f: goto('Ideeën')
        if st.button('← Alle mappen',key='back_folders'): goto('Ideeën')
        st.markdown(f"### {f['icon']} {f['name']}")
        st.caption('Ideeën zijn ingeklapt. Tik op een titel om de details en reacties te zien.')
        for idea in db.get_ideas(f['id']):
            label=f"{idea['title']}   ·   👍 {idea['votes']}   ·   💬 {len(idea['comments'])}"
            with st.expander(label,expanded=False):
                st.markdown(f'<span class="badge">{idea["status"]}</span>',unsafe_allow_html=True)
                st.caption(f"door {idea['author_name']}")
                if idea['description']: st.write(idea['description'])
                st.markdown(f"**Puntenvoorstel:** {idea['points_suggestion'] or 0}")
                if st.button('👍 Stem / stem intrekken',key=f'vote_{idea["id"]}'): db.toggle_vote(idea['id'],player['id']); st.rerun()
                st.markdown('**Reacties**')
                if not idea['comments']: st.caption('Nog geen reacties.')
                for c in idea['comments']: st.markdown(f"**{c['player_name']}**  \n{c['body']}")
                body=st.text_input('Reageer',key=f'comment_{idea["id"]}')
                if st.button('Plaatsen',key=f'comment_btn_{idea["id"]}',disabled=not body): db.add_comment(idea['id'],player['id'],body); st.rerun()
                if player['role']=='admin':
                    statuses=['Nieuw idee','In bespreking','Gekozen','Uitgevoerd','Geparkeerd','Niet uitvoeren']
                    status=st.selectbox('Status',statuses,index=statuses.index(idea['status']) if idea['status'] in statuses else 0,key=f'status_{idea["id"]}')
                    if st.button('Status opslaan',key=f'status_btn_{idea["id"]}'): db.set_idea_status(idea['id'],status); st.rerun()

elif page=='Ranglijst':
    st.markdown('## ⭐ Ranglijst')
    view=st.segmented_control('Weergave',['Balken','Spelercards'],default='Spelercards',key='rank_view')
    if view=='Balken' and lb:
        df=pd.DataFrame(lb); df['label']=[f'{i}. {n}' for i,n in enumerate(df.name,1)]
        bars=alt.Chart(df).mark_bar(cornerRadiusEnd=8,height=25).encode(x=alt.X('points:Q',axis=None,title=None),y=alt.Y('label:N',sort=df.label.tolist(),title=None),color=alt.value('#6EA6F8'),tooltip=['name','points','activities'])
        txt=bars.mark_text(align='left',dx=7,fontWeight='bold').encode(text='points:Q',color=alt.value('#254360'))
        st.altair_chart((bars+txt).properties(height=max(180,len(df)*40)),use_container_width=True)
        st.caption('Kies Spelercards om op een speler te kunnen tikken.')
    else:
        st.caption('Tik op een speler voor een popup met de punten en activiteiten.')
        for i,r in enumerate(lb,1): player_card(r,i,'rank_player')
    st.info(recommendation())

elif page=='Profiel':
    st.markdown(f"## 👤 {player['name']}")
    pts=my['points'] if my else 0; rank=lb.index(my)+1 if my in lb else '—'; acts=my['activities'] if my else 0
    metric_strip(pts,rank,acts)
    st.markdown('<div class="section">Mijn bijdrage</div>',unsafe_allow_html=True)
    for b in db.breakdown(player['id']):
        if b['count']: st.markdown(f'<div class="card">{b["icon"]} <b>{b["name"]}</b><span style="float:right"><b>{b["points"]} pt</b></span><br><span class="muted">{b["count"]}×</span></div>',unsafe_allow_html=True)
    st.markdown('<div class="section">Taakhistorie</div>',unsafe_allow_html=True)
    for t in db.tasks_for_player(player['id'],include_past=True)[:8]: task_card(t)

elif page=='Meldingen':
    st.markdown('## 🔔 Meldingen')
    ns=db.notifications(player['id'])
    if not ns: st.info('Geen meldingen.')
    for n in ns: st.markdown(f'<div class="card"><b>{n["text"]}</b><br><span class="muted">{n["created_at"]}</span></div>',unsafe_allow_html=True)

elif page=='Teamrekening':
    st.markdown('## 💰 Teamrekening')
    summary=db.money_summary()
    st.markdown(f'''<div class="metric-row">
      <div class="mini-metric"><div class="label">Saldo</div><div class="value">€ {summary['balance']:.2f}</div></div>
      <div class="mini-metric"><div class="label">Inkomsten</div><div class="value">€ {summary['income']:.2f}</div></div>
      <div class="mini-metric"><div class="label">Uitgaven</div><div class="value">€ {summary['expense']:.2f}</div></div>
    </div>'''.replace('.',','),unsafe_allow_html=True)
    tab1,tab2,tab3=st.tabs(['Overzicht','Uitgave toevoegen','Inkomst toevoegen'])
    with tab1:
        tx=db.get_transactions()
        if tx:
            df=pd.DataFrame(tx); df['signed']=df.apply(lambda r: r['amount'] if r['transaction_type']=='income' else -r['amount'],axis=1)
            chart=alt.Chart(df).mark_bar(cornerRadiusEnd=5).encode(x=alt.X('transaction_date:T',title=None),y=alt.Y('signed:Q',title='€'),tooltip=['description','amount','transaction_type'])
            st.altair_chart(chart,use_container_width=True)
        st.markdown('#### Transacties')
        for t in tx:
            sign='+' if t['transaction_type']=='income' else '−'; cls='money-positive' if t['transaction_type']=='income' else 'money-negative'
            receipt={'uploaded':'Bon toegevoegd','lost':'Bonnetje kwijt','none':'Geen bonnetje'}.get(t['receipt_status'],'')
            st.markdown(f'<div class="card"><b>{t["description"]}</b><span class="{cls}" style="float:right">{sign} € {t["amount"]:.2f}</span><br><span class="muted">{t["transaction_date"]} · {t["category"] or "Overig"} · {t["player_name"] or "Team"}</span><br><span class="muted">{receipt}</span></div>'.replace('.',','),unsafe_allow_html=True)
    with tab2:
        d=st.date_input('Datum',date.today(),key='money_expense_date'); amount=st.number_input('Bedrag (€)',min_value=0.0,step=1.0,key='money_expense_amount')
        category=st.text_input('Categorie',placeholder='Bijv. boodschappen, materiaal, teamactiviteit',key='money_expense_category'); desc=st.text_input('Waarvoor was de uitgave?',key='money_expense_desc')
        receipt_choice=st.radio('Bonnetje',['Ik heb een bonnetje','Geen bonnetje','Bonnetje kwijt'],horizontal=True,key='money_expense_receipt')
        upload=None
        if receipt_choice=='Ik heb een bonnetje': upload=st.file_uploader('Upload bonnetje',type=['png','jpg','jpeg','pdf'],key='money_expense_upload')
        if st.button('Uitgave opslaan',type='primary',use_container_width=True,key='money_expense_save',disabled=amount<=0 or not desc):
            status={'Ik heb een bonnetje':'uploaded','Geen bonnetje':'none','Bonnetje kwijt':'lost'}[receipt_choice]
            db.add_transaction('expense',d,amount,category,desc,player['id'],status,upload.name if upload else None,upload.getvalue() if upload else None); st.success('Uitgave opgeslagen.'); st.rerun()
    with tab3:
        d=st.date_input('Datum',date.today(),key='money_income_date'); amount=st.number_input('Bedrag (€)',min_value=0.0,step=1.0,key='money_income_amount')
        category=st.text_input('Categorie',placeholder='Bijv. sponsor, verkoop, actie',key='money_income_category'); desc=st.text_input('Waar komt het bedrag vandaan?',key='money_income_desc')
        if st.button('Inkomst opslaan',type='primary',use_container_width=True,key='money_income_save',disabled=amount<=0 or not desc): db.add_transaction('income',d,amount,category,desc,player['id']); st.success('Inkomst opgeslagen.'); st.rerun()

elif page=='Wijzigingsverzoeken' and player['role']=='admin':
    st.markdown('## ✅ Wijzigingsverzoeken')
    reqs=db.get_change_requests()
    if not reqs: st.info('Geen openstaande verzoeken.')
    for r in reqs:
        st.markdown(f'<div class="card"><b>{r["player_name"]}</b> · {r["activity_name"]}<br><span class="muted">{r["activity_date"]}</span><p>{r["request_text"]}</p></div>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        if c1.button('Goedkeuren',key=f'approve_{r["id"]}',use_container_width=True): db.resolve_change_request(r['id'],'approved'); st.rerun()
        if c2.button('Afwijzen',key=f'reject_{r["id"]}',use_container_width=True): db.resolve_change_request(r['id'],'rejected'); st.rerun()

elif page=='Instellingen' and player['role']=='admin':
    st.markdown('## ⚙️ Activiteiten instellen')
    st.caption('Een activiteit kan alleen basispunten hebben, of één of meerdere zelfgemaakte keuzevelden met extra punten.')
    for t in db.get_activity_types():
        with st.expander(f"{t['icon']} {t['name']} · {t['base_points']} basispunten"):
            pts=st.number_input('Basispunten',min_value=0,value=int(t['base_points']),key=f'base_{t["id"]}')
            if st.button('Basispunten opslaan',key=f'base_save_{t["id"]}'): db.update_activity_base_points(t['id'],pts); st.rerun()
            fields=db.get_fields(t['id'])
            for f in fields:
                st.markdown(f"**{f['label']}**")
                st.caption(' · '.join(f"{o['label']} (+{o['points']})" for o in f['options']))
            st.markdown('**+ Eigen keuzeveld toevoegen**')
            label=st.text_input('Onderwerp / veldnaam',placeholder='Bijv. Aanwezigheid',key=f'new_field_{t["id"]}')
            count=st.number_input('Aantal opties',min_value=1,max_value=6,value=2,key=f'opt_count_{t["id"]}')
            options=[]
            for i in range(int(count)):
                c1,c2=st.columns([2,1]); name=c1.text_input(f'Optie {i+1}',key=f'opt_name_{t["id"]}_{i}'); op=c2.number_input('Punten',min_value=0,value=0,key=f'opt_pts_{t["id"]}_{i}'); options.append((name,op))
            if st.button('Veld toevoegen',key=f'field_add_{t["id"]}',disabled=not label or any(not n for n,_ in options)): db.add_select_field(t['id'],label,options); st.success('Veld toegevoegd.'); st.rerun()
    st.divider(); st.markdown('### Nieuw activiteitstype')
    name=st.text_input('Naam',key='new_type_name'); icon=st.text_input('Icoon',value='⭐',key='new_type_icon'); category=st.selectbox('Categorie',['training','fluiten','team','geld','club'],key='new_type_category'); base=st.number_input('Basispunten',min_value=0,value=0,key='new_type_base')
    if st.button('Activiteitstype toevoegen',type='primary',disabled=not name,key='new_type_save'): db.add_activity_type(name,icon,category,base); st.success('Toegevoegd.'); st.rerun()
