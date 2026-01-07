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

// Generate unique token for resource names
var resourceToken = toLower(uniqueString(resourceGroup().id, environmentName))

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

// Container App
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
    postgresConnectionString: postgres.outputs.connectionString
    redisConnectionString: redis.outputs.connectionString
    azureOpenAIEndpoint: openai.outputs.endpoint
    azureOpenAIRealtimeDeployment: 'gpt-4o-mini-realtime'
    azureAdClientId: azureAdClientId
    azureAdTenantId: azureAdTenantId
  }
}

// Outputs
output containerAppUrl string = containerApp.outputs.fqdn
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer
output openaiEndpoint string = openai.outputs.endpoint
output managedIdentityClientId string = managedIdentity.properties.clientId
