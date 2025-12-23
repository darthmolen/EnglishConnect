#!/bin/bash
# azure/infrastructure/conversation-identity/deploy.sh
set -e

RESOURCE_GROUP="${1:-rg-englishconnect}"
LOCATION="${2:-eastus}"

echo "=== EnglishConnect Identity Deployment ==="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo ""

# Check if user has permission to create app registrations
echo "Checking permissions..."
CAN_CREATE_APPS=$(az rest --method get \
  --url "https://graph.microsoft.com/v1.0/policies/authorizationPolicy" \
  --query "defaultUserRolePermissions.allowedToCreateApps" \
  --output tsv 2>/dev/null || echo "false")

if [ "$CAN_CREATE_APPS" != "true" ]; then
  echo "ERROR: You do not have permission to create app registrations."
  echo "Contact your Azure AD administrator to enable 'Users can register applications'"
  echo "or request Application.ReadWrite.All permission."
  exit 1
fi
echo "Permission check passed."
echo ""

# Create resource group if needed
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none 2>/dev/null || true

# Deploy Bicep template
echo "Deploying Microsoft Graph resources..."
RESULT=$(az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file main.bicep \
  --query 'properties.outputs' \
  --output json)

APP_ID=$(echo $RESULT | jq -r '.appId.value')
TENANT_ID=$(echo $RESULT | jq -r '.tenantId.value')

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Add these to your .env files:"
echo ""
echo "# Backend (.env)"
echo "AZURE_AD_CLIENT_ID=$APP_ID"
echo "AZURE_AD_TENANT_ID=$TENANT_ID"
echo ""
echo "# Frontend (.env)"
echo "VITE_AZURE_AD_CLIENT_ID=$APP_ID"
echo "VITE_AZURE_AD_TENANT_ID=$TENANT_ID"
echo ""
echo "To create a client secret for backend token validation:"
echo "az ad app credential reset --id $APP_ID --display-name 'backend-secret' --query password -o tsv"
