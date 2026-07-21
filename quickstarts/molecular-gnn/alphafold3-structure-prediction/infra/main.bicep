// ============================================================
// AlphaFold 3 クイックスタート — Azure ML Workspace + H100/A100 Compute
//
// 使い方:
//   MY_OID=$(az ad signed-in-user show --query id -o tsv)
//   MY_TID=$(az account show --query tenantId -o tsv)
//   az group create -n rg-spread1000-alphafold3-structure-prediction-<name> -l japaneast
//   az deployment group create \
//     -g rg-spread1000-alphafold3-structure-prediction-<name> \
//     -f main.bicep \
//     -p yourName=<name> ownerEmail=<mail> assignedUserObjectId=$MY_OID assignedUserTenantId=$MY_TID
//
// 前提: Azure ML GPU クォータ (NCadsH100v5 40 vCPU 以上 or NCADSA100v4 24 vCPU 以上)。
//       AF3 の推奨は H100 80GB クラス以上。A100 80GB はフォールバック。
//       CI/CD/service principal からデプロイする場合、researcher の
//       objectId/tenantId を assignedUser* パラメータに渡すこと。
// ============================================================

targetScope = 'resourceGroup'

@description('衝突回避用のユーザー識別子（半角小文字英数字、3-8 文字）')
@minLength(3)
@maxLength(8)
param yourName string

@description('課金追跡タグに入れる owner')
param ownerEmail string

@description('Compute Instance を割り当てる Entra ID ユーザー object ID (`az ad signed-in-user show --query id -o tsv`)')
param assignedUserObjectId string

@description('Assigned user のテナント ID (`az account show --query tenantId -o tsv`)')
param assignedUserTenantId string = subscription().tenantId

@description('リージョン')
param location string = resourceGroup().location

@description('GPU コンピュートの VM サイズ (AF3 は VRAM 80GB 以上と大容量 /mnt が必須)')
@allowed([
  'Standard_NC40ads_H100_v5'    // H100 NVL 94GB (推奨・最速、/mnt 3.5TiB)
  'Standard_NC24ads_A100_v4'    // A100 80GB (フォールバック、/mnt 960GiB)
])
param computeSize string = 'Standard_NC40ads_H100_v5'

// ---- タグ ----
var commonTags = {
  project: 'spread1000'
  field: 'life-pharma-science'
  category: 'molecular-gnn'
  scenario: 'alphafold3-structure-prediction'
  owner: ownerEmail
}

// ---- 名前 (決定論的だが RG 単位で一意化) ----
var suffix        = take(uniqueString(resourceGroup().id, yourName), 5)
var workspaceName = take('mlw-af3-${yourName}', 33)
var computeName   = take('ci-af3-${yourName}-${suffix}', 24)
var storageName   = take('staf3${uniqueString(resourceGroup().id, yourName)}', 24)
var kvName        = take('kv-af3-${suffix}-${uniqueString(resourceGroup().id)}', 24)
var appiName      = 'appi-af3-${yourName}-${suffix}'
var crName        = take('craf3${uniqueString(resourceGroup().id, yourName)}', 50)

// ---- 依存リソース ----
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: commonTags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    encryption: {
      services: {
        blob: { enabled: true }
        file: { enabled: true }
      }
      keySource: 'Microsoft.Storage'
    }
  }
}

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  tags: commonTags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    accessPolicies: []
  }
}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: appiName
  location: location
  tags: commonTags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource cr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: crName
  location: location
  tags: commonTags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

// ---- Azure ML Workspace ----
resource ws 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: workspaceName
  location: location
  tags: commonTags
  identity: { type: 'SystemAssigned' }
  properties: {
    friendlyName: 'AlphaFold 3 Quickstart (${yourName})'
    storageAccount: storage.id
    keyVault: kv.id
    applicationInsights: appi.id
    containerRegistry: cr.id
    publicNetworkAccess: 'Enabled'
    hbiWorkspace: false
  }
}

// ---- GPU Compute Instance ----
// NOTE: Compute Instance は「単一ユーザー」に紐づく。CI/CD デプロイでは
// personalComputeInstanceSettings.assignedUser を明示する必要がある。
// NOTE: idleTimeBeforeShutdown は 2024-04-01 スキーマに型定義がまだ存在せず、
// az bicep build が BCP037 警告を出すことがあるが、ARM 側でサポートされ動作する。
// デプロイ後 `az ml compute show` で idleTimeBeforeShutdown を必ず検証すること。
// NOTE: AF3 は Docker ビルド + 630GB DB ダウンロードで初回 90-150 分かかるため、
// アイドル時間は ESMFold より長めの 60 分に設定 (作業中断時の課金抑止と作業継続のバランス)。
resource ci 'Microsoft.MachineLearningServices/workspaces/computes@2024-04-01' = {
  parent: ws
  name: computeName
  location: location
  tags: commonTags
  properties: {
    computeType: 'ComputeInstance'
    properties: {
      vmSize: computeSize
      idleTimeBeforeShutdown: 'PT60M'  // 60 分アイドルで自動停止 (H100 の停止忘れは 1 日 ¥39,000 になるため必ず有効化)
      personalComputeInstanceSettings: {
        assignedUser: {
          objectId: assignedUserObjectId
          tenantId: assignedUserTenantId
        }
      }
    }
  }
}

// ---- 出力 ----
output workspaceName string = ws.name
output computeName   string = ci.name
output studioUrl     string = 'https://ml.azure.com/?wsid=/subscriptions/${subscription().subscriptionId}/resourceGroups/${resourceGroup().name}/providers/Microsoft.MachineLearningServices/workspaces/${ws.name}'
