using '../main.bicep'

param environmentName = 'dev'
param location = 'southcentralus'
param openaiLocation = 'eastus2'  // Realtime API only in eastus2/swedencentral

// Custom domain (englishconnect.vozloop.com) is managed via Azure CLI
// in the deploy workflow to support managed certificates
