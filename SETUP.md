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

**Quick glossary of terms in this diagram:**

- **S3** — Amazon Simple Storage Service. A file storage service. Think of it like a hard drive in the cloud — you store files in "buckets" (folders). CloudSnap uses two: one for your app's HTML/JS files, and one for users' uploaded images.
- **CloudFront** — Amazon's CDN (Content Delivery Network). It sits in front of your S3 bucket and serves your app files to users from servers near them worldwide, making it load faster. It also handles HTTPS.
- **API Gateway** — The front door for your backend. Every HTTP request from the browser (upload, search, delete) goes through API Gateway, which routes it to the right Lambda function.
- **Lambda** — Serverless functions. Instead of running a server 24/7, you write a function and AWS runs it only when a request comes in. You pay per call, not per hour.
- **DynamoDB** — Amazon's NoSQL database. CloudSnap stores image metadata (URLs, tags, who uploaded it) as items in a DynamoDB table. There's no SQL — items are key-value documents.
- **GSI (Global Secondary Index)** — A way to query DynamoDB on a field other than the primary key. CloudSnap uses a GSI on `UserID + UploadedAt` so it can fetch "all images for this user, sorted by date" efficiently.
- **Cognito** — Amazon's authentication service. It handles user sign-up, sign-in, and password rules. When a user logs in, Cognito issues a **JWT** (JSON Web Token) — a signed proof of identity that gets sent with every API request.
- **JWT (JSON Web Token)** — A compact, digitally signed token that proves who you are. The browser attaches it to every API call as a header. API Gateway verifies the signature — if it's invalid or missing, the request is rejected with a 401 error before it even reaches your Lambda.
- **Rekognition** — Amazon's image analysis service. When you upload a photo, a Lambda function sends it to Rekognition, which returns a list of labels (e.g. "dog", "outdoors", "grass"). CloudSnap stores those labels as tags in DynamoDB.
- **CloudWatch** — Amazon's logging and monitoring service. All Lambda function logs go here. You can also set alarms (e.g. "alert me if errors spike") and view dashboards.
- **X-Ray** — Amazon's request tracing service. It tracks a request as it flows through API Gateway → Lambda → DynamoDB and shows you where time is being spent, useful for debugging slow requests.
- **OIDC** — OpenID Connect. A secure way for GitHub Actions to prove to AWS "I am running in *your* repository" without needing a stored password or access key. AWS checks the GitHub-issued token and grants temporary credentials.

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

**What each tool is for:**

- **AWS CLI** — A command-line tool that lets you control AWS services from your terminal. Instead of clicking through the AWS Console web UI every time, you can type commands like `aws s3 sync ...` to upload files or `aws logs tail ...` to stream logs.
- **Terraform** — An "Infrastructure as Code" tool. Instead of clicking buttons in the AWS Console to create resources, you write `.tf` files that describe what you want (a Lambda function, a DynamoDB table, etc.) and Terraform creates, updates, or deletes them automatically. This makes infrastructure repeatable and reviewable in Git.
- **Node.js** — The JavaScript runtime needed to build and run the Next.js frontend. `npm` (Node Package Manager) comes with it and is used to install frontend dependencies.
- **Python 3.12** — The language the Lambda functions are written in. You need it locally to run the test suite.
- **Git** — Version control. You need it to clone this repository and to push code that triggers GitHub Actions CI/CD.

You also need an **AWS account**. If you don't have one, create one free at [aws.amazon.com](https://aws.amazon.com). A credit card is required but you will not be charged at hobby scale.

---

