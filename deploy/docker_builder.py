import os
import subprocess
import boto3
from core.utils import get_logger

logger = get_logger("docker_builder")

AWS_REGION      = os.getenv("AWS_REGION", "us-west-2")
AWS_ACCOUNT_ID  = os.getenv("AWS_ACCOUNT_ID")
ECR_REGISTRY    = os.getenv("ECR_REGISTRY")
FRONTEND_REPO   = os.getenv("ECR_FRONTEND_REPO", "app-builder-frontend")
BACKEND_REPO    = os.getenv("ECR_BACKEND_REPO", "app-builder-backend")


def run_command(cmd: str, cwd: str = None) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr

def ecr_login():
    """Authenticate Docker with ECR."""
    logger.info("Logging into ECR...")
    cmd = (
        f"aws ecr get-login-password --region {AWS_REGION} | "
        f"docker login --username AWS --password-stdin {ECR_REGISTRY}"
    )
    code, out, err = run_command(cmd)
    if code != 0:
        raise RuntimeError(f"ECR login failed: {err}")
    logger.info("ECR login successful")

def write_env_file(path: str, env_vars: dict):
    """Write environment variables to a .env file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

def build_and_push_frontend(project_id: str, project_dir: str, backend_url: str) -> str:
    """Build frontend Docker image and push to ECR."""
    image_tag = f"{ECR_REGISTRY}/{FRONTEND_REPO}:{project_id}"
    frontend_dir = os.path.join(project_dir, "frontend")

    logger.info(f"Building frontend image: {image_tag}")

    # Write frontend .env
    write_env_file(
        os.path.join(frontend_dir, ".env"),
        {"REACT_APP_API_URL": backend_url}
    )
    write_frontend_package_json(frontend_dir)
    write_frontend_scaffold(frontend_dir)

    # Check if Dockerfile exists, create one if not
    dockerfile_path = os.path.join(frontend_dir, "Dockerfile")
    with open(dockerfile_path, "w") as f:
        f.write("""FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
RUN echo 'server { listen 80; location / { root /usr/share/nginx/html; index index.html; try_files $uri $uri/ /index.html; } }' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
""")

    # Build image
    code, out, err = run_command(
        f"docker build --no-cache --platform linux/amd64 -t {image_tag} .",
        cwd=frontend_dir
    )
    if code != 0:
        raise RuntimeError(f"Frontend build failed: {err}")

    # Push image
    code, out, err = run_command(f"docker push {image_tag}")
    if code != 0:
        raise RuntimeError(f"Frontend push failed: {err}")

    logger.info(f"Frontend image pushed: {image_tag}")
    return image_tag

def write_backend_package_json(backend_dir: str):
    """Create package.json if agents didn't generate one."""
    package_path = os.path.join(backend_dir, "package.json")
    if not os.path.exists(package_path):
        import json
        package = {
            "name": "app-builder-backend",
            "version": "1.0.0",
            "main": "src/server.js",
            "scripts": {
                "start": "node src/server.js",
                "dev": "nodemon src/server.js"
            },
            "dependencies": {
                "express": "^4.18.2",
                "mongoose": "^7.6.3",
                "bcryptjs": "^2.4.3",
                "bcrypt": "^5.1.1",
                "jsonwebtoken": "^9.0.2",
                "cors": "^2.8.5",
                "dotenv": "^16.3.1",
                "express-validator": "^7.0.1",
                "express-rate-limit": "^7.1.5",
                "helmet": "^7.1.0",
                "morgan": "^1.10.0",
            }
        }
        with open(package_path, "w") as f:
            json.dump(package, f, indent=2)
        logger.info("Generated backend package.json")

def write_frontend_package_json(frontend_dir: str):
    """Always write correct package.json with all required dependencies."""
    import json
    package_path = os.path.join(frontend_dir, "package.json")
    package = {
        "name": "generated-app-frontend",
        "version": "1.0.0",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview"
        },
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "react-router-dom": "^6.20.0",
            "axios": "^1.6.2",
            "prop-types": "^15.8.1",
            "lucide-react": "^0.363.0"
        },
        "devDependencies": {
            "@vitejs/plugin-react": "^4.2.0",
            "vite": "^5.0.0",
            "tailwindcss": "^3.3.5",
            "autoprefixer": "^10.4.16",
            "postcss": "^8.4.31"
        }
    }
    with open(package_path, "w") as f:
        json.dump(package, f, indent=2)



def write_frontend_scaffold(frontend_dir: str):
    """Create vite.config.js and public/index.html if missing."""
    import json

    # vite.config.js
    vite_config = os.path.join(frontend_dir, "vite.config.js")
    if not os.path.exists(vite_config):
        with open(vite_config, "w") as f:
            f.write("""import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 }
})
""")
        logger.info("Generated vite.config.js")

    # public/index.html
    public_dir = os.path.join(frontend_dir, "public")
    os.makedirs(public_dir, exist_ok=True)

    # index.html at root (Vite uses root index.html)
    index_path = os.path.join(frontend_dir, "index.html")
    if not os.path.exists(index_path):
        with open(index_path, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
""")
        logger.info("Generated index.html")

    # tailwind.config.js
    tailwind_config = os.path.join(frontend_dir, "tailwind.config.js")
    if not os.path.exists(tailwind_config):
        with open(tailwind_config, "w") as f:
            f.write("""/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
""")
        logger.info("Generated tailwind.config.js")

    # postcss.config.js
    postcss_config = os.path.join(frontend_dir, "postcss.config.js")
    if not os.path.exists(postcss_config):
        with open(postcss_config, "w") as f:
            f.write("""export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
""")
        logger.info("Generated postcss.config.js")

    # src/index.css if missing
    src_dir = os.path.join(frontend_dir, "src")
    os.makedirs(src_dir, exist_ok=True)
    css_path = os.path.join(src_dir, "index.css")
    if not os.path.exists(css_path):
        with open(css_path, "w") as f:
            f.write("@tailwind base;\n@tailwind components;\n@tailwind utilities;\n")
        logger.info("Generated index.css")
        
    # main.jsx entry point if missing
    main_path = os.path.join(src_dir, "main.jsx")
    if not os.path.exists(main_path):
        with open(main_path, "w") as f:
            f.write("""import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
""")
        logger.info("Generated main.jsx")
        
def build_and_push_backend(project_id: str, project_dir: str, env_vars: dict) -> str:
    """Build backend Docker image and push to ECR."""
    image_tag = f"{ECR_REGISTRY}/{BACKEND_REPO}:{project_id}"
    backend_dir = os.path.join(project_dir, "backend")

    logger.info(f"Building backend image: {image_tag}")

    # Write backend .env with real values
    write_env_file(
        os.path.join(backend_dir, ".env"),
        env_vars
    )
    
    write_backend_package_json(backend_dir)
    
    # Check if Dockerfile exists, create one if not
    dockerfile_path = os.path.join(backend_dir, "Dockerfile")
    with open(dockerfile_path, "w") as f:
        f.write("""FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5000
CMD ["node", "src/server.js"]
""")

    # Build image
    code, out, err = run_command(
        f"docker build --no-cache --platform linux/amd64 -t {image_tag} .",
        cwd=backend_dir
    )
    if code != 0:
        raise RuntimeError(f"Backend build failed: {err}")

    # Push image
    code, out, err = run_command(f"docker push {image_tag}")
    if code != 0:
        raise RuntimeError(f"Backend push failed: {err}")

    logger.info(f"Backend image pushed: {image_tag}")
    return image_tag