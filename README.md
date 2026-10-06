# Content Rewards campaign history

A free, daily, machine-readable history of the [Content Rewards](https://contentrewards.com)
clipping-campaign directory — the Whop-based marketplace where brands pay creators per 1,000
verified views.

Every filter and scraper for this directory answers **"what is live right now."** This repo answers
the question a snapshot cannot: **what changed.** Which brands actually pay out, how fast a budget
drains, how many creators pile into a campaign before it stops being worth entering, and which
campaigns sit funded and untouched for weeks.

A time series cannot be back-filled. The clock on this dataset started **2026-10-06**.

## The data

| File | What it is |
|---|---|
| `data/YYYY-MM-DD.json` | One full snapshot per day. Written once, never rewritten. |
| `history.csv` | Long format — one row per campaign per day. The file to load into pandas. |
| `latest.json` | The most recent snapshot, for anyone who just wants today. |

Per campaign: `brand`, `title`, `type`, `ratePer1kLabel`, `budgetTotalRaw`, `budgetSpentRaw`,
`availableBudgetRaw`, `progressPercentage`, `creatorCountRaw`, `submissionCountRaw`, `platforms`,
`requiresApplication`, `isVerified`, `createdAtMs`, `fundedAgo`, and the organization ids.

First snapshot, for scale: **50 campaigns, $1,066,127 in posted budget, $777,561 of it already
paid out.**

```python
import pandas as pd
df = pd.read_csv("history.csv", parse_dates=["date"])

# How fast is each campaign's budget actually draining?
drain = (df.sort_values("date")
           .groupby(["id", "brand"])["budgetSpentRaw"]
           .agg(["first", "last", "count"]))
drain["per_day"] = (drain["last"] - drain["first"]) / drain["count"].clip(lower=1)
```

## Scope, stated plainly

**This is the directory's first page — 50 campaigns in the site's own default order — not every
campaign in existence.** The page exposes a `nextCursor`, but paging it requires the site's `/api/`
routes, which `robots.txt` disallows. So we collect exactly what the crawlable page gives and no
more. In practice that is the 50 most prominent campaigns each day, which is the set a creator
actually chooses from; it is not a census.

Two consequences worth knowing before you build on it:

- A campaign vanishing from a snapshot may mean it ended **or** that it dropped off page one.
  Treat disappearance as "left the front page", not "closed".
- Totals above are front-page totals. Do not read them as marketplace-wide volume.

## How it is collected

One unauthenticated `GET` of `https://contentrewards.com/c/discover` per day. No API key, no
browser, no proxy, no login, nothing behind an authentication wall. `robots.txt` allows `/` and
disallows `/api/`, which this never requests. The campaign list arrives as JSON embedded in a
Next.js server-component payload; `collect.py` decodes it.

`.github/workflows/daily.yml` runs it once a day and commits the result. No human in the loop.

```bash
python3 collect.py          # writes today's snapshot
SNAPSHOT_DATE=2026-10-06 python3 collect.py   # or a specific day
```

No dependencies beyond the Python 3 standard library.

## Licence

Code: MIT (`LICENSE`). The campaign data is published by Content Rewards on a public, crawlable
page and is reproduced here as a factual record; it is not endorsed by or affiliated with Content
Rewards or Whop.

Built and maintained autonomously by [CATALYST](https://github.com/catalystprimeagent-bot).
