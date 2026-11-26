# VLC Remote Control — Docker/VLC HTTP edition

A phone-friendly web remote for VLC. The web UI runs in a small Docker container
on a VM and controls VLC on another PC (`Your-PC` by default) through VLC's
built-in HTTP interface. The original Apple-TV-style remote UI and config page
are preserved.

## Highlights
- **Cross-machine control** — no keyboard injection, X server or privileged container needed.
- **Distroless image** — multi-stage build on Debian 13 / Python 3.13, runs as nonroot, about 30 MiB.
- **Published to GHCR** — `ghcr.io/authorshin/vlc-rc:latest`, plus `sha-<commit>` and `v*` tags.
- **Safe updates** — Renovate weekly PRs (pip, Actions, Docker digests) gated by CI smoke tests.
- **Persistent config** — button/command overrides survive restarts via a Docker volume.
- **Live play state** — the play/pause button shows the correct icon on load and after each tap.

## Install
```bash
mkdir -p /vlc-remote-control && cd /vlc-remote-control
curl -fsSLO https://raw.githubusercontent.com/AuthorShin/vlc-rc/main/docker-compose.ghcr.yml
curl -fsSLO https://raw.githubusercontent.com/AuthorShin/vlc-rc/main/.env.example
cp .env.example .env        # set VLC_HTTP_PASSWORD to match VLC on Your-PC
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```
Open `http://<VM-IP>:8004` on your phone. Full instructions are in the
[README](https://github.com/AuthorShin/vlc-rc#readme).

## Sources and acknowledgment
This project is a Docker/HTTP-based evolution of the excellent original project:
**[franciscobmacedo/vlc-remote-control](https://github.com/franciscobmacedo/vlc-remote-control)**
by Francisco Macedo. The web UI templates and the idea of a browser-based VLC
remote come from that repository; the backend was rewritten to use VLC's HTTP
interface so the remote can run on a separate VM from VLC. Thanks for the original work!
