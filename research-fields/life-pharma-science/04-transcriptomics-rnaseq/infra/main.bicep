// SPReAD-1000 RNA-Seq on Azure Batch クイックスタート用 Bicep テンプレート
// Batch account (Batch service allocation mode)
// + Storage account (LRS, Hot tier)
// + Controller VM (Standard_B2s) with system-assigned MI
// + RBAC assignments (Storage Blob Data Contributor + Azure Batch Data Contributor)
targetScope = 'resourceGroup'

@description('リソースの命名に使用するプレフィクス (英小文字数字のみ、3-15 文字)')
@minLength(3)
@maxLength(15)
param namePrefix string

@description('Azure リージョン (Japan East 推奨)')
param location string = resourceGroup().location

@description('Controller VM の管理者ユーザー名')
param adminUsername string = 'azureuser'

@description('Controller VM の SSH 公開鍵')
@secure()
param adminSshPublicKey string

@description('Controller VM の SKU (デフォルト B2s = ¥8.80/h)')
param controllerVmSize string = 'Standard_B2s'

@description('タグ (全リソースに付与)')
param tags object = {
  project: 'spread1000'
  field: 'life-pharma-science'
  scenario: 'rnaseq-nextflow'
}

// ---- Storage account ----
var storageAccountName = toLower('st${namePrefix}${uniqueString(resourceGroup().id)}')

resource storage 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: substring(storageAccountName, 0, min(24, length(storageAccountName)))
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true // Batch account の autoStorage で必要
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    networkAcls: {
      defaultAction: 'Allow' // 初心者向け。本番は Private Endpoint を検討
      bypass: 'AzureServices'
    }
  }
}

resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2024-01-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

resource omicsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2024-01-01' = {
  parent: blobServices
  name: 'omics'
  properties: {
    publicAccess: 'None'
  }
}

// ---- User-assigned Managed Identity (Batch pool 用 — 現在は使用しない) ----
// 注: 既定の Nextflow Azure Batch executor は Controller の MI で SAS を発行し、
//     タスクは SAS 経由で Blob にアクセスします。プールに UAMI を付けるのは
//     Fusion filesystem を使う場合など高度な用途のみに必要です。
// 本テンプレートでは SAS 認証に統一し、UAMI は作成しません。

// ---- Batch account (Batch service allocation mode = 追加料金なし、初心者向け) ----
resource batchAccount 'Microsoft.Batch/batchAccounts@2024-07-01' = {
  name: substring(toLower('bat${namePrefix}${uniqueString(resourceGroup().id)}'), 0, min(24, length(toLower('bat${namePrefix}${uniqueString(resourceGroup().id)}'))))
  location: location
  tags: tags
  properties: {
    poolAllocationMode: 'BatchService'
    publicNetworkAccess: 'Enabled'
    // autoStorage は使用しない (Nextflow は独自に Storage account を扱う)
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ---- Controller VM (Standard_B2s, Ubuntu 24.04 LTS) ----
resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: 'vnet-${namePrefix}'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: ['10.42.0.0/16']
    }
    subnets: [
      {
        name: 'controller'
        properties: {
          addressPrefix: '10.42.1.0/24'
        }
      }
    ]
  }
}

resource nsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-controller-${namePrefix}'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowSSH'
        properties: {
          priority: 1000
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '22'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

resource publicIp 'Microsoft.Network/publicIPAddresses@2024-05-01' = {
  name: 'pip-controller-${namePrefix}'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

resource nic 'Microsoft.Network/networkInterfaces@2024-05-01' = {
  name: 'nic-controller-${namePrefix}'
  location: location
  tags: tags
  properties: {
    networkSecurityGroup: {
      id: nsg.id
    }
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          subnet: {
            id: '${vnet.id}/subnets/controller'
          }
          publicIPAddress: {
            id: publicIp.id
          }
          privateIPAllocationMethod: 'Dynamic'
        }
      }
    ]
  }
}

resource controllerVm 'Microsoft.Compute/virtualMachines@2024-07-01' = {
  name: 'vm-nf-controller'
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    hardwareProfile: {
      vmSize: controllerVmSize
    }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: 'ubuntu-24_04-lts'
        sku: 'server'
        version: 'latest'
      }
      osDisk: {
        createOption: 'FromImage'
        managedDisk: {
          storageAccountType: 'StandardSSD_LRS'
        }
        diskSizeGB: 64
      }
    }
    osProfile: {
      computerName: 'nf-controller'
      adminUsername: adminUsername
      linuxConfiguration: {
        disablePasswordAuthentication: true
        ssh: {
          publicKeys: [
            {
              path: '/home/${adminUsername}/.ssh/authorized_keys'
              keyData: adminSshPublicKey
            }
          ]
        }
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: nic.id
        }
      ]
    }
  }
}

// ---- RBAC ----
// Storage Blob Data Contributor: Blob の読み書き
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
// Azure Batch Data Contributor: Batch job/pool の作成・更新・削除、autoscale enable/disable、
// タスク実行 (data plane)。Microsoft.Batch/batchAccounts/read も含むため
// `az batch account login` にも十分。
// 参考: https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/compute#azure-batch-data-contributor
var batchDataContributorRoleId = '6aaa78f1-f7de-44ca-8722-c64a23943cae'

// Controller VM MI → Storage Blob Data Contributor on Storage account
resource rbacControllerStorage 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, controllerVm.id, storageBlobDataContributorRoleId)
  properties: {
    principalId: controllerVm.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
  }
}

// Controller VM MI → Azure Batch Data Contributor on Batch account
resource rbacControllerBatchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: batchAccount
  name: guid(batchAccount.id, controllerVm.id, batchDataContributorRoleId)
  properties: {
    principalId: controllerVm.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', batchDataContributorRoleId)
  }
}

// ---- Outputs ----
output resourceGroupName string = resourceGroup().name
output location string = location
output batchAccountName string = batchAccount.name
output batchAccountEndpoint string = batchAccount.properties.accountEndpoint
output storageAccountName string = storage.name
output blobContainerName string = omicsContainer.name
output controllerVmName string = controllerVm.name
output controllerVmPublicIp string = publicIp.properties.ipAddress
