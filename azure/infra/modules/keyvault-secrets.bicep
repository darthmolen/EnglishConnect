// Store secrets in existing Key Vault (cross-resource-group)
// This module is deployed to the resource group containing the Key Vault

param keyVaultName string

@description('Secrets to store in Key Vault')
param secrets array // Array of { name: string, value: string }

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Create/update secrets
resource keyVaultSecrets 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = [for secret in secrets: {
  parent: keyVault
  name: secret.name
  properties: {
    value: secret.value
  }
}]

output keyVaultUri string = keyVault.properties.vaultUri