## PART 1 — Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/cloudsnap.git
cd cloudsnap
```

**What this does:** `git clone` downloads a full copy of the repository (all code, history, and branches) to your machine. `cd cloudsnap` moves your terminal into that folder so subsequent commands run in the right place.

---

## PART 2 — AWS credentials for local work

Terraform needs AWS credentials to provision infrastructure from your machine. Without them, every AWS API call would be rejected with "access denied" because AWS has no way of knowing who you are or what you're allowed to do.

### Step 2.1 — Create a deploy IAM user

**What is IAM?** IAM (Identity and Access Management) is how AWS controls *who* can do *what*. Every API call to AWS must come from an **identity** (a user, a role, or a service) that has the right **policies** (permission rules) attached to it.

**Why create a separate user instead of using your root account?** Your AWS root account has unlimited power over everything in your account, including billing. It's best practice to create a dedicated user with only the permissions it needs. If the credentials were ever leaked, the blast radius is limited.

1. Go to the AWS Console → **IAM** → **Users** → **Create user**
2. User name: `cloudsnap-deploy` → **Next**
3. **Attach policies directly** — add each of the following:

   - `AmazonS3FullAccess` — read, write, and delete files in any S3 bucket
   - `AmazonDynamoDBFullAccess` — create tables, read and write items
   - `AWSLambda_FullAccess` — create, update, and invoke Lambda functions
   - `AmazonAPIGatewayAdministrator` — create and configure API Gateway routes
   - `AmazonCognitoPowerUser` — manage user pools and app clients
   - `CloudWatchFullAccess` — create log groups, dashboards, and alarms
   - `AmazonSNSFullAccess` — create topics for email alerts
   - `AmazonSQSFullAccess` — create queues (used as a dead-letter queue for Lambda)
   - `AWSXRayFullAccess` — write and read X-Ray tracing data
   - `IAMFullAccess` — create and attach IAM roles for your Lambda functions

   > **Why does Terraform need IAMFullAccess?** Each Lambda function needs its own IAM execution role — a set of permissions that says "this function is allowed to write to DynamoDB" etc. Terraform creates those roles for you, so it needs permission to create and manage IAM roles.

4. **Create user**, then open the user → **Security credentials** tab → **Create access key** → select **CLI** → download the CSV

   > **What is an access key?** An access key is a username + password pair for the AWS API (not the console). It's two strings: an **Access Key ID** (public, like a username) and a **Secret Access Key** (private, like a password). Together they prove to AWS that you are `cloudsnap-deploy`. Treat the CSV like a password — never commit it to Git.

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

**What this does:** This saves your credentials to `~/.aws/credentials` and your region preference to `~/.aws/config` under a named **profile** called `cloudsnap`. A profile lets you have credentials for multiple AWS accounts on the same machine without them interfering with each other. The `--profile cloudsnap` flag tells the CLI "use this specific set of credentials, not the default ones".

**What is a region?** AWS runs data centres in locations around the world (Sydney = `ap-southeast-2`, US East = `us-east-1`, etc.). All your resources will be created in the region you specify here. Resources in one region can't directly access resources in another by default. Consistency matters — always use the same region throughout this guide.

Verify it worked:

```bash
aws sts get-caller-identity --profile cloudsnap
```

**What this does:** `sts get-caller-identity` asks AWS "who am I authenticated as right now?". If your credentials are correct, AWS responds with your account ID, user ID, and ARN. An ARN (Amazon Resource Name) is a unique identifier for any AWS resource — format: `arn:aws:iam::ACCOUNT_ID:user/cloudsnap-deploy`.

### Step 2.3 — Set the profile as your terminal default

```bash
echo 'export AWS_PROFILE=cloudsnap' >> ~/.zshrc
source ~/.zshrc

