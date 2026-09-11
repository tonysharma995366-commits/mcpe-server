FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Essential packages, desktop environment, and dependencies
RUN apt update -y && apt install --no-install-recommends -y \
    xfce4 xfce4-goodies tigervnc-standalone-server novnc websockify \
    sudo xterm init systemd snapd vim net-tools curl wget git tzdata \
    dbus-x11 x11-utils x11-xserver-utils x11-apps software-properties-common \
    python3 python3-pip python3-requests unzip screen libcurl4 zip ca-certificates

# Firefox setup via PPA
RUN add-apt-repository ppa:mozillateam/ppa -y && \
    echo 'Package: *' >> /etc/apt/preferences.d/mozilla-firefox && \
    echo 'Pin: release o=LP-PPA-mozillateam' >> /etc/apt/preferences.d/mozilla-firefox && \
    echo 'Pin-Priority: 1001' >> /etc/apt/preferences.d/mozilla-firefox && \
    echo 'Unattended-Upgrade::Allowed-Origins:: "LP-PPA-mozillateam:jammy";' | tee /etc/apt/apt.conf.d/51unattended-upgrades-firefox && \
    apt update -y && apt install -y firefox xubuntu-icon-theme

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
