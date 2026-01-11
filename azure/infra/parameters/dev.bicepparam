using '../main.bicep'

param environmentName = 'dev'
param location = 'southcentralus'
param openaiLocation = 'eastus2'  // Realtime API only in eastus2/swedencentral

// Key Vault for secrets (cross-resource-group)
param keyVaultName = 'kv-aif-voz-preprod-001'
param keyVaultResourceGroup = 'rg-aif-vozloop-preprod-001'

// Custom domain (englishconnect.vozloop.com) is managed via Azure CLI
// in the deploy workflow to support managed certificates