aws sts get-caller-identity   # should work without --profile
```

**What this does:** `export AWS_PROFILE=cloudsnap` sets an environment variable that the AWS CLI reads automatically. This means every `aws` command and every Terraform command will use the `cloudsnap` profile without you needing to type `--profile cloudsnap` every time.

`echo '...' >> ~/.zshrc` appends the line to your shell's startup file so it persists across terminal sessions. `source ~/.zshrc` reloads the file in your current terminal session so you don't have to open a new window.

---

## PART 3 — Create Terraform remote state storage

Terraform stores a **state file** that tracks every resource it manages. The state file is the map between your `.tf` code and the real AWS resources that exist. If you delete the state file, Terraform loses track of what it created and can't manage those resources anymore.

Storing it in S3 means:
- It persists between machines (e.g. your laptop and GitHub Actions both use the same state)
- It's versioned, so you can recover from a bad state
- Multiple people can work on the same infrastructure

The DynamoDB table acts as a **distributed lock** — it prevents two Terraform runs from modifying state simultaneously and corrupting it.

**This is a one-time manual step** — you cannot use Terraform to create the bucket that Terraform stores its own state in (circular dependency).

### Step 3.1 — Create the S3 state bucket

1. AWS Console → **S3** → **Create bucket**
2. **Bucket name:** `cloudsnap-tfstate`
   > S3 names are globally unique across all AWS accounts in the world. If `cloudsnap-tfstate` is taken, add a personal suffix (e.g. `cloudsnap-tfstate-yourname`) and update `infrastructure/backend.tf` to match.
3. **Region:** same region you chose in Part 2
4. Block Public Access: **all four boxes ticked**
   > State files often contain resource IDs and ARNs. No one outside AWS should be able to read them. CloudFront and Terraform access this bucket using AWS credentials, not public URLs.
5. Bucket Versioning: **Enable**
   > Versioning keeps a history of every previous state file. If a `terraform apply` goes wrong and corrupts the state, you can roll back to the last good version.
6. Default encryption: **SSE-S3**
   > SSE-S3 (Server-Side Encryption with S3-managed keys) means files are encrypted at rest automatically. This is a free, low-effort security improvement.
7. **Create bucket**

### Step 3.2 — Create the DynamoDB lock table

1. AWS Console → **DynamoDB** → **Create table**
2. Table name: `cloudsnap-tfstate-lock`
3. Partition key: `LockID` (String)
   > Terraform writes a lock item with key `LockID` when it starts a run. Any other run that tries to start will see the lock and wait. When the run finishes, the lock is deleted.
4. Table settings: Customize → **On-demand**
   > On-demand billing means you pay per request (fractions of a cent) instead of reserving capacity. For a lock table that's written to rarely, this is always cheaper.
5. **Create table**

### Step 3.3 — Verify backend.tf

Open `infrastructure/backend.tf` — confirm the bucket name and region match what you created. Update them if you used a different name:

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

**What is `key`?** The `key` is the file path inside the S3 bucket where the state file will be stored. `cloudsnap/terraform.tfstate` means a file named `terraform.tfstate` inside a "folder" called `cloudsnap`. You can have multiple projects sharing one state bucket by giving each a different key.

---

## PART 4 — Configure Terraform variables

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
```

**What are Terraform variables?** Variables let you parameterise your infrastructure. Instead of hard-coding your email address or region inside `.tf` files (which are committed to Git), you put them in `terraform.tfvars`, which is gitignored. This keeps secrets out of version control and makes the same codebase reusable across environments.

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

**What is CORS?** CORS (Cross-Origin Resource Sharing) is a browser security rule. By default, a browser will refuse to make an API call to a *different* domain than the page it's on — so a page loaded from `https://dxxxxx.cloudfront.net` cannot call `https://api.execute-api.amazonaws.com` unless the API explicitly says "requests from cloudfront.net are allowed". The `allowed_origins` variable controls that allowlist. We start with `"*"` (everything allowed) for initial testing, then restrict it once we have the real URL.

> **`allowed_origin` and `allowed_origins`** — Use `"*"` / `["http://localhost:3000"]`
> for now. You will restrict them to your CloudFront URL in Part 7.3.

> **`alert_email`** — AWS sends a confirmation email immediately after `terraform apply`.
> Click the link in that email or you will never receive alerts. This is an SNS subscription — AWS requires explicit opt-in for email notifications.

`terraform.tfvars` is gitignored and will never be committed.

---

## PART 5 — Deploy infrastructure with Terraform

### Step 5.1 — Initialise

```bash
cd infrastructure
terraform init
```

**What this does:** `terraform init` prepares the working directory for use. Specifically it:
1. Downloads the **provider plugins** (the AWS provider is a Go binary that knows how to talk to the AWS API)
2. Configures the **remote backend** (connects to your S3 state bucket)
3. Downloads any **modules** referenced in the code

