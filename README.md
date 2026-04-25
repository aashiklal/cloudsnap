# CloudSnap

A serverless image management platform built on AWS. Upload images, get automatic AI-powered object detection, search by tags or by query image, browse your personal library, and manage everything from a Next.js frontend — without managing a single server.

Built as a portfolio project demonstrating production-grade AWS architecture: Terraform IaC, Cognito JWT auth, per-user data isolation, GitHub Actions CI/CD with OIDC, distributed tracing, and full observability.

---

## Features

- **Upload** — drag-and-drop upload to S3 (JPEG, PNG, up to 10 MB per file)
- **Auto-tagging** — object detection runs automatically via AWS Rekognition on every upload
- **Browse** — paginated gallery of your images with detected tags; images not yet analysed show an "Analysing…" badge
- **Search by tags** — find your images by tag name and minimum detection count; combine multiple tags
- **Reverse image search** — upload a query image to find visually similar images in your library
- **Tag management** — add custom tags or remove existing ones with a chip-based UI; existing tags are pre-loaded
- **Delete** — removes an image from S3 and DynamoDB in a single confirmed action
- **Authentication** — sign up, sign in, and sign out via AWS Cognito; every API route requires a valid JWT
- **Per-user isolation** — every query, upload, and delete is scoped to the authenticated user; you can only see and modify your own images

---

## Architecture

