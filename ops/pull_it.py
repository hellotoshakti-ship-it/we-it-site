#!/usr/bin/env python3
"""pull_it.py - install on the kumarshakti.com web server; run every 15 minutes (cron).

Fetches the WE IT public page from the PUBLIC repository hellotoshakti-ship-it/we-it-site, all three files from
ONE commit, checks every file's sha256 against that commit's it/BUILD.json, refuses a rollback (the frozen
ledger only grows), and then swaps the files into place atomically. Python 3 standard library only; no
credentials; read-only on GitHub.

usage: python3 pull_it.py --dest /path/served/as/it        (DEST must be a symlink or absent; see INSTALL.md)
       python3 pull_it.py --dest ... --check                (fetch and verify only, change nothing)
exit 0 = installed or already current; non-zero = nothing changed on the site.
"""
import argparse, hashlib, json, os, shutil, sys, tempfile, time, urllib.request

REPO = "hellotoshakti-ship-it/we-it-site"
FILES = ("index.html", "predictions.json", "BUILD.json")
UA = "kumarshakti-it-pull/1.0"


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    dest = os.path.abspath(a.dest)
    state_path = dest.rstrip("/") + ".state.json"

    sha = json.loads(get("https://api.github.com/repos/%s/commits/main" % REPO))["sha"]
    old = {}
    if os.path.exists(state_path):
        old = json.load(open(state_path, encoding="utf-8"))
        if old.get("commit") == sha and os.path.exists(os.path.join(dest, "index.html")):
            print("current", sha[:12]); return 0

    data = {f: get("https://raw.githubusercontent.com/%s/%s/it/%s" % (REPO, sha, f)) for f in FILES}
    build = json.loads(data["BUILD.json"])
    for name, want in build["files"].items():
        if hashlib.sha256(data[name]).hexdigest() != want:
            sys.exit("REFUSED: %s hash does not match BUILD.json at %s" % (name, sha[:12]))
    if old and (build["ledger_records"] < old.get("ledger_records", 0)
                or build["outcomes_lines"] < old.get("outcomes_lines", 0)):
        sys.exit("REFUSED: rollback (ledger records or outcomes fewer than the installed build)")
    if a.check:
        print("verified", sha[:12], build["latest_base_session"], build["ledger_records"]); return 0

    if os.path.exists(dest) and not os.path.islink(dest):
        sys.exit("REFUSED: %s is a real directory; make it a symlink once (see INSTALL.md)" % dest)
    parent = os.path.dirname(dest)
    new_dir = tempfile.mkdtemp(prefix=".it-%s-" % sha[:12], dir=parent)
    for f in FILES:
        with open(os.path.join(new_dir, f), "wb") as fh:
            fh.write(data[f])
    os.chmod(new_dir, 0o755)
    for f in FILES:
        os.chmod(os.path.join(new_dir, f), 0o644)
    prev = os.path.realpath(dest) if os.path.islink(dest) else None
    tmp_link = dest + ".new"
    if os.path.lexists(tmp_link):
        os.remove(tmp_link)
    os.symlink(new_dir, tmp_link)
    os.replace(tmp_link, dest)                      # atomic swap of what /it/ serves
    with open(state_path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump({"commit": sha, "ledger_records": build["ledger_records"], "outcomes_lines": build["outcomes_lines"],
                   "base_session": build["latest_base_session"], "installed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, fh)
    os.replace(state_path + ".tmp", state_path)
    if prev and prev != new_dir and os.path.basename(prev).startswith(".it-"):
        shutil.rmtree(prev, ignore_errors=True)
    print("installed", sha[:12], build["latest_base_session"], build["ledger_records"]); return 0


if __name__ == "__main__":
    sys.exit(main())
