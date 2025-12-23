# EnglishConnect Azure Identity Setup

Infrastructure as Code for Azure Entra ID app registration using Bicep.

## Prerequisites

1. Azure CLI installed: `az --version` (2.61.0+)
2. Bicep CLI installed: `az bicep version` (0.36.1+)
3. Logged in to Azure: `az login`
4. Required permissions: `Application.ReadWrite.All`

## Deploy

```bash
cd azure/infrastructure/conversation-identity
chmod +x deploy.sh
./deploy.sh [resource-group] [location]
```

Default: `./deploy.sh rg-englishconnect eastus`

## After Deployment

1. Copy the output values to your `.env` files (backend and frontend)

2. Create a client secret for backend token validation:
   ```bash
   az ad app credential reset --id <APP_ID> --display-name 'backend-secret' --query password -o tsv
   ```

3. Add `AZURE_AD_CLIENT_SECRET` to backend `.env`

## What Gets Created

- **App Registration**: EnglishConnect SPA application
- **Service Principal**: For authentication
- **API Permissions**: openid, profile, email (delegated)
- **Sign-in Audience**: Single tenant (AzureADMyOrg)

## Redirect URIs

Configured by default:
- `http://localhost:5173` (SPA root)
- `http://localhost:5173/auth/callback` (OAuth callback)

To add production URIs, update `spaRedirectUris` in main.bicep and redeploy.

## Troubleshooting

**"Application.ReadWrite.All permission required"**
- Ensure you have admin consent or sufficient privileges

**"Extension not found"**
- Run `az bicep upgrade` to get latest Bicep version
- Verify bicepconfig.json has extensibility enabled
