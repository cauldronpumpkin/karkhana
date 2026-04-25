param(
  [string]$Region = "us-east-1",
  [string]$HostedZoneId = "Z01660593TIGO81BJOQNG",
  [string]$DomainName = "api.karkhana.one",
  [string]$CertificateArn = "arn:aws:acm:us-east-1:187457215906:certificate/25e6d17b-a8fe-4089-90c2-85ae1f86d066",
  [string]$ApiName = "idearefinery-backend-prod",
  [string]$StageName = '$default'
)

$ErrorActionPreference = "Stop"

$certStatus = aws acm describe-certificate `
  --region $Region `
  --certificate-arn $CertificateArn `
  --query "Certificate.Status" `
  --output text

if ($certStatus -ne "ISSUED") {
  throw "ACM certificate is $certStatus. Update Spaceship nameservers to Route 53 and rerun this after validation."
}

$apiId = aws apigatewayv2 get-apis `
  --region $Region `
  --query "Items[?Name=='$ApiName'].ApiId | [0]" `
  --output text

if (-not $apiId -or $apiId -eq "None") {
  throw "Could not find HTTP API named $ApiName in $Region."
}

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$domainJson = aws apigatewayv2 get-domain-name `
  --region $Region `
  --domain-name $DomainName `
  --output json 2>$null
$domainLookupExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference

if ($domainLookupExitCode -eq 0 -and $domainJson) {
  $domain = $domainJson | ConvertFrom-Json
} else {
  $domain = aws apigatewayv2 create-domain-name `
    --region $Region `
    --domain-name $DomainName `
    --domain-name-configurations CertificateArn=$CertificateArn,EndpointType=REGIONAL,SecurityPolicy=TLS_1_2 `
    --output json | ConvertFrom-Json
}

$existingMapping = aws apigatewayv2 get-api-mappings `
  --region $Region `
  --domain-name $DomainName `
  --query "Items[?ApiId=='$apiId'].ApiMappingId | [0]" `
  --output text 2>$null

if (-not $existingMapping -or $existingMapping -eq "None") {
  aws apigatewayv2 create-api-mapping `
    --region $Region `
    --domain-name $DomainName `
    --api-id $apiId `
    --stage $StageName | Out-Null
}

$config = $domain.DomainNameConfigurations[0]
$aliasTarget = $config.ApiGatewayDomainName
$aliasHostedZoneId = $config.HostedZoneId

$change = @{
  Changes = @(@{
    Action = "UPSERT"
    ResourceRecordSet = @{
      Name = $DomainName
      Type = "A"
      AliasTarget = @{
        DNSName = $aliasTarget
        HostedZoneId = $aliasHostedZoneId
        EvaluateTargetHealth = $false
      }
    }
  })
} | ConvertTo-Json -Depth 10

$tmp = New-TemporaryFile
Set-Content -LiteralPath $tmp -Value $change -Encoding ASCII
aws route53 change-resource-record-sets `
  --hosted-zone-id $HostedZoneId `
  --change-batch "file://$tmp" | Out-Null
Remove-Item -LiteralPath $tmp -Force

Write-Output "API custom domain configured: https://$DomainName"
