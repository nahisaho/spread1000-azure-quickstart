// C-3: Text classification/clustering
// Single AOAI account + 2 deployments (embed + label) + RBAC
targetScope = 'resourceGroup'

@description('Deployment location (Japan East supports Regional Standard embed-3-small).')
param location string = 'japaneast'

@minLength(2)
@maxLength(64)
@description('Azure OpenAI account name. Must be globally unique. Default appends uniqueString(rg id) for reproducibility; override for a fixed name.')
param aoaiAccountName string = 'aoai-social-03-${uniqueString(resourceGroup().id)}'

@description('Object ID of the principal (user or service principal) to grant Cognitive Services OpenAI User role.')
param principalId string

@description('Principal type for role assignment.')
@allowed(['User', 'ServicePrincipal', 'Group'])
param principalType string = 'User'

@description('Embedding deployment name (used from client code as model=<deployment>).')
param embedDeploymentName string = 'embed-small'

@description('Cluster labeling GPT deployment name.')
param labelDeploymentName string = 'label-gpt54mini'

@description('Embedding deployment TPM capacity in thousands (30 = 30K TPM).')
@minValue(1)
@maxValue(300)
param embedCapacityK int = 30

@description('Label GPT deployment TPM capacity in thousands.')
@minValue(1)
@maxValue(300)
param labelCapacityK int = 30

// Cognitive Services OpenAI User
// https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/ai-machine-learning#cognitive-services-openai-user
var openAiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource aoai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: aoaiAccountName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: aoaiAccountName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource embedDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aoai
  name: embedDeploymentName
  sku: {
    name: 'Standard'
    capacity: embedCapacityK
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
    versionUpgradeOption: 'NoAutoUpgrade'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

resource labelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aoai
  // NOTE: deployments must be created sequentially to avoid throttling from the Cognitive Services control plane
  dependsOn: [
    embedDeployment
  ]
  name: labelDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: labelCapacityK
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-5.4-mini'
      version: '2026-03-17'
    }
    versionUpgradeOption: 'NoAutoUpgrade'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

resource openAiUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: aoai
  name: guid(aoai.id, principalId, openAiUserRoleId)
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUserRoleId)
  }
}

output aoaiEndpoint string = aoai.properties.endpoint
output aoaiName string = aoai.name
output embedDeployment string = embedDeployment.name
output labelDeployment string = labelDeployment.name
