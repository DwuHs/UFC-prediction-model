from bs4 import BeautifulSoup
import csv
import hashlib
import re
import time
from pathlib import Path

import requests

EVENTS_URL = "http://ufcstats.com/statistics/events/completed?page=all"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "fights_raw.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
FIELDNAMES = ["date", "fighter a", "fighter b", "result"]


def get_session_page(session: requests.Session, url: str) -> requests.Response:
    """Fetch a ufcstats page, solving the JS browser check if present."""
    response = session.get(url)
    if "Checking your browser" not in response.text:
        return response

    nonce = re.search(r'nonce="([^"]+)"', response.text).group(1)
    zeros_match = re.search(r"new Array\((\d+)\+1\)\.join\('0'\)", response.text)
    zeros = int(zeros_match.group(1)) if zeros_match else 2
    target = "0" * zeros

    n = 0
    while not hashlib.sha256(f"{nonce}:{n}".encode()).hexdigest().startswith(target):
        n += 1

    session.post(
        "http://ufcstats.com/__c",
        data={"nonce": nonce, "n": str(n)},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": url,
        },
    )
    return session.get(url)


def get_event_links(html: str) -> list[tuple[str, str]]:
    """Return (event_url, date) pairs from the completed events list."""
    soup = BeautifulSoup(html, "html.parser")
    events = []

    for row in soup.select("tr.b-statistics__table-row"):
        link = row.select_one("a.b-link.b-link_style_black")
        date_el = row.select_one("span.b-statistics__date")
        if link is None or date_el is None:
            continue
        href = link.get("href", "")
        if "event-details" not in href:
            continue
        events.append((href, date_el.get_text(strip=True)))

    return events


def parse_event_fights(html: str, event_date: str):
    """Yield raw fight rows from an event page."""
    soup = BeautifulSoup(html, "html.parser")

    for row in soup.select("tr.b-fight-details__table-row"):
        fighter_links = row.select(
            "td.b-fight-details__table-col.l-page_align_left a.b-link"
        )
        if len(fighter_links) < 2:
            continue

        flag = row.select_one("a.b-flag .b-flag__text")
        result = flag.get_text(strip=True) if flag else ""

        fighter_a = fighter_links[0].get_text(strip=True)
        fighter_b = fighter_links[1].get_text(strip=True)

        yield {
            "date": event_date,
            "fighter a": fighter_a,
            "fighter b": fighter_b,
            "result": result,
        }


def load_existing(path: Path) -> tuple[set[str], set[tuple[str, str, str]]]:
    """Load parsed event dates and fight keys already in the CSV.

    The last date in the file is treated as possibly incomplete (scrape may have
    stopped mid-event), so it is not skipped and will be re-checked.
    """
    parsed_dates: set[str] = set()
    fight_keys: set[tuple[str, str, str]] = set()
    last_date = None

    if not path.exists() or path.stat().st_size == 0:
        return parsed_dates, fight_keys

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row["date"]
            parsed_dates.add(date)
            fight_keys.add((date, row["fighter a"], row["fighter b"]))
            last_date = date

    if last_date is not None:
        parsed_dates.discard(last_date)

    return parsed_dates, fight_keys


def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    print(f"Fetching events list: {EVENTS_URL}", flush=True)
    events_response = get_session_page(session, EVENTS_URL)
    events = get_event_links(events_response.text)
    print(f"Found {len(events)} events", flush=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    parsed_dates, fight_keys = load_existing(OUTPUT_PATH)
    print(f"Skipping {len(parsed_dates)} already-parsed event dates", flush=True)

    file_exists = OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0
    fight_count = 0
    skipped = 0

    with OUTPUT_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
            f.flush()

        for i, (event_url, event_date) in enumerate(events, start=1):
            if event_date in parsed_dates:
                skipped += 1
                print(
                    f"[{i}/{len(events)}] skip {event_date} — already parsed",
                    flush=True,
                )
                continue

            print(f"[{i}/{len(events)}] {event_date} — {event_url}", flush=True)
            event_response = get_session_page(session, event_url)

            for fight in parse_event_fights(event_response.text, event_date):
                key = (fight["date"], fight["fighter a"], fight["fighter b"])
                if key in fight_keys:
                    continue

                writer.writerow(fight)
                f.flush()
                fight_keys.add(key)
                fight_count += 1
                print(
                    f"  {fight['date']}, {fight['fighter a']}, "
                    f"{fight['fighter b']}, {fight['result']}",
                    flush=True,
                )

            parsed_dates.add(event_date)
            time.sleep(0.3)

    print(
        f"Done. Wrote {fight_count} new fights "
        f"({skipped} events skipped) to {OUTPUT_PATH}",
        flush=True,
    )


if __name__ == "__main__":
    main()
