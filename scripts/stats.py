"""Render GitHub stats as an SVG in the same type style as the profile header."""

import json
import os
import sys
import urllib.request
from datetime import date

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100) {
      totalCount
      nodes { stargazerCount }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 150" width="850" height="150" role="img" aria-label="{label}">
  <style>
    .num {{ font: 700 42px "Helvetica Neue", Arial, sans-serif; letter-spacing: 4px; text-anchor: middle; fill: #f0f6fc; }}
    .en {{ font: 400 11px "Helvetica Neue", Arial, sans-serif; letter-spacing: 3px; text-anchor: middle; fill: #6e7681; }}
    .jp {{ font: 400 14px "Hiragino Sans", "Noto Sans CJK JP", "Yu Gothic", sans-serif; letter-spacing: 6px; text-anchor: middle; fill: #8b949e; }}
    .rule {{ stroke: #d73a49; stroke-width: 2; }}
  </style>
{columns}
</svg>
"""

COLUMN = """  <text class="num" x="{x}" y="60">{value}</text>
  <line class="rule" x1="{x1}" y1="78" x2="{x2}" y2="78"/>
  <text class="jp" x="{x}" y="106">{jp}</text>
  <text class="en" x="{x}" y="128">{en}</text>"""


def fetch(login, token):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if "errors" in payload:
        sys.exit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def current_streak(calendar, today):
    days = [
        day
        for week in calendar["weeks"]
        for day in week["contributionDays"]
        if date.fromisoformat(day["date"]) <= today
    ]
    days.sort(key=lambda day: day["date"], reverse=True)
    # A quiet today does not break the streak until the day is over.
    if days and days[0]["contributionCount"] == 0:
        days = days[1:]
    streak = 0
    for day in days:
        if day["contributionCount"] == 0:
            break
        streak += 1
    return streak


def render(user, today):
    contributions = user["contributionsCollection"]
    calendar = contributions["contributionCalendar"]
    stats = [
        (calendar["totalContributions"], "貢献", "CONTRIBUTIONS"),
        (contributions["totalCommitContributions"], "コミット", "COMMITS"),
        (current_streak(calendar, today), "連続", "STREAK"),
        (sum(repo["stargazerCount"] for repo in user["repositories"]["nodes"]), "星", "STARS"),
    ]
    columns = "\n".join(
        COLUMN.format(x=x, x1=x - 70, x2=x + 70, value=value, jp=jp, en=en)
        for x, (value, jp, en) in zip((125, 325, 525, 725), stats)
    )
    label = ", ".join(f"{en.lower()}: {value}" for value, _, en in stats)
    return TEMPLATE.format(label=label, columns=columns)


def main():
    login, output = sys.argv[1], sys.argv[2]
    user = fetch(login, os.environ["GITHUB_TOKEN"])
    with open(output, "w", encoding="utf-8") as file:
        file.write(render(user, date.today()))


if __name__ == "__main__":
    main()
