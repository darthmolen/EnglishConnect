// Azure OpenAI with gpt-4o-mini and Realtime models

param name string
param location string
param tags object
param managedIdentityPrincipalId string

resource openai 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: name
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

// gpt-4o-mini for chat completions
resource chatModel 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openai
  name: 'gpt-4o-mini'
  sku: {
    name: 'GlobalStandard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: '2024-07-18'
    }
  }
}

// gpt-4o-mini-realtime for STT+LLM+TTS
resource realtimeModel 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openai
  name: 'gpt-4o-mini-realtime'
  sku: {
    name: 'GlobalStandard'
    capacity: 1
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini-realtime-preview'
      version: '2024-12-17'
    }
  }
  dependsOn: [chatModel] // Serial deployment to avoid conflicts
}

// Grant managed identity Cognitive Services User role
resource cognitiveServicesUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: openai
  name: guid(openai.id, managedIdentityPrincipalId, 'cogservicesuser')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908') // Cognitive Services User
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output endpoint string = openai.properties.endpoint
output name string = openai.name
output id string = openai.id
