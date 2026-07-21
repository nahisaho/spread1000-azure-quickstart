#!/usr/bin/env bash
# Controller VM 上で Nextflow + Java + jq + az CLI をインストール
# 対象: Ubuntu 24.04 LTS
set -euo pipefail

NEXTFLOW_VERSION="${NEXTFLOW_VERSION:-26.04.6}"

echo "==== apt update ===="
sudo apt-get update -qq

echo "==== 必要パッケージのインストール ===="
sudo apt-get install -y -qq \
  curl \
  wget \
  jq \
  git \
  tmux \
  ca-certificates \
  gettext-base \
  build-essential

echo "==== Java 17 (Temurin 推奨、OpenJDK でも可) ===="
if ! command -v java >/dev/null 2>&1; then
  sudo apt-get install -y -qq openjdk-17-jre-headless
fi
java -version

echo "==== Azure CLI ===="
if ! command -v az >/dev/null 2>&1; then
  curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
fi
az version --output table

echo "==== Nextflow ${NEXTFLOW_VERSION} ===="
mkdir -p "$HOME/bin"
if [[ ! -x "$HOME/bin/nextflow" ]]; then
  curl -sSL https://github.com/nextflow-io/nextflow/releases/download/v${NEXTFLOW_VERSION}/nextflow \
    -o "$HOME/bin/nextflow"
  chmod +x "$HOME/bin/nextflow"
fi

# PATH に追加 (~/.bashrc)
if ! grep -q 'HOME/bin' "$HOME/.bashrc"; then
  echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"
fi
export PATH="$HOME/bin:$PATH"

# NXF_VER を固定
if ! grep -q '^export NXF_VER=' "$HOME/.bashrc"; then
  echo "export NXF_VER=${NEXTFLOW_VERSION}" >> "$HOME/.bashrc"
fi
export NXF_VER="${NEXTFLOW_VERSION}"

echo "==== Nextflow バージョン確認 ===="
nextflow -version || true

# Managed Identity で az login
echo "==== Managed Identity で Azure にログイン ===="
if ! az account show >/dev/null 2>&1; then
  az login --identity
fi

# nf-azure plugin の事前インストール (最初の run で自動 download されるが、明示的に)
echo "==== nf-azure plugin 事前ダウンロード ===="
nextflow plugin install nf-azure@1.23.1 || {
  echo "⚠️  nf-azure plugin の事前 install に失敗。初回 run で自動 install されるので続行可"
}

cat <<EOF

==== インストール完了 ====
  Nextflow:  $(nextflow -version 2>&1 | head -3 | tail -1)
  Java:      $(java -version 2>&1 | head -1)
  Azure CLI: $(az version --query '"azure-cli"' -o tsv)

次のステップ:
  1. 新しいシェルを開く (source ~/.bashrc)
  2. docs/03-run-demo.md に従って test プロファイルを実行
EOF
