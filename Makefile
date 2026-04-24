.PHONY: test infra-plan infra-apply local-up local-down lint

test:
	pip install --quiet pytest moto[s3,dynamodb] boto3
	pytest tests/ -v --tb=short

infra-plan:
	cd infrastructure && terraform init && terraform plan

infra-apply:
	cd infrastructure && terraform apply

local-up:
	docker compose -f docker/docker-compose.yml up -d
	@echo "LocalStack running at http://localhost:4566"
	@echo "Frontend running at http://localhost:3000"

local-down:
	docker compose -f docker/docker-compose.yml down

lint:
	cd frontend && npm run lint
