FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Combine all updates & installs in a single layer to speed up build drastically
RUN apt update -y && apt install --no-install-recommends -y \
    xfce4 tigervnc-standalone-server novnc websockify \
    sudo xterm curl wget git tzdata \
    dbus-x11 x11-utils x11-xserver-utils x11-apps \
    python3 python3-requests unzip screen libcurl4 zip ca-certificates \
    libgtk-3-0 libasound2 libdbus-glib-1-2 libx11-xcb1 bzip2 \
    && rm -rf /var/lib/apt/lists/*

# Install official Firefox directly from Mozilla CDN (Zero PPA, 100% reliable & ultra-fast)
RUN wget -q "https://download.mozilla.org/?product=firefox-latest&os=linux64&lang=en-US" -O /tmp/firefox.tar.bz2 && \
    tar -xjf /tmp/firefox.tar.bz2 -C /opt/ && \
    ln -s /opt/firefox/firefox /usr/bin/firefox && \
    rm -f /tmp/firefox.tar.bz2

RUN touch /root/.Xauthority

# Install Playit CLI binary
RUN curl -SsL https://github.com/playit-cloud/playit-agent/releases/download/v0.15.26/playit-linux-amd64 -o /usr/local/bin/playit-cli && \
    chmod +x /usr/local/bin/playit-cli

# Copy automation scripts
COPY entrypoint.sh /root/entrypoint.sh
COPY tg_manager.py /root/tg_manager.py
RUN chmod +x /root/entrypoint.sh

WORKDIR /root
EXPOSE 5901
EXPOSE 6080

CMD ["/bin/bash", "/root/entrypoint.sh"]
