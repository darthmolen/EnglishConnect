// Azure Database for PostgreSQL Flexible Server

param name string
param location string
param tags object
param administratorLogin string
param managedIdentityPrincipalId string
param managedIdentityName string

@secure()
param administratorPassword string = newGuid()

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Enabled'
    }
  }
}

// Create database
resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  parent: postgres
  name: 'englishconnect'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Enable Microsoft Entra admin
// Note: Server needs to be fully accessible before adding Entra admin.
// Adding dependsOn ensures the server has time to start up.
resource entraAdmin 'Microsoft.DBforPostgreSQL/flexibleServers/administrators@2023-12-01-preview' = {
  parent: postgres
  name: managedIdentityPrincipalId
  properties: {
    principalType: 'ServicePrincipal'
    principalName: managedIdentityName
    tenantId: tenant().tenantId
  }
  dependsOn: [
    database
    firewallRule
  ]
}

// Allow Azure services (for Container Apps)
resource firewallRule 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-12-01-preview' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

output connectionString string = 'postgresql+asyncpg://${administratorLogin}:${administratorPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/englishconnect?ssl=require'
output serverName string = postgres.name
output serverFqdn string = postgres.properties.fullyQualifiedDomainName