```
Browser  ─────────────────────────────────────────────────────────────────────
 │  Next.js 16 · TypeScript · Tailwind CSS v4                                 │
 │  Hosted: CloudFront (CDN) → S3 static export                               │
─┼──────────────────────────────────────────────────────────────────────────
 │
 ├── AWS Cognito ───── user accounts, sign-up / sign-in, JWT tokens (4 h expiry)
 │
 └── API Gateway HTTP v2 (JWT-protected, all routes require valid token)
          │
          ├── POST   /upload          → Lambda → S3 (key: {user_id}/{uuid}_{name})
          │                                    → DynamoDB item (Tags: [])
          │                                    → S3 event triggers object-detection Lambda
          │                                                    → Rekognition labels → DynamoDB
          │
          ├── GET    /images          → Lambda → DynamoDB GSI query (UserID, newest first)
          │                                    → presigned S3 URLs (1 h)
          │
          ├── GET    /search          → Lambda → DynamoDB GSI + in-memory tag filter
          │                                    → presigned S3 URLs (1 h)
          │
          ├── POST   /search-by-image → Lambda → Rekognition detect labels on query image
          │                                    → DynamoDB GSI query by matching labels
          │                                    → presigned S3 URLs (1 h)
          │
          ├── POST   /modify-tags     → Lambda → ownership check (403 on mismatch)
          │                                    → DynamoDB update
          │
          └── DELETE /delete          → Lambda → ownership check (403 on mismatch)
                                              → S3 delete + DynamoDB delete
                                                        │
                                        ┌───────────────┴────────────────┐
                                    S3 (images)                    DynamoDB (metadata)
                               private, served via                 PK: ImageURL
                               presigned URLs only                 GSI: UserID-UploadedAt-index

Monitoring:  CloudWatch (logs, dashboards, SNS email alerts)
Tracing:     AWS X-Ray (10 % sampling across all Lambda functions)
IaC:         Terraform 1.7+ (modules: storage, auth, compute, api, observability)
CI/CD:       GitHub Actions (OIDC auth — plan on PR · deploy on push to main)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4, AWS Amplify v6 |
| Backend | Python 3.12, AWS Lambda (7 functions) |
| Object storage | AWS S3 |
| Database | AWS DynamoDB (PAY_PER_REQUEST, GSI for per-user queries) |
| AI / ML | AWS Rekognition (object detection + visual similarity) |
| Auth | AWS Cognito (User Pool + JWT authorizer on API Gateway) |
| API | AWS API Gateway v2 (HTTP), 200 req/s throttle |
| Infrastructure | Terraform 1.7+ |
| CI/CD | GitHub Actions (OIDC, no long-lived credentials) |
| Observability | CloudWatch dashboards + alarms, AWS X-Ray |
| Local dev | Docker, LocalStack 3 |
| Testing | pytest, moto |

---

## Project Structure

```
cloudsnap/
├── backend/
│   ├── upload/              # POST /upload — validates, stores to S3, seeds DynamoDB
│   ├── object-detection/    # S3-triggered — Rekognition labels → DynamoDB update
│   ├── list-images/         # GET  /images — GSI query by UserID, returns presigned URLs
│   ├── search-tags/         # GET  /search — GSI query + in-memory tag filter
│   ├── search-by-image/     # POST /search-by-image — Rekognition + GSI query
│   ├── modify-tags/         # POST /modify-tags — ownership check + DynamoDB update
│   └── delete/              # DELETE /delete — ownership check + S3 + DynamoDB delete
├── frontend/
│   ├── app/                 # Next.js App Router (login, signup, dashboard)
│   ├── components/          # UploadTab, GalleryTab, SearchTagsTab, ReverseSearchTab,
│   │                        # ModifyTagsTab, ResultsPanel, AmplifyProvider, ErrorBoundary
│   └── lib/                 # api.ts (HTTP client), auth.ts (token cache), types.ts,
│                            # amplify-config.ts
├── infrastructure/
│   ├── modules/
│   │   ├── storage/         # S3 bucket + DynamoDB table + GSI
│   │   ├── auth/            # Cognito User Pool + App Client + Identity Pool
│   │   ├── compute/         # Lambda functions, IAM roles, DLQ, S3 trigger
│   │   ├── api/             # API Gateway v2 + JWT authorizer + routes
│   │   └── observability/   # CloudWatch dashboards, alarms, SNS, X-Ray
│   ├── main.tf
│   ├── outputs.tf
│   ├── variables.tf
│   ├── backend.tf           # Remote Terraform state (S3 + DynamoDB lock)
│   └── terraform.tfvars.example
├── tests/                   # pytest unit tests — moto mocks AWS, no real calls
├── docker/                  # docker-compose: LocalStack 3 + frontend dev server
├── .github/workflows/       # terraform.yml · deploy-backend.yml · deploy-frontend.yml
├── Makefile                 # Shorthand for common commands
├── SETUP.md                 # Full deployment walkthrough
└── README.md
```

---

## Deploy to Your Own AWS Account

See **[SETUP.md](SETUP.md)** for a complete step-by-step walkthrough — from AWS credentials through a live public URL with GitHub Actions CI/CD.

**Estimated cost:** $0–2/month at hobby scale. All services are either free-tier eligible or near-zero at low traffic.

---

## Local Development

### Frontend only

```bash
cd frontend
npm install
cp .env.local.example .env.local   # fill in your Terraform outputs
npm run dev
# open http://localhost:3000
```

### Full local stack (LocalStack + frontend)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop).

```bash
make local-up    # starts LocalStack + frontend dev server
make local-down  # stops everything
```

LocalStack runs at `http://localhost:4566`. The frontend dev server runs at `http://localhost:3000`.

---

## Tests

```bash
make test
```

Uses **moto** to mock AWS — no real AWS calls, no credentials needed.

Test files cover: upload, object detection, list images, search by tags, search by image, modify tags, delete.

---

## CI/CD

| Workflow | Trigger | What happens |
|---|---|---|
| `terraform.yml` | PR touching `infrastructure/` | `terraform plan` — diff posted as PR comment |
| `terraform.yml` | Push to `main` touching `infrastructure/` | `terraform apply` — requires manual approval via the `production` environment gate |
| `deploy-backend.yml` | Push to `main` touching `backend/` or `tests/` | pytest (coverage ≥ 70 %) → update Lambda function code |
| `deploy-frontend.yml` | Push to `main` touching `frontend/` | Type-check + lint → `npm run build` → sync to S3 → CloudFront invalidation |

All workflows authenticate to AWS using **OIDC** — no long-lived access keys stored as secrets.
