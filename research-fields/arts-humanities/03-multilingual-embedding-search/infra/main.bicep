// Azure AI Search + Azure OpenAI for multilingual embedding search
// Deploy: az deployment group create -g <rg> -f infra/main.bicep -p infra/parameters.example.json
@description('リソース名の識別子 (英小字+数字, 最大8文字)')
@minLength(2)
@maxLength(8)
param namePrefix string = 'multil'

@description('デプロイリージョン')
param location string = resourceGroup().location

@description('Azure AI Search SKU')
@allowed(['basic', 'standard', 'standard2', 'standard3'])
param searchSku string = 'basic'

@description('デプロイヤーの Object ID (RBAC 割り当て用)')
param deployerObjectId string

@description('Azure OpenAI 埋め込みデプロイメント名')
param aoaiEmbedDeploymentName string = 'text-embedding-3-large'

@description('Azure OpenAI 埋め込み次元数')
@allowed([256, 512, 1024, 3072])
param aoaiEmbedDim int = 3072

// ユニーク識別子 (サブスクリプション + RG + prefix から生成)
var uniqueSuffix = take(uniqueString(subscription().subscriptionId, resourceGroup().id, namePrefix), 8)
var searchName = '${namePrefix}-search-${uniqueSuffix}'
var aoaiName = '${namePrefix}-aoai-${uniqueSuffix}'

// =====================================================================
// Azure AI Search
// =====================================================================
resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchName
  location: location
  sku: {
    name: searchSku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    partitionCount: 1
    replicaCount: 1
    hostingMode: 'default'
    disableLocalAuth: true
    semanticSearch: 'free'
  }
}

// =====================================================================
// Azure OpenAI
// =====================================================================
resource aoaiAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: aoaiName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: aoaiName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource aoaiEmbedDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aoaiAccount
  name: aoaiEmbedDeploymentName
  sku: {
    name: 'Standard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-large'
      version: '1'
    }
  }
}

// =====================================================================
// RBAC Role Assignments
// =====================================================================

// Role definition IDs
var searchServiceContributorRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
var searchIndexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var searchIndexDataReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

// Deployer: Search Service Contributor
resource deployerSearchContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, deployerObjectId, searchServiceContributorRoleId)
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleId)
    principalId: deployerObjectId
    principalType: 'User'
  }
}

// Deployer: Search Index Data Contributor
resource deployerSearchIndexContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, deployerObjectId, searchIndexDataContributorRoleId)
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributorRoleId)
    principalId: deployerObjectId
    principalType: 'User'
  }
}

// Deployer: Cognitive Services OpenAI User (AOAI)
resource deployerAoaiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aoaiAccount.id, deployerObjectId, cognitiveServicesOpenAIUserRoleId)
  scope: aoaiAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalId: deployerObjectId
    principalType: 'User'
  }
}

// Search Service Managed Identity: Cognitive Services OpenAI User (統合ベクトル化)
resource searchMiAoaiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aoaiAccount.id, searchService.id, cognitiveServicesOpenAIUserRoleId)
  scope: aoaiAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalId: searchService.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// =====================================================================
// Outputs
// =====================================================================
output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
output searchName string = searchService.name
output aoaiEndpoint string = aoaiAccount.properties.endpoint
output aoaiEmbedDeployment string = aoaiEmbedDeploymentName
output aoaiEmbedDim int = aoaiEmbedDim
