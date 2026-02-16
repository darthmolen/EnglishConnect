// Azure Container App

param name string
param location string
param tags object
param containerAppsEnvironmentId string
param containerRegistryName string
param managedIdentityId string
param managedIdentityClientId string
param azureOpenAIEndpoint string
param azureOpenAIRealtimeDeployment string
param azureAdClientId string = ''
param azureAdTenantId string = ''

// Key Vault integration for secrets
@description('Key Vault URI for secret references (e.g., https://kv-name.vault.azure.net/)')
param keyVaultUri string = ''

// Legacy direct secret values (used only when keyVaultUri is empty)
@secure()
param postgresConnectionString string = ''
@secure()
param redisConnectionString string = ''

// Azure Files storage mount name (registered on the Container Apps Environment)
@description('Name of the storage mount registered on the environment for audio files')
param audioStorageName string = ''

// Determine if using Key Vault for secrets
var useKeyVault = keyVaultUri != ''

// Build Key Vault secret URLs
var databaseUrlKvRef = useKeyVault ? '${keyVaultUri}secrets/database-url' : ''
var redisUrlKvRef = useKeyVault ? '${keyVaultUri}secrets/redis-url' : ''
var jwtSecretUrl = useKeyVault ? '${keyVaultUri}secrets/jwt-secret-key' : ''
var initialAdminEmailUrl = useKeyVault ? '${keyVaultUri}secrets/initial-admin-email' : ''

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnvironmentId
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
        }
        // Custom domain is managed via Azure CLI in the deploy workflow
        // to support managed certificates (which require DNS validation)
      }
      registries: [
        {
          server: '${containerRegistryName}.azurecr.io'
          identity: managedIdentityId
        }
      ]
      // When using Key Vault, all secrets come from KV. Otherwise, use direct values.
      secrets: useKeyVault ? [
        {
          name: 'database-url'
          keyVaultUrl: databaseUrlKvRef
          identity: managedIdentityId
        }
        {
          name: 'redis-url'
          keyVaultUrl: redisUrlKvRef
          identity: managedIdentityId
        }
        {
          name: 'jwt-secret-key'
          keyVaultUrl: jwtSecretUrl
          identity: managedIdentityId
        }
        {
          name: 'initial-admin-email'
          keyVaultUrl: initialAdminEmailUrl
          identity: managedIdentityId
        }
      ] : [
        {
          name: 'database-url'
          value: postgresConnectionString
        }
        {
          name: 'redis-url'
          value: 'redis://${redisConnectionString}'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'englishconnect'
          image: '${containerRegistryName}.azurecr.io/englishconnect:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat([
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'REDIS_URL'
              secretRef: 'redis-url'
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAIEndpoint
            }
            {
              name: 'AZURE_OPENAI_REALTIME_DEPLOYMENT'
              value: azureOpenAIRealtimeDeployment
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: managedIdentityClientId
            }
            {
              name: 'USE_REALTIME_API'
              value: 'true'
            }
            {
              name: 'APP_ENV'
              value: 'production'
            }
            {
              name: 'DEBUG'
              value: 'false'
            }
            {
              name: 'AZURE_AD_CLIENT_ID'
              value: azureAdClientId
            }
            {
              name: 'AZURE_AD_TENANT_ID'
              value: azureAdTenantId
            }
          ], useKeyVault ? [
            {
              name: 'JWT_SECRET_KEY'
              secretRef: 'jwt-secret-key'
            }
            {
              name: 'INITIAL_ADMIN_EMAIL'
              secretRef: 'initial-admin-email'
            }
          ] : [])
          volumeMounts: audioStorageName != '' ? [
            {
              volumeName: 'audio-files'
              mountPath: '/app/content/audio'
            }
          ] : []
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      volumes: audioStorageName != '' ? [
        {
          name: 'audio-files'
          storageName: audioStorageName
          storageType: 'AzureFile'
        }
      ] : []
      scale: {
        minReplicas: 1
        maxReplicas: 5
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn
output name string = containerApp.name
