IFM Campus Venues

Find a free lecture room right now, or see your class timetable, from your phone.

Free Now / In Use: live room status with how long a room stays free
2+ hours filter: finds rooms for group study
My Classes: pick your course and tutorial group to see your week
Favourites and share: star rooms and share a room’s status
Private by design: no accounts, no tracking. Only your course and favourites are saved, on your own device.

How it works: convert.py turns the CELCAT timetable PDFs into timetable.json. The page in index.html reads that file and works out which rooms are free from the phone’s clock.

Security: there are no external scripts. Styling is self-hosted in styles.css, and a Content-Security-Policy blocks unexpected code.

Data note: based on the “Draft TWO” timetable, so room details can change. Always confirm with your lecturer.

Run it locally: python3 -m http.server, then open http://localhost:8000.
