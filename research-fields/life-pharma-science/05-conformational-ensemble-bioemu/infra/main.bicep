// BioEmu quickstart — AML workspace (subscription-scope)
// - workspace-based Application Insights + Log Analytics
// - Standard storage (LRS)
// - Key Vault (RBAC 認可)

targetScope = 'subscription'

@description('Deployment location')
param location string = 'japaneast'

@description('Resource group name')
param resourceGroupName string = 'rg-spread1000-bioemu'

@description('Globally unique 6-char suffix (英数字)')
param suffix string = substring(uniqueString(subscription().id, resourceGroupName), 0, 6)

resource rg 'Microsoft.Resources/resourceGroups@2024-11-01' = {
  name: resourceGroupName
  location: location
}

module workspace 'workspace.bicep' = {
  name: 'bioemu-workspace-deploy'
  scope: rg
  params: {
    location: location
    suffix: suffix
  }
}

output resourceGroupName string = rg.name
output workspaceName string = workspace.outputs.workspaceName
output storageAccountName string = workspace.outputs.storageAccountName
output keyVaultName string = workspace.outputs.keyVaultName
