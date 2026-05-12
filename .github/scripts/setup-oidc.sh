#!/usr/bin/env bash
# Karkhana OIDC IAM Role Setup
# Creates a GitHub OIDC identity provider (if needed) and an IAM role
# for the deploy-frontend GHA workflow to assume.
#
# Usage: bash .github/scripts/setup-oidc.sh
# Requires: AWS CLI configured with admin credentials, jq
#
# Outputs the role ARN at the end — add to GitHub secret as OIDC_ROLE_ARN

set -euo pipefail

GITHUB_ORG="cauldronpumpkin"
GITHUB_REPO="karkhana"
ROLE_NAME="github-actions-deploy-karkhana-frontend"

echo "=== Step 1: Check/Create GitHub OIDC Identity Provider ==="
EXISTING_PROVIDER=$(aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[?contains(Arn, 'token.actions.githubusercontent.com')].Arn" --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_PROVIDER" ]; then
  echo "OIDC provider already exists: $EXISTING_PROVIDER"
else
  echo "Creating OIDC identity provider..."
  aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "$(
      curl -s https://token.actions.githubusercontent.com/.well-known/openid-configuration \
      | jq -r '.jwks_uri' \
      | xargs curl -s \
      | jq -r '.keys[0].x5c[0]' \
      | openssl x509 -fingerprint -noout \
      | sed 's/.*=//' | tr -d ':'
    )"
  echo "OIDC provider created."
fi

echo ""
echo "=== Step 2: Create IAM Role ==="

# Policy document for GitHub OIDC trust
cat > /tmp/oidc-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
EOF

if aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
  echo "Role '$ROLE_NAME' already exists. Updating trust policy..."
  aws iam update-assume-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-document file:///tmp/oidc-trust-policy.json
else
  echo "Creating role '$ROLE_NAME'..."
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document file:///tmp/oidc-trust-policy.json \
    --description "GitHub Actions OIDC role for deploying Karkhana frontend"
fi

echo ""
echo "=== Step 3: Attach Deployment Permissions ==="

# Minimal policy: Amplify start-job + read config
cat > /tmp/deploy-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "amplify:StartJob",
        "amplify:GetApp",
        "amplify:GetBranch",
        "amplify:ListApps",
        "amplify:ListBranches"
      ],
      "Resource": "*"
    }
  ]
}
EOF

POLICY_NAME="${ROLE_NAME}-policy"
EXISTING_POLICY=$(aws iam list-attached-role-policies --role-name "$ROLE_NAME" --query "AttachedPolicies[?PolicyName=='$POLICY_NAME'].PolicyName" --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_POLICY" ]; then
  echo "Policy '$POLICY_NAME' already attached."
else
  echo "Creating and attaching policy..."
  POLICY_ARN=$(aws iam create-policy \
    --policy-name "$POLICY_NAME" \
    --policy-document file:///tmp/deploy-policy.json \
    --query "Policy.Arn" \
    --output text)
  aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "$POLICY_ARN"
  echo "Policy attached."
fi

echo ""
echo "=== Complete ==="
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo "Role ARN: $ROLE_ARN"
echo ""
echo "Next steps:"
echo "1. Add this ARN as a GitHub Actions secret named OIDC_ROLE_ARN"
echo "   gh secret set OIDC_ROLE_ARN --repo ${GITHUB_ORG}/${GITHUB_REPO} --body \"$ROLE_ARN\""
echo "2. The deploy-frontend.yml workflow will use it automatically"
