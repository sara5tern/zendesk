#!/usr/bin/env python3
"""Zendesk helper: search / ticket / sync (to SQLite) / sql.

Env: ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_API_KEY
"""
import base64, json, os, sqlite3, sys, time, urllib.parse, urllib.request

DB = os.environ.get("ZENDESK_DB", "zendesk.db")


def api(path_or_url):
    sub = os.environ["ZENDESK_SUBDOMAIN"]
    auth = f'{os.environ["ZENDESK_EMAIL"]}/token:{os.environ["ZENDESK_API_KEY"]}'
    url = path_or_url if path_or_url.startswith("http") else f"https://{sub}.zendesk.com{path_or_url}"
    req = urllib.request.Request(url, headers={
        "Authorization": "Basic " + base64.b64encode(auth.encode()).decode()})
    while True:
        try:
            with urllib.request.urlopen(req) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(int(e.headers.get("Retry-After", 10)))
                continue
            sys.exit(f"HTTP {e.code}: {e.read().decode()[:300]}")


def search(query):
    data = api("/api/v2/search.json?" + urllib.parse.urlencode({"query": query}))
    for t in data["results"]:
        print(t.get("id"), t.get("status"), t.get("priority"), t.get("subject") or t.get("name"))
    print(f'{data["count"]} total', file=sys.stderr)


def ticket(tid):
    t = api(f"/api/v2/tickets/{tid}.json")["ticket"]
    print(json.dumps(t, indent=2))
    for c in api(f"/api/v2/tickets/{tid}/comments.json")["comments"]:
        print(f'\n--- {c["created_at"]} author {c["author_id"]}\n{c["plain_body"]}')


def sync():
    """Incremental ticket export into SQLite (re-runnable; resumes from last cursor)."""
    db = sqlite3.connect(DB)
    db.execute("CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY, status, priority, subject,"
               " requester_id, assignee_id, created_at, updated_at, tags, raw)")
    db.execute("CREATE TABLE IF NOT EXISTS meta(k PRIMARY KEY, v)")
    row = db.execute("SELECT v FROM meta WHERE k='cursor'").fetchone()
    url = ("/api/v2/incremental/tickets/cursor.json?cursor=" + row[0]) if row \
        else "/api/v2/incremental/tickets/cursor.json?start_time=0"
    n = 0
    while True:
        d = api(url)
        for t in d["tickets"]:
            db.execute("INSERT OR REPLACE INTO tickets VALUES(?,?,?,?,?,?,?,?,?,?)", (
                t["id"], t["status"], t["priority"], t["subject"], t["requester_id"],
                t["assignee_id"], t["created_at"], t["updated_at"], ",".join(t["tags"]),
                json.dumps(t)))
        n += len(d["tickets"])
        if d.get("after_cursor"):
            db.execute("INSERT OR REPLACE INTO meta VALUES('cursor',?)", (d["after_cursor"],))
        db.commit()
        if d.get("end_of_stream"):
            break
        url = d["after_url"]
    print(f"synced {n} tickets into {DB}")


def sql(q):
    cur = sqlite3.connect(DB).execute(q)
    print("\t".join(c[0] for c in cur.description))
    for r in cur:
        print("\t".join(str(x) for x in r))


CMDS = {"search": search, "ticket": ticket, "sync": sync, "sql": sql}
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        sys.exit(__doc__)
    CMDS[sys.argv[1]](*sys.argv[2:])
