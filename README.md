# Hockey TeamApp

Alle gegevens van de app staan in een SQLite-database. De app wist bij een
start nooit automatisch activiteiten, punten, taken, ideeën, meldingen of
teamrekening-transacties.

## Lokaal starten

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

De lokale database staat standaard in `teamapp_v2_5.db` naast de broncode. Dit
bestand hoort niet verwijderd of vervangen te worden als de teamgeschiedenis
behouden moet blijven.

## Permanente opslag bij deployment

Geef de app op een server een vast databestand op een permanente schijf mee:

```bash
TEAMAPP_DB_PATH=/pad/naar/permanente-opslag/teamapp.db
```

De map van dit pad moet een permanente volume/schijf van de host zijn. Een
platform met alleen tijdelijke bestandsopslag kan een SQLite-bestand bij een
herstart verliezen; daarvoor is een permanente volume of een externe database
nodig. GitHub zelf is geen database en bewaart nieuwe invoer uit een draaiende
app niet automatisch.
