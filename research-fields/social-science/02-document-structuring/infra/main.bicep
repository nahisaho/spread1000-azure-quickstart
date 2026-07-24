// Bicep — Document Intelligence + Azure OpenAI for document structuring
// AAD-only authentication (disableLocalAuth: true on both).

targetScope = 'resourceGroup'

@minLength(2)
@maxLength(20)
@description('Short prefix used to build globally-unique resource names. Must be lowercase alphanumeric + hyphen.')
param namePrefix string = 'spr-soc02'

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

@description('Set to false to disable public network access for real research data.')
param enablePublicNetworkAccess bool = true

@description('Object ID of the deployer (auto-populated by deploy.sh).')
param deployerObjectId string = ''

@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
param deployerPrincipalType string = 'User'

// Derive unique, stable suffixes so that re-deployments reuse the same names.
var uniqueSuffix = take(uniqueString(subscription().id, resourceGroup().id), 8)
var docIntelName  = take('${namePrefix}-di-${uniqueSuffix}', 64)
var aoaiName      = take('${namePrefix}-oai-${uniqueSuffix}', 64)
var pnaValue      = enablePublicNetworkAccess ? 'Enabled' : 'Disabled'

// ------------- Document Intelligence -------------
resource docIntel 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: docIntelName
  location: location
  kind: 'FormRecognizer'
  sku: {
    name: 'S0'
  }
  // Present for future service-to-service scenarios; not used by this quickstart.
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: docIntelName
    disableLocalAuth: true
    publicNetworkAccess: pnaValue
  }
}

// ------------- Azure OpenAI -------------
resource aoai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: aoaiName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  // Present for future service-to-service scenarios; not used by this quickstart.
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: aoaiName
    disableLocalAuth: true
    publicNetworkAccess: pnaValue
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

// Outputs — consumed by deploy.sh to write .env
output docIntelEndpoint   string = docIntel.properties.endpoint
output docIntelName       string = docIntel.name
output aoaiEndpoint       string = aoai.properties.endpoint
output aoaiAccountName    string = aoai.name
output aoaiDeploymentName string = aoaiDeployment.name
output aoaiModelName      string = aoaiModelName
output aoaiModelVersion   string = aoaiModelVersion
output location           string = location
