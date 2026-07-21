// AML Workspace + 依存リソース (Storage, ACR, Key Vault, App Insights)
// SPReAD-1000 medical-imaging quickstart (MONAI 3D Segmentation)
//
// リソース:
//   - Storage Account (LRS, Hot, public access disabled)
//   - Key Vault (Standard, RBAC 認可)
//   - Application Insights
//   - Container Registry (Basic)
//   - Machine Learning Workspace (system-assigned MI)
//
// RBAC:
//   - デプロイ実行ユーザーに Storage Blob Data Contributor (データアップロード用)
//   - Workspace MI には AzureML が Storage/ACR に対する必要 role を自動付与

targetScope = 'resourceGroup'

@description('デプロイリージョン (Japan East 推奨)')
param location string = resourceGroup().location

@description('Workspace 名 (globally unique 推奨)')
param workspaceName string

@description('Storage Account 名 (3-24 chars, 小文字英数)')
param storageAccountName string = toLower('stmonai${uniqueString(resourceGroup().id)}')

@description('Key Vault 名 (3-24 chars)')
param keyVaultName string = 'kv-monai-${uniqueString(resourceGroup().id)}'

@description('Application Insights 名')
param appInsightsName string = 'ai-monai-${uniqueString(resourceGroup().id)}'

@description('ACR 名 (5-50 chars, 英数のみ, globally unique)')
param acrName string = toLower('crmonai${uniqueString(resourceGroup().id)}')

@description('Log Analytics Workspace 名 (Application Insights のバックエンド)')
param logAnalyticsName string = 'log-monai-${uniqueString(resourceGroup().id)}'

@description('Bicep デプロイ実行者の objectId (Storage RBAC 用)')
param deployerObjectId string

@description('共通タグ')
param tags object = {
  scenario: 'monai-3d-seg'
  project: 'spread1000'
}

// ----------------------------------------------------------------------------
// Storage Account
// ----------------------------------------------------------------------------
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true  // AML workspace の一部機能が SAS を利用
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {}
}

resource datasetsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'datasets'
  properties: { publicAccess: 'None' }
}

// ----------------------------------------------------------------------------
// Key Vault (Standard, RBAC 認可)
// ----------------------------------------------------------------------------
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: false
    publicNetworkAccess: 'Enabled'
  }
}

// ----------------------------------------------------------------------------
// Log Analytics Workspace (Application Insights のバックエンド)
// ----------------------------------------------------------------------------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ----------------------------------------------------------------------------
// Application Insights (workspace-based; classic 作成は 2024-02 に廃止)
// ----------------------------------------------------------------------------
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ----------------------------------------------------------------------------
// Azure Container Registry (Basic tier)
// ----------------------------------------------------------------------------
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

// ----------------------------------------------------------------------------
// AML Workspace (system-assigned MI)
// ----------------------------------------------------------------------------
resource workspace 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: workspaceName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: workspaceName
    storageAccount: storage.id
    keyVault: keyVault.id
    applicationInsights: appInsights.id
    containerRegistry: acr.id
    publicNetworkAccess: 'Enabled'
    hbiWorkspace: false
  }
}

// ----------------------------------------------------------------------------
// RBAC: デプロイ実行者に Storage Blob Data Contributor
// (Bundle/データセットを local から blob へアップロードするため)
// ----------------------------------------------------------------------------
var blobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource deployerStorageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, deployerObjectId, blobDataContributorRoleId)
  properties: {
    principalId: deployerObjectId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      blobDataContributorRoleId
    )
  }
}

// ----------------------------------------------------------------------------
// Outputs
// ----------------------------------------------------------------------------
output workspaceName string = workspace.name
output workspaceId string = workspace.id
output storageAccountName string = storage.name
output storageAccountBlobEndpoint string = storage.properties.primaryEndpoints.blob
output keyVaultName string = keyVault.name
output acrName string = acr.name
output appInsightsName string = appInsights.name
output logAnalyticsName string = logAnalytics.name
output workspacePrincipalId string = workspace.identity.principalId
