param namePrefix string
param location string = resourceGroup().location
param logRetentionDays int = 30
param kvSoftDeleteDays int = 7
param deployerObjectId string
param deployerPrincipalType string = 'User'
param enablePublicNetworkAccess bool = true

var suffix = uniqueString(subscription().subscriptionId, resourceGroup().id, 'timeseries')
var storagePrefix = toLower(replace(namePrefix, '-', ''))
var acrPrefix = toLower(replace(namePrefix, '-', ''))
var logAnalyticsName = take('${namePrefix}-la-${suffix}', 63)
var appInsightsName = take('${namePrefix}-ai-${suffix}', 63)
var keyVaultName = take('${namePrefix}-kv-${suffix}', 24)
var storageAccountName = take('${storagePrefix}st${suffix}', 24)
var containerRegistryName = take('${acrPrefix}acr${suffix}', 50)
var amlWorkspaceName = take('${namePrefix}-aml-${suffix}', 63)
var contributorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'b24988ac-6180-42a0-ab88-20f7382dd24c'
)

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    retentionInDays: logRetentionDays
    publicNetworkAccessForIngestion: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
    publicNetworkAccessForQuery: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
    publicNetworkAccessForQuery: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: tenant().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    softDeleteRetentionInDays: kvSoftDeleteDays
    enableSoftDelete: true
    enablePurgeProtection: false
    publicNetworkAccess: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
    accessPolicies: []
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
    supportsHttpsTrafficOnly: true
  }
}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: containerRegistryName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
  }
}

resource amlWorkspace 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: amlWorkspaceName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    applicationInsights: appInsights.id
    containerRegistry: containerRegistry.id
    description: 'SPReAD-1000 timeseries 1D-CNN quickstart workspace'
    friendlyName: amlWorkspaceName
    keyVault: keyVault.id
    publicNetworkAccess: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
    storageAccount: storageAccount.id
  }
}

resource workspaceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(amlWorkspace.id, deployerObjectId, contributorRoleDefinitionId)
  scope: amlWorkspace
  properties: {
    roleDefinitionId: contributorRoleDefinitionId
    principalId: deployerObjectId
    principalType: deployerPrincipalType
  }
}

output logAnalyticsName string = logAnalytics.name
output logAnalyticsId string = logAnalytics.id
output logAnalyticsLocation string = logAnalytics.location

output appInsightsName string = appInsights.name
output appInsightsId string = appInsights.id
output appInsightsLocation string = appInsights.location

output keyVaultName string = keyVault.name
output keyVaultId string = keyVault.id
output keyVaultLocation string = keyVault.location

output storageAccountName string = storageAccount.name
output storageAccountId string = storageAccount.id
output storageAccountLocation string = storageAccount.location

output containerRegistryName string = containerRegistry.name
output containerRegistryId string = containerRegistry.id
output containerRegistryLocation string = containerRegistry.location

output workspaceName string = amlWorkspace.name
output workspaceId string = amlWorkspace.id
output workspaceLocation string = amlWorkspace.location
output workspaceSubscriptionId string = subscription().subscriptionId
output workspaceResourceGroup string = resourceGroup().name
output workspaceIdentityPrincipalId string = amlWorkspace.identity.principalId
output roleAssignmentId string = workspaceContributor.id
