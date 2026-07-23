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
NEXTFLOW_URL="https://github.com/nextflow-io/nextflow/releases/download/v${NEXTFLOW_VERSION}/nextflow"
if [[ ! -x "$HOME/bin/nextflow" ]]; then
  # --fail: HTTP エラーで exit non-zero
  # -S: エラー時にメッセージを表示
  # -L: リダイレクト追従
  # 別名一時ファイルに落としてから rename (中断時に破損 nextflow を残さない)
  curl --fail -sSL -o "$HOME/bin/nextflow.tmp" "${NEXTFLOW_URL}" \
    || { echo "❌ Nextflow ダウンロードに失敗: ${NEXTFLOW_URL}"; rm -f "$HOME/bin/nextflow.tmp"; exit 1; }
  # 上流はリリース資産の GPG 署名は提供するが SHA256 マニフェストは公開していないため、
  # スクリプトでは pin バージョンでの HTTP 200 完全ダウンロード + バージョン一致検証で担保する。
  chmod +x "$HOME/bin/nextflow.tmp"
  mv "$HOME/bin/nextflow.tmp" "$HOME/bin/nextflow"
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
# 実際にリクエストしたバージョンを報告するか厳密に検証 (`|| true` で失敗を握りつぶさない)
NF_REPORTED=$(nextflow -version 2>&1 | grep -oE 'version [0-9]+\.[0-9]+\.[0-9]+' | awk '{print $2}' | head -1)
if [[ -z "${NF_REPORTED}" ]]; then
  echo "❌ nextflow -version が期待通り応答しません。バイナリが破損している可能性:"
  nextflow -version 2>&1 | head -5
  exit 1
fi
if [[ "${NF_REPORTED}" != "${NEXTFLOW_VERSION}" ]]; then
  echo "❌ Nextflow のバージョン不一致: 期待 ${NEXTFLOW_VERSION}, 実測 ${NF_REPORTED}"
  echo "   (~/.bashrc の NXF_VER が override されている可能性。別 shell で 'unset NXF_VER' して再確認)"
  exit 1
fi
echo "✅ Nextflow ${NF_REPORTED} を確認"

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
