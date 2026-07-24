// Bicep — Azure OpenAI for persona survey simulation
// Deploys: Azure OpenAI (S0) + gpt-4.1-mini deployment + Cognitive Services OpenAI User role
// AAD-only authentication (disableLocalAuth: true)

targetScope = 'resourceGroup'

@description('Azure OpenAI account name (globally unique, 2-24 lowercase alphanumeric + hyphen).')
@minLength(2)
@maxLength(24)
param accountName string = 'aoai-spread-social-01'

@description('Azure region.')
param location string = resourceGroup().location

@description('Model deployment name (used as `model=` in API calls).')
param deploymentName string = 'survey-gpt41mini'

@description('Model to deploy. Verify GA availability with `az cognitiveservices model list -l $LOCATION`.')
param modelName string = 'gpt-4.1-mini'

@description('''Model version. **REQUIRED — no default.** gpt-4.1-mini
`2025-04-14` was marked Deprecated on Microsoft''s 2026-07-21 lifecycle
list (retirement 2026-10-14) and new subscriptions cannot deploy it.
Discover a currently GA version with:
  az cognitiveservices model list -l $LOCATION \\
    --query "[?model.name==''gpt-4.1-mini'' && model.lifecycleStatus==''generallyAvailable'' && (model.deprecation.inference==null || model.deprecation.inference > ''2026-12-31'')].model.version" \\
    -o tsv | sort -r | head -1
Set that value via .env `MODEL_VERSION=` before running deploy.sh.''')
@minLength(1)
param modelVersion string

@description('Deployment capacity in K TPM (thousand tokens per minute).')
@minValue(1)
@maxValue(300)
param deploymentCapacity int = 10

@description('Object ID of the deployer (auto-populated by deploy.sh).')
param deployerObjectId string = ''

@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
@description('Principal type for the deployer role assignment.')
param deployerPrincipalType string = 'User'

// ------------- Azure OpenAI account -------------
resource aoai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: accountName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: accountName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

// ------------- Model deployment -------------
resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aoai
  name: deploymentName
  sku: {
    name: 'Standard'
    capacity: deploymentCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
}

// ------------- Deployer RBAC (Cognitive Services OpenAI User) -------------
var openAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource deployerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerObjectId)) {
  name: guid(aoai.id, deployerObjectId, openAIUserRoleId)
  scope: aoai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAIUserRoleId)
    principalId: deployerObjectId
    principalType: deployerPrincipalType
  }
}

output endpoint string = aoai.properties.endpoint
output accountName string = aoai.name
output deploymentName string = deployment.name
