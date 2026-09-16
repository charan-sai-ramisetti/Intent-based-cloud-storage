# TriCloud Vault

TriCloud Vault is a production-grade multi-cloud file storage platform where users can upload, manage, and download files across AWS S3, Azure Blob Storage, and Google Cloud Storage — all from a single dashboard. It's built with a Django REST backend, a lightweight HTML/JS frontend, and a fully automated infrastructure pipeline using Terraform, Ansible, and GitHub Actions.

The project is designed to demonstrate real-world cloud and backend engineering: not just making something work, but building it the way it would be built at a company — with proper security, automated deployments, zero-downtime rollouts, and production-safe secrets management.

---

## What it does

When a user signs up, they get a free tier with 1 GB of storage per cloud. They can upload a file and choose which clouds to store it on — AWS, Azure, GCP, or all three simultaneously. Files above 10 MB are uploaded in parallel chunks (multipart upload) with a real-time progress bar. Downloads use short-lived signed URLs so files are never exposed publicly.

Users who need more storage can upgrade to PRO (50 GB per cloud) through a Razorpay UPI payment flow. The dashboard shows storage usage per cloud, recent uploads, and file type breakdown in real time.

---

## Architecture

```
User → Route 53 → ACM (SSL) → ALB → Auto Scaling Group (EC2)
                                           ↓
                                    Caddy (reverse proxy)
                                      ↙         ↘
                               Gunicorn        Static files
                               (Django)        (frontend)
                                  ↓
                    ┌─────────────┼─────────────┐
                   AWS S3     Azure Blob      GCP Storage
                                  ↓
                            RDS PostgreSQL (private subnet)
```

The EC2 instances run inside private subnets behind an Application Load Balancer. They have no public IPs — all access is through the ALB or AWS SSM (for deployments and Ansible). The RDS instance is in a separate private subnet with no public access.

---

## Tech stack

**Backend** — Django 5, Django REST Framework, SimpleJWT, Razorpay SDK, boto3, azure-storage-blob, google-cloud-storage, Gunicorn, PostgreSQL 15 (AWS RDS)

**Frontend** — Vanilla HTML, CSS, JavaScript (no framework)

**Infrastructure** — Terraform (AWS VPC, ALB, Auto Scaling, RDS, S3, security groups; Azure Blob Storage; GCP Cloud Storage), Ansible over AWS SSM, GitHub Actions, Caddy

**Cloud** — AWS (ap-south-1), Azure (Central India), GCP (asia-south1)

---

## Project structure

```
tricloud-vault/
├── backend/
│   └── tri_cloud_vault/
│       ├── accounts/        # JWT auth, email verification, password reset
│       ├── files/           # Upload, download, delete, multipart flow
│       ├── clouds/          # AWS, Azure, GCP SDK integrations
│       ├── dashboard/       # Storage summary, folder breakdown, recent files
│       ├── payments/        # Razorpay orders, verification, webhook
│       └── tri_cloud_vault/ # Django settings, URLs, middleware, health check
├── frontend/
│   ├── auth/                # Login, register, verify, forgot/reset password
│   ├── dashboard/           # Main dashboard
│   └── js/                  # auth.js, upload.js, dashboard.js, files.js, payments.js
├── infra/
│   └── terraform/
│       ├── modules/
│       │   ├── aws/         # vpc, alb, autoscaling, rds, s3, security-groups
│       │   ├── azure/       # blob-storage, resource-group
│       │   └── gcp/         # storage-bucket
│       └── environments/
│           ├── dev/
│           └── prod/
└── ansible/
    ├── roles/
    │   ├── common/          # System packages
    │   ├── backend/         # App deploy, secrets fetch, migrations
    │   └── caddy/           # Reverse proxy setup
    └── templates/
        ├── tricloud.service.j2
        └── Caddyfile.j2
```

---

## How uploads work

Files under 10 MB use a single presigned URL — the browser PUTs the file directly to the cloud provider, bypassing the Django server entirely. Files over 10 MB use a multipart flow:

1. Frontend calls `/api/files/multipart/start/` to initialize the upload
2. For each 10 MB chunk, it calls `/api/files/multipart/presign-part/` to get a short-lived signed URL
3. Chunks are uploaded in parallel batches of 3 directly to the cloud, with per-chunk XHR progress tracking
4. Once all chunks are uploaded, `/api/files/multipart/complete/` commits them
5. `/api/files/confirm-upload/` saves the file metadata to the database

This means large file uploads never pass through the Django server — bandwidth cost stays on the cloud provider.

---

## Infrastructure details

**VPC** — Two public subnets (ALB) and two private subnets (EC2, RDS) across two availability zones in ap-south-1. NAT Gateway for outbound internet from private subnets.

