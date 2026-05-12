param(
  [string]$Region = "us-east-1",
  [string]$NamePrefix = "idearefinery"
)

$ErrorActionPreference = "Stop"

Write-Output "Read-only AWS retirement inventory. No resources will be changed or deleted."
Write-Output "Region: $Region"
Write-Output "NamePrefix: $NamePrefix"

function AwsRead {
  param([Parameter(ValueFromRemainingArguments = $true)] [string[]] $Args)
  & aws --region $Region @Args
  if ($LASTEXITCODE -ne 0) {
    throw "aws read-only command failed: aws --region $Region $($Args -join ' ')"
  }
}

Write-Output "`n## CloudFormation stacks"
AwsRead cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE ROLLBACK_COMPLETE --query "StackSummaries[?contains(StackName, '$NamePrefix')].[StackName,StackStatus,CreationTime]" --output table

Write-Output "`n## Lambda functions"
AwsRead lambda list-functions --query "Functions[?contains(FunctionName, '$NamePrefix')].[FunctionName,Runtime,LastModified]" --output table

Write-Output "`n## API Gateway v2 APIs"
AwsRead apigatewayv2 get-apis --query "Items[?contains(Name, '$NamePrefix')].[Name,ApiId,ApiEndpoint]" --output table

Write-Output "`n## DynamoDB tables"
AwsRead dynamodb list-tables --query "TableNames[?contains(@, '$NamePrefix')]" --output table

Write-Output "`n## SQS queues"
AwsRead sqs list-queues --queue-name-prefix $NamePrefix --output table

Write-Output "`n## IAM roles"
AwsRead iam list-roles --query "Roles[?contains(RoleName, '$NamePrefix')].[RoleName,Arn,CreateDate]" --output table

Write-Output "`n## Amplify apps"
AwsRead amplify list-apps --query "apps[?contains(name, '$NamePrefix') || contains(defaultDomain, '$NamePrefix')].[name,appId,defaultDomain]" --output table

Write-Output "`nInventory complete. Review docs/aws-retirement.md before any deletion."
