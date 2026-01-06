// Azure Container Registry

param name string
param location string
param tags object
param managedIdentityPrincipalId string

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

// Grant managed identity AcrPull role
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: containerRegistry
  name: guid(containerRegistry.id, managedIdentityPrincipalId, 'acrpull')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output name string = containerRegistry.name
output loginServer string = containerRegistry.properties.loginServer
output id string = containerRegistry.id
