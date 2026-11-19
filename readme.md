# Proxy by leolevd

Yay this is free ai proxy source code!

Website: [ai.leolevd.dev](https://ai.leolevd.dev)

## Instructions:

Create `config.json` in `API` folder.

Fill it with data by this format:

```json
{
    "apiname1": {
        "key": "API KEY HERE",
        "base": "BASE URL HERE",
        "model": "MODEL TO USE HERE"
    },
    "apiname2": {
        "key": "API KEY HERE",
        "base": "BASE URL HERE",
        "model": "MODEL TO USE HERE"
    }
}
```

Yay have fun!!

## Optional higher-limit API keys

The free proxy stays open: omit `Authorization` for **10 requests/minute per IP**.
An optional key grants **30 requests/minute per key**, shared across all clients using
that key. Invalid or revoked credentials return 401; exceeding either limit returns 429.
Do not supply a placeholder key in clients that support omitting authentication.

### Manage keys with a JSON file (no terminal needed)

Use your hosting dashboard's file editor or upload feature to create a private
`API/keys.json` file with this structure:

```json
{
  "keys": [
    "REPLACE_WITH_A_RANDOM_SECRET_FROM_YOUR_PASSWORD_MANAGER"
  ]
}
```

Replace the placeholder with a password-manager-generated random secret of at least
32 characters (ASCII, no whitespace, at most 256 characters). Add more strings to
issue more keys. Remove a string to revoke that key. Changes apply on the next request,
without restarting the app. An empty list or missing file means free access only.
Invalid/unreadable configuration returns 503 for keyed requests; free access still works.

**Your hosting account controls who can edit this private file.** There is no public
key-creation endpoint or embedded admin password. Cloning the open-source project
cannot authorize keys on your deployment. The real `API/keys.json` is ignored by Git;
only placeholder examples belong in the public repository. Upload the private file
separately, restrict access to it, and keep it across deployments. The keys are stored
as plain text in this file, so protect its backups too. Do not expose it through your
web server's static-file configuration.

Send the key only over HTTPS, in the header (never a URL or request body):

```sh
curl https://ai.leolevd.dev/api/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

Rate-limit counters use a SHA-256 key identifier. The proxy never forwards your incoming
authorization header to providers.

Rate limits are hardcoded in `main.py`: `FREE_RPM = 10` and `KEY_RPM = 30`.
Environment variables cannot override these limits.

Optional server environment variables for file storage and counter storage:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LEOAI_KEYS_FILE` | `API/keys.json` under the project | Optional alternative path to your private JSON key file |
| `LEOAI_RATE_LIMIT_STORAGE_URI` | `memory://` | SlowAPI counter backend; e.g. `redis://localhost:6379/0` |

The default counters are per process and reset on restart. Run one worker for these
limits, or install the Redis client (`pip install redis`) and configure shared Redis
for multiple workers/instances. Keep the private key file synchronized across instances. Configure your reverse
proxy to trust forwarded IP headers only from your actual proxy, and never log
authorization headers. Key creation does not change upstream provider quotas.

Run local tests with `python -m unittest discover -s tests`.
