FROM node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:1 \
    REMOTION_STUDIO_PORT=3000 \
    NOVNC_PORT=8080 \
    VNC_PORT=5900 \
    REMOTION_APP_DIR=/workspace/app \
    REMOTION_OUTPUT_DIR=/workspace/storage/output \
    CHOKIDAR_USEPOLLING=true \
    WATCHPACK_POLLING=true

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    dbus-x11 \
    ffmpeg \
    file \
    git \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libgbm-dev \
    libnss3 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon-dev \
    libxrandr2 \
    nano \
    novnc \
    openbox \
    pcmanfm \
    procps \
    python3 \
    python3-websockify \
    supervisor \
    websockify \
    x11vnc \
    xauth \
    xfonts-base \
    xterm \
    xvfb \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

COPY app/package.json app/package-lock.json* ./app/
RUN cd /workspace/app && npm install

COPY app ./app
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/openbox/autostart /root/.config/openbox/autostart

RUN chmod +x /usr/local/bin/entrypoint.sh /root/.config/openbox/autostart \
    && mkdir -p /workspace/storage/output /workspace/storage/assets /root/.cache/remotion

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
