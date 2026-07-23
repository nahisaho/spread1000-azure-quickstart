// Bicep — Document Intelligence + Azure OpenAI for document structuring
// AAD-only authentication (disableLocalAuth: true on both).

targetScope = 'resourceGroup'

@minLength(2)
@maxLength(64)
@description('Document Intelligence account name (globally unique, lowercase alphanumeric + hyphen, 2-64 chars).')
param docIntelName string = 'docintel-spread-social-02'

@minLength(2)
@maxLength(64)
@description('Azure OpenAI account name (globally unique, 2-64 chars).')
param aoaiAccountName string = 'aoai-spread-social-02'

@description('Azure region.')
param location string = resourceGroup().location

@description('AOAI model deployment name.')
param aoaiDeploymentName string = 'extract-gpt54mini'

@description('AOAI model.')
param aoaiModelName string = 'gpt-5.4-mini'

@description('AOAI model version.')
param aoaiModelVersion string = '2026-03-17'

@minValue(1)
@maxValue(300)
@description('AOAI deployment capacity in K TPM.')
param aoaiDeploymentCapacity int = 10

@description('Object ID of the deployer (auto-populated by deploy.sh).')
param deployerObjectId string = ''

@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
param deployerPrincipalType string = 'User'

// ------------- Document Intelligence -------------
resource docIntel 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: docIntelName
  location: location
  kind: 'FormRecognizer'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: docIntelName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

// ------------- Azure OpenAI -------------
resource aoai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: aoaiAccountName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: aoaiAccountName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

// ------------- AOAI model deployment -------------
resource aoaiDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aoai
  name: aoaiDeploymentName
  sku: {
    name: 'Standard'
    capacity: aoaiDeploymentCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: aoaiModelName
      version: aoaiModelVersion
    }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
}

// ------------- RBAC -------------
var cognitiveServicesUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908'
var openAIUserRoleId            = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource docIntelUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerObjectId)) {
  name: guid(docIntel.id, deployerObjectId, cognitiveServicesUserRoleId)
  scope: docIntel
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleId)
    principalId: deployerObjectId
    principalType: deployerPrincipalType
  }
}

resource aoaiUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerObjectId)) {
  name: guid(aoai.id, deployerObjectId, openAIUserRoleId)
  scope: aoai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAIUserRoleId)
    principalId: deployerObjectId
    principalType: deployerPrincipalType
  }
}

output docIntelEndpoint string = docIntel.properties.endpoint
output docIntelName string     = docIntel.name
output aoaiEndpoint string     = aoai.properties.endpoint
output aoaiAccountName string  = aoai.name
output aoaiDeploymentName string = aoaiDeployment.name
