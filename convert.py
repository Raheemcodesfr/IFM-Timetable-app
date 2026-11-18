#!/usr/bin/env python3
"""
convert.py - turn timetable.csv into timetable.json for the Campus Venues app.

Usage:
    python convert.py                       # timetable.csv -> timetable.json
    python convert.py in.csv out.json       # custom paths

Input columns : Day, Start Time, End Time, Venue, Module, Type, Course
Output keys   : day, start, end, venue, module, type, course

Rules applied
  1. A Venue cell with several rooms ("111 / 215 / TH_E") becomes one object per room.
  2. Underscores in room names become spaces (TH_E -> TH E).
  3. Entries are de-duplicated on Day + Start + End + Venue + Course.
  4. Rows with no venue are skipped (a room-availability app can't use them).
"""

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Rename venues after splitting. Empty by default.
# The PDFs contain a venue written "F/H" (which splits into "F" and "H"). If those are really
# the theatres "TH F" and "TH H", uncomment the next line so their bookings land on the right rooms:
VENUE_ALIASES = {
    # "F": "TH F",
    # "H": "TH H",
}


def clean(text):
    """Trim and collapse runs of whitespace."""
    return re.sub(r"\s+", " ", (text or "").strip())


def normalize_day(text):
    t = clean(text).lower()
    if len(t) < 3:
        return None
    for d in DAY_ORDER:
        if d.lower().startswith(t[:3]):   # accepts "Mon", "monday", "MONDAY"
            return d
    return None


def normalize_time(text):
    """'7:00' / '07:00' / '07:00:00' -> '07:00'. Returns None if unparseable."""
    m = re.match(r"^\s*(\d{1,2}):(\d{2})(?::\d{2})?\s*$", text or "")
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 23 or mi > 59:
        return None
    return f"{h:02d}:{mi:02d}"


def split_venues(cell):
    """'111 / 215 / TH_E' -> ['111', '215', 'TH E'] (underscores -> spaces, order kept, no repeats)."""
    seen, out = set(), []
    for part in (cell or "").split("/"):
        v = clean(part.replace("_", " "))
        v = VENUE_ALIASES.get(v, v)
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def fix_module(text):
    """
    Repair module codes that were broken across lines in the PDF extraction,
    e.g. 'G3_TMT_0410 / 8' -> 'G3_TMT_04108' and 'IRD_ 06102' -> 'IRD_06102'.
    Genuine lists such as 'G1_ITU 07104 / G2_ITU 07105' are left alone.
    """
    t = clean(text)
    t = re.sub(r"_ (?=\d)", "_", t)
    t = re.sub(r"(_\d{4}) / (\d)(?=\s|/|$)", r"\1\2", t)
    return t


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "timetable.csv")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else "timetable.json")

    if not src.exists():
        sys.exit(f"Cannot find {src}. Put it next to convert.py or pass the path.")

    stats = Counter()
    seen = {}      # dedupe key -> module already stored (to report real conflicts)
    out = []

    # utf-8-sig silently drops the BOM that Excel adds when saving CSV
    with src.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # tolerate header case/spacing differences
        reader.fieldnames = [clean(h).lower() for h in reader.fieldnames or []]
        needed = {"day", "start time", "end time", "venue", "module", "type", "course"}
        missing = needed - set(reader.fieldnames)
        if missing:
            sys.exit(f"CSV is missing columns: {', '.join(sorted(missing))}")

        for line_no, row in enumerate(reader, start=2):
            stats["rows_read"] += 1

            day = normalize_day(row["day"])
            start = normalize_time(row["start time"])
            end = normalize_time(row["end time"])
            if not (day and start and end and start < end):
                stats["skipped_bad_day_or_time"] += 1
                print(f"  line {line_no}: bad day/time, skipped -> {row}")
                continue

            venues = split_venues(row["venue"])
            if not venues:
                stats["skipped_no_venue"] += 1
                continue

            module = fix_module(row["module"])
            ctype = clean(row["type"].replace("_", " ")) or "Class"
            course = clean(row["course"])  # keep codes like BAcc_3A exactly as written

            if len(venues) > 1:
                stats["rows_split_into_rooms"] += 1

            for venue in venues:
                key = (day, start, end, venue, course)
                if key in seen:
                    stats["duplicates_removed"] += 1
                    if seen[key] != module:
                        stats["duplicates_with_different_module"] += 1
                    continue
                seen[key] = module
                out.append({
                    "day": day,
                    "start": start,
                    "end": end,
                    "venue": venue,
                    "module": module,
                    "type": ctype,
                    "course": course,
                })

    def sort_key(b):
        return (DAY_ORDER.index(b["day"]), b["start"], b["venue"], b["course"])

    out.sort(key=sort_key)

    with dst.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"Read {stats['rows_read']} CSV rows -> wrote {len(out)} bookings to {dst}")
    print(f"  distinct venues            : {len({b['venue'] for b in out})}")
    print(f"  rows split into rooms      : {stats['rows_split_into_rooms']}")
    print(f"  duplicates removed         : {stats['duplicates_removed']}")
    if stats["duplicates_with_different_module"]:
        print(f"    (of which different module: {stats['duplicates_with_different_module']})")
    print(f"  skipped (no venue)         : {stats['skipped_no_venue']}")
    print(f"  skipped (bad day/time)     : {stats['skipped_bad_day_or_time']}")


if __name__ == "__main__":
    main()
