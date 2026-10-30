# Installing the /it/ pull on the kumarshakti.com web server (one time)

The WE IT page is published to this public repository after every forecast freeze and every settlement. The web
server only reads it; nothing is ever pushed to the web server and no credentials are needed.

1. Copy `ops/pull_it.py` to the server (for example `/opt/we-it/pull_it.py`). It needs only Python 3.
2. Choose the folder nginx will serve as `/it/`, for example `/var/www/kumarshakti-it/it` (a symlink the script
   manages; its parent `/var/www/kumarshakti-it` must be writable by the user that runs the script). Run once:
   `python3 /opt/we-it/pull_it.py --dest /var/www/kumarshakti-it/it`
3. Serve it, for example in the kumarshakti.com nginx server block:
   `location /it/ { alias /var/www/kumarshakti-it/it/; index index.html; add_header Cache-Control "no-cache"; }`
   then reload nginx.
4. Cron (every 15 minutes):
   `*/15 * * * * python3 /opt/we-it/pull_it.py --dest /var/www/kumarshakti-it/it >> /var/log/we-it-pull.log 2>&1`

Safety built in: all three files come from one commit; each file's sha256 must match that commit's BUILD.json;
a build with fewer ledger records or outcomes than the installed one is refused; the swap is atomic; on any error
the site keeps serving the previous page.
