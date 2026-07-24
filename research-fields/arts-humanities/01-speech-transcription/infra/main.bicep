// Azure AI Speech — Infrastructure as Code
// Resource: Microsoft.CognitiveServices/accounts@2026-05-01 kind:SpeechServices
// Auth: System-assigned MI + Cognitive Services User RBAC (no local auth by default)

@description('Short prefix used in resource names (3-15 alphanumeric).')
@minLength(3)
@maxLength(15)
param namePrefix string

@description('Azure region for all resources.')
param location string = 'japaneast'

@description('Object ID of the deployer (user or service principal) that receives Cognitive Services User role.')
param deployerObjectId string

@description('Principal type of the deployer: "User", "ServicePrincipal", or "Group".')
@allowed(['User', 'ServicePrincipal', 'Group'])
param deployerPrincipalType string = 'User'

@description('Set to true only in dev/test to allow key-based auth. Default: false (Entra-only).')
param enableLocalAuth bool = false

// ── Log Analytics Workspace ──────────────────────────────────────────────────
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${namePrefix}-law'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ── Application Insights ─────────────────────────────────────────────────────
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${namePrefix}-appi'
  location: location
  kind: 'other'
  properties: {
    Application_Type: 'other'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ── Speech Cognitive Services Account ────────────────────────────────────────
resource speechAccount 'Microsoft.CognitiveServices/accounts@2026-05-01' = {
  name: '${namePrefix}-speech'
  location: location
  kind: 'SpeechServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: '${namePrefix}-${uniqueString(resourceGroup().id, namePrefix)}'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: !enableLocalAuth
    // Diagnostic settings wired via separate resource below
  }
}

// ── Diagnostic Settings → Log Analytics ──────────────────────────────────────
resource speechDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: '${namePrefix}-speech-diag'
  scope: speechAccount
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
        retentionPolicy: { enabled: true, days: 30 }
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: { enabled: true, days: 30 }
      }
    ]
  }
}

// ── RBAC: Cognitive Services User ────────────────────────────────────────────
// Role definition ID: a97b65f3-24c7-4388-baec-2e87135dc908 (Cognitive Services User)
resource cogServicesUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(speechAccount.id, deployerObjectId, 'a97b65f3-24c7-4388-baec-2e87135dc908')
  scope: speechAccount
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'a97b65f3-24c7-4388-baec-2e87135dc908'
    )
    principalId: deployerObjectId
    principalType: deployerPrincipalType
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────
output speechResourceName string = speechAccount.name
output speechEndpoint string = speechAccount.properties.endpoint
output speechRegion string = location
output speechIdentityPrincipalId string = speechAccount.identity.principalId
output appInsightsConnectionString string = appInsights.properties.ConnectionString
