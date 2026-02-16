// EnglishConnect Azure Infrastructure
// Deploy with: az deployment group create -g <resource-group> -f main.bicep -p parameters/dev.bicepparam

targetScope = 'resourceGroup'

@description('Environment name (dev, staging, prod)')
param environmentName string

@description('Location for resources')
param location string = resourceGroup().location

@description('Azure OpenAI location (must support Realtime API: eastus2, swedencentral)')
param openaiLocation string = 'eastus2'

@description('PostgreSQL location (some regions may be restricted)')
param postgresLocation string = 'canadacentral'

@description('Azure AD Client ID for OAuth')
param azureAdClientId string = ''

@description('Azure AD Tenant ID for OAuth')
param azureAdTenantId string = ''

@description('Key Vault name for secrets (external, in different resource group)')
param keyVaultName string = ''

@description('Key Vault resource group (required if keyVaultName is set)')
param keyVaultResourceGroup string = ''

// Generate unique token for resource names
var resourceToken = toLower(uniqueString(resourceGroup().id, environmentName))

// Key Vault URI (constructed if keyVaultName is provided)
var keyVaultUri = keyVaultName != '' ? 'https://${keyVaultName}${environment().suffixes.keyvaultDns}/' : ''

// Use Key Vault for secrets (true if both keyVaultName and keyVaultResourceGroup are provided)
var useKeyVault = keyVaultName != '' && keyVaultResourceGroup != ''

var tags = {
  'azd-env-name': environmentName
  application: 'englishconnect'
  environment: environmentName
}

// User-assigned managed identity for secure access
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-ec-${resourceToken}'
  location: location
  tags: tags
}

// Log Analytics workspace for monitoring
module logAnalytics 'modules/log-analytics.bicep' = {
  name: 'log-analytics'
  params: {
    name: 'log-ec-${resourceToken}'
    location: location
    tags: tags
  }
}

// Container Registry for Docker images
module containerRegistry 'modules/container-registry.bicep' = {
  name: 'container-registry'
  params: {
    name: 'acrec${resourceToken}'
    location: location
    tags: tags
    managedIdentityPrincipalId: managedIdentity.properties.principalId
  }
}

// Azure OpenAI with gpt-4o-mini and Realtime models
module openai 'modules/openai.bicep' = {
  name: 'openai'
  params: {
    name: 'oai-ec-${resourceToken}'
    location: openaiLocation
    tags: tags
    managedIdentityPrincipalId: managedIdentity.properties.principalId
  }
}

// PostgreSQL Flexible Server
module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    name: 'psql-ec-${resourceToken}-v4'
    location: postgresLocation
    tags: tags
    administratorLogin: 'ecadmin'
    managedIdentityPrincipalId: managedIdentity.properties.principalId
    managedIdentityName: managedIdentity.name
  }
}

// Azure Cache for Redis
module redis 'modules/redis.bicep' = {
  name: 'redis'
  params: {
    name: 'redis-ec-${resourceToken}'
    location: location
    tags: tags
  }
}

// Azure Storage Account with File Share for audio content
module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    name: 'stec${resourceToken}'
    location: location
    tags: tags
  }
}

// Grant managed identity access to Key Vault (cross-resource-group)
module keyVaultAccess 'modules/keyvault-access.bicep' = if (useKeyVault) {
  name: 'keyvault-access'
  scope: resourceGroup(keyVaultResourceGroup)
  params: {
    keyVaultName: keyVaultName
    principalId: managedIdentity.properties.principalId
  }
}

// Store secrets in Key Vault (cross-resource-group)
module keyVaultSecrets 'modules/keyvault-secrets.bicep' = if (useKeyVault) {
  name: 'keyvault-secrets'
  scope: resourceGroup(keyVaultResourceGroup)
  params: {
    keyVaultName: keyVaultName
    secrets: [
      {
        name: 'database-url'
        value: postgres.outputs.connectionString
      }
      {
        name: 'redis-url'
        value: 'redis://${redis.outputs.connectionString}'
      }
    ]
  }
  dependsOn: [
    keyVaultAccess
  ]
}

// Container Apps Environment
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-ec-${resourceToken}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.outputs.customerId
        sharedKey: logAnalytics.outputs.primarySharedKey
      }
    }
  }
}

// Mount Azure Files share on the Container Apps Environment for audio content
resource audioStorageMount 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  name: 'audio-storage'
  parent: containerAppsEnv
  properties: {
    azureFile: {
      accountName: storage.outputs.storageAccountName
      accountKey: storage.outputs.storageAccountKey
      shareName: storage.outputs.fileShareName
      accessMode: 'ReadOnly'
    }
  }
}

// Container App
// When using Key Vault, secrets are pulled from KV; otherwise, passed directly
module containerApp 'modules/container-app.bicep' = {
  name: 'container-app'
  params: {
    name: 'ca-ec-${resourceToken}'
    location: location
    tags: tags
    containerAppsEnvironmentId: containerAppsEnv.id
    containerRegistryName: containerRegistry.outputs.name
    managedIdentityId: managedIdentity.id
    managedIdentityClientId: managedIdentity.properties.clientId
    azureOpenAIEndpoint: openai.outputs.endpoint
    azureOpenAIRealtimeDeployment: 'gpt-4o-mini-realtime'
    azureAdClientId: azureAdClientId
    azureAdTenantId: azureAdTenantId
    keyVaultUri: keyVaultUri
    audioStorageName: audioStorageMount.name
    // Only pass connection strings when NOT using Key Vault (legacy/fallback)
    postgresConnectionString: useKeyVault ? '' : postgres.outputs.connectionString
    redisConnectionString: useKeyVault ? '' : redis.outputs.connectionString
  }
  // Ensure secrets exist in KV before container app tries to reference them
  // (audioStorageMount dependency is inferred from audioStorageName param)
  dependsOn: useKeyVault ? [
    keyVaultSecrets
  ] : []
}

// Outputs
output containerAppUrl string = containerApp.outputs.fqdn
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer
output openaiEndpoint string = openai.outputs.endpoint
output managedIdentityClientId string = managedIdentity.properties.clientId
output managedIdentityPrincipalId string = managedIdentity.properties.principalId
