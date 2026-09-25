#!/bin/bash
# =============================================================================
# create-secret.sh — Create / update the TriCloud Vault production secret in
# AWS Secrets Manager.
#
# Usage:
#   bash create-secret.sh          # create (first time)
#   bash create-secret.sh update   # update existing secret
# =============================================================================

REGION="ap-south-1"
SECRET_ID="tricloud/production/secrets"

SECRET_JSON='{
  "DJANGO_SECRET_KEY":            "REPLACE_WITH_REAL_KEY",
  "DEBUG":                        "False",

  "DB_ENGINE":                    "django.db.backends.postgresql",
  "DB_NAME":                      "tricloud_vault",
  "DB_USER":                      "tricloud_vault",
  "DB_PASSWORD":                  "REPLACE_WITH_DB_PASSWORD",
  "DB_HOST":                      "REPLACE_WITH_RDS_ENDPOINT",
  "DB_PORT":                      "5432",

  "JWT_ACCESS_TOKEN_LIFETIME":    "15",
  "JWT_REFRESH_TOKEN_LIFETIME":   "7",

  "AWS_REGION":                   "ap-south-1",
  "AWS_STORAGE_BUCKET_NAME":      "REPLACE_WITH_S3_BUCKET",
  "AWS_ACCESS_KEY_ID":            "REPLACE_WITH_ACCESS_KEY",
  "AWS_SECRET_ACCESS_KEY":        "REPLACE_WITH_SECRET_KEY",

  "AZURE_ACCOUNT_NAME":           "REPLACE_WITH_AZURE_ACCOUNT",
  "AZURE_ACCOUNT_KEY":            "REPLACE_WITH_AZURE_KEY",
  "AZURE_CONTAINER":              "REPLACE_WITH_CONTAINER_NAME",

  "GCS_BUCKET_NAME":              "REPLACE_WITH_GCS_BUCKET",

  "EMAIL_HOST_USER":              "REPLACE_WITH_EMAIL",
  "EMAIL_HOST_PASSWORD":          "REPLACE_WITH_APP_PASSWORD",

  "RAZORPAY_KEY_ID":              "REPLACE_WITH_KEY_ID",
  "RAZORPAY_KEY_SECRET":          "REPLACE_WITH_KEY_SECRET",
  "RAZORPAY_WEBHOOK_SECRET":      "REPLACE_WITH_WEBHOOK_SECRET",

  "REDIS_URL":                    "redis://127.0.0.1:6379/0",

  "GCP_SERVICE_ACCOUNT_JSON":     "{ \"type\": \"service_account\", \"project_id\": \"REPLACE\" }",

  "DEFAULT_LLM_PROVIDER":         "bedrock",

  "AWS_BEDROCK_REGION":           "ap-south-1",
  "AWS_BEDROCK_MODEL_ID":         "anthropic.claude-3-5-sonnet-20241022-v2:0",

  "AZURE_OPENAI_ENDPOINT":        "REPLACE_WITH_AZURE_OPENAI_ENDPOINT",
  "AZURE_OPENAI_API_KEY":         "REPLACE_WITH_AZURE_OPENAI_KEY",
  "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-4o",
  "AZURE_OPENAI_API_VERSION":     "2024-08-01-preview",

  "ANTHROPIC_API_KEY":            "",
  "OPENAI_API_KEY":               ""
}'

if [ "${1}" = "update" ]; then
  echo "Updating existing secret: ${SECRET_ID}"
  aws secretsmanager update-secret \
    --secret-id    "${SECRET_ID}" \
    --region       "${REGION}" \
    --secret-string "${SECRET_JSON}"
else
  echo "Creating new secret: ${SECRET_ID}"
  aws secretsmanager create-secret \
    --name          "${SECRET_ID}" \
    --description   "All runtime secrets for TriCloud Vault production app" \
    --region        "${REGION}" \
    --secret-string "${SECRET_JSON}"
fi

echo ""
echo "=== Done. Verify with: ==="
echo "aws secretsmanager get-secret-value --secret-id ${SECRET_ID} --region ${REGION} --query SecretString --output text | jq ."
