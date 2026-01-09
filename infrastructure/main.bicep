// infrastructure/main.bicep
// Main Bicep template for EnglishConnect infrastructure
//
// Deployment:
//   az deployment group create \
//     --resource-group rg-englishconnect \
//     --template-file infrastructure/main.bicep \
//     --parameters environmentName=dev

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environmentName string = 'dev'

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Data location for Communication Services')
param communicationDataLocation string = 'United States'

// Tags applied to all resources
var tags = {
  environment: environmentName
  project: 'EnglishConnect'
  managedBy: 'Bicep'
}

// Resource naming convention
var resourceSuffix = '${environmentName}-ec'

// Azure Communication Services for email (password reset, notifications)
module communicationServices 'modules/communication-services.bicep' = {
  name: 'deploy-communication-services'
  params: {
    name: 'acs-${resourceSuffix}'
    location: 'global'
    dataLocation: communicationDataLocation
    tags: tags
  }
}

// Outputs
output communicationServicesName string = communicationServices.outputs.name
output communicationServicesHostName string = communicationServices.outputs.hostName
