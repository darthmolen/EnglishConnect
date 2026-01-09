# EnglishConnect Infrastructure

Azure infrastructure definitions using Bicep.

## Resources

- **Azure Communication Services**: Email notifications for password reset and user approval

## Deployment

### Prerequisites

1. Azure CLI installed and logged in
2. Resource group created

### Deploy

```bash
# Create resource group (if not exists)
az group create --name rg-englishconnect --location southcentralus

# Deploy infrastructure
az deployment group create \
  --resource-group rg-englishconnect \
  --template-file infrastructure/main.bicep \
  --parameters environmentName=dev
```

### Get Connection String

After deployment, retrieve the Communication Services connection string:

```bash
az communication list-key \
  --name acs-dev-ec \
  --resource-group rg-englishconnect \
  --query primaryConnectionString \
  --output tsv
```

Store the connection string in Azure Key Vault or environment variables:

```bash
# Add to .env file
AZURE_COMMUNICATION_CONNECTION_STRING=endpoint=https://...
```

## Email Domain Configuration

Azure Communication Services requires domain verification for sending emails:

1. Go to Azure Portal > Communication Services > Email > Domains
2. Add a custom domain or use Azure-managed domain
3. Verify domain ownership via DNS records
4. Configure sender address (e.g., noreply@englishconnect.org)

## Environment Variables

Add these to your deployment configuration:

```env
# Azure Communication Services
AZURE_COMMUNICATION_CONNECTION_STRING=endpoint=https://acs-dev-ec.communication.azure.com/...
EMAIL_SENDER_ADDRESS=noreply@englishconnect.org
```
