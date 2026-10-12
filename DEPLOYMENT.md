# 🚀 ResearchLens Deployment Guide

This guide covers all options for deploying ResearchLens to production, from free cloud hosting to containerized deployment.

---

## 📋 Pre-Deployment Checklist

Before deploying, ensure you have:
1. **Groq API Key**: Get your API key from [Groq Console](https://console.groq.com/keys).
2. **Git Repository**: Initialize git and push to GitHub/GitLab (see [Git Setup](#1-git-repository-setup)).

---

## 1. Git Repository Setup

If your project is not yet on GitHub:

```bash
# 1. Initialize git
git init

# 2. Add files (.gitignore is already set up to exclude .env and PDF uploads)
git add .

# 3. Create initial commit
git commit -m "feat: production-ready ResearchLens with deployment configurations"

# 4. Link to your GitHub repository
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git

# 5. Push to GitHub
git push -u origin main
```

---

## 2. Option A (Recommended): Render.com (100% Free & Easy)

Render offers free web service hosting with automatic HTTPS and GitHub integration.

### Method 1: Unified Docker Deployment (Single Service)

Deploy frontend and backend together in a single container.

1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New +** -> **Web Service**.
2. Connect your GitHub repository.
3. Select **Docker** as the Runtime:
   - **Name**: `researchlens`
   - **Region**: Choose the closest region (e.g., Oregon or Frankfurt)
   - **Branch**: `main`
   - **Plan**: `Free`
4. Under **Environment Variables**, add:
   - `GROQ_API_KEY`: `<Your Groq API Key>`
   - `CORS_ORIGINS`: `*`
5. Click **Create Web Service**. Render will automatically build the React UI and start the FastAPI server!

---

### Method 2: Split Deployment (Render Backend + Vercel Frontend)

#### Step 1: Deploy Backend on Render
1. Click **New +** -> **Web Service** on Render.
2. Settings:
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Environment Variables:
   - `GROQ_API_KEY`: `<Your Groq API Key>`
   - `CORS_ORIGINS`: `*`
4. Note your backend URL (e.g. `https://researchlens-api.onrender.com`).

#### Step 2: Deploy Frontend on Vercel
1. Go to [Vercel](https://vercel.com/) and click **Add New Project**.
2. Import your GitHub repository.
3. Settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
4. Under **Environment Variables**, add:
   - `VITE_API_BASE_URL`: `https://researchlens-api.onrender.com` (your Render backend URL)
5. Click **Deploy**.

---

## 3. Option B: Docker / Docker Compose (VPS / Self-Hosted)

Run on any Linux server (DigitalOcean droplet, AWS EC2, Linode, Hetzner, etc.):

### Step 1: Clone and Configure
```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd "research paper summarizer"

# Create production .env file
cp .env.example .env
nano .env  # Add your GROQ_API_KEY
```

### Step 2: Start with Docker Compose
```bash
docker compose up -d --build
```

The application is now live at `http://your-server-ip:8000`!

---

## 4. Option C: Railway.app

1. Go to [Railway](https://railway.app/) and click **New Project** -> **Deploy from GitHub repo**.
2. Select your repository.
3. In service settings:
   - Add Variable: `GROQ_API_KEY` = your Groq key.
   - Railway will detect the `Dockerfile` automatically and build both the frontend and backend.
4. Click **Generate Domain** under Networking to get your public HTTPS URL.

---

## 5. Local Production Preview

To test the production build locally without development hot-reloading:

```bash
# 1. Build the frontend
cd frontend
npm run build
cd ..

# 2. Run the production backend (serves both API & Frontend)
.\.venv\Scripts\uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Open your browser at `http://127.0.0.1:8000`.

---

## 🔒 Security & Environment Variables

| Variable | Required | Description | Default |
| :--- | :---: | :--- | :--- |
| `GROQ_API_KEY` | **Yes** | Groq API Key for LLM summarization | — |
| `PORT` | No | Server port (bound by cloud providers) | `8000` |
| `CORS_ORIGINS` | No | Allowed frontend origins (comma-separated or `*`) | `*` |
| `UPLOAD_DIR` | No | Custom folder path for PDF storage | `./uploads` |
| `OUTPUTS_DIR` | No | Custom folder path for generated summaries | `./outputs` |
| `VITE_API_BASE_URL` | Frontend | Target backend API URL (for split deployments) | Relative `""` |
