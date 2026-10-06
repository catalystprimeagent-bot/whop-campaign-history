#!/usr/bin/env python3
"""Take one daily snapshot of the Content Rewards campaign directory.

Source: https://contentrewards.com/c/discover  (one unauthenticated GET, no API key,
no browser, no proxy). robots.txt allows `/`; `/api/` is disallowed and we never touch it.

The page is a Next.js server-component payload: the campaign list is JSON embedded inside a
JS string literal, so quotes arrive as \\" and the structure needs two decodes.

Writes:
  data/YYYY-MM-DD.json  full snapshot for that day (one file per day, never overwritten)
  history.csv           one row per campaign per day, appended
  latest.json           the most recent snapshot, for convenience
"""

import csv
import datetime
import json
import os
import pathlib
import sys
import urllib.request

URL = "https://contentrewards.com/c/discover"
UA = ("catalyst-whop-campaign-history/1.0 "
      "(+https://github.com/catalystprimeagent-bot/whop-campaign-history)")
ROOT = pathlib.Path(__file__).resolve().parent

# Dropped on purpose: avatar, thumbnail, avatarSeed (S3 URLs, no analytical value) and
# description (long marketing prose; it would multiply the repo size every single day).
FIELDS = [
    "id", "brand", "title", "type", "category", "group",
    "ratePer1kLabel", "payoutSortRaw",
    "budgetTotalRaw", "budgetSpentRaw", "availableBudgetRaw", "progressPercentage",
    "creatorCountRaw", "submissionCountRaw",
    "platforms", "requiresApplication", "isVerified", "opensAt",
    "createdAtMs", "fundedAgo",
    "organizationId", "organizationExperienceId", "organizationProfileHandle",
]

CSV_COLUMNS = ["date"] + FIELDS


def fetch(url=URL):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def extract(html):
    """Pull the campaigns array out of the escaped flight payload.

    Scans the *escaped* text, where a string delimiter is the two-character sequence \\"
    rather than a bare quote, so braces inside campaign prose cannot throw the depth count off.
    """
    key = '\\"campaigns\\":'
    i = html.find(key)
    if i == -1:
        raise SystemExit("FAIL: no campaigns key on the page. The layout changed, or the "
                         "directory moved behind a login.")
    start = html.index("[", i)
    k, depth, instr = start, 0, False
    while k < len(html):
        c = html[k]
        if instr:
            if c == "\\" and html[k + 1] == '"':
                instr = False
                k += 2
                continue
            k += 2 if c == "\\" else 1
            continue
        if c == "\\" and html[k + 1] == '"':
            instr = True
            k += 2
            continue
        if c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
            if depth == 0:
                k += 1
                break
        k += 1
    campaigns = json.loads(json.loads('"' + html[start:k] + '"'))
    if not isinstance(campaigns, list) or not campaigns:
        raise SystemExit("FAIL: campaigns array parsed but is empty.")
    return campaigns


def slim(c):
    return {f: c.get(f) for f in FIELDS}


def main():
    day = os.environ.get("SNAPSHOT_DATE") or datetime.date.today().isoformat()
    html = fetch()
    campaigns = [slim(c) for c in extract(html)]

    total = sum(c["budgetTotalRaw"] or 0 for c in campaigns)
    spent = sum(c["budgetSpentRaw"] or 0 for c in campaigns)
    snapshot = {
        "date": day,
        "capturedAtUtc": datetime.datetime.now(datetime.timezone.utc)
                                  .replace(microsecond=0).isoformat(),
        "source": URL,
        "campaignCount": len(campaigns),
        # Honest scope: this is the directory's own first page, not every campaign that exists.
        "scope": "first page of the discover directory, in the site's default order",
        "budgetTotalSum": round(total, 2),
        "budgetSpentSum": round(spent, 2),
        "campaigns": campaigns,
    }

    (ROOT / "data").mkdir(exist_ok=True)
    out = ROOT / "data" / f"{day}.json"
    if out.exists():
        print(f"{day} already captured ({out}); not overwriting.")
        return 0
    out.write_text(json.dumps(snapshot, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "latest.json").write_text(
        json.dumps(snapshot, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    hist = ROOT / "history.csv"
    new = not hist.exists()
    with hist.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        if new:
            w.writeheader()
        for c in campaigns:
            row = dict(c, date=day)
            row["platforms"] = "|".join(c["platforms"] or [])
            w.writerow(row)

    print(f"{day}: {len(campaigns)} campaigns, "
          f"${total:,.0f} budget posted, ${spent:,.0f} paid out so far")
    return 0


if __name__ == "__main__":
    sys.exit(main())