You only need to run this once per machine, or again after adding new providers or modules.

Expected output: `Terraform has been successfully initialized!`

If you see `NoSuchBucket`: the S3 state bucket doesn't exist yet, or the name in `backend.tf` doesn't match. Complete Part 3.1 first.

### Step 5.2 — Preview

```bash
terraform plan
```

**What this does:** `terraform plan` compares your `.tf` files against the current state file and figures out exactly what needs to be created, changed, or deleted — without doing anything yet. Think of it as a dry run. It shows you a diff:
- `+` green lines = resources that will be **created**
- `~` yellow lines = resources that will be **modified**
- `-` red lines = resources that will be **destroyed**

**Always read the plan before applying.** Nothing changes yet. If it lists anything to **destroy** on a first run, stop and investigate before continuing — something may be misconfigured.

### Step 5.3 — Apply

```bash
terraform apply
```

**What this does:** `terraform apply` executes the plan. It calls the AWS API to create every resource in your `.tf` files — Lambda functions, the DynamoDB table, API Gateway, Cognito user pool, S3 buckets, CloudWatch alarms, IAM roles, and more. It then saves the resulting state to your S3 state bucket.

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

**Save these values.** You need them in Parts 6 and 7. You can always retrieve them again later with `terraform output`.

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

**What this does:** `npm install` reads `package.json` (the list of libraries the project depends on) and downloads all of them into a `node_modules/` folder. This includes React, Next.js, Tailwind, AWS Amplify, and all their transitive dependencies. The `package-lock.json` file pins the exact version of every package so the same versions are installed on every machine.

### Step 6.2 — Create the environment file

```bash
cp .env.local.example .env.local
```

**What are environment variables?** Environment variables are configuration values injected into a running process. Rather than hard-coding URLs and IDs in source code (which would break when you redeploy with different values, and could accidentally leak secrets to Git), you store them outside the code in a `.env.local` file. Next.js reads this file on startup.

**Why `NEXT_PUBLIC_` prefix?** Next.js distinguishes between server-only variables and variables that are safe to expose to the browser. Any variable prefixed with `NEXT_PUBLIC_` is bundled into the client-side JavaScript (it becomes part of your HTML/JS files that anyone can download). Variables without the prefix are only available during the server-side build and are never sent to the browser. Since this app uses a static export with no server, all variables must be `NEXT_PUBLIC_`.

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

**What this does:** `npm run dev` starts Next.js in development mode. It compiles your TypeScript and Tailwind CSS on the fly and serves the app at `http://localhost:3000`. It also watches for file changes and hot-reloads them instantly so you don't need to restart the server every time you edit code.

Open **http://localhost:3000**. You should see the login page.

Test the full flow:
1. Click "Create account" to sign up
2. Enter your first name, last name, email, and a password
   > Password requirements: minimum 12 characters, must include uppercase, lowercase,
   > a number, and a symbol (these rules are defined in Cognito and enforced by AWS — the frontend just surfaces the error)
3. Check your email for a 6-digit verification code from AWS
   > Cognito sends this to verify the email address is real. The verification is required before the account is usable.
4. Enter the code on the confirmation screen
5. Sign in — you should reach the dashboard

Press `Ctrl+C` to stop the dev server.

---

## PART 7 — Host the frontend publicly (S3 + CloudFront)

### Step 7.1 — Create the frontend S3 bucket

This is a separate bucket from the image storage bucket — one holds your app files (HTML, CSS, JavaScript), the other holds users' uploaded images. Keeping them separate limits blast radius and makes it easy to set different access policies on each.

1. AWS Console → **S3** → **Create bucket**
2. **Bucket name:** `cloudsnap-frontend-<yourname>`
3. Region: same region as the rest
4. Block all public access: **all four boxes ticked**
   > Even though this bucket holds your app files, you do NOT want them publicly readable from S3 directly. You will let CloudFront read them privately using an Origin Access Control (OAC). Users access the files through CloudFront URLs, not S3 URLs. This way you can enforce HTTPS, use CloudFront's CDN caching, and add security headers.
