// azure/infrastructure/conversation-identity/main.bicep
// Deploys EnglishConnect app registration using Microsoft Graph Bicep extension

extension microsoftGraphV1

@description('Display name for the app registration')
param appDisplayName string = 'EnglishConnect'

@description('Unique name for idempotent deployments')
param uniqueName string = 'englishconnect-spa'

@description('Redirect URIs for SPA')
param spaRedirectUris array = [
  'http://localhost:5173'
  'http://localhost:5173/auth/callback'
]

// Microsoft Graph API resource ID
var microsoftGraphAppId = '00000003-0000-0000-c000-000000000000'

// Permission IDs for openid, profile, email (delegated)
var openIdScopeId = '37f7f235-527c-4136-accd-4a02d197296e'
var profileScopeId = '14dad69e-099b-42c9-810b-d002981feec1'
var emailScopeId = '64a6cdd6-aab1-4aaf-94b8-3cc8405e90d0'

// App Registration
resource app 'Microsoft.Graph/applications@v1.0' = {
  uniqueName: uniqueName
  displayName: appDisplayName
  signInAudience: 'AzureADMyOrg'

  // SPA configuration for MSAL.js
  spa: {
    redirectUris: spaRedirectUris
  }

  // Request OpenID Connect permissions
  requiredResourceAccess: [
    {
      resourceAppId: microsoftGraphAppId
      resourceAccess: [
        { id: openIdScopeId, type: 'Scope' }   // openid
        { id: profileScopeId, type: 'Scope' }  // profile
        { id: emailScopeId, type: 'Scope' }    // email
      ]
    }
  ]
}

// Service Principal (required for authentication)
resource servicePrincipal 'Microsoft.Graph/servicePrincipals@v1.0' = {
  appId: app.appId
}

// Outputs
output appId string = app.appId
output objectId string = app.id
output servicePrincipalId string = servicePrincipal.id
output tenantId string = tenant().tenantId
