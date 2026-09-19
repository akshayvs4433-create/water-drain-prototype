# DrainWatch

DrainWatch is a beginner-friendly Flask prototype for SC-08: Canal and Storm-Drain Blockage Reporting. Residents can upload a photo, pin a blockage with GPS or a map click, receive a prototype ward assignment and ticket ID, then follow the report through a public map and a simple response dashboard.

## Features

- Photo upload with JPG, JPEG and PNG validation
- Browser GPS plus a built-in clickable coordinate picker
- Prototype ward detection from coordinate ranges
- SQLite-backed ticket generation and tracking
- Status workflow: Reported, Verified, Assigned, In Progress, Resolved
- Public map of reports with marker info windows
- Automatic 48-hour escalation and an admin test-escalation button
- No external map API or key required

## Stack

HTML5, CSS3, JavaScript, Bootstrap 5, Python, Flask, SQLite and the browser Geolocation API.

## Project structure

```text
drainwatch/
├── app.py
├── requirements.txt
├── .env.example
├── drainwatch.db          # generated on first run, ignored by git
├── templates/
├── static/css/style.css
├── static/js/report.js
├── static/js/map.js
└── uploads/               # uploaded photos, ignored by git
```

## Install and run

From the `drainwatch` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open http://127.0.0.1:5000.

On Windows, activate the environment with `.venv\\Scripts\\activate` instead.

## Local map picker

No map API key is required. The report form uses a built-in clickable map area centered on the prototype location. Clicking it converts the point into valid latitude and longitude values; the browser GPS button remains available when location permission is granted. The public reports page uses the same coordinate projection to display clickable local markers.

## Prototype ward detection

`detect_ward()` in `app.py` uses three sample latitude/longitude ranges. A coordinate inside the Bengaluru-like sample range is labeled `Ward 27`; other sample regions map to Ward 14 or Ward 8. Coordinates outside those ranges are labeled `Prototype Review Zone`. Replace `WARD_RANGES` and this function with official GIS boundary data when it becomes available.

## Escalation

Every report starts with `escalated = false`. Each request checks whether an unresolved report is older than 48 hours and marks it escalated. The admin dashboard also includes **Test escalation**, which sets the flag immediately for a live demo. Resolving a report changes its status to `Resolved`; the record remains available for history while the public map reflects the new status.

## End-to-end demo

1. Open the home page and choose **Report a blockage**.
2. Upload a JPG/PNG image.
3. Choose **Use my location**, or click the map. Confirm the coordinates and detected ward.
4. Enter `Drain blocked with plastic waste.` and submit.
5. Copy the generated ticket ID, then open the ticket confirmation and **Track this report**.
6. Open `/admin`, move the report through the status selector, and use **Test escalation**.
7. Open **Open reports** to see the marker and its public info window.
8. Set the report to `Resolved` and refresh the public page.

## SC-08 coverage

The prototype implements resident reporting, GPS/map location, prototype ward routing, unique tickets, status tracking, public unresolved reports, escalation, SQLite persistence and an end-to-end admin demonstration. Official ward boundaries, address reverse geocoding, authentication and production notification channels are deliberately left as future integrations.

## Future improvements

Use official ward GIS polygons, add reverse geocoding, add role-based authentication, send SMS/email updates, add CSRF protection and deploy SQLite behind a production database backup strategy.
