// Bicep — ReactionT5v2 quickstart infrastructure
// Deploys: Azure ML Workspace + Storage + Key Vault + Log Analytics + App Insights + ACR Basic
// Grants deployer Storage Blob Data Contributor (needed to upload data via workspaceblobstore)

targetScope = 'resourceGroup'

@description('Base name for the AML workspace (must be unique within the RG).')
param workspaceName string = 'spread-chem-react-ws'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Object ID of the deployer (defaults to empty; set via deploy.sh).')
param deployerObjectId string = ''

@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
@description('Principal type for the deployer role assignment.')
param deployerPrincipalType string = 'User'

var suffix = uniqueString(resourceGroup().id, workspaceName)
var storageName = toLower(replace('st${workspaceName}${suffix}', '-', ''))
var kvName = toLower('kv-${take(replace(workspaceName, '-', ''), 12)}-${take(suffix, 6)}')
var laName = 'la-${workspaceName}'
var appiName = 'appi-${workspaceName}'
var acrName = toLower(replace('cr${workspaceName}${suffix}', '-', ''))

// ------------- Storage -------------
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: take(storageName, 24)
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
  }
}

// ------------- Key Vault -------------
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: null
  }
}

// ------------- Log Analytics + App Insights -------------
resource la 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: laName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: appiName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: la.id
  }
}

// ------------- Container Registry (Basic) -------------
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: take(acrName, 50)
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

// ------------- Azure ML Workspace -------------
resource ws 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: workspaceName
  location: location
  identity: { type: 'SystemAssigned' }
  sku: { name: 'Basic', tier: 'Basic' }
  properties: {
    friendlyName: workspaceName
    storageAccount: storage.id
    keyVault: kv.id
    applicationInsights: appi.id
    containerRegistry: acr.id
    publicNetworkAccess: 'Enabled'
    hbiWorkspace: false
  }
}

// ------------- Deployer RBAC on Storage (needed to upload data) -------------
var storageBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource deployerStorageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerObjectId)) {
  name: guid(storage.id, deployerObjectId, storageBlobDataContributor)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributor)
    principalId: deployerObjectId
    principalType: deployerPrincipalType
  }
}

output workspaceName string = ws.name
output storageAccount string = storage.name
output acrName string = acr.name
output keyVault string = kv.name
