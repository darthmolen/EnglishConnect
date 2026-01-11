// Grant managed identity access to an existing Key Vault
// Deploy this module scoped to the Key Vault's resource group

@description('Principal ID of the managed identity to grant access')
param principalId string

@description('Key Vault name')
param keyVaultName string

// Reference the existing Key Vault (in the same resource group as deployment scope)
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
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
