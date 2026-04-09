@description('Azure Monitoring Solution - Infrastructure as Code')
param location string = resourceGroup().location
param prefix string = 'monitor'
param mysqlAdminPassword string

// --- MySQL Flexible Server ---
resource mysqlServer 'Microsoft.DBforMySQL/flexibleServers@2023-06-30' = {
  name: '${prefix}-mysql'
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '8.0.21'
    administratorLogin: 'adminuser'
    administratorLoginPassword: mysqlAdminPassword
    storage: {
      storageSizeGB: 20
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
  }
}

resource mysqlDatabase 'Microsoft.DBforMySQL/flexibleServers/databases@2023-06-30' = {
  parent: mysqlServer
  name: 'monitoring_db'
  properties: {
    charset: 'utf8mb4'
    collation: 'utf8mb4_unicode_ci'
  }
}

// --- Key Vault ---
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${prefix}-kv'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    accessPolicies: []
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
  }
}

// --- App Service Plan ---
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: '${prefix}-plan'
  location: location
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// --- Backend App Service ---
resource backendApp 'Microsoft.Web/sites@2023-01-01' = {
  name: '${prefix}-api'
  location: location
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|${prefix}acr.azurecr.io/backend:latest'
      appSettings: [
        { name: 'DB_HOST', value: mysqlServer.properties.fullyQualifiedDomainName }
        { name: 'DB_USER', value: 'adminuser' }
        { name: 'DB_PASSWORD', value: mysqlAdminPassword }
        { name: 'DB_NAME', value: 'monitoring_db' }
        { name: 'AZURE_KEY_VAULT_URL', value: keyVault.properties.vaultUri }
      ]
    }
  }
}

// --- Container App Environment (for monitoring engine) ---
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${prefix}-cae'
  location: location
  properties: {}
}

resource monitoringEngineApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${prefix}-engine'
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8001
      }
    }
    template: {
      containers: [
        {
          name: 'monitoring-engine'
          image: '${prefix}acr.azurecr.io/monitoring-engine:latest'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            { name: 'BACKEND_API_URL', value: 'https://${backendApp.properties.defaultHostName}/api/v1' }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 5
      }
    }
  }
}

// --- Azure Functions (Scheduler) ---
resource functionStorageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${prefix}funcsa'
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
}

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: '${prefix}-scheduler'
  location: location
  kind: 'functionapp,linux'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appSettings: [
        { name: 'AzureWebJobsStorage', value: 'DefaultEndpointsProtocol=https;AccountName=${functionStorageAccount.name};AccountKey=${functionStorageAccount.listKeys().keys[0].value}' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'BACKEND_API_URL', value: 'https://${backendApp.properties.defaultHostName}/api/v1' }
        { name: 'MONITORING_ENGINE_URL', value: 'https://${monitoringEngineApp.properties.configuration.ingress.fqdn}' }
      ]
    }
  }
}

// --- Application Insights ---
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${prefix}-insights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
  }
}

// --- Communication Services (Email) ---
resource commService 'Microsoft.Communication/communicationServices@2023-04-01' = {
  name: '${prefix}-comm'
  location: 'global'
  properties: {
    dataLocation: 'United States'
  }
}

// Outputs
output backendUrl string = 'https://${backendApp.properties.defaultHostName}'
output mysqlHost string = mysqlServer.properties.fullyQualifiedDomainName
output keyVaultUri string = keyVault.properties.vaultUri
output appInsightsKey string = appInsights.properties.InstrumentationKey
