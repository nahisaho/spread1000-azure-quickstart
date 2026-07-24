// infra/main.bicep — AML workspace + dependencies for E-1 LLM LoRA quickstart
// Stable API versions as of 2026-07.
targetScope = 'resourceGroup'

@description('Short prefix for all resource names (2-8 lowercase alphanumeric).')
@minLength(2)
@maxLength(8)
param prefix string = 'spread'

@description('Azure region for all resources.')
param location string = resourceGroup().location

// Unique 8-char suffix derived from subscription + resource group
var suffix = substring(uniqueString(subscription().subscriptionId, resourceGroup().id), 0, 8)

// Name helpers — comply with per-service naming constraints
var storageRaw = '${prefix}st${suffix}'
var storageName = take(toLower(replace(storageRaw, '-', '')), 24)
var vaultRaw = '${prefix}-kv-${suffix}'
var vaultName = take(toLower(vaultRaw), 24)
var acrRaw = '${prefix}acr${suffix}'
var acrName = take(toLower(replace(acrRaw, '-', '')), 50)
var logsName = '${prefix}-logs-${suffix}'
var aiName = '${prefix}-ai-${suffix}'
var workspaceName = '${prefix}-aml-${suffix}'

// ── Log Analytics workspace ────────────────────────────────────────────────
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logsName
  location: location
  properties: {
    retentionInDays: 30
    sku: { name: 'PerGB2018' }
    workspaceCapping: { dailyQuotaGb: json('0.5') }
  }
}

// ── Application Insights ───────────────────────────────────────────────────
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: aiName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logs.id
  }
}

// ── Key Vault ──────────────────────────────────────────────────────────────
resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  // BCP334: vaultName is guaranteed >= 5 chars (prefix >=2 + '-kv-' + suffix 8). False positive.
  #disable-next-line BCP334
  name: vaultName
  location: location
  properties: {
    tenantId: tenant().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: true
  }
}

// ── Storage account ────────────────────────────────────────────────────────
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  // BCP334: storageName is guaranteed >= 3 chars (prefix >=2 + suffix 8). False positive.
  #disable-next-line BCP334
  name: storageName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

// ── Azure Container Registry ───────────────────────────────────────────────
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  // BCP334: acrName is guaranteed >= 5 chars (prefix >=2 + 'acr' + suffix 8). False positive.
  #disable-next-line BCP334
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
    // anonymousPull is disabled by default; omitted to avoid type-definition warnings
  }
}

// ── Azure ML workspace ─────────────────────────────────────────────────────
resource workspace 'Microsoft.MachineLearningServices/workspaces@2024-10-01' = {
  name: workspaceName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    applicationInsights: appInsights.id
    keyVault: vault.id
    storageAccount: storage.id
    containerRegistry: acr.id
    // systemDatastoresAuthMode: 'identity' — supported at runtime but not yet in Bicep types
  }
}

// ── RBAC: AML workspace identity → Storage Blob Data Contributor ──────────
resource wsStorageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(workspace.id, storage.id, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    )
    principalId: workspace.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ── RBAC: AML workspace identity → Key Vault Secrets User ────────────────
resource wsKvRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: vault
  name: guid(workspace.id, vault.id, '4633458b-17de-408a-b874-0445c86b69e6')
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '4633458b-17de-408a-b874-0445c86b69e6'
    )
    principalId: workspace.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ── RBAC: AML workspace identity → ACR Pull ──────────────────────────────
resource wsAcrRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(workspace.id, acr.id, '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d'
    )
    principalId: workspace.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────
output workspaceName string = workspace.name
output workspaceId string = workspace.id
output resourceGroupName string = resourceGroup().name
output keyVaultName string = vault.name
output storageAccountName string = storage.name
output acrName string = acr.name
output logAnalyticsName string = logs.name
output location string = location
