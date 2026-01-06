// Azure Cache for Redis

param name string
param location string
param tags object

resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

output connectionString string = '${redis.properties.hostName}:${redis.properties.sslPort},password=${redis.listKeys().primaryKey},ssl=True,abortConnect=False'
output hostName string = redis.properties.hostName
output id string = redis.id
