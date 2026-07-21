// Subscription-scope monthly budget with actual/forecast alerts.
// Deploy from repository root:
//   az deployment sub create \
//     --location japaneast \
//     --template-file shared/bicep-modules/budget.bicep \
//     --parameters alertEmails="['pi@example.ac.jp']"

targetScope = 'subscription'

@description('Budget name')
param budgetName string = 'spread1000-monthly'

@description('Monthly budget amount (in the billing currency of the subscription)')
param amount int = 100000

@description('Email addresses that receive alerts')
param alertEmails array = [
  'pi@example.ac.jp'
]

@description('First day of the current month in yyyy-MM-01 format. Default = current month at deployment time. IMPORTANT: startDate is IMMUTABLE after the budget is created — if redeploying in a later month, either pass the ORIGINAL startDate explicitly as a parameter, or delete the existing budget first (az consumption budget delete).')
param startDate string = utcNow('yyyy-MM-01')

resource budget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: budgetName
  properties: {
    category: 'Cost'
    amount: amount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: startDate
    }
    notifications: {
      Actual_80_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: alertEmails
      }
      Actual_100_Percent: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        thresholdType: 'Actual'
        contactEmails: alertEmails
      }
      Forecasted_100_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: alertEmails
      }
    }
  }
}

output budgetId string = budget.id