5. **Create bucket**

### Step 7.2 — Create a CloudFront distribution

**Why CloudFront instead of just serving from S3 directly?** Several reasons:
- **HTTPS** — S3 static website hosting doesn't give you a custom domain with HTTPS for free. CloudFront does.
- **Speed** — CloudFront caches your files at 450+ edge locations worldwide. A user in London gets files from a London server, not from your Sydney S3 bucket.
- **Security** — CloudFront lets you add security headers, rate limiting, and WAF (Web Application Firewall) rules.
- **Client-side routing** — Next.js uses client-side navigation. When a user refreshes the page at `/dashboard`, the browser asks S3 for `/dashboard/index.html`, which doesn't exist. CloudFront's custom error pages let you serve `index.html` instead, keeping the app working.

1. AWS Console → **CloudFront** → **Create distribution**
2. **Origin domain:** select your S3 frontend bucket from the dropdown
3. **Origin access:** select **Origin access control settings (recommended)**
4. **Create new OAC** → leave defaults → **Create**
   > **What is OAC?** An Origin Access Control is a CloudFront identity that CloudFront uses to sign requests to S3. S3 will only serve the file if the request comes from this specific CloudFront distribution — no public access needed.
5. **Viewer protocol policy:** Redirect HTTP to HTTPS
   > This ensures all traffic is encrypted. Anyone who types `http://` gets automatically redirected to `https://`.
6. **Cache policy:** Managed-CachingOptimized
   > This tells CloudFront how long to cache files at the edge. The optimized policy caches aggressively (up to 1 year for hashed filenames). Next.js adds content hashes to filenames (e.g. `_next/static/abc123.js`) so cached files are always stale-safe.
7. **Create distribution**

Then apply three fixes on the distribution detail page:

**Fix 1 — Default root object** (General tab → Edit → Settings):
Set **Default root object** to `index.html` → **Save changes**
> Without this, visiting `https://dxxxxx.cloudfront.net/` would return a "NoSuchKey" XML error from S3 instead of your app, because S3 doesn't know to serve `index.html` for `/`.

**Fix 2 — Custom error pages for client-side routing** (Error pages tab):

| HTTP error code | Response page path | HTTP response code |
|---|---|---|
| 403 | `/index.html` | 200 |
| 404 | `/index.html` | 200 |

Click **Create custom error response** for each row.

> **Why 403 and not just 404?** When CloudFront asks S3 for a path that doesn't exist (like `/dashboard`), S3 returns a 403 Forbidden (not 404) because the bucket has public access blocked. Both cases need to be caught and redirected to `index.html` so Next.js's client-side router can handle the URL. The response code is changed to 200 so the browser doesn't think anything went wrong.

**Fix 3 — S3 bucket policy** (Origins tab):
1. Select the origin row → **Edit**
2. Scroll to **Origin access** → click **Copy policy**
3. Open a new tab → **S3** → your frontend bucket → **Permissions** → **Bucket policy** → **Edit**
4. Paste the policy → **Save changes**

> **What is a bucket policy?** A bucket policy is a JSON document attached to an S3 bucket that defines who is allowed to do what. By default, the bucket denies all access. The policy you're pasting grants read access to one specific CloudFront distribution only — nothing else can read from it.

Wait 5–10 minutes for the distribution status to leave "Deploying". CloudFront needs time to push your configuration to all edge locations.

From the **General** tab, note:
- **Distribution ID** — looks like `E1ABCDEFGHIJKL`
- **Distribution domain name** — looks like `dxxxxxxxxxxxxx.cloudfront.net`

### Step 7.3 — Lock down CORS to your CloudFront URL

Now that you have the real URL, restrict both CORS variables so that only your app is allowed to call the API:

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

