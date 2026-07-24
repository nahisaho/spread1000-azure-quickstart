// EHR-NLP RAG quickstart infrastructure
// Deploys: Azure OpenAI + AI Search + Storage + Key Vault + Log Analytics
// Scope: resourceGroup (deploy with `az deployment group create`)

@description('Deployment location. Use japaneast (in-country) if available, otherwise fall back to sweden central / east us 2. This template is for synthetic data only — never deploy real patient data (PHI) into it (see docs/01-prerequisites.md §6).')
param location string = resourceGroup().location

@description('Unique suffix for globally-unique resource names (3-8 chars lowercase/digits).')
@minLength(3)
@maxLength(8)
param uniqueSuffix string

@description('Project tag')
param projectTag string = 'spread1000'

@description('Scenario tag')
param scenarioTag string = 'ehr-nlp'

@description('PI tag')
param piTag string = 'unknown'

// Storage account names must be 3-24 chars, lowercase alphanumeric only (no hyphens).
// Sanitize scenarioTag by stripping hyphens for the storage-account name.
var storageAccountName = toLower(replace('st${scenarioTag}${uniqueSuffix}', '-', ''))

@description('Azure OpenAI SKU')
@allowed([ 'S0' ])
param openAiSku string = 'S0'

@description('AI Search SKU (basic is minimum with vector support; use standard for production)')
@allowed([ 'basic', 'standard', 'standard2', 'standard3' ])
param searchSku string = 'basic'

@description('Deploy gpt-4o completion model')
param deployGpt4o bool = true

@description('gpt-4o TPM capacity in thousands (default 30 = 30k tokens/min)')
@minValue(1)
@maxValue(1000)
param gpt4oTpmCapacityK int = 30

@description('Chat model name. Verify availability with: az cognitiveservices model list -l <region> --query "[?kind==\'OpenAI\' && model.name==\'gpt-4o\'].model.version" -o tsv')
param chatModelName string = 'gpt-4o'

@description('''Chat model version. **YOU MUST verify the model+version is currently
GA and available in your subscription/region BEFORE deployment.** Both 2024-08-06
(retired 2026-03-31) and 2024-11-20 (retiring 2026-10-01) are past or near retirement.
Preflight command:
  az cognitiveservices model list -l $LOCATION \\
    --query "[?model.name=='gpt-4o' && model.lifecycleStatus=='generallyAvailable' && (model.deprecation.inference==null || model.deprecation.inference > '2026-12-31')].model.version" \\
    -o tsv | sort -r | head -1
Set to that value. Leaving the placeholder will FAIL deployment (empty version is rejected below).''')
@minLength(1)
param chatModelVersion string

@description('Chat deployment name (referenced by scripts). Keep stable.')
param chatDeploymentName string = 'gpt-4o'

@description('Deploy text-embedding-3-large embedding model')
param deployEmbedding bool = true

@description('embedding TPM capacity in thousands')
@minValue(1)
@maxValue(1000)
param embeddingTpmCapacityK int = 350

@description('Embedding model name. NOTE: the Search index is created with 3072 vector dimensions, matching text-embedding-3-large. Overriding to a different model requires manually changing `dimensions` below (text-embedding-3-small=1536, text-embedding-ada-002=1536). Locked to text-embedding-3-large by default.')
@allowed([ 'text-embedding-3-large' ])
param embeddingModelName string = 'text-embedding-3-large'

@description('Embedding model version. Verify with `az cognitiveservices model list -l $LOCATION`.')
param embeddingModelVersion string = '1'

@description('Embedding deployment name (referenced by scripts). Keep stable.')
param embeddingDeploymentName string = 'text-embedding-3-large'

var tags = {
  project: projectTag
  scenario: scenarioTag
  pi: piTag
}

// ---------- Log Analytics ----------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${scenarioTag}-${uniqueSuffix}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ---------- Storage Account ----------
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    supportsHttpsTrafficOnly: true
    encryption: {
      services: {
        blob: { enabled: true, keyType: 'Account' }
      }
      keySource: 'Microsoft.Storage'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: { enabled: true, days: 7 }
    containerDeleteRetentionPolicy: { enabled: true, days: 7 }
  }
}

resource documentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'documents'
  properties: {
    publicAccess: 'None'
  }
}

// ---------- Key Vault ----------
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${scenarioTag}-${uniqueSuffix}'
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: false
    publicNetworkAccess: 'Enabled'
  }
}

// ---------- Azure OpenAI ----------
resource openAi 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'oai-${scenarioTag}-${uniqueSuffix}'
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: { name: openAiSku }
  properties: {
    customSubDomainName: 'oai-${scenarioTag}-${uniqueSuffix}'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

resource gpt4oDeploy 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (deployGpt4o) {
  parent: openAi
  name: chatDeploymentName
  sku: {
    name: 'Standard'
    capacity: gpt4oTpmCapacityK
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: chatModelName
      version: chatModelVersion
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

resource embeddingDeploy 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (deployEmbedding) {
  parent: openAi
  name: embeddingDeploymentName
  sku: {
    name: 'Standard'
    capacity: embeddingTpmCapacityK
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: embeddingModelName
      version: embeddingModelVersion
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
  // Deploy embeddings after gpt-4o to avoid parallel provisioning throttling
  dependsOn: [
    gpt4oDeploy
  ]
}

// ---------- Azure AI Search ----------
resource search 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: 'srch-${scenarioTag}-${uniqueSuffix}'
  location: location
  tags: tags
  sku: { name: searchSku }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    disableLocalAuth: false
    semanticSearch: 'free'
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ---------- Diagnostic settings ----------
// AI Search の allLogs は Query.Search カテゴリを含み、生の検索クエリ (=臨床質問文)
// が AzureDiagnostics.Query_s に 30 日間保持される。臨床データ相当の内容として
// Log Analytics workspace の RBAC を扱う必要がある。
// 本設定は監査 (audit) のみに絞り、Query 本体のログ化は既定で無効。
// 実データ運用時は "OperationLogs" だけ有効にし、必要に応じて別の CMK 付き
// workspace + 短期保持設定へ切り替えること。
resource searchDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: search
  name: 'to-log-analytics'
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      { category: 'OperationLogs', enabled: true }
      // 生のクエリを含む Query.Search カテゴリはデフォルト無効
      // ({ category: 'QueryLogs', enabled: false } は互換のため明示不要)
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

resource openAiDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: openAi
  name: 'to-log-analytics'
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      { categoryGroup: 'allLogs', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

// Blob data-plane logs (StorageRead / StorageWrite / StorageDelete) are essential for
// PHI incident forensics — configured at the blob sub-resource level.
resource blobDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: blobService
  name: 'to-log-analytics'
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      { category: 'StorageRead', enabled: true }
      { category: 'StorageWrite', enabled: true }
      { category: 'StorageDelete', enabled: true }
    ]
    metrics: [
      { category: 'Transaction', enabled: true }
    ]
  }
}

// ---------- Outputs ----------
output openAiEndpoint string = openAi.properties.endpoint
output openAiName string = openAi.name
output chatDeploymentName string = chatDeploymentName
output embeddingDeploymentName string = embeddingDeploymentName
output searchEndpoint string = 'https://${search.name}.search.windows.net'
output searchName string = search.name
output searchPrincipalId string = search.identity.principalId
output storageAccountName string = storage.name
output storageBlobEndpoint string = storage.properties.primaryEndpoints.blob
output documentsContainerName string = documentsContainer.name
output keyVaultName string = keyVault.name
output logAnalyticsId string = logAnalytics.id
