from flask import Flask, request, redirect, render_template_string
import sqlite3
import folium

app = Flask(__name__)
DB_NAME = "floodguard.db"


# Create database and preserve existing reports
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                latitude REAL,
                longitude REAL
            )
        """)

        columns = [
            row[1] for row in
            conn.execute("PRAGMA table_info(reports)").fetchall()
        ]

        if "latitude" not in columns:
            conn.execute(
                "ALTER TABLE reports ADD COLUMN latitude REAL"
            )

        if "longitude" not in columns:
            conn.execute(
                "ALTER TABLE reports ADD COLUMN longitude REAL"
            )


PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FloodGuard AI</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #eef4fb;
    color: #183153;
}
header {
    background: #102b50;
    color: white;
    padding: 22px 7%;
}
header h1 { margin: 0; }
header p { color: #c8d9ef; }
main {
    max-width: 1000px;
    margin: 30px auto;
    padding: 0 18px;
}
.hero {
    background: linear-gradient(120deg, #153e70, #1685b5);
    color: white;
    padding: 30px;
    border-radius: 16px;
    margin-bottom: 24px;
}
.panel {
    background: white;
    padding: 25px;
    border-radius: 15px;
    margin-bottom: 24px;
    box-shadow: 0 4px 18px #dce5f0;
}
label {
    display: block;
    font-weight: bold;
    margin: 15px 0 7px;
}
input, select, textarea {
    width: 100%;
    padding: 12px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font: inherit;
}
textarea { min-height: 90px; }
button {
    margin-top: 16px;
    background: #1677d2;
    color: white;
    border: 0;
    padding: 13px 20px;
    border-radius: 8px;
    cursor: pointer;
    font-weight: bold;
}
.report {
    border: 1px solid #dce5f0;
    padding: 16px;
    border-radius: 10px;
    margin-top: 12px;
}
.Low { color: #16805d; }
.Medium { color: #b77900; }
.High { color: #c62828; }
.map {
    width: 100%;
    height: 480px;
    border: 0;
}
.note { color: #64748b; font-size: 14px; }
footer { text-align: center; padding: 20px; color: #64748b; }
</style>
</head>
<body>
<header>
    <h1>🌧️ FloodGuard AI</h1>
    <p>Smart Urban Flood Risk & Waterlogging Management</p>
</header>

<main>
    <section class="hero">
        <h2>Building Safer, Resilient Cities</h2>
        <p>Report waterlogging and explore reported locations in your city.</p>
    </section>

    <section class="panel">
        <h2>📍 Report Waterlogging</h2>
        <form method="POST" action="/report">
            <label for="location">Road or location name</label>
            <input id="location" name="location" required maxlength="150"
                   placeholder="e.g. Main Road, Ward 4">

            <label for="latitude">Latitude (optional)</label>
            <input id="latitude" type="number" name="latitude"
                   step="any" min="-90" max="90" placeholder="e.g. 19.0760">

            <label for="longitude">Longitude (optional)</label>
            <input id="longitude" type="number" name="longitude"
                   step="any" min="-180" max="180" placeholder="e.g. 72.8777">

            <label for="severity">Severity</label>
            <select id="severity" name="severity">
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
            </select>

            <label for="description">Description</label>
            <textarea id="description" name="description" required
                      maxlength="1000"
                      placeholder="Describe the waterlogging..."></textarea>

            <button type="submit">Submit Report</button>
        </form>
        <p class="note">
            Community reports are not official emergency alerts.
        </p>
    </section>

    <section class="panel">
        <h2>🗺️ Waterlogging Map</h2>
        <p class="note">
            Markers show submitted reports that have coordinates.
        </p>
        <iframe class="map" src="/map" title="Waterlogging map"></iframe>
    </section>

    <section class="panel">
        <h2>Recent Waterlogging Reports</h2>
        {% for r in reports %}
        <div class="report">
            <h3>{{ r[1] }}</h3>
            <p>Severity:
                <strong class="{{ r[2] }}">{{ r[2] }}</strong>
            </p>
            <p>{{ r[3] }}</p>
            {% if r[4] is not none and r[5] is not none %}
            <p class="note">Coordinates: {{ r[4] }}, {{ r[5] }}</p>
            {% else %}
            <p class="note">No coordinates provided.</p>
            {% endif %}
            <p class="note">Report #{{ r[0] }}</p>
        </div>
        {% else %}
        <p>No reports yet. Submit your first report above.</p>
        {% endfor %}
    </section>
</main>

<footer>FloodGuard AI | Urban Development Innovation Project</footer>
</body>
</html>
"""


@app.route("/")
def home():
    with sqlite3.connect(DB_NAME) as conn:
        reports = conn.execute("""
            SELECT id, location, severity, description,
                   latitude, longitude
            FROM reports
            ORDER BY id DESC
        """).fetchall()

    return render_template_string(PAGE, reports=reports)


@app.route("/report", methods=["POST"])
def submit_report():
    location = request.form.get("location", "").strip()
    severity = request.form.get("severity", "")
    description = request.form.get("description", "").strip()
    lat_text = request.form.get("latitude", "").strip()
    lon_text = request.form.get("longitude", "").strip()

    if not location or not description:
        return "Location and description are required.", 400

    if severity not in ("Low", "Medium", "High"):
        return "Invalid severity.", 400

    if bool(lat_text) != bool(lon_text):
        return "Enter both coordinates or leave both blank.", 400

    latitude = longitude = None

    if lat_text and lon_text:
        try:
            latitude = float(lat_text)
            longitude = float(lon_text)
        except ValueError:
            return "Coordinates must be numbers.", 400

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return "Coordinates are outside valid ranges.", 400

    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO reports
            (location, severity, description, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
        """, (location, severity, description, latitude, longitude))

    return redirect("/")


@app.route("/map")
def show_map():
    city_map = folium.Map(
        location=[19.0760, 72.8777],
        zoom_start=11,
        control_scale=True
    )

    with sqlite3.connect(DB_NAME) as conn:
        reports = conn.execute("""
            SELECT id, location, severity, description,
                   latitude, longitude
            FROM reports
            WHERE latitude IS NOT NULL
              AND longitude IS NOT NULL
        """).fetchall()

    colors = {
        "Low": "green",
        "Medium": "orange",
        "High": "red"
    }

    for report in reports:
        folium.Marker(
            location=[report[4], report[5]],
            tooltip=f"{report[1]} - {report[2]} severity",
            popup=(
                f"Report #{report[0]}: {report[1]} | "
                f"Severity: {report[2]} | {report[3]}"
            ),
            icon=folium.Icon(
                color=colors.get(report[2], "blue")
            )
        ).add_to(city_map)

    return city_map.get_root().render()


init_db()

if __name__ == "__main__":
    app.run(debug=True)