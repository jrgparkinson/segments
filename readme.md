# Segment explorer
Tool for retrieving all segments and the fastest time in a particular region.

Requires a strava developer account to run.

# For retrieving results

1. Set environment variables: `STRAVA_SECRET`, `STRAVA_ID`, `FLASK_SECRET`.
2. Setup python environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
3. Run web server
```
python app.py
```
4. Go to `http://127.0.0.1:5000/retrieve` to retrieve results.


# For displaying results (static)

```
python3 -m http.server 8080
```

Visit `http://127.0.0.1:8080`.


