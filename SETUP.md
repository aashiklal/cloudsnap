# CloudSnap — Deployment Guide

This guide walks you through deploying CloudSnap to your own AWS account from scratch.
Follow every step in order — each part builds on the previous one.

**Time required:** 45–90 minutes for a first deployment.

---

## What you are building

```
Your browser
    │
    ▼
CloudFront (CDN) → S3 bucket (Next.js static frontend)
    │
    ▼
API Gateway v2 HTTP (all routes require a valid Cognito JWT)
    │
    ├── POST   /upload          → Lambda → S3 + DynamoDB
    │                                    → S3 event → object-detection Lambda
    │                                                → Rekognition → DynamoDB
    ├── GET    /images          → Lambda → DynamoDB GSI (per-user, newest first)
    ├── GET    /search          → Lambda → DynamoDB GSI + tag filter
    ├── POST   /search-by-image → Lambda → Rekognition + DynamoDB GSI
    ├── POST   /modify-tags     → Lambda → ownership check + DynamoDB
    └── DELETE /delete          → Lambda → ownership check + S3 + DynamoDB
                                          │
                              ┌───────────┴──────────────┐
                              S3 (image files)       DynamoDB (metadata + tags)
                         private, presigned           GSI: UserID-UploadedAt-index
                         URL access only

Auth:        AWS Cognito (User Pool, JWT tokens)
Monitoring:  CloudWatch (logs, dashboards, email alerts via SNS)
Tracing:     AWS X-Ray (10 % sampling)
CI/CD:       GitHub Actions (OIDC — no long-lived credentials)
```

---

## Prerequisites

Make sure you have the following installed before starting:

