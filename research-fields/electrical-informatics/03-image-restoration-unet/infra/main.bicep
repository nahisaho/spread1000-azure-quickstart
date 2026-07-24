// E-3 Image-Restoration U-Net — Azure infrastructure
// Deploys: Log Analytics, App Insights, Storage, Key Vault, ACR, AML Workspace
// RBAC:    Storage Blob Data Contributor + AzureML Data Scientist → deployerObjectId

@description('Short name prefix for all resource names (lowercase alphanumeric + hyphens).')
param namePrefix string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Log Analytics retention in days.')
param logRetentionDays int = 30

@description('Key Vault soft-delete retention in days (min 7, max 90).')
param kvSoftDeleteDays int = 7

@description('Object ID of the principal (user / SP / group) to receive RBAC assignments.')
param deployerObjectId string

@description('Principal type for the RBAC assignment.')
@allowed(['User', 'ServicePrincipal', 'Group'])
param deployerPrincipalType string

@description('Whether to allow public network access to all resources.')
param enablePublicNetworkAccess bool = true

// ── Name determinism ──────────────────────────────────────────────────────────
var suffix = uniqueString(subscription().id, resourceGroup().id)
// Storage: 3-24 chars, lowercase alphanumeric only
var storageName = take(toLower('${replace(namePrefix, '-', '')}st${suffix}'), 24)
// Other resources: prefix-role-shortSuffix
var shortSuffix = take(suffix, 6)
var logName     = '${namePrefix}-log-${shortSuffix}'
var appiName    = '${namePrefix}-appi-${shortSuffix}'
var kvName      = '${namePrefix}-kv-${shortSuffix}'
var acrName     = toLower('${replace(namePrefix, '-', '')}acr${shortSuffix}')
var amlName     = '${namePrefix}-aml-${shortSuffix}'

// ── Role definition IDs ───────────────────────────────────────────────────────
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var amlDataScientistRoleId           = 'f6c7c914-8db3-469d-8ca1-694a8f32e121'

// ── Log Analytics workspace ───────────────────────────────────────────────────
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: logRetentionDays
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ── Application Insights (required by AML workspace) ─────────────────────────
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appiName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ── Storage Account ───────────────────────────────────────────────────────────
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
  }
}

// ── Key Vault ─────────────────────────────────────────────────────────────────
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableSoftDelete: true
    softDeleteRetentionInDays: kvSoftDeleteDays
    enablePurgeProtection: false
    enableRbacAuthorization: true
    publicNetworkAccess: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
  }
}

// ── Container Registry ────────────────────────────────────────────────────────
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
  }
}

// ── AML Workspace ─────────────────────────────────────────────────────────────
resource amlWorkspace 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: amlName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    storageAccount: storage.id
    keyVault: keyVault.id
    containerRegistry: acr.id
    applicationInsights: appInsights.id
    publicNetworkAccess: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
  }
}

// ── RBAC: Storage Blob Data Contributor → deployerObjectId ───────────────────
resource storageBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, deployerObjectId, storageBlobDataContributorRoleId)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: deployerObjectId
    principalType: deployerPrincipalType
  }
}

// ── RBAC: AzureML Data Scientist → deployerObjectId ──────────────────────────
resource amlDataScientistRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(amlWorkspace.id, deployerObjectId, amlDataScientistRoleId)
  scope: amlWorkspace
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions', amlDataScientistRoleId)
    principalId: deployerObjectId
    principalType: deployerPrincipalType
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────
output workspaceName    string = amlWorkspace.name
output storageAccountName string = storage.name
output keyVaultName     string = keyVault.name
output acrLoginServer   string = acr.properties.loginServer
output resourceGroupName string = resourceGroup().name
output deployedLocation string = location
