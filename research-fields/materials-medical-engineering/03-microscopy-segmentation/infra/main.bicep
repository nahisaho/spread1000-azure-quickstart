// infra/main.bicep — AML workspace + dependencies for 03-microscopy-segmentation
//
// Resources created:
//   Log Analytics workspace → Application Insights → Storage → Key Vault
//   → Container Registry → AML workspace
//   RBAC: Storage Blob Data Contributor + AzureML Data Scientist → deployerObjectId

@description('Short prefix for all resource names (3-10 lowercase alphanumeric)')
param namePrefix string = 'microseg'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Log Analytics retention in days (7–730)')
@minValue(7)
@maxValue(730)
param logRetentionDays int = 30

@description('Key Vault soft-delete retention in days (7–90)')
@minValue(7)
@maxValue(90)
param kvSoftDeleteDays int = 7

@description('Object ID of the deployer (user or service principal) for RBAC assignment')
param deployerObjectId string

@description('Principal type of the deployer identity')
@allowed(['User', 'ServicePrincipal', 'Group', 'ForeignGroup'])
param deployerPrincipalType string = 'User'

@description('Allow public-network access to the AML workspace')
param enablePublicNetworkAccess bool = true

// ── Name generation ──────────────────────────────────────────────────────────
var suffix = uniqueString(subscription().subscriptionId, resourceGroup().id)
var storageName = take('st${namePrefix}${suffix}', 24)
var keyVaultName = take('kv-${namePrefix}-${suffix}', 24)
var acrName = take('acr${namePrefix}${suffix}', 50)
var logName = 'log-${namePrefix}-${suffix}'
var appiName = 'appi-${namePrefix}-${suffix}'
var workspaceName = 'aml-${namePrefix}-${suffix}'

// ── Role definition IDs (built-in) ──────────────────────────────────────────
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var amlDataScientistRoleId = 'f6c7c914-8db3-469d-8ca1-694a8f32e121'

// ── Log Analytics ────────────────────────────────────────────────────────────
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logName
  location: location
  properties: {
    retentionInDays: logRetentionDays
    sku: { name: 'PerGB2018' }
  }
}

// ── Application Insights (linked to Log Analytics) ───────────────────────────
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appiName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logs.id
  }
}

// ── Storage ──────────────────────────────────────────────────────────────────
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

// ── Key Vault ────────────────────────────────────────────────────────────────
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: tenant().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    softDeleteRetentionInDays: kvSoftDeleteDays
    enableSoftDelete: true
    // purgeProtection disabled to allow deletion during the retention window in dev
    enablePurgeProtection: false
  }
}

// ── Container Registry ────────────────────────────────────────────────────────
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

// ── AML Workspace ─────────────────────────────────────────────────────────────
resource aml 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: workspaceName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    storageAccount: storage.id
    keyVault: kv.id
    applicationInsights: appInsights.id
    containerRegistry: acr.id
    publicNetworkAccess: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
  }
}

// ── RBAC: Storage Blob Data Contributor → deployer ───────────────────────────
resource rbacStorageDeployer 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, deployerObjectId, storageBlobDataContributorRoleId)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      storageBlobDataContributorRoleId
    )
    principalId: deployerObjectId
    principalType: deployerPrincipalType
  }
}

// ── RBAC: AzureML Data Scientist → deployer ──────────────────────────────────
resource rbacAmlDeployer 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aml.id, deployerObjectId, amlDataScientistRoleId)
  scope: aml
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      amlDataScientistRoleId
    )
    principalId: deployerObjectId
    principalType: deployerPrincipalType
  }
}

// ── Outputs ──────────────────────────────────────────────────────────────────
output workspaceName string = aml.name
output storageName string = storage.name
output keyVaultName string = kv.name
output acrLoginServer string = acr.properties.loginServer
output logAnalyticsWorkspaceId string = logs.id
