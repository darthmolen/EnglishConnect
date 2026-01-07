// Azure Container App

param name string
param location string
param tags object
param containerAppsEnvironmentId string
param containerRegistryName string
param managedIdentityId string
param managedIdentityClientId string
param postgresConnectionString string
param redisConnectionString string
param azureOpenAIEndpoint string
param azureOpenAIRealtimeDeployment string
param azureAdClientId string = ''
param azureAdTenantId string = ''

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
      }
      registries: [
        {
          server: '${containerRegistryName}.azurecr.io'
          identity: managedIdentityId
        }
      ]
      secrets: [
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
          env: [
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
          ]
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
