// Grant managed identity access to an existing Key Vault in another resource group
// This module creates a role assignment for Key Vault Secrets User

@description('Principal ID of the managed identity to grant access')
param principalId string

@description('Key Vault name')
param keyVaultName string

@description('Key Vault resource group')
param keyVaultResourceGroup string

@description('Key Vault subscription ID (defaults to current)')
param keyVaultSubscriptionId string = subscription().subscriptionId

// Reference the existing Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
  scope: resourceGroup(keyVaultSubscriptionId, keyVaultResourceGroup)
}

// Key Vault Secrets User role definition ID
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

// Grant Key Vault Secrets User role to the managed identity
resource keyVaultRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, principalId, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalType: 'ServicePrincipal'
  }
}

// Output the Key Vault URI for secret references
output keyVaultUri string = keyVault.properties.vaultUri
