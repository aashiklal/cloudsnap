# CloudSnap — Deployment Guide

This guide walks you through deploying CloudSnap to your own AWS account from scratch.
Follow every step in order — each part builds on the previous one.

**Time required:** 30–60 minutes for a first deployment.

---

## What you are building

```
Your browser
    │
    ▼
CloudFront (CDN) → S3 bucket (Next.js static frontend)
    │
    ▼
API Gateway (HTTPS · all routes require a valid login token)
    │
    ├── POST   /upload          → Lambda → S3 store → triggers object-detection
    ├── GET    /images          → Lambda → DynamoDB (browse library)
    ├── GET    /search          → Lambda → DynamoDB (tag search)
    ├── POST   /search-by-image → Lambda → Rekognition (visual similarity)
    ├── POST   /modify-tags     → Lambda → DynamoDB (edit tags)
    └── DELETE /delete          → Lambda → S3 + DynamoDB (delete image)
                                          │
                              ┌───────────┴──────────────┐
                              S3                    DynamoDB
                       (image files)            (metadata + tags)

Auth:        AWS Cognito (user accounts, JWT tokens)
Monitoring:  CloudWatch (logs, dashboards, email alerts)
Tracing:     AWS X-Ray
CI/CD:       GitHub Actions
```

---

## Prerequisites

Before you start, make sure you have the following installed:

