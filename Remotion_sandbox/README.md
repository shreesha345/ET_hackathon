# Remotion Sandbox

This folder contains a Docker sandbox for running Remotion with:

- a browser-accessible Linux desktop
- a file manager opened on the Remotion project
- a terminal running as `root`
- persistent app files, output, npm cache, and Remotion browser cache

## What you get

- Remotion Studio on `http://localhost:3000`
- noVNC desktop on `http://localhost:8080/vnc.html?autoconnect=1&resize=remote`
- raw VNC on `localhost:5900`
- the Remotion app stored in [`app`](./app)
- rendered files stored in [`storage/output`](./storage/output)
- extra assets stored in [`storage/assets`](./storage/assets)

## Start the sandbox

```bash
docker compose up --build
```

Run it in the background:

```bash
docker compose up --build -d
```

Open a root shell in the running container:

```bash
docker exec -it remotion-sandbox bash
```

Stop it:

```bash
docker compose down
```

## Render a video

Inside the container:

```bash
cd /workspace/app
npx remotion render HelloWorld /workspace/storage/output/hello-world.mp4
```

## Persistence

The following paths are stored outside the image and survive container rebuilds:

- [`app`](./app)
- [`storage`](./storage)
- [`cache/npm`](./cache/npm)
- [`cache/remotion`](./cache/remotion)

## Security note

The Compose file runs the container as `root` with `privileged: true` and `cap_add: ALL` because you asked for full access. Keep this sandbox local and do not expose it to an untrusted network.

