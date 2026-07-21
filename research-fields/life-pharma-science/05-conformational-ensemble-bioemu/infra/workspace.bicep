// AML workspace 一式 (RG スコープ)

param location string
param suffix string

var storageName = toLower(take(replace('stbioemu${suffix}', '-', ''), 24))
var keyVaultName = take('kv-bioemu-${suffix}', 24)
var logAnalyticsName = 'log-bioemu-${suffix}'
var insightsName = 'appi-bioemu-${suffix}'
var workspaceName = 'mlw-bioemu-${suffix}'

resource storage 'Microsoft.Storage/storageAccounts@2025-06-01' = {
  name: storageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowSharedKeyAccess: true
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: tenant().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: null
    publicNetworkAccess: 'Enabled'
    sku: {
      family: 'A'
      name: 'standard'
    }
  }
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2025-02-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: insightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource workspace 'Microsoft.MachineLearningServices/workspaces@2026-05-01' = {
  name: workspaceName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    friendlyName: 'BioEmu Quickstart'
    applicationInsights: insights.id
    keyVault: keyVault.id
    storageAccount: storage.id
    publicNetworkAccess: 'Enabled'
    v1LegacyMode: false
  }
}

output workspaceName string = workspace.name
output storageAccountName string = storage.name
output keyVaultName string = keyVault.name
output insightsName string = insights.name
output logAnalyticsName string = logAnalytics.name
