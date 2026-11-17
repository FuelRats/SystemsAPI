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

Release, in `/home/fuelrats/systemsapi`. First compare the deployed `compose.yml` with the one
at the release SHA:

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

Rollback: the same commands with the previous tag, using the `compose.yml` that matches the
rolled-back SHA (run `git -C src checkout --detach <previous sha>` before the diff and install).
The weekly image prune deletes unused images older than 7 days, so rebuild the previous tag first
if it is more than 6 days old.

After every `sudo docker compose up -d` (release or rollback) and every
`sudo docker compose restart`, once pserve is serving (a few seconds), in
`/home/fuelrats/systemsapi`:

```
sh src/systems_api/deploy/smoke.sh http://127.0.0.1:6543
sudo docker inspect -f '{{.RestartCount}}' fr-sapi-eddn
sudo docker compose logs --since 2m fr-sapi-eddn
```

`smoke.sh` must print only `ok` lines, the restart count must stay 0, and the ingester log must
have no `Traceback`.

## Config

The inis live in `data/`. After editing one, run `sudo docker compose restart <svc>`
(`fr-sapi` or `fr-sapi-eddn`), then verify as under Release and rollback. `data/` is a
directory bind mount, so an editor that replaces the file (new inode) is picked up on restart.

Never set `pyramid.includes = pyramid_debugtoolbar` in `data/*.ini`. The image keeps the package
installed (`setup.py` requires it), and behind nginx every request arrives from 127.0.0.1, which
the toolbar trusts, so one include line exposes its settings panel (the DB URL and `rpc_token`)
publicly. The `/_debug_toolbar/` 404 check in `smoke.sh` is meaningful over loopback or through
nginx.

## Logs

`sudo docker compose logs` (add a service name to narrow it). The EDDN client's stdout is
discarded, as under systemd (`StandardOutput=null`): that is the status line per message and also
its handled-error prints (Anope JSON-RPC failures, ZMQ reconnects, rejected payloads). Python
warnings and uncaught tracebacks go to stderr and show here. For ingest liveness, read
`lastupdate` from `/api/stats`.

## Heatmap

`data/heatmap.json` must always exist. The view regenerates it when the file is missing or its
mtime is more than 1 day ahead; on the read-only mount every such `/heatmap` request reruns the
rescue-DB aggregation plus one galmap query per system, the write fails, and the answer is
`null`.

To refresh it, run `generate_heatmap` in the native checkout with its venv, then copy the file in
with a rename, so no request reads a partial file:

```
cp -a <src> data/.heatmap.json.new && mv -f data/.heatmap.json.new data/heatmap.json
```

Never give it a future mtime.

## Listen address

If a direct caller needs :6543 beyond loopback, set `listen = *:6543` in `data/run.ini` and run
`sudo docker compose restart fr-sapi`, then verify as under Release and rollback.

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