| Tool | Check | Install |
|---|---|---|
| AWS CLI | `aws --version` | [aws.amazon.com/cli](https://aws.amazon.com/cli/) |
| Terraform | `terraform version` | `brew install terraform` |
| Node.js 18+ | `node --version` | [nodejs.org](https://nodejs.org) |
| Python 3.10+ | `python3 --version` | [python.org](https://python.org) |
| Git | `git --version` | pre-installed on macOS |

You also need an **AWS account**. If you don't have one, create one free at [aws.amazon.com](https://aws.amazon.com). A credit card is required but you will not be charged at hobby scale.

---

## PART 1 — Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/cloudsnap.git
cd cloudsnap
```

---

## PART 2 — AWS IAM: Create a deploy user

### Why you need this

Your AWS account's root user is the master key — never use it in code or the CLI.
If root credentials leak (e.g. accidentally pushed to GitHub), an attacker could delete
everything and rack up thousands of dollars in charges.

Instead, create a limited `cloudsnap-deploy` user that only has the permissions
CloudSnap needs.

### Step 2.1 — Create the user in the AWS Console

1. Go to [console.aws.amazon.com](https://console.aws.amazon.com) and sign in
2. Search for **IAM** and open it
3. In the left sidebar, click **Users** → **Create user**
4. User name: `cloudsnap-deploy` → click **Next**
5. Under **Permissions options**, select **Attach policies directly**
6. Search for and tick each of these policies:

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

7. Click **Next** → review → **Create user**

Then add an inline policy for CloudFront (AWS limits managed policies to 10 per user):

1. Click the user → **Permissions** tab → **Add permissions** → **Create inline policy**
2. Switch to the **JSON** editor and paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "cloudfront:CreateInvalidation",
      "Resource": "*"
    }
  ]
}
```

3. Name it `cloudsnap-cloudfront` → **Create policy**

### Step 2.2 — Create access keys

1. In IAM → Users, click **cloudsnap-deploy**
2. Click the **Security credentials** tab → **Create access key**
3. Select **Command Line Interface (CLI)** → tick the acknowledgement → **Next** → **Create access key**
4. Click **Download .csv file** — save it somewhere safe. You only get one chance to see the secret key.

The CSV contains:
- **Access key ID** — starts with `AKIA…`
- **Secret access key** — a long random string

### Step 2.3 — Connect your terminal to AWS

```bash
aws configure --profile cloudsnap
```

Answer the four prompts using the values from the CSV:

```
AWS Access Key ID [None]:     AKIAIOSFODNN7EXAMPLE   ← paste Access key ID
AWS Secret Access Key [None]: wJalrXUtnFEMI/...      ← paste Secret access key
Default region name [None]:   ap-southeast-2
Default output format [None]: json
```

> **Tip:** You can use any AWS region — just use the same one consistently throughout
> this guide. `ap-southeast-2` (Sydney) is the example used here.

Verify it worked:

```bash
aws sts get-caller-identity --profile cloudsnap
```

Expected output (your numbers will differ):

```json
{
    "UserId": "AIDAIOSFODNN7EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/cloudsnap-deploy"
}
```

### Step 2.4 — Set this profile as your terminal default

```bash
echo 'export AWS_PROFILE=cloudsnap' >> ~/.zshrc
source ~/.zshrc

# Verify — should work without --profile now
aws sts get-caller-identity
```

---

## PART 3 — Create Terraform's remote state storage

### Why this is needed

Terraform tracks everything it creates in a "state file". Storing it in S3 means it
persists between machines and lets GitHub Actions access it. The DynamoDB table acts as
a lock — it prevents two concurrent Terraform runs from corrupting the state.

This is a one-time manual step. You cannot use Terraform to create the bucket that
Terraform stores its own state in.

### Step 3.1 — Create the S3 state bucket

1. In the AWS Console, go to **S3** → **Create bucket**
2. **Bucket name:** `cloudsnap-tfstate-<yourname>`
   > S3 names are globally unique. If the name is taken, add your name or a random
   > suffix. Remember whatever name you use — you need it in Step 3.3.
3. **Region:** match the region you chose in Part 2 (`ap-southeast-2`)
4. Block Public Access: **all four boxes ticked**
5. **Bucket Versioning:** Enable (lets you roll back a corrupted state file)
6. **Default encryption:** SSE-S3
7. Click **Create bucket**

### Step 3.2 — Create the DynamoDB lock table

1. In the AWS Console, go to **DynamoDB** → **Create table**
2. **Table name:** `cloudsnap-tfstate-lock`
3. **Partition key:** `LockID` (String)
4. **Table settings:** Customize → Read/write capacity → **On-demand**
5. Click **Create table**

### Step 3.3 — Point Terraform at your state bucket

Open `infrastructure/backend.tf` and update it with the bucket name and region you used:

```hcl
terraform {
  backend "s3" {
    bucket       = "cloudsnap-tfstate-<yourname>"   # ← your bucket name
    key          = "cloudsnap/terraform.tfstate"
    region       = "ap-southeast-2"                 # ← your region
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
aws_region     = "ap-southeast-2"            # your AWS region
project_name   = "cloudsnap"
environment    = "prod"
allowed_origin = "*"                          # set to your CloudFront URL after Part 6
lambda_runtime = "python3.12"
alert_email    = "your-email@example.com"    # CloudWatch alerts go here
```

> **`allowed_origin`** restricts which website can call your API. Start with `"*"` so
> you can test locally. You will lock it down to your CloudFront URL in Part 6.3.

> **`alert_email`** — AWS will send you a confirmation email. You must click the link
> or you will never receive alerts.

`terraform.tfvars` is gitignored — it will never be committed.

---

## PART 5 — Deploy infrastructure with Terraform

### Step 5.1 — Initialise

Downloads the AWS provider plugin and connects to your remote state bucket.
Run this once:

```bash
cd infrastructure
terraform init
```

Expected: `Terraform has been successfully initialized!`

If you see `NoSuchBucket`, the S3 state bucket from Part 3.1 was not created yet,
or the bucket name in `backend.tf` does not match.

### Step 5.2 — Preview

```bash
terraform plan
```

Shows every AWS resource Terraform will create. Nothing changes yet. You should see
roughly **37 resources to add** and **0 to destroy**. If it lists anything to destroy
on a first run, stop and investigate before continuing.

### Step 5.3 — Apply

```bash
terraform apply
```

Terraform shows the plan again and asks:

```
Do you want to perform these actions?
  Enter a value:
```

Type `yes` and press Enter. This takes 3–5 minutes.

When it finishes, Terraform prints your resource details:

```
Outputs:

api_gateway_url             = "https://abc123xyz.execute-api.ap-southeast-2.amazonaws.com/prod"
cognito_user_pool_id        = "ap-southeast-2_AbCdEfGhI"
cognito_user_pool_client_id = "1a2b3c4d5e6f7g8h9i0j1k2l"
image_bucket_name           = "cloudsnap-images-prod"
dynamodb_table_name         = "cloudsnap-results-table"
```

**Save these values.** You need them in Parts 6 and 7.
You can always retrieve them again with `terraform output`.

### Step 5.4 — Verify in the Console

Check these services to confirm everything was created:

- **Lambda → Functions** — 7 functions starting with `cloudsnap-`
- **DynamoDB → Tables** — one table
- **API Gateway** — `cloudsnap-api-prod`
- **Cognito → User pools** — `cloudsnap-users-prod`
- **S3** — `cloudsnap-images-prod`
- **CloudWatch → Dashboards** — `cloudsnap-prod`

---

## PART 6 — Configure and test the frontend locally

### Step 6.1 — Install dependencies

```bash
cd frontend
npm install
```

### Step 6.2 — Create the environment file

The frontend never has URLs or IDs hardcoded in source. It reads them from `.env.local`,
which is gitignored and lives only on your machine.

```bash
cp .env.local.example .env.local
```

Open `.env.local` and fill in the values from `terraform output`:

```
NEXT_PUBLIC_API_URL=https://abc123xyz.execute-api.ap-southeast-2.amazonaws.com/prod
NEXT_PUBLIC_USER_POOL_ID=ap-southeast-2_AbCdEfGhI
NEXT_PUBLIC_USER_POOL_CLIENT_ID=1a2b3c4d5e6f7g8h9i0j1k2l
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
2. Enter your name, email, and a password (min 8 chars, must include uppercase + number)
3. Check your email for a 6-digit verification code from AWS
4. Enter the code on the confirmation screen
5. Log in — you should reach the dashboard

If login works, the frontend is correctly connected to Cognito and API Gateway.

Press `Ctrl+C` to stop the dev server.

---

## PART 7 — Host the frontend publicly (S3 + CloudFront)

The dev server only runs on your machine. This part makes the app publicly accessible.

### Step 7.1 — Create the frontend S3 bucket

This is a separate bucket from the image storage bucket — one holds your app files,
the other holds uploaded images.

1. In the AWS Console, go to **S3** → **Create bucket**
2. **Bucket name:** `cloudsnap-frontend-<yourname>`
3. **Region:** same region as before
4. **Block all public access:** all four boxes ticked
   (CloudFront reads from it privately — users never access S3 directly)
5. Click **Create bucket**

### Step 7.2 — Create a CloudFront distribution

CloudFront is a CDN that caches your app files in edge locations worldwide.

1. Go to **CloudFront** → **Create distribution**
2. **Origin domain:** select your S3 frontend bucket from the dropdown
3. **Origin access:** select **Origin access control settings (recommended)**
4. Click **Create new OAC** → leave defaults → **Create**
5. **Viewer protocol policy:** Redirect HTTP to HTTPS
6. **Cache policy:** Managed-CachingOptimized
7. Click **Create distribution**

On the distribution detail page, do three quick fixes:

**Fix 1 — Default root object (General tab → Edit → Settings):**
Set **Default root object** to `index.html` → **Save changes**

**Fix 2 — Error pages for Next.js client-side routing (Error pages tab):**

Add two custom error responses so direct links to sub-pages work:

| HTTP error code | Response page path | HTTP response code |
|---|---|---|
| 403 | `/index.html` | 200 |
| 404 | `/index.html` | 200 |

Click **Create custom error response** for each.

**Fix 3 — S3 bucket policy (Origins tab):**

CloudFront needs permission to read your S3 bucket privately:

1. On the **Origins** tab, select the origin row → click **Edit**
2. Scroll to **Origin access** → click **Copy policy** (copies JSON to clipboard)
3. Open a new tab → **S3** → your frontend bucket → **Permissions** tab → **Bucket policy** → **Edit**
4. Paste the policy → **Save changes**

Wait 5–10 minutes for the distribution to finish deploying (`Last modified` shows a timestamp, not `Deploying`).

From the **General** tab, note:
- **Distribution ID** — looks like `E1ABCDEFGHIJKL`
- **Distribution domain name** — looks like `dxxxxxxxxxxxxx.cloudfront.net`

### Step 7.3 — Lock down CORS to your CloudFront URL

Now that you have the real URL, restrict the API to only accept requests from it.

Open `infrastructure/terraform.tfvars` and update:

```hcl
allowed_origin = "https://dxxxxxxxxxxxxx.cloudfront.net"
```

Apply the change:

```bash
cd infrastructure
terraform apply
# type yes when prompted
```

### Step 7.4 — Build and deploy the frontend

```bash
cd frontend

# Build the static site
npm run build

# Upload to S3 (replace with your actual bucket name from Step 7.1)
aws s3 sync out/ s3://cloudsnap-frontend-<yourname> --delete

# Clear the CloudFront cache so users see the new version
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

Open **https://dxxxxxxxxxxxxx.cloudfront.net** — your app is now live.

---

## PART 8 — GitHub Actions CI/CD

Every push to `main` will automatically deploy your changes.

### Step 8.1 — Create the GitHub repository

1. Go to [github.com](https://github.com) → **+** → **New repository**
2. Name: `cloudsnap` → set to **Public** → do NOT add a README or .gitignore
3. Click **Create repository**

```bash
cd cloudsnap
git remote add origin https://github.com/YOUR_USERNAME/cloudsnap.git
git push -u origin main
```

### Step 8.2 — Add GitHub Secrets

The workflows need your AWS credentials and resource IDs.
Store them as Secrets so they never appear in code or logs.

Go to your repo → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret**. Add each of the following:

| Secret name | Value | Where to find it |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | Starts with `AKIA…` | The CSV from Part 2.2 |
| `AWS_SECRET_ACCESS_KEY` | Long random string | The CSV from Part 2.2 |
| `API_GATEWAY_URL` | Full API Gateway URL | `terraform output api_gateway_url` |
| `COGNITO_USER_POOL_ID` | Starts with `ap-southeast-2_` | `terraform output cognito_user_pool_id` |
| `COGNITO_CLIENT_ID` | Long alphanumeric string | `terraform output cognito_user_pool_client_id` |
| `FRONTEND_BUCKET` | Your frontend S3 bucket name | Step 7.1 |
| `CF_DISTRIBUTION_ID` | Starts with `E`, e.g. `E1234567890ABC` | CloudFront console |

### Step 8.3 — Create a production approval gate

Terraform `apply` (real infrastructure changes) will require your manual approval before
it runs — this prevents accidental changes.

1. In your repo → **Settings** → **Environments** → **New environment**
2. Name: `production` (must be exactly this — the workflow files reference it)
3. Click **Configure environment**
4. Under **Deployment protection rules**, tick **Required reviewers**
5. Add your own GitHub username → **Save protection rules**

### Step 8.4 — Verify CI/CD

Make any small change, commit, and push:

```bash
git add .
git commit -m "chore: test CI/CD"
git push
```

Go to your repo → **Actions** tab. You should see the workflows start.
Click any workflow run to watch the live log output.

---

## PART 9 — Local development with Docker (optional)

Run a fake AWS locally using LocalStack — no real AWS calls, no charges, works offline.

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop).

```bash
make local-up    # starts LocalStack at localhost:4566 + frontend at localhost:3000
make local-down  # stops everything
```

---

## Day-to-day commands

```bash
# Run tests before pushing
make test

# Preview infrastructure changes before applying
make infra-plan

# Apply infrastructure changes
make infra-apply

# See your AWS resource URLs and IDs
cd infrastructure && terraform output

# Build and manually redeploy the frontend
cd frontend && npm run build
aws s3 sync out/ s3://YOUR_FRONTEND_BUCKET --delete
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"

# Stream live Lambda logs in your terminal
aws logs tail /aws/lambda/cloudsnap-upload-prod --follow
aws logs tail /aws/lambda/cloudsnap-delete-prod --follow
```

---

## Troubleshooting

**`aws sts get-caller-identity` returns "Unable to locate credentials"**
→ Open `~/.aws/credentials` and verify the `[cloudsnap]` section exists. The key ID
  must start with `AKIA` and the secret key must be the long random string.
  They are commonly pasted into the wrong fields.

**`terraform init` fails with "NoSuchBucket"**
→ The tfstate S3 bucket does not exist yet, or the name in `backend.tf` doesn't match
  the bucket you created. Complete Part 3.1 first.

**`terraform apply` fails with "AccessDenied"**
→ The deploy user is missing a permission. The error message names the missing action.
  Go to IAM → Users → cloudsnap-deploy → Add permissions.

**`npm install` fails with EACCES**
→ Run `sudo chown -R $(whoami) ~/.npm` then retry.

**Login page shows a Cognito error**
→ Values in `frontend/.env.local` don't match `terraform output`. Check for trailing
  slashes, extra spaces, or copy-paste errors.

**API calls return 401 Unauthorized**
→ The JWT authorizer is working correctly — you need to be logged in. If you are logged
  in and still get 401, check that `NEXT_PUBLIC_API_URL` has no trailing slash and
  exactly matches `terraform output api_gateway_url`.

**CloudFront shows "403 Forbidden"**
→ The S3 bucket policy is missing. Go to CloudFront → your distribution → Origins →
  Edit → copy the OAC policy → paste it into the S3 bucket's Bucket Policy → Save.

**Images don't load on the frontend**
→ The S3 image bucket may not have public read access configured for CloudFront, or the
  Next.js image domain config in `next.config.ts` doesn't match your bucket's region.
  Check `remotePatterns` in `next.config.ts`.

**GitHub Actions shows "Unable to resolve action"**
→ This is a VS Code display bug, not a real error. Push and the workflows will run
  correctly on GitHub.

**`terraform apply` creates fewer than 37 resources**
→ Some resources already existed from a previous run. This is expected — Terraform is
  idempotent. Check `terraform output` to confirm all five outputs have values.
