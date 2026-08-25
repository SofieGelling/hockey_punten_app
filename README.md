# Hockey Team Punten-app

Mobielvriendelijke Streamlit-app voor een hockeyteam. Spelers bouwen punten op door teamtaken en geldinzamelingsactiviteiten te doen. Nieuwe activiteiten worden eerst ingediend en tellen pas mee na goedkeuring door een beheerder.

## Wat zit erin?

- Inloggen met alleen je naam
- Persoonlijke startkaart met punten, positie en aantal activiteiten
- Ranglijst met horizontale balken of spelercards
- Activiteiten indienen
- Goedkeuringsflow voor beheerders
- Instelbare vaste punten per activiteit
- Training geven, fluiten, geld-opbrengende activiteit, bardienst en sleepover als startactiviteiten
- Optioneel geldbedrag en beschrijving bij een activiteit
- Recente activiteiten
- Komende taken
- Automatisch advies wie met de minste punten als eerste voor een volgende taak in aanmerking komt
- Spelers en nieuwe activiteitstypen toevoegen
- Lichte mobiele stijl met blauwe tinten
- SQLite-opslag voor lokale ontwikkeling

## Starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

De database `hockey_app.db` wordt automatisch aangemaakt bij de eerste start.

## Demo-login

Bij de eerste start worden een paar voorbeeldspelers aangemaakt. `Beheerder` heeft beheerdersrechten. Vervang deze via **Instellingen → Spelers** door jullie echte teamleden.

## Belangrijk over de naam-login

Een login met alleen een naam is eenvoudig, maar niet veilig: iemand kan een andere naam selecteren. Dat is prima voor een gesloten prototype, maar voor een echte teamdeployment raad ik minimaal een persoonlijke PIN aan.

## Online publiceren

SQLite is geschikt voor lokaal testen. Voor gebruik door het hele team op een gehoste Streamlit-app is een externe database zoals Supabase/PostgreSQL beter, zodat data niet afhankelijk is van de lokale app-container. De functies in `db.py` zijn bewust apart gehouden zodat deze overstap later overzichtelijk blijft.

## Logica van punten

De puntenwaarde wordt bij het indienen van een activiteit vastgelegd. Als een beheerder later bijvoorbeeld `Fluiten` van 3 naar 4 punten wijzigt, krijgen nieuwe inzendingen 4 punten. Bestaande goedgekeurde activiteiten blijven op hun oorspronkelijke puntenwaarde staan.

## Volgende uitbreidingen

- echte teamleden en clubnaam
- profielfoto's
- persoonlijke PIN/accountlogin
- Supabase-database
- taken accepteren/ruilen
- push/e-mailnotificaties
- filters per maand/seizoen
- aparte pagina's met `st.Page` / `st.navigation`
- uitgebreide categorie- en trendgrafieken
