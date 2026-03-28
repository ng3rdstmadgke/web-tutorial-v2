# https://mcr.microsoft.com/en-us/product/devcontainers/base/about
FROM mcr.microsoft.com/devcontainers/base:dev-ubuntu-24.04

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt update && \
    apt install -y \
      sudo \
      locales \
      net-tools \
      iputils-ping \
      dnsutils \
      bash-completion \
      less \
      curl \
      wget \
      tar \
      xz-utils \
      unzip \
      make \
      gcc \
      git \
      vim \
      tmux \
      jq \
      fzf \
      groff \
      procps \
      python3.12 \
      default-mysql-client \
      redis-tools

# ロケール設定
RUN echo 'ja_JP.UTF-8 UTF-8' >> /etc/locale.gen && \
    locale-gen && \
    update-locale LANG=ja_JP.UTF-8
RUN ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime

# terraform インストール
# https://developer.hashicorp.com/terraform/install
ENV TERRAFORM_VERSION=1.14.0
RUN wget https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
mv terraform /usr/local/bin/ && \
terraform -install-autocomplete

# aws cli インストール
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install

# kubectl インストール
# https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/
RUN curl -LO https://dl.k8s.io/release/v1.30.0/bin/linux/amd64/kubectl && \
    chmod +x ./kubectl && \
    mv ./kubectl /usr/local/bin/kubectl

# eksctl インストール
# https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/setting-up-eksctl.html#setting-up-eksctl-linux
RUN curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp && \
    mv /tmp/eksctl /usr/local/bin

# helmインストール
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Argo CD CLI インストール
# https://argo-cd.readthedocs.io/en/stable/cli_installation/#download-with-curl
RUN curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64 && \
    sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd && \
    rm argocd-linux-amd64

# spotinfo インストール
RUN wget https://github.com/alexei-led/spotinfo/releases/download/1.0.7/spotinfo_linux_amd64 && \
    chmod 755 spotinfo_linux_amd64 && \
    mv spotinfo_linux_amd64 /usr/local/bin/spotinfo

# PostgreSQL インストール
# https://www.postgresql.org/download/linux/ubuntu/
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt update && apt install -y postgresql-common && \
    /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y && \
    apt update && apt install -y postgresql-client-18

# rabbitmqadmin インストール
RUN wget -O /usr/local/bin/rabbitmqadmin https://github.com/rabbitmq/rabbitmqadmin-ng/releases/download/v2.9.0/rabbitmqadmin-2.9.0-x86_64-unknown-linux-gnu && \
    chmod +x /usr/local/bin/rabbitmqadmin

# uv をグローバルにインストール
RUN curl -LsSf https://astral.sh/uv/install.sh \
  | env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh

ENV UV_PROJECT_ENVIRONMENT="/workspaces/web-tutorial-v2/.venv"

# Node.js インストール
# https://nodesource.com/products/distributions
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && \
    apt-get install -y nodejs && \
    node -v

# Gemini CLI インストール
# https://github.com/google-gemini/gemini-cli
RUN npm install -g @google/gemini-cli

# Google Chrome のインストール
RUN wget -q  https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install -y ./google-chrome-stable_current_amd64.deb

USER vscode

# Claude Code CLI インストール
# https://code.claude.com/docs/en/setup#standard-installation
RUN curl -fsSL https://claude.ai/install.sh | bash

# Rust インストール
# https://rust-lang.org/tools/install/
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path

# pnpm
RUN export SHELL=/bin/bash && curl -fsSL https://get.pnpm.io/install.sh | sh -

# DuckDB インストール
# https://duckdb.org/install/?platform=macos&environment=cli
RUN curl https://install.duckdb.org | sh