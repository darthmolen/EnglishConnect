// Log Analytics Workspace for monitoring

param name string
param location string
param tags object

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

output id string = logAnalytics.id
output customerId string = logAnalytics.properties.customerId
output primarySharedKey string = logAnalytics.listKeys().primarySharedKey
