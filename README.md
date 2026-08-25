# Hockey TeamApp V2.5

Nieuwe mobiele prototype-versie.

## Starten
Dubbelklik op `start_app.command`, of voer uit:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Nieuw in V2.5
- Punten, rang en activiteiten compact naast elkaar op mobiel.
- Sidebar-navigatie via echte links: op mobiel klapt de sidebar na navigeren weer in wanneer Streamlit de pagina opnieuw opent.
- Klikbare spelercards openen een popup in plaats van een aparte pagina.
- Brainstormideeën zijn standaard ingeklapt.
- Zowel `Ik kan` als `Ik kan niet` kan later worden gewijzigd.
- `Bekijk alles` bij Recent opent Activiteiten > Alle recente.
- Activiteitenpagina bevat zowel eigen als teamactiviteiten.
- Eerste Teamrekening: saldo, inkomsten, uitgaven, grafiek, transacties, inkomsten invoeren, uitgaven invoeren en bon uploaden / geen bon / bon kwijt.
- Teamlijst gebruikt de namen uit het aangeleverde overzicht.

Let op: deze prototypeversie gebruikt SQLite in de projectmap. Voor een definitief online teamgebruik is een externe database (bijv. Supabase) verstandiger.
