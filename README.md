# App Builder — AI-Powered Full-Stack App Generator

> Describe an app in plain English. Get a fully deployed, production-ready full-stack application in under 5 minutes.

## Demo

Type: _"Build me a task management app with user authentication and MongoDB"_

Watch 6 specialized AI agents work in parallel to generate, review, and deploy your app to AWS.

## Architecture

### Multi-Agent Pipeline (LangGraph)

- **Planner Agent** — breaks prompt into structured technical plan
- **Frontend Agent** — generates React + Tailwind components
- **Backend Agent** — generates Node.js + Express APIs
- **Database Agent** — generates Mongoose models
- **DevOps Agent** — generates Docker + GitHub Actions CI/CD
- **Review Agent** — checks consistency, triggers self-correction loop

### Template Engine

Battle-tested boilerplate applied after generation — guarantees correct JWT auth, bcryptjs, consistent API routes regardless of LLM output.

### Deployment Pipeline

- MongoDB Atlas database provisioned per app
- Docker images built for `linux/amd64` and pushed to AWS ECR
- ECS Fargate containers deployed with ALB routing
- Live URL returned in ~3 minutes

## Tech Stack

| Layer               | Technology                       |
| ------------------- | -------------------------------- |
| Agent Framework     | LangGraph + LangChain            |
| Agent Observability | LangSmith                        |
| Backend             | FastAPI + WebSockets             |
| Frontend            | React + Tailwind + Monaco Editor |
| LLM                 | GPT-4o + GPT-4o-mini             |
| Database            | MongoDB Atlas                    |
| Infrastructure      | AWS ECS Fargate + ECR + ALB      |
| IaC                 | Terraform (planned)              |
| Containerization    | Docker (linux/amd64)             |

## Getting Started

```bash
git clone https://github.com/msshahs/app-builder.git
cd app-builder
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your API keys
python main.py
```

## Environment Variables

OPENAI_API_KEY=
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=app-builder
MONGODB_ATLAS_URI=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-west-2
AWS_ACCOUNT_ID=
ECR_REGISTRY=
ECS_CLUSTER_NAME=app-builder-cluster
ECS_EXECUTION_ROLE_ARN=

## Project Structure

agents/ # 6 LangGraph agents
api/ # FastAPI routes + WebSocket streaming
core/ # Config, prompts, utils, template engine
deploy/ # MongoDB, Docker builder, ECS deployer
frontend/ # React UI (Forge)
graph/ # LangGraph graph assembly
templates/ # Battle-tested boilerplate files

## Inspired By

Bolt.new, Base44, Replit Agent — built from scratch to understand every layer.