| Tool | Check | Install |
|---|---|---|
| AWS CLI | `aws --version` | [aws.amazon.com/cli](https://aws.amazon.com/cli/) |
| Terraform 1.7+ | `terraform version` | `brew install terraform` |
| Node.js 20+ | `node --version` | [nodejs.org](https://nodejs.org) |
| Python 3.12 | `python3 --version` | [python.org](https://python.org) |
| Git | `git --version` | pre-installed on macOS |

You also need an **AWS account**. If you don't have one, create one free at [aws.amazon.com](https://aws.amazon.com). A credit card is required but you will not be charged at hobby scale.

---

## PART 1 — Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/cloudsnap.git
cd cloudsnap
```

---

## PART 2 — AWS credentials for local work

Terraform needs AWS credentials to provision infrastructure from your machine.

### Step 2.1 — Create a deploy IAM user

1. Go to the AWS Console → **IAM** → **Users** → **Create user**
2. User name: `cloudsnap-deploy` → **Next**
3. **Attach policies directly** — add each of the following:

   - `AmazonS3FullAccess`
   - `AmazonDynamoDBFullAccess`
   - `AWSLambda_FullAccess`
   - `AmazonAPIGatewayAdministrator`
   - `AmazonCognitoPowerUser`
   - `CloudWatchFullAccess`
   - `AmazonSNSFullAccess`
   - `AmazonSQSFullAccess`
   - `AWSXRayFullAccess`
   - `IAMFullAccess`

4. **Create user**, then open the user → **Security credentials** tab → **Create access key** → select **CLI** → download the CSV

> **Note:** AWS limits managed policies to 10 per user. If you need CloudFront permissions for manual deploys, add a custom inline policy with `cloudfront:*`.

### Step 2.2 — Configure the AWS CLI

```bash
aws configure --profile cloudsnap
```

Enter the values from the CSV:

```
AWS Access Key ID:     (paste from CSV)
AWS Secret Access Key: (paste from CSV)
Default region name:   ap-southeast-2
Default output format: json
```

Verify it worked:

```bash
aws sts get-caller-identity --profile cloudsnap
```

### Step 2.3 — Set the profile as your terminal default

```bash
echo 'export AWS_PROFILE=cloudsnap' >> ~/.zshrc
source ~/.zshrc

aws sts get-caller-identity   # should work without --profile
```

---

## PART 3 — Create Terraform remote state storage

Terraform stores a state file that tracks every resource it manages. Storing it in S3
means it persists between machines and lets GitHub Actions access it. The DynamoDB table
prevents concurrent runs from corrupting the state.

**This is a one-time manual step** — you cannot use Terraform to create the bucket that
Terraform stores its own state in.

### Step 3.1 — Create the S3 state bucket

1. AWS Console → **S3** → **Create bucket**
2. **Bucket name:** `cloudsnap-tfstate`
   > S3 names are globally unique. If `cloudsnap-tfstate` is taken, add a personal suffix
   > and update `infrastructure/backend.tf` to match.
3. **Region:** same region you chose in Part 2
4. Block Public Access: **all four boxes ticked**
5. Bucket Versioning: **Enable**
6. Default encryption: **SSE-S3**
7. **Create bucket**

### Step 3.2 — Create the DynamoDB lock table

1. AWS Console → **DynamoDB** → **Create table**
2. Table name: `cloudsnap-tfstate-lock`
3. Partition key: `LockID` (String)
4. Table settings: Customize → **On-demand**
5. **Create table**

### Step 3.3 — Verify backend.tf

Open `infrastructure/backend.tf` — confirm the bucket name and region match what you
created. Update them if you used a different name:

```hcl
terraform {
  backend "s3" {
    bucket       = "cloudsnap-tfstate"    # ← must match the bucket you created
    key          = "cloudsnap/terraform.tfstate"
    region       = "ap-southeast-2"       # ← must match your chosen region
    use_lockfile = true
    encrypt      = true
  }
}
```

---

## PART 4 — Configure Terraform variables

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
```

Open `terraform.tfvars` and fill in your values:

```hcl
aws_region     = "ap-southeast-2"           # your AWS region
project_name   = "cloudsnap"
environment    = "prod"

# Single origin for S3 CORS — start with "*", lock it down after Part 7
allowed_origin  = "*"

# List of origins for API Gateway CORS — include your CloudFront URL once you have it
allowed_origins = ["http://localhost:3000"]

lambda_runtime = "python3.12"
alert_email    = "your-email@example.com"   # CloudWatch alarms notify this address
```

> **`allowed_origin` and `allowed_origins`** — Use `"*"` / `["http://localhost:3000"]`
> for now. You will restrict them to your CloudFront URL in Part 7.3.

> **`alert_email`** — AWS sends a confirmation email immediately after `terraform apply`.
> Click the link in that email or you will never receive alerts.

`terraform.tfvars` is gitignored and will never be committed.

---

## PART 5 — Deploy infrastructure with Terraform

### Step 5.1 — Initialise

```bash
cd infrastructure
terraform init
```

Expected: `Terraform has been successfully initialized!`

If you see `NoSuchBucket`: the S3 state bucket doesn't exist yet, or the name in
`backend.tf` doesn't match. Complete Part 3.1 first.

### Step 5.2 — Preview

```bash
terraform plan
```

Nothing changes yet. Review the list of resources to add. If it lists anything to
**destroy** on a first run, stop and investigate before continuing.

### Step 5.3 — Apply

```bash
terraform apply
```

Type `yes` when prompted. This takes 3–5 minutes.

When it finishes, Terraform prints your resource details:

```
Outputs:

api_gateway_url             = "https://<id>.execute-api.ap-southeast-2.amazonaws.com/prod"
cognito_user_pool_id        = "ap-southeast-2_<id>"
cognito_user_pool_client_id = "<alphanumeric id>"
image_bucket_name           = "cloudsnap-img-prod"
dynamodb_table_name         = "cloudsnap-results-table"
```

**Save these values.** You need them in Parts 6 and 7.
You can always retrieve them again later with `terraform output`.

### Step 5.4 — Verify in the Console

Check these services to confirm everything was created:

- **Lambda → Functions** — 7 functions starting with `cloudsnap-`
- **DynamoDB → Tables** — one table (`cloudsnap-results-table`) with a `UserID-UploadedAt-index` GSI
- **API Gateway** — `cloudsnap-api-prod`
- **Cognito → User pools** — `cloudsnap-users-prod`
- **S3** — `cloudsnap-img-prod`
- **CloudWatch → Dashboards** — `cloudsnap-prod`

---

## PART 6 — Configure and test the frontend locally

### Step 6.1 — Install dependencies

```bash
cd frontend
npm install
```

### Step 6.2 — Create the environment file

```bash
cp .env.local.example .env.local
```

Open `.env.local` and fill in the values from `terraform output`:

```
NEXT_PUBLIC_API_URL=https://<id>.execute-api.ap-southeast-2.amazonaws.com/prod
NEXT_PUBLIC_USER_POOL_ID=ap-southeast-2_<id>
NEXT_PUBLIC_USER_POOL_CLIENT_ID=<alphanumeric id>
NEXT_PUBLIC_REGION=ap-southeast-2
```

No trailing slashes. No extra spaces.

### Step 6.3 — Test locally

```bash
npm run dev
```

Open **http://localhost:3000**. You should see the login page.

Test the full flow:
1. Click "Create account" to sign up
2. Enter your first name, last name, email, and a password
   > Password requirements: minimum 12 characters, must include uppercase, lowercase,
   > a number, and a symbol
3. Check your email for a 6-digit verification code from AWS
4. Enter the code on the confirmation screen
5. Sign in — you should reach the dashboard

Press `Ctrl+C` to stop the dev server.

---

## PART 7 — Host the frontend publicly (S3 + CloudFront)

### Step 7.1 — Create the frontend S3 bucket

This is a separate bucket from the image storage bucket — one holds your app files,
the other holds uploaded images.

1. AWS Console → **S3** → **Create bucket**
2. **Bucket name:** `cloudsnap-frontend-<yourname>`
3. Region: same region as the rest
4. Block all public access: **all four boxes ticked**
   (CloudFront reads from it privately — users never access S3 directly)
5. **Create bucket**

### Step 7.2 — Create a CloudFront distribution

1. AWS Console → **CloudFront** → **Create distribution**
2. **Origin domain:** select your S3 frontend bucket from the dropdown
3. **Origin access:** select **Origin access control settings (recommended)**
4. **Create new OAC** → leave defaults → **Create**
5. **Viewer protocol policy:** Redirect HTTP to HTTPS
6. **Cache policy:** Managed-CachingOptimized
7. **Create distribution**

Then apply three fixes on the distribution detail page:

**Fix 1 — Default root object** (General tab → Edit → Settings):
Set **Default root object** to `index.html` → **Save changes**

**Fix 2 — Custom error pages for client-side routing** (Error pages tab):

| HTTP error code | Response page path | HTTP response code |
|---|---|---|
| 403 | `/index.html` | 200 |
| 404 | `/index.html` | 200 |

Click **Create custom error response** for each row.

**Fix 3 — S3 bucket policy** (Origins tab):
1. Select the origin row → **Edit**
2. Scroll to **Origin access** → click **Copy policy**
3. Open a new tab → **S3** → your frontend bucket → **Permissions** → **Bucket policy** → **Edit**
4. Paste the policy → **Save changes**

Wait 5–10 minutes for the distribution status to leave "Deploying".

From the **General** tab, note:
- **Distribution ID** — looks like `E1ABCDEFGHIJKL`
- **Distribution domain name** — looks like `dxxxxxxxxxxxxx.cloudfront.net`

### Step 7.3 — Lock down CORS to your CloudFront URL

Now that you have the real URL, restrict both CORS variables:

```hcl
# infrastructure/terraform.tfvars
allowed_origin  = "https://dxxxxxxxxxxxxx.cloudfront.net"
allowed_origins = ["https://dxxxxxxxxxxxxx.cloudfront.net", "http://localhost:3000"]
```

Apply the change:

```bash
cd infrastructure
terraform apply   # type yes when prompted
```

### Step 7.4 — Build and deploy the frontend

```bash
cd frontend

# Rebuild with the locked-down CORS origin in the env file
npm run build

# Upload to S3
aws s3 sync out/ s3://cloudsnap-frontend-<yourname> --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

Open **https://dxxxxxxxxxxxxx.cloudfront.net** — your app is live.

---

## PART 8 — GitHub Actions CI/CD

Every push to `main` will automatically deploy your changes. The workflows authenticate
to AWS using **OIDC** — no long-lived access keys are stored as GitHub secrets.

### Step 8.1 — Create an OIDC identity provider in IAM

1. AWS Console → **IAM** → **Identity providers** → **Add provider**
2. **Provider type:** OpenID Connect
3. **Provider URL:** `https://token.actions.githubusercontent.com`
4. **Audience:** `sts.amazonaws.com`
5. **Add provider**

### Step 8.2 — Create a deploy IAM role for GitHub Actions

1. IAM → **Roles** → **Create role**
2. **Trusted entity type:** Web identity
3. **Identity provider:** `token.actions.githubusercontent.com`
4. **Audience:** `sts.amazonaws.com`
5. Add a condition to limit the role to your repository:
   - Key: `token.actions.githubusercontent.com:sub`
   - Condition: `StringLike`
   - Value: `repo:YOUR_GITHUB_USERNAME/cloudsnap:*`
6. **Next** → attach the same policies you used in Part 2.1 → **Create role**
7. Note the **Role ARN** — looks like `arn:aws:iam::123456789012:role/cloudsnap-github-actions`

### Step 8.3 — Create the GitHub repository

1. [github.com](https://github.com) → **+** → **New repository**
2. Name: `cloudsnap` → **Public** → do NOT add a README or .gitignore
3. **Create repository**

```bash
cd cloudsnap
git remote add origin https://github.com/YOUR_USERNAME/cloudsnap.git
git push -u origin main
```

### Step 8.4 — Add GitHub Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret**. Add each of the following:

| Secret name | Value | Where to find it |
|---|---|---|
| `AWS_DEPLOY_ROLE_ARN` | `arn:aws:iam::...` | Step 8.2 |
| `API_GATEWAY_URL` | Full API Gateway URL | `terraform output api_gateway_url` |
| `COGNITO_USER_POOL_ID` | Starts with region prefix | `terraform output cognito_user_pool_id` |
| `COGNITO_CLIENT_ID` | Alphanumeric string | `terraform output cognito_user_pool_client_id` |
| `FRONTEND_BUCKET` | Your frontend S3 bucket name | Step 7.1 |
| `CF_DISTRIBUTION_ID` | Starts with `E` | CloudFront console |

### Step 8.5 — Create a production approval gate

Infrastructure `apply` requires your manual approval to prevent accidental changes.

1. Repo → **Settings** → **Environments** → **New environment**
2. Name: `production` (must be exactly this — the workflow references it)
3. **Configure environment**
4. **Deployment protection rules** → tick **Required reviewers**
5. Add your own GitHub username → **Save protection rules**

### Step 8.6 — Verify CI/CD

Make a small change, commit, and push:

```bash
git add README.md
git commit -m "chore: test CI/CD pipeline"
git push
```

Go to your repo → **Actions** tab and watch the workflows run.

---

## PART 9 — Local development with Docker (optional)

Run a fake AWS environment locally using LocalStack — no real AWS calls, no charges,
works completely offline.

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop).

```bash
make local-up    # starts LocalStack at localhost:4566 + frontend at localhost:3000
make local-down  # stops everything
```

---

## Day-to-day commands

```bash
# Run tests
make test

# Preview infrastructure changes
make infra-plan

# Apply infrastructure changes
make infra-apply

# See your AWS resource URLs and IDs
cd infrastructure && terraform output

# Build and manually redeploy the frontend
cd frontend && npm run build
aws s3 sync out/ s3://YOUR_FRONTEND_BUCKET --delete
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"

# Stream live Lambda logs
aws logs tail /aws/lambda/cloudsnap-upload-prod --follow
aws logs tail /aws/lambda/cloudsnap-object-detection-prod --follow
```

---

## Troubleshooting

**`aws sts get-caller-identity` returns "Unable to locate credentials"**
→ Run `cat ~/.aws/credentials` and verify a `[cloudsnap]` section exists. Check that
  the key ID starts with `AKIA` and that the profile is exported: `echo $AWS_PROFILE`.

**`terraform init` fails with "NoSuchBucket"**
→ The tfstate S3 bucket doesn't exist yet, or the name in `backend.tf` doesn't match.
  Complete Part 3.1 first.

**`terraform apply` fails with "AccessDenied"**
→ The deploy user is missing a permission. The error message names the missing IAM
  action. Go to IAM → Users → cloudsnap-deploy → Add permissions.

**`npm install` fails with EACCES**
→ Run `sudo chown -R $(whoami) ~/.npm` then retry.

**Sign-up password rejected**
→ The Cognito password policy requires minimum 12 characters with uppercase, lowercase,
  a number, and a symbol.

**Login page shows a Cognito error**
→ Values in `frontend/.env.local` don't match `terraform output`. Check for trailing
  slashes, extra spaces, or copy-paste errors.

**API calls return 401 Unauthorized**
→ The JWT authorizer is working correctly — you must be logged in. If you are logged in
  and still get 401, check that `NEXT_PUBLIC_API_URL` has no trailing slash and exactly
  matches `terraform output api_gateway_url`.

**API calls return 403 Forbidden**
→ You are authenticated but trying to modify or delete an image that belongs to a
  different user. This is expected ownership-enforcement behaviour.

**CloudFront shows "403 Forbidden"**
→ The S3 bucket policy is missing. CloudFront → your distribution → Origins → Edit →
  copy the OAC policy → paste into the S3 frontend bucket's Bucket Policy → Save.

**Images don't load on the frontend**
→ Check `remotePatterns` in `next.config.ts` — the S3 bucket's region and hostname
  must match the pattern `*.s3.amazonaws.com` or `*.s3.*.amazonaws.com`.

**GitHub Actions shows "Could not assume role"**
→ Verify the trust policy condition on the OIDC role (Step 8.2) matches your repository
  name exactly. The `sub` value format is `repo:USERNAME/REPONAME:ref:refs/heads/main`.

**`terraform apply` output shows fewer resources than expected**
→ Some resources already existed from a previous run. Terraform is idempotent — this is
  normal. Run `terraform output` to confirm all five outputs have values.
