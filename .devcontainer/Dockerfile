FROM python:3.12-slim

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y \
    git \
    curl \
    # Japanese / CJK fonts (prevents mojibake in Playwright screenshots)
    fonts-noto-cjk \
    # Playwright / Chromium headless dependencies
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# Allow vscode user to install npm global packages without sudo
RUN mkdir -p /home/$USERNAME/.npm-global \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME/.npm-global

ENV NPM_CONFIG_PREFIX=/home/$USERNAME/.npm-global
ENV PATH=$PATH:/home/$USERNAME/.npm-global/bin

WORKDIR /workspace
