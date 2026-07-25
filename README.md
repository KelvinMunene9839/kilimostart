# KilimoSmart

AI-driven agricultural platform prototype for de-risking small-holder farmers facing
unpredictable climate change. KilimoSmart analyzes soil chemistry, weather patterns, and
regional market prices to deliver profit-optimized crop recommendations — reachable over
USSD/SMS so feature-phone users with low connectivity and high data costs can still access it.

This repository contains the PLP-2 deliverable: a menu-driven, object-oriented Python
command-line prototype that simulates a USSD session end-to-end.

## Running it

```bash
python main.py
```

You'll be prompted to "dial in" with a phone number, then navigate a numbered USSD-style
menu (register your farm, get a crop recommendation, check weather, check market prices,
view your profile).

## Project structure

```
main.py                    Entry point / session loop
kilimosmart/
  models.py                Farmer, Crop, SoilProfile, WeatherForecast, MarketPrice, Recommendation
  data_store.py            MockDataProvider — soil/weather/crop/market mock data (swap for real APIs later)
  recommendation.py        RecommendationEngine — profit-optimized crop scoring
  repository.py            FarmerRepository — offline JSON-file persistence
  session.py                USSDSession — CON/END screen state machine
data/farmers.json          Registered farmer profiles (created at runtime, gitignored)
```

## Notes on this prototype

- Soil, weather, and market data are simulated (`MockDataProvider`) rather than pulled from
  live APIs, since this milestone focuses on the recommendation logic and USSD-style UX.
  Market prices use a day-seeded random walk so they look "live" while staying reproducible.
- The terminal menu mirrors a real USSD gateway's CON (continue) / END (terminate) screen
  model, so the same `USSDSession` class could later sit behind an actual Africa's
  Talking/Safaricom USSD or SMS webhook with no changes to the recommendation logic.
