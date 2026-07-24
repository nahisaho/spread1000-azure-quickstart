// infra/main.bicep — Azure ML workspace + supporting resources for the D-2 MACE-MP quickstart.
//
// Design:
//   - All globally-unique names use uniqueString(subscription().id, resourceGroup().id)
//     so multiple workshop participants can deploy into different resource groups
//     without collisions.
//   - The identity granted RBAC is the current user (or CI principal); parameterized so
//     scripts can pass in $(az ad signed-in-user show --query id -o tsv).
//   - Log Analytics retention and Key Vault soft-delete/purge protection are parameterized
//     so short-lived workshop deployments do not accidentally retain data forever.
//   - Every output needed by cleanup (RG name, workspace name, Key Vault name, storage
//     account name, ACR name) is emitted so deploy.sh can save them into .env.

targetScope = 'resourceGroup'

@description('Location for all resources. AML workspace must be in a region that supports the desired GPU SKUs.')
param location string = resourceGroup().location

@description('Short scenario prefix, used as a name component.')
@minLength(3)
@maxLength(12)
param namePrefix string = 'macemp02'

@description('Object ID (principalId) of the identity that will use this workspace. Pass $(az ad signed-in-user show --query id -o tsv).')
@minLength(1)
param principalId string

@description('Principal type of the RBAC assignee. Defaults to User; set to ServicePrincipal for CI/CD.')
@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
param principalType string = 'User'

@description('Log Analytics retention in days for AML diagnostics. Keep short for workshops (7-30).')
@minValue(7)
@maxValue(730)
param logRetentionDays int = 30

@description('Enable Key Vault purge protection. Off for workshop resource groups you plan to delete quickly; ON for anything with real customer data.')
param kvEnablePurgeProtection bool = false

@description('Key Vault soft-delete retention (days). 7 = minimum for fast redeploy.')
@minValue(7)
@maxValue(90)
param kvSoftDeleteRetentionDays int = 7

var suffix = uniqueString(subscription().id, resourceGroup().id)
var kvName = take('kv-${namePrefix}-${suffix}', 24)
var storageName = take(toLower('st${namePrefix}${suffix}'), 24)
var acrName = take(toLower('acr${namePrefix}${suffix}'), 50)
var laName = 'la-${namePrefix}-${suffix}'
var wsName = 'aml-${namePrefix}-${suffix}'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: laName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: logRetentionDays
    features: {
      immediatePurgeDataOn30Days: true
    }
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    encryption: {
      keySource: 'Microsoft.Storage'
      services: {
        blob: {
          enabled: true
        }
        file: {
          enabled: true
        }
      }
    }
  }
}

resource kv 'Microsoft.KeyVault/vaults@2024-04-01-preview' = {
  name: kvName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableSoftDelete: true
    softDeleteRetentionInDays: kvSoftDeleteRetentionDays
    enablePurgeProtection: kvEnablePurgeProtection ? true : null
    enableRbacAuthorization: true
    accessPolicies: []
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource workspace 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: wsName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: '${namePrefix} MACE-MP quickstart'
    description: 'Workshop workspace for the D-2 NNP MACE-MP quickstart.'
    storageAccount: storage.id
    keyVault: kv.id
    containerRegistry: acr.id
    hbiWorkspace: false
    publicNetworkAccess: 'Enabled'
  }
}

resource roleAmlDataScientist 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: workspace
  name: guid(workspace.id, principalId, 'aml-data-scientist')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'f6c7c914-8db3-469d-8ca1-694a8f32e121')
    principalId: principalId
    principalType: principalType
  }
}

resource roleAmlComputeOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: workspace
  name: guid(workspace.id, principalId, 'aml-compute-operator')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'e503ece1-11d0-4e8e-8e2c-7a6c3bf38815')
    principalId: principalId
    principalType: principalType
  }
}

resource roleBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, principalId, 'blob-contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: principalId
    principalType: principalType
  }
}

output workspaceName string = workspace.name
output workspaceId string = workspace.id
output resourceGroupName string = resourceGroup().name
output location string = location
output storageAccountName string = storage.name
output keyVaultName string = kv.name
output acrName string = acr.name
output logAnalyticsWorkspaceId string = logAnalytics.id