**Load balancer** — Application Load Balancer with HTTPS on port 443, HTTP redirected to HTTPS, ACM certificate. Health checks hit `/health/` every 10 seconds. An instance is marked unhealthy after 2 consecutive failures (20 seconds) and replaced.

**Auto Scaling** — Launch template with the golden AMI. Min 1, max 3 instances, desired 1. Scales out at 70% average CPU. When a new AMI is deployed, an instance refresh rolls out new instances one at a time with zero downtime — new instance launches, passes health checks, old instance drains and terminates.

**Database** — RDS PostgreSQL 15 on db.t3.micro, 20 GB, in a private subnet. Not publicly accessible. Connection pooling via `CONN_MAX_AGE=60` in Django.

**Secrets** — All runtime secrets (DB credentials, cloud API keys, Razorpay keys, Django secret key) are stored in AWS Secrets Manager at `tricloud/prod/app`. Ansible fetches them at deploy time and writes `/etc/tricloud.env` (root-only, mode 600). Nothing secret is in the AMI, the repo, or any template file.

---

## CI/CD pipeline

Pushing to `main` triggers the GitHub Actions pipeline:

```
1. Run Django tests (with a fresh Postgres container)
2. Deploy latest code to the golden EC2 instance via SSM
3. Verify /health/ passes on the instance
4. Create a new AMI (named tricloud-vault-prod-YYYYMMDD-<commit>)
5. Update ami_id in prod tfvars
6. terraform apply (creates new launch template version)
7. Trigger ASG instance refresh (rolling replacement, zero downtime)
8. Commit updated ami_id back to the repo
```

If any step fails, the refresh is cancelled and no users are affected — old instances keep running.

---

## Running locally

**Requirements** — Python 3.13, PostgreSQL, AWS/Azure/GCP credentials

```bash
# Clone and set up
git clone https://github.com/charan-sai-ramisetti/tricloud-vault.git
cd tricloud-vault/backend/tri_cloud_vault

python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Copy and fill in env vars
cp .env.example .env

# Run
python manage.py migrate
python manage.py runserver
```

The frontend is static HTML — open `frontend/index.html` directly in a browser, or serve it with any static file server. Set `API_BASE_URL` in `frontend/js/config.js` to point to your local Django server.

**Environment variables needed:**

```
DJANGO_SECRET_KEY=
DEBUG=True

DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432

AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-south-1
AWS_S3_BUCKET_NAME=

AZURE_STORAGE_ACCOUNT_NAME=
AZURE_STORAGE_ACCOUNT_KEY=
AZURE_CONTAINER_NAME=

GCP_BUCKET_NAME=
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-service-account.json

EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
```

---

## Deploying infrastructure

```bash
cd infra/terraform

# Initialise (S3 backend + DynamoDB lock table must exist first)
terraform init

# Deploy to dev
terraform workspace select dev
terraform apply -var-file="environments/dev/terraform.tfvars" -var="db_password=..."

# Deploy to prod
terraform workspace select prod
terraform apply -var-file="environments/prod/terraform.tfvars" -var="db_password=..."
```

---

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Create account |
| POST | `/api/auth/login/` | Get JWT tokens |
| GET | `/api/auth/verify-email/` | Verify email from link |
| POST | `/api/auth/forgot-password/` | Send reset email |
| POST | `/api/auth/reset-password/` | Set new password |
| GET | `/api/files/` | List all files |
| POST | `/api/files/presign/upload/` | Get upload URL (single or multipart) |
| POST | `/api/files/multipart/start/` | Initialize multipart upload |
| POST | `/api/files/multipart/presign-part/` | Get signed URL for one chunk |
| POST | `/api/files/multipart/complete/` | Commit all chunks |
| POST | `/api/files/confirm-upload/` | Save file metadata after upload |
| GET | `/api/files/<id>/presign/download/` | Get download URL |
| DELETE | `/api/files/<id>/` | Delete from selected clouds |
| GET | `/api/storage/summary/` | Storage used per cloud |
| GET | `/api/storage/folders/` | File count by type |
| GET | `/api/storage/recent-files/` | Last 5 uploads |
| POST | `/api/payments/create-order/` | Create Razorpay order |
| POST | `/api/payments/verify/` | Verify payment signature |
| POST | `/api/payments/webhook/` | Razorpay webhook handler |
| GET | `/api/payments/subscription/status/` | Current plan |
| GET | `/health/` | ALB health check |

---

## Plans

| | Free | PRO |
|--|------|-----|
| Storage per cloud | 1 GB | 50 GB |
| Max file size | 100 MB | 50 GB |
| Price | Free | ₹500 one-time |

---

## License

Built for educational and portfolio purposes.
