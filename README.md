# KilimoSmart

AI-driven agricultural platform prototype for de-risking small-holder farmers facing
unpredictable climate change. KilimoSmart analyzes soil chemistry, weather patterns, and
regional market prices to deliver profit-optimized crop recommendations — reachable over
USSD/SMS so feature-phone users with low connectivity and high data costs can still access it.

This repository contains the PLP-2 deliverable: a menu-driven, object-oriented Python
command-line prototype that simulates a USSD session end-to-end.

## Running it

Farmer profiles and recommendation history are stored in MySQL. Start XAMPP's
MySQL server first (default `root` user, no password, `127.0.0.1:3306` — override
with the `KILIMOSMART_DB_HOST` / `KILIMOSMART_DB_PORT` / `KILIMOSMART_DB_USER` /
`KILIMOSMART_DB_PASSWORD` / `KILIMOSMART_DB_NAME` env vars if yours differs). The
`kilimosmart` database and its tables are created automatically on first run.

```bash
pip install -r requirements.txt
python main.py
```

You'll be prompted to "dial in" with a phone number, then navigate a numbered USSD-style
menu:

1. Register / update my farm (with SMS alerts opt-in)
2. Get a profit-optimized crop recommendation
3. View weather forecast (with a drought-resilience tip when the outlook is poor)
4. View today's market prices
5. View my farm profile and recent recommendation history
6. Toggle SMS alerts on/off

A single phone number can own several farms. Option 1 offers "register a new farm" or
"update an existing farm" once you have at least one; options 2 and 6 ask which farm to
act on whenever you have more than one; and option 5 lists every farm registered to that
number along with each farm's own recommendation history.

Enter `admin` instead of a phone number to see platform-wide insights (registered farmers,
SMS opt-in rate, farmers by region, most-recommended crops) — the operator-facing view of
the same data a real deployment would show on a dashboard.

## Running the tests

Tests run against a dedicated `kilimosmart_test` MySQL database (also created
automatically), separate from the `kilimosmart` database used by the app, so
they never touch real data.

```bash
python -m unittest discover -s tests
```

## Project structure

```
main.py                    Entry point / session loop
kilimosmart/
  models.py                Farmer, Crop, SoilProfile, WeatherForecast, MarketPrice, Recommendation, RecommendationLog
  data_store.py            MockDataProvider — soil/weather/crop/market mock data (swap for real APIs later)
  recommendation.py        RecommendationEngine — profit-optimized crop scoring
  repository.py            FarmerRepository — MySQL persistence (farmer profiles + recommendation history)
  session.py                USSDSession — CON/END screen state machine
  sms.py                    SMSSimulator — stands in for a real SMS gateway (e.g. Africa's Talking)
  analytics.py              PlatformAnalytics — operator-facing aggregate insights across all farmers
  validators.py             Phone number validation
tests/                      unittest suite for the recommendation engine, repository, session, and analytics
requirements.txt           Python dependencies (mysql-connector-python)
```

## Notes on this prototype

- Soil, weather, and market data are simulated (`MockDataProvider`) rather than pulled from
  live APIs, since this milestone focuses on the recommendation logic and USSD-style UX.
  Market prices use a day-seeded random walk so they look "live" while staying reproducible.
- The terminal menu mirrors a real USSD gateway's CON (continue) / END (terminate) screen
  model, so the same `USSDSession` class could later sit behind an actual Africa's
  Talking/Safaricom USSD or SMS webhook with no changes to the recommendation logic.
- SMS delivery is simulated by printing `[SMS -> phone] message` lines; swapping `SMSSimulator`
  for a real gateway client is the only change needed to go live.
- When a region's weather outlook is "poor," the app surfaces a climate-resilience tip
  (drought-tolerant crop suggestions) and, for opted-in farmers, sends a simulated proactive
  SMS alert — directly supporting the "build long-term climate resilience" goal.

