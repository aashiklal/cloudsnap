# CloudSnap

A serverless image management platform built on AWS. Upload images, get automatic AI-powered object detection, search by tags or by query image, browse your full library, and manage everything from a Next.js frontend — without managing a single server.

Built as a portfolio project demonstrating production-grade AWS architecture: Terraform IaC, Cognito JWT auth, GitHub Actions CI/CD, distributed tracing, and full observability.

---

## Features

- **Upload** — drag-and-drop uploads to S3 (JPEG, PNG, GIF, WebP, up to 10 MB)
- **Auto-tagging** — object detection runs automatically via AWS Rekognition on every upload
- **Browse** — gallery view of all stored images with their detected tags
- **Search by tags** — find images by object name and minimum detection count
- **Reverse image search** — upload a query image to find visually similar stored images
- **Tag management** — add custom tags or remove existing ones with a chip-based UI; tags pre-populated when browsing
- **Delete** — removes an image from S3 and the database in a single action
- **Authentication** — sign up, log in, and log out via AWS Cognito; every API route requires a valid JWT

---

## Architecture

```
Browser  ─────────────────────────────────────────────────────────────────
 │  Next.js 14 · TypeScript · Tailwind CSS                                │
 │  Hosted: CloudFront (CDN) → S3 (static export)                         │
─┼───────────────────────────────────────────────────────────────────────
 │
 ├── AWS Cognito ───── user accounts, sign-up / login, JWT tokens
 │
 └── API Gateway HTTP API (JWT-protected, all routes)
         │
         ├── POST   /upload          → Lambda → S3 store image
         │                                   → S3 event triggers object-detection Lambda
         │                                   → Rekognition detects labels → DynamoDB
         ├── GET    /images          → Lambda → DynamoDB  (browse full library)
         ├── GET    /search          → Lambda → DynamoDB  (tag-based search)
         ├── POST   /search-by-image → Lambda → Rekognition (visual similarity)
         ├── POST   /modify-tags     → Lambda → DynamoDB  (add / remove tags)
         └── DELETE /delete          → Lambda → S3 + DynamoDB (delete image)
                                               │
                                   ┌───────────┴───────────┐
                                   S3                 DynamoDB
                            (image files)         (metadata + tags)

Monitoring:  CloudWatch (logs, dashboards, SNS email alerts)
Tracing:     AWS X-Ray (across all Lambda functions)
IaC:         Terraform (modules: storage, auth, compute, api, observability)
CI/CD:       GitHub Actions (plan on PR · deploy on push to main)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, AWS Amplify Auth |
| Backend | Python 3.12, AWS Lambda |
| Object storage | AWS S3 |
| Database | AWS DynamoDB |
| AI / ML | AWS Rekognition (object detection + visual similarity) |
| Auth | AWS Cognito (user pool + JWT authorizer) |
| API | AWS API Gateway v2 (HTTP) |
| Infrastructure | Terraform |
| CI/CD | GitHub Actions |
| Observability | CloudWatch, AWS X-Ray |
| Local dev | Docker, LocalStack |
| Testing | pytest, moto |

---

## Project Structure

```
cloudsnap/
├── backend/
│   ├── upload/              # POST /upload — stores image to S3
│   ├── list-images/         # GET  /images — lists all images with tags
│   ├── search-tags/         # GET  /search — queries DynamoDB by tag
│   ├── search-by-image/     # POST /search-by-image — visual similarity
│   ├── modify-tags/         # POST /modify-tags — adds / removes tags
│   ├── delete/              # DELETE /delete — removes image from S3 + DynamoDB
│   └── object-detection/    # S3-triggered — Rekognition labels → DynamoDB
├── frontend/
│   ├── app/                 # Next.js App Router pages (login, signup, dashboard)
│   ├── components/          # React components (GalleryTab, UploadTab, …)
│   └── lib/                 # API client, Amplify auth helpers, TypeScript types
├── infrastructure/
│   ├── modules/
│   │   ├── storage/         # S3 bucket + DynamoDB table
│   │   ├── auth/            # Cognito user pool + app client
│   │   ├── compute/         # Lambda functions + IAM roles
│   │   ├── api/             # API Gateway + JWT authorizer + routes
│   │   └── observability/   # CloudWatch dashboards, alarms, X-Ray
│   ├── main.tf
│   ├── outputs.tf
│   ├── variables.tf
│   ├── backend.tf           # Remote Terraform state (S3 + DynamoDB lock)
│   └── terraform.tfvars.example
├── tests/                   # pytest unit tests (moto mocks AWS)
├── docker/                  # docker-compose with LocalStack
├── .github/workflows/       # terraform.yml · deploy-backend.yml · deploy-frontend.yml
├── Makefile                 # Shorthand for common commands
├── SETUP.md                 # Full deployment walkthrough
└── README.md
```

---

## Deploy to Your Own AWS Account

See **[SETUP.md](SETUP.md)** for a complete step-by-step walkthrough — from creating an IAM user through a live public URL with GitHub Actions CI/CD.

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

---

## Tests

```bash
make test
```

Uses **moto** to mock AWS — no real AWS calls, no cost, no credentials needed.

```
tests/test_upload.py       .....
tests/test_search_tags.py  ......
tests/test_modify_tags.py  ......
tests/test_delete.py       ....

====== 21 passed in 2.1s ======
```

---

## CI/CD

| Workflow | Trigger | What happens |
|---|---|---|
| `terraform.yml` | PR to `main` | Runs `terraform plan`, posts the diff as a PR comment |
| `deploy-backend.yml` | Push to `main` (backend changed) | Runs tests → deploys updated Lambda functions |
| `deploy-frontend.yml` | Push to `main` (frontend changed) | Builds Next.js → syncs to S3 → invalidates CloudFront |

`terraform apply` (real infrastructure changes) requires manual approval via a GitHub **production** environment gate before it runs.
