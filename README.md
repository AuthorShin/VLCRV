# VLC Remote Control (Docker edition)

A phone-friendly web remote for VLC. **The web UI runs in a Docker container on a VM; VLC keeps playing on the PC named `Your-PC`.** The container talks to VLC over VLC's built-in HTTP interface, so no shared keyboard, X server, or privileged container is needed.

```
phone ──(LAN / Wi-Fi)──> VM:8004 (this container) ──(LAN)──> Your-PC:8080 (VLC)
```

The original keyboard-injection backend was replaced because the `keyboard` library can only inject keys on the machine it runs on — useless when VLC is on another PC. The **web UI (remote buttons + config page) is unchanged**.

**Based on [franciscobmacedo/vlc-remote-control](https://github.com/franciscobmacedo/vlc-remote-control)** — this repo keeps the original browser remote UI and adapts it for Docker + VLC's HTTP interface. See [Acknowledgments](#acknowledgments).

## 1. Enable VLC's web interface on PC `Your-PC`

1. In VLC: **Tools → Preferences**, set **Show settings** to **All**.
2. Go to **Interface → Main interfaces** and tick **Web**.
3. Go to **Interface → Main interfaces → Lua → Lua HTTP** and set a password (e.g. `changeme`). Leave the username empty.
4. Restart VLC. Check `http://Your-PC:8080` from another machine — it should ask for the password.
5. If access from other machines is blocked, edit VLC's `lua/http/.hosts` file on that PC and add the VM's IP address (see [VideoLAN's guide](https://wiki.videolan.org/Control_VLC_via_a_browser/)).

See also [How-To Geek's walkthrough](https://www.howtogeek.com/117261/how-to-activate-vlcs-web-interface-control-vlc-from-a-browser-use-any-smartphone-as-a-remote/).

## 2. Run the container on the VM

### Option A — install from GHCR (recommended)

The image is published to `ghcr.io/authorshin/vlcrv` by GitHub Actions on every push to `main`.

```bash
mkdir -p /vlc-remote-control && cd /vlc-remote-control
curl -fsSLO https://raw.githubusercontent.com/AuthorShin/VLCRV/main/docker-compose.ghcr.yml
curl -fsSLO https://raw.githubusercontent.com/AuthorShin/VLCRV/main/.env.example
cp .env.example .env      # set VLC_HTTP_PASSWORD to the password from step 1
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
docker compose -f docker-compose.ghcr.yml logs -f   # URL + QR code
```

Or with plain Docker (no compose file):

```bash
docker pull ghcr.io/authorshin/vlcrv:latest
docker run -d --name vlc-remote-control --restart unless-stopped --network host \
  -e VLC_HOST=Your-PC -e VLC_HTTP_PORT=8080 -e VLC_HTTP_PASSWORD=changeme \
  -e PORT=8004 -v vlc-remote-config:/app/data ghcr.io/authorshin/vlcrv:latest
```

### Option B — build from source

```bash
cd /vlc-remote-control
cp .env.example .env      # set VLC_HTTP_PASSWORD to the password from step 1
git pull
docker compose up -d --build
docker compose logs -f    # shows the URL + QR code
```

Open **`http://<VM-IP>:8004`** on the phone (same Wi-Fi/LAN as the VM). The QR code in the logs points to the same URL. `curl http://<VM-IP>:8004/health` returns `{"status":"ok",...}`.

To stop: `docker compose down`. Configuration changes from the config page survive restarts (stored in a named Docker volume mounted at `/app/data`).

## 3. Configuration page (`/config`)

The same UI is kept, but each field now holds a **VLC HTTP command** instead of a keystroke:

| Button | Default value | What it does |
| --- | --- | --- |
| play_pause | `pl_pause` | Play / pause toggle |
| fullscreen | `key\|toggle-fullscreen` | Toggle fullscreen |
| mute | `key\|vol-mute` | Toggle mute |
| volume_up | `volume\|+10` | Volume +10 |
| volume_down | `volume\|-10` | Volume -10 |
| move_forward | `seek\|+10s` | Jump 10 s forward |
| move_back | `seek\|-10s` | Jump 10 s back |
| quit | `key\|quit` | Quit VLC (use `pl_stop` if your build ignores it) |
| open_vlc | *(empty)* | Optional command sent once at container start, e.g. `pl_play` |

Format: `command` or `command|val`. Legacy strings like `command=seek&val=+10s` are also accepted. Full VLC command list: `pl_play`, `pl_pause`, `pl_forcepause`, `pl_forceresume`, `pl_stop`, `pl_next`, `pl_previous`, `pl_empty`, `fullscreen`, `volume`, `seek`, `key`, `rate`, `snapshot`, ...

## 4. Environment variables (`.env`)

| Variable | Default | Purpose |
| --- | --- | --- |
| `VLC_HOST` | `Your-PC` | Hostname/IP of the PC running VLC |
| `VLC_HTTP_PORT` | `8080` | VLC HTTP interface port |
| `VLC_HTTP_PASSWORD` | `changeme` | VLC Lua HTTP password (**must match**) |
| `PORT` | `8004` | Port of this web UI on the VM |
| `PUBLIC_URL` | *(empty)* | Override the URL printed / shown as QR |
| `LOG_LEVEL` | `info` | Uvicorn log level |

`network_mode: host` is used so the container is reachable at the VM's own LAN IP (and hostname resolution of `Your-PC` works from the container). If you prefer bridge networking, replace it with `ports: ["8004:8004"]` and set `PUBLIC_URL=http://<VM-IP>:8004` so the QR code is correct.

API endpoints: `/` (remote UI), `/config` (config page), `/action/<button>` (send a command), `/status` (VLC state, useful for debugging), `/health` (container liveness).

### Distroless notes
The final image contains only the Python 3.13 interpreter, your app, and the installed packages — there is no shell, so `docker compose exec ... sh` will not work. To inspect a running container, temporarily switch the image to the debug variant `gcr.io/distroless/python3-debian13:debug` (which includes a shell), then rebuild. The container runs as nonroot (UID 65532); only `/app/data` is writable, which is where `db.json` is stored via the named volume. Because distroless python3-debian13 uses Python 3.13, the builder stage uses `python:3.13-slim` so compiled dependencies (e.g. `pydantic-core`) are ABI-compatible.

## 5. What was updated

- **Dependencies** (latest PyPI versions, verified 2026-11-26): `fastapi 0.165.0`, `uvicorn 0.54.0`, `jinja2 3.1.6`, `python-multipart 0.0.34`, `qrcode 8.2`, `requests 2.34.2`. The obsolete `keyboard 0.13.5` dependency was removed.
- **Starlette 1.x compatibility**: `TemplateResponse` now uses the current `(request, name, context)` signature — the old call style breaks on modern FastAPI.
- **Backend**: keystroke injection → VLC HTTP requests; works across machines, no root/`--privileged`/`/dev/input` mounts required.
- **Config persistence**: `src/db.json` → `/app/data/db.json` (Docker volume), atomic writes, missing keys auto-repaired.
- **Server**: removed `reload=True`, added health/status endpoints, safer startup, thread-safe config, configurable host/port/logging.
- **Docker**: multi-stage **distroless Debian 13** image (`gcr.io/distroless/python3-debian13:nonroot`) — no shell, no package manager, runs as UID 65532; `docker-compose.yml`, `.dockerignore`, `.env.example`, shell-free healthcheck. Dependencies are built with Python 3.13 in a builder stage to match the distroless interpreter.
- **Maintenance automation**: Renovate config, CI workflow, smoke test, dev requirements and an update-check script (section 7).

## 6. Why distroless? Size and resource notes

**Benefits**
- **Small attack surface** — no shell (`sh`/`bash`), no `apt`, no package manager, no compilers, no package caches. An attacker who gets code execution has nothing to pivot with, and OS-package CVEs are largely absent.
- **Non-root by default** — the `:nonroot` tag runs as UID 65532. Only `/app/data` is writable, so a compromised process cannot rewrite the app code.
- **Smaller and faster to pull/start** — far fewer layers to download and unpack; less disk used on the VM.
- **Consistent glibc base** — Debian 13 userspace means normal Python wheels work without Alpine/musl surprises.

**How it compares** (measured registry layer sizes, amd64, compressed, 2026-11-24):

| Image | Base | With app+deps | Shell/apt | libc | Notes |
| --- | --- | --- | --- | --- | --- |
| `gcr.io/distroless/python3-debian13:nonroot` | **21.5 MiB** | **~30–32 MiB** | no/no | glibc | **Current choice** — secure, small, Python 3.13 |
| `python:3.13-slim` | 41.1 MiB | ~50 MiB | yes/yes | glibc | Easier to debug; ~60% larger base |
| `python:3.13` (full) | 394.9 MiB | ~405 MiB | yes/yes | glibc | Build tools + docs; unnecessary for runtime |
| `python:3.13-alpine` | 16.2 MiB | ~25 MiB | yes/yes | musl | Smallest, but musl-specific wheel/DNS/SSL quirks |
| `scratch` + manual Python | ~0 | ~20 MiB+ | no/no | — | You must bundle the interpreter and CA certs yourself |

The builder stage is thrown away — only the installed packages and app files reach the runtime image.

**Resource needs** — distroless mainly saves **disk size and attack surface**, not RAM/CPU:
- **Disk**: ~30–32 MiB image; writable layer is essentially just `db.json` (a few hundred bytes) plus the small named volume.
- **RAM**: ~30–60 MB RSS at idle (Python + FastAPI + uvicorn). Distroless vs slim barely changes this — the interpreter dominates. One uvicorn worker keeps it low.
- **CPU**: negligible; sleeps until a phone sends a request. **Startup**: ~1 second.

**Trade-offs**: no interactive shell (use the `:debug` tag temporarily), no runtime `apt install` (rebuild instead), healthchecks must use exec form with an absolute interpreter path — all handled here.

## 7. Maintenance: tracking and updating dependencies

Once this repo is on GitHub, maintenance is mostly automatic:

1. **Renovate** (`renovate.json`) is the dependency bot (Dependabot was removed to avoid duplicate PRs). It checks Python packages, GitHub Actions and Docker images **every Monday** and opens grouped PRs. It also pins Docker images to digests, so moving `nonroot`/`debian13` tags are detected even though those tag names are not semantic versions.
   - **One-time setup**: install the [Renovate GitHub App](https://github.com/apps/renovate) on `AuthorShin/VLCRV` (choose "All repositories" or select just this one). It reads `renovate.json` from `main` automatically. A **Dependency Dashboard** issue will be created for overview/approval.
   - Docker updates are grouped into one PR (`python:3.13-slim` builder + distroless runtime + healthcheck path) so the Python versions stay in sync; review that PR before merging.
2. **CI** (`.github/workflows/ci.yml`) runs on every push/PR: Python 3.13 install, syntax check, a smoke test against a fake VLC server, a security audit (`pip-audit`, report only), and a Docker build of the distroless image. A Renovate PR is safe to merge when CI is green.
3. **Manual check** any time:
   ```bash
   ./scripts/update-deps.sh       # prints OK / OUTDATED for every pinned package
   pip-audit -r requirements.txt  # known vulnerabilities (needs requirements-dev.txt)
   ```
4. **To apply an update**:
   ```bash
   # edit requirements.txt (and/or requirements-dev.txt) with the new versions
   pip install -r requirements.txt -r requirements-dev.txt
   python tests/smoke_test.py
   docker compose up -d --build   # rebuild on the VM
   curl http://<VM-IP>:8004/health
   ```
5. **Fully reproducible builds (optional)**: direct packages are pinned but transitive ones float. Run `pip-compile -o requirements.lock.txt requirements.txt` and have the Dockerfile install that lock file if you want byte-for-byte repeatable images.
6. **VLC on `Your-PC`** is an external dependency too: after VLC upgrades, re-check that the Web interface is enabled, the password still matches `VLC_HTTP_PASSWORD`, and `/status` shows `reachable: true`.

**GHCR publishing** (`.github/workflows/publish.yml`): a push to `main` publishes `ghcr.io/authorshin/vlcrv:latest` and a `sha-<commit>` tag; a `v*` tag also publishes that version tag. The workflow logs in with the built-in `GITHUB_TOKEN` (`packages: write`), so no extra secret is needed. The package is public because the repo is public. On the VM, update with:

```bash
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```

## Acknowledgments

This project is a Docker/HTTP-based evolution of **[franciscobmacedo/vlc-remote-control](https://github.com/franciscobmacedo/vlc-remote-control)** by Francisco Macedo. The web UI templates (`src/templates/index.html`, `src/templates/config.html`) and the concept of a phone browser as a VLC remote come from that repository. The backend was rewritten to talk to VLC over its HTTP interface so the container can run on a different machine from the one playing the video. Thanks for the original work!

## Troubleshooting

- **`Cannot reach VLC`** → check `Your-PC` resolves from the VM (`ping Your-PC`), VLC is running, and firewall allows port 8080.
- **`VLC rejected the password`** → fix `VLC_HTTP_PASSWORD` in `.env` and `docker compose up -d`.
- **Phone cannot open the page** → use the VM's LAN IP (not the container's 172.x IP); make sure phone and VM share the same network.
- **Buttons do nothing** → visit `/status`; if `state` is `stopped`, load something into VLC. `quit` may need changing to `pl_stop` on some VLC versions.
- **`PermissionError: /app/data/db.json.tmp`** → the volume was created when the container ran as root, but the distroless image runs as UID 65532. Fix it once, then recreate the container:
  ```bash
  # named volume from either compose file:
  docker run --rm -v vlc-remote-config:/data alpine:3 chown -R 65532:65532 /data
  # plain docker run example uses the same volume name vlc-remote-config
  docker compose -f docker-compose.ghcr.yml up -d --force-recreate
  ```
  (For a bind mount, run `chown -R 65532:65532 /path/on/host`.) The app now survives this error and runs with in-memory commands until the ownership is fixed — check the config page message.
- **QR code shows `172.x.x.x`** → the container is on Docker's bridge network, which the phone can't reach. Use the supplied compose file (`network_mode: host`) or `docker run --network host -p 8004:8004` and set `PUBLIC_URL=http://<VM-IP>:8004` in `.env` so the QR code uses the VM address.

MIT License (see `LICENSE`).
