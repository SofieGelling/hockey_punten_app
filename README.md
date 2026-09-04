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

## Permanente opslag op Streamlit Cloud

Voor Streamlit Community Cloud gebruikt de app PostgreSQL in Supabase. Zet in
Streamlit Cloud bij je app onder `Settings` > `Secrets` deze gegevens uit
Supabase `Connect` > `Session pooler`:

```toml
[connections.postgresql]
dialect = "postgresql"
host = "aws-JOUW-REGIO.pooler.supabase.com"
port = "5432"
database = "postgres"
username = "postgres.JOUW-PROJECT-ID"
password = "JOUW-SUPABASE-DATABASE-WACHTWOORD"
```

Bij de eerste start maakt de app alle benodigde tabellen in Supabase aan.
Daarna blijven activiteiten, punten, taken, ideeën, meldingen, uitgaven,
inkomsten en bonnetjes in Supabase bewaard, ook na een herstart of nieuwe
deployment. Plaats Secrets nooit in GitHub.

Voor lokaal gebruik zonder Supabase blijft SQLite beschikbaar. Je kunt de locatie
daarvan desgewenst instellen met `TEAMAPP_DB_PATH=/pad/naar/teamapp.db`.
