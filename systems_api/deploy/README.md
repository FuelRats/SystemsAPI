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

Release, in `/home/fuelrats/systemsapi`:

```
sed -i "s/^SAPI_TAG=.*/SAPI_TAG=<sha7>/" .env && sudo docker compose up -d
```

Rollback: the same command with the previous tag. The weekly image prune deletes unused images
older than 7 days, so rebuild the previous tag first if it is more than 6 days old.

## Config

The inis live in `data/`. After editing one, run `sudo docker compose restart <svc>`
(`fr-sapi` or `fr-sapi-eddn`). `data/` is a directory bind mount, so an editor that replaces
the file (new inode) is picked up on restart.

## Logs

`sudo docker compose logs` (add a service name to narrow it). The EDDN client's stdout (one
status line per message) is discarded; its warnings and tracebacks go to stderr and show here.

## Heatmap

To refresh `heatmap.json`, run `generate_heatmap` in the native checkout with its venv, then
`cp -a` the file into `data/`. Never give it a future mtime: on the read-only mount the view
would then answer `null`.

## Listen address

If a direct caller needs :6543 beyond loopback, set `listen = *:6543` in `data/run.ini` and run
`sudo docker compose restart fr-sapi`.

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
