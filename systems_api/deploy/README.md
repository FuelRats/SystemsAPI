# SystemsAPI container deployment

One image, `fr-sapi:<sha7>`, built from `systems_api/Dockerfile`, runs two services in the
compose project `systemsapi`:

- `fr-sapi`: the web app (`pserve /data/run.ini`), listening on :6543 behind nginx;
- `fr-sapi-eddn`: the EDDN ingester (`python -m systems_api.eddn_client /data/eddn.ini`).

Both use host networking, an init process, uid 1000 and a read-only root filesystem.

## Layout

```
/home/fuelrats/systemsapi/
  compose.yml   copy of deploy/compose.yml
  .env          SAPI_TAG=<sha7> and nothing else
  data/         uid 1000, mode 750: run.ini and eddn.ini (0600), heatmap.json
  src/          clone of FuelRats/SystemsAPI, used only to build the image
```

## Build at a SHA

Run in `/home/fuelrats/systemsapi`:

```
git -C src fetch && git -C src checkout --detach <sha> && chmod -R o+rX src && cd src/systems_api && sudo docker build --no-cache -t fr-sapi:<sha7> .
```

## Release and rollback

Release, in `/home/fuelrats/systemsapi`. First check `src` out at the release SHA, so the compose
steps below read that SHA's file, also when the image already exists (for example a roll-forward
after a rollback):

```
git -C src fetch && git -C src checkout --detach <sha>
```

Then compare the deployed `compose.yml` with the one at the release SHA:

```
diff src/systems_api/deploy/compose.yml compose.yml
```

When the change is intended, install it:

```
install -m 644 src/systems_api/deploy/compose.yml compose.yml
```

Then:

```
sed -i "s/^SAPI_TAG=.*/SAPI_TAG=<sha7>/" .env && sudo docker compose up -d
```

Rollback: the same commands with the previous SHA and tag, so the diff and install use the
`compose.yml` that matches the rolled-back SHA. The weekly image prune deletes unused images older
than 7 days, so rebuild the previous tag first if it is more than 6 days old.

Verify every `sudo docker compose up -d` (release or rollback) and every
`sudo docker compose restart`. Before the command, in `/home/fuelrats/systemsapi`, record the time
and the ingester's restart count (the before-readings):

```
T=$(date +%s); sudo docker inspect -f '{{.RestartCount}}' fr-sapi-eddn
```

After it, in the same shell, wait until pserve answers the health marker (at most 40 tries,
0.5 s apart; the loop only bounds the wait), then run the checks:

```
i=0; until curl -fsS --max-time 2 'http://127.0.0.1:6543/mecha?name=Sol&fast=1' | grep -q '"Perfect match"'; do i=$((i+1)); [ "$i" -ge 40 ] && break; sleep 0.5; done
sh src/systems_api/deploy/smoke.sh http://127.0.0.1:6543
sudo docker inspect -f '{{.RestartCount}}' fr-sapi-eddn
sudo docker compose logs --since "$T" fr-sapi-eddn
```

`smoke.sh` must exit 0 after 8 `ok` lines, the last one `ok /`; a run cut short prints no `FAIL`
line, so check the exit code. The restart count must not grow: after `up -d` recreated
`fr-sapi-eddn` or after `restart fr-sapi-eddn` (both reset it) it must be 0; after an action that
left `fr-sapi-eddn` running (`restart fr-sapi`, or `up -d` that did not recreate it) it must equal
the value recorded before. The ingester log must have no `Traceback`.

After a release, a rollback or a `restart fr-sapi-eddn`, the ingester first touches galmap at its
first accepted EDDN message. Wait until `lastupdate` from `/api/stats` (see Logs) is greater than
`$T`, then repeat the restart-count and `Traceback` checks above:

```
curl -s --max-time 5 http://127.0.0.1:6543/api/stats
```

## Config

The inis live in `data/`. After editing one, take the before-readings under Release and
rollback, run `sudo docker compose restart <svc>` (`fr-sapi` or `fr-sapi-eddn`), then verify as
described there. `data/` is a directory bind mount, so an editor that replaces the file (new
inode) is picked up on restart.

Never list `pyramid_debugtoolbar` under `pyramid.includes` in `data/*.ini`, on the key line or on
a continuation line. The image keeps the package installed (`setup.py` requires it), and behind
nginx every request arrives from 127.0.0.1, which the toolbar trusts, so including it exposes its
settings panel (the DB URL and `rpc_token`) publicly. The `/_debug_toolbar/` 404 check in
`smoke.sh` is meaningful over loopback or through nginx.

## Logs

`sudo docker compose logs` (add a service name to narrow it). The EDDN client's stdout is
discarded, as under systemd (`StandardOutput=null`): that is the status line per message and also
its handled-error prints (Anope JSON-RPC failures, ZMQ reconnects, rejected payloads). Python
warnings and uncaught tracebacks go to stderr and show here. For ingest liveness, read
`lastupdate` from `/api/stats` (the record's `id`, in Unix seconds). The ingester writes it at its
first accepted EDDN message after a start, then about hourly, so a value older than about 2 h
means a stalled ingester.

## Heatmap

`data/heatmap.json` must always exist. The view regenerates it when the file is missing or its
mtime is more than 1 day ahead; on the read-only mount every such `/heatmap` request reruns the
rescue-DB aggregation plus one galmap query per system, the write fails, and the answer is
`null`.

To refresh it, run `generate_heatmap` with the native venv in
`/home/fuelrats/SystemsAPI/systems_api`; it writes `heatmap.json` to its working directory. Copy
the file only after the run printed `New heatmap generated.`: on an error it prints a message
(usually `Oops! ...`) and still exits 0. Copy it in with a rename, so no request reads a partial
file:

```
cp -a /home/fuelrats/SystemsAPI/systems_api/heatmap.json /home/fuelrats/systemsapi/data/.heatmap.json.new && mv -f /home/fuelrats/systemsapi/data/.heatmap.json.new /home/fuelrats/systemsapi/data/heatmap.json
```

Never give it a future mtime. Then verify with `smoke.sh` as under Release and rollback (nothing
restarts, so the restart-count and log checks do not apply).

## Listen address

If a direct caller needs :6543 beyond loopback, set `listen = *:6543` in `data/run.ini`, take the
before-readings under Release and rollback, run `sudo docker compose restart fr-sapi`, then verify
as described there.

## Never run a second ingester

- Never start `fr-sapi.service` or `fr-sapi-eddn.service` while the containers exist.
- `fr-sapi.service` has `Wants=fr-sapi-eddn.service`, so starting the web unit also starts the
  ingester unit. A guard drop-in blocks both units while
  `/home/fuelrats/systemsapi/.container-live` exists.
- Never run a second EDDN ingester in any form: every start posts to #rattech, and every
  instance ingests into galmap.

## Manual tooling

pgloader, `generate_heatmap` and alembic stay in the native checkout
(`/home/fuelrats/SystemsAPI/systems_api`) and its venv.

## Backups

`mozzarella-backup.sh` lists `/home/fuelrats/systemsapi` and the native `alembic/versions`
directory. restic aborts on a missing path, so removing either path without removing its line
breaks the nightly backup for every service.