**What happens if you skip this?** If `allowed_origins` stays as `"*"`, any website on the internet could make API calls to your backend (though they'd still need a valid Cognito JWT to get a useful response). Locking it down adds an extra layer of defence.

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

**What each command does:**
- `npm run build` — Compiles your TypeScript, bundles your JavaScript, generates optimised static HTML/CSS/JS files in the `out/` directory. The `NEXT_PUBLIC_*` environment variables in `.env.local` are baked into the compiled files at this point.
- `aws s3 sync out/ s3://... --delete` — Uploads every file in `out/` to your S3 bucket. The `--delete` flag removes any files in S3 that no longer exist locally (e.g. old builds from previous deploys).
- `aws cloudfront create-invalidation --paths "/*"` — Tells CloudFront to throw away its cached copies of all files. Without this, users would see the old version of your app for up to 24 hours. The `/*` wildcard invalidates everything.

Open **https://dxxxxxxxxxxxxx.cloudfront.net** — your app is live.

---

## PART 8 — GitHub Actions CI/CD

Every push to `main` will automatically deploy your changes. The workflows authenticate to AWS using **OIDC** — no long-lived access keys are stored as GitHub secrets.

**What is CI/CD?** CI/CD stands for Continuous Integration / Continuous Deployment. "Continuous Integration" means every push runs automated tests to catch regressions. "Continuous Deployment" means passing code is automatically deployed to production. Together they mean: push code → it's tested → it's live, with no manual steps in between.

**Why OIDC instead of storing AWS keys in GitHub?** If you store an AWS access key as a GitHub secret, that key exists forever until manually rotated. If your GitHub account is compromised, the attacker gets permanent AWS access. With OIDC, GitHub issues a short-lived (15-minute) token for each workflow run. AWS verifies it came from your specific repository and grants temporary credentials. There's nothing to leak.

### Step 8.1 — Create an OIDC identity provider in IAM

**What is an identity provider?** AWS IAM can trust external identity systems (like GitHub) to vouch for users or processes. By adding GitHub as an identity provider, you're telling AWS "when GitHub says a token came from my repository, believe it and grant the associated IAM role".

1. AWS Console → **IAM** → **Identity providers** → **Add provider**
2. **Provider type:** OpenID Connect
3. **Provider URL:** `https://token.actions.githubusercontent.com`
4. **Audience:** `sts.amazonaws.com`
   > The audience is who the token is intended for. `sts.amazonaws.com` means the token is intended for AWS's Security Token Service — the service that issues temporary credentials.
5. **Add provider**

### Step 8.2 — Create a deploy IAM role for GitHub Actions

**What is an IAM role?** Unlike an IAM user (which has permanent credentials), an IAM role has no password or access key. Instead, it's *assumed* — a trusted identity temporarily takes on the role and gets short-lived credentials. GitHub Actions will assume this role via OIDC.

1. IAM → **Roles** → **Create role**
2. **Trusted entity type:** Web identity
3. **Identity provider:** `token.actions.githubusercontent.com`
4. **Audience:** `sts.amazonaws.com`
5. Add a condition to limit the role to your repository:
   - Key: `token.actions.githubusercontent.com:sub`
   - Condition: `StringLike`
   - Value: `repo:YOUR_GITHUB_USERNAME/cloudsnap:*`
   > This condition is critical. Without it, anyone with a GitHub account could assume this role from their own repository. The `sub` claim in the OIDC token includes the repo name — this condition checks that it matches yours.
6. **Next** → attach the same policies you used in Part 2.1 → **Create role**
7. Note the **Role ARN** — looks like `arn:aws:iam::123456789012:role/cloudsnap-github-actions`

### Step 8.3 — Create the GitHub repository

1. [github.com](https://github.com) → **+** → **New repository**
2. Name: `cloudsnap` → **Public** → do NOT add a README or .gitignore
   > Don't let GitHub initialise the repo with any files — your local repo already has a full history. Adding files in GitHub would create a diverged history that requires a force push to reconcile.
3. **Create repository**

```bash
cd cloudsnap
git remote add origin https://github.com/YOUR_USERNAME/cloudsnap.git
git push -u origin main
```

**What this does:** `git remote add origin` tells your local repo where to push. `git push -u origin main` pushes your local `main` branch to GitHub and sets it as the default remote branch for future pushes (so you can just type `git push` next time).

### Step 8.4 — Add GitHub Secrets

**What are GitHub Secrets?** Secrets are encrypted values stored in your repository settings. They're injected as environment variables into GitHub Actions workflow runs. They're never shown in logs. Use them for anything that must not appear in your code — API keys, ARNs, bucket names.

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

**Why an approval gate?** A `terraform apply` can delete or modify production resources. Even with a plan preview step, it's good practice to require a human to click "approve" before infrastructure changes are deployed. The `production` environment in GitHub provides that gate.

1. Repo → **Settings** → **Environments** → **New environment**
2. Name: `production` (must be exactly this — the workflow references it by name)
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

Go to your repo → **Actions** tab and watch the workflows run. You should see:
1. Tests run automatically
2. The frontend build runs automatically
3. If infrastructure changes are detected, an approval request appears before `terraform apply` runs

---

## PART 9 — Local development with Docker (optional)

Run a fake AWS environment locally using LocalStack — no real AWS calls, no charges, works completely offline.

**What is LocalStack?** LocalStack is an open-source tool that runs emulated versions of AWS services (S3, DynamoDB, Lambda, etc.) on your machine inside Docker containers. It's useful for rapid local development and testing without incurring AWS costs or touching production infrastructure.

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop).

```bash
make local-up    # starts LocalStack at localhost:4566 + frontend at localhost:3000
make local-down  # stops everything
```

**What is `make`?** `make` reads a file called `Makefile` in the project root and runs predefined commands. `make local-up` is a shorthand for a longer `docker compose` command — instead of memorising a complex invocation, you type a readable name.

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

**`aws logs tail --follow`** is the cloud equivalent of `tail -f` on a local log file. It streams new log lines to your terminal in real time as Lambda functions are invoked. Invaluable for debugging.

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
→ Run `sudo chown -R $(whoami) ~/.npm` then retry. This error means npm doesn't have
  write permission to its cache directory — the `chown` command makes you the owner.

**Sign-up password rejected**
→ The Cognito password policy requires minimum 12 characters with uppercase, lowercase,
  a number, and a symbol. These rules are defined in Terraform — see `infrastructure/modules/auth/main.tf`.

**Login page shows a Cognito error**
→ Values in `frontend/.env.local` don't match `terraform output`. Check for trailing
  slashes, extra spaces, or copy-paste errors.

**API calls return 401 Unauthorized**
→ The JWT authorizer is working correctly — you must be logged in. If you are logged in
  and still get 401, check that `NEXT_PUBLIC_API_URL` has no trailing slash and exactly
  matches `terraform output api_gateway_url`. The token may also have expired — try signing out and back in.

**API calls return 403 Forbidden**
→ You are authenticated but trying to modify or delete an image that belongs to a
  different user. This is expected ownership-enforcement behaviour — each Lambda checks
  that the `sub` claim in your JWT matches the `UserID` on the item in DynamoDB.

**CloudFront shows "403 Forbidden"**
→ The S3 bucket policy is missing. CloudFront → your distribution → Origins → Edit →
  copy the OAC policy → paste into the S3 frontend bucket's Bucket Policy → Save.

**Images don't load on the frontend**
→ Check `remotePatterns` in `next.config.ts` — the S3 bucket's region and hostname
  must match the pattern `*.s3.amazonaws.com` or `*.s3.*.amazonaws.com`. Next.js
  blocks images from domains not listed in `remotePatterns` as a security measure.

**GitHub Actions shows "Could not assume role"**
→ Verify the trust policy condition on the OIDC role (Step 8.2) matches your repository
  name exactly. The `sub` value format is `repo:USERNAME/REPONAME:ref:refs/heads/main`.

**`terraform apply` output shows fewer resources than expected**
→ Some resources already existed from a previous run. Terraform is idempotent — running
  `apply` twice produces the same result as running it once. Run `terraform output` to
  confirm all five outputs have values.
