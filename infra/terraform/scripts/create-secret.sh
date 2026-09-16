#!/bin/bash

aws secretsmanager create-secret \
  --name "tricloud/prod/app" \
  --description "All runtime secrets for TriCloud Vault production app" \
  --region "ap-south-1" \
  --secret-string '{
    "DJANGO_SECRET_KEY": "REPLACE_WITH_REAL_KEY",
    "DEBUG": "False",

    "DB_ENGINE": "django.db.backends.postgresql",
    "DB_NAME": "tricloud_vault",
    "DB_USER": "tricloud_vault",
    "DB_PASSWORD": "REPLACE_WITH_DB_PASSWORD",
    "DB_HOST": "REPLACE_WITH_RDS_ENDPOINT",
    "DB_PORT": "5432",

    "JWT_ACCESS_TOKEN_LIFETIME": "15",
    "JWT_REFRESH_TOKEN_LIFETIME": "7",

    "AWS_REGION": "ap-south-1",
    "AWS_S3_BUCKET_NAME": "REPLACE_WITH_BUCKET_NAME",

    "AZURE_STORAGE_ACCOUNT_NAME": "REPLACE_WITH_ACCOUNT_NAME",
    "AZURE_STORAGE_ACCOUNT_KEY": "REPLACE_WITH_ACCOUNT_KEY",
    "AZURE_CONTAINER_NAME": "REPLACE_WITH_CONTAINER_NAME",

    "GCP_BUCKET_NAME": "REPLACE_WITH_GCP_BUCKET",

    "EMAIL_HOST_USER": "REPLACE_WITH_EMAIL",
    "EMAIL_HOST_PASSWORD": "REPLACE_WITH_APP_PASSWORD",

    "RAZORPAY_KEY_ID": "REPLACE_WITH_KEY_ID",
    "RAZORPAY_KEY_SECRET": "REPLACE_WITH_KEY_SECRET",
    "RAZORPAY_WEBHOOK_SECRET": "REPLACE_WITH_WEBHOOK_SECRET",

    "GCP_SERVICE_ACCOUNT_JSON": "{ \"type\": \"service_account\", \"project_id\": \"REPLACE\", \"private_key_id\": \"REPLACE\", \"private_key\": \"-----BEGIN PRIVATE KEY-----\\nREPLACE\\n-----END PRIVATE KEY-----\\n\", \"client_email\": \"REPLACE\", \"client_id\": \"REPLACE\" }"
  }'

echo "Secret created successfully."
echo "Verify with:"
echo "aws secretsmanager get-secret-value --secret-id tricloud/prod/app --query SecretString --output text | jq ."