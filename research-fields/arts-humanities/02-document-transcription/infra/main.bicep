@description('Deployment location. Must support both Document Intelligence and Azure OpenAI.')
param location string = resourceGroup().location

@description('Object ID of the principal (user or SP) to grant RBAC roles to.')
param deployerObjectId string

@description('Optional suffix for resource names. Defaults to uniqueString of resource group.')
param nameSuffix string = ''

var suffix = empty(nameSuffix) ? uniqueString(resourceGroup().id) : nameSuffix
var diName = 'docint-${suffix}'
var aoaiName = 'aoai-${suffix}'
var aoaiDeploymentName = 'gpt-4o-mini'

// ── Document Intelligence (Form Recognizer) ───────────────────────────────────
resource docint 'Microsoft.CognitiveServices/accounts@2026-05-01' = {
  name: diName
  location: location
  kind: 'FormRecognizer'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: diName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

// ── Azure OpenAI ──────────────────────────────────────────────────────────────
resource aoai 'Microsoft.CognitiveServices/accounts@2026-05-01' = {
  name: aoaiName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: aoaiName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

// ── gpt-4o-mini model deployment ──────────────────────────────────────────────
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2026-05-01' = {
  parent: aoai
  name: aoaiDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: '2024-07-18'
    }
  }
}

// ── RBAC: Cognitive Services User → Document Intelligence ────────────────────
// Role: a97b65f3-24c7-4388-baec-2e87135dc908
resource diRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(docint.id, deployerObjectId, 'a97b65f3-24c7-4388-baec-2e87135dc908')
  scope: docint
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'a97b65f3-24c7-4388-baec-2e87135dc908'
    )
    principalId: deployerObjectId
    principalType: 'User'
  }
}

// ── RBAC: Cognitive Services OpenAI User → Azure OpenAI ─────────────────────
// Role: 5e0bd9bd-7b93-4f28-af87-19fc36ad61bd
resource aoaiRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aoai.id, deployerObjectId, '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  scope: aoai
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    )
    principalId: deployerObjectId
    principalType: 'User'
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────
output diEndpoint string = docint.properties.endpoint
output aoaiEndpoint string = aoai.properties.endpoint
output aoaiDeploymentName string = modelDeployment.name
