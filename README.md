# Hockey TeamApp V2.1 – visueel prototype

Deze map is een aparte V2.1 om eerst de nieuwe app-structuur te bekijken.

## Starten

```bash
python3 -m pip install -r requirements.txt
streamlit run app.py
```

Of dubbelklik op `start_app.command` op macOS.

## Demo-login
- Sofie / Lisa / Emma / Noor / Anna: speler
- Beheerder: beheerderweergave

## Wat al zichtbaar/klikbaar is
- mobiele onderste navigatie
- persoonlijk Home-dashboard
- komende taken voor jou + Kan / Kan niet met zichtbare reden
- ranglijst en advies wie aan de beurt is
- activiteiten direct toevoegen, zonder goedkeuring
- Mijn activiteiten + wijzigingsverzoek
- flexibele activiteitvelden met opties en punten
- lijst + maandkalender, Mijn agenda / Hele team
- meerdere personen per taak
- brainstormmappen, ideeën, stemmen, reacties, puntenvoorstel
- beheerderstatus voor ideeën
- meldingen
- eerste statistiekenpagina

Dit is bewust een ontwerp/prototype. De data staat lokaal in SQLite.


## V2.1 wijzigingen
- Fout met `st.info(+recommendation())` opgelost.
- Tekst `(zichtbaar voor iedereen)` verwijderd bij reden invullen.
- Een antwoord `Ik kan niet` kan later worden gewijzigd naar `Toch wel kunnen`.
- De opgegeven reden kan later worden bewerkt.


## V2.2 wijzigingen
- Spelercards op Home en in de Ranglijst zijn klikbaar.
- Klik op een speler om diens punten, rang en activiteiten te bekijken.
- Pagina Statistieken is verwijderd.
- Alle date_input-velden in Toevoegen hebben unieke Streamlit keys.
- TypeError bij recommendation is opgelost.
- Bij 'Ik kan niet' kan de speler later de reden wijzigen of alsnog aangeven te kunnen.
- Het label bij de reden vermeldt niet meer '(zichtbaar voor iedereen)'.


## V2.3
- Onderste mobiele navigatie verwijderd.
- Alle navigatie staat in de inklapbare linker sidebar.
- Sidebar opent standaard op desktop; op telefoon blijft deze via het hamburgericoon bereikbaar.


## V2.4
- De huidige pagina en ingelogde naam blijven behouden na verversen via URL-queryparameters.
- Ook een geopende spelercard en brainstormmap worden na verversen hersteld.
- Op telefoons is extra ruimte boven de content toegevoegd zodat de Streamlit-balk de paginatitel niet bedekt.
