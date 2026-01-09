// infrastructure/modules/communication-services.bicep
// Azure Communication Services for email notifications (password reset, approval notifications)

@description('Name of the Communication Services resource')
param name string = 'acs-englishconnect'

@description('Location - Communication Services is global')
param location string = 'global'

@description('Data location for email data residency')
@allowed([
  'United States'
  'Europe'
  'Australia'
  'UK'
  'Japan'
  'Canada'
  'India'
  'France'
])
param dataLocation string = 'United States'

@description('Tags for the resource')
param tags object = {}

// Azure Communication Services resource
resource communicationService 'Microsoft.Communication/communicationServices@2023-03-31' = {
  name: name
  location: location
  tags: tags
  properties: {
    dataLocation: dataLocation
  }
}

// Output the connection string (in practice, use Key Vault)
output name string = communicationService.name
output id string = communicationService.id
output hostName string = '${communicationService.name}.communication.azure.com'

// Note: Connection string should be retrieved via Key Vault reference or az CLI
// az communication list-key --name <name> --resource-group <rg>
