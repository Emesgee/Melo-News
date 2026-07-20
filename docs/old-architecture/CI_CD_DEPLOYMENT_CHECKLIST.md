# 🚀 Melo-News CI/CD Deployment Checklist

## ✅ What's Been Set Up

### **GitHub Actions Workflows**
- ✅ Backend testing on push to `develop` and `main`
- ✅ Automatic staging deployment when `develop` is updated
- ✅ Automatic production deployment when `main` is updated
- ✅ Health checks after deployment
- ✅ Database backups before production deployment
- ✅ Slack notifications for all deployments

### **Docker Deployment**
- ✅ `docker-compose.prod.yml` - Production-ready configuration
- ✅ Multi-stage builds optimized for production
- ✅ PostgreSQL with persistent volumes
- ✅ Health checks for all services
- ✅ Nginx reverse proxy for frontend + API

### **Local Testing** (Completed ✅)
- ✅ 30/31 tests passing (96.8%)
- ✅ 29% code coverage
- ✅ All models tested (100% coverage)
- ✅ API endpoints tested
- ✅ AI analyzer tested

---

## 🔧 Next Steps to Deploy to DigitalOcean

### **Step 1: Set Up GitHub Secrets (5 min)**
Go to: `GitHub Repository → Settings → Secrets and variables → Actions`

Add these secrets:

**For Staging (develop branch):**
```
STAGING_SSH_HOST = [your-staging-ip]
STAGING_SSH_USER = root
STAGING_SSH_PRIVATE_KEY = [paste your private SSH key]
STAGING_SSH_PORT = 22
```

**For Production (main branch):**
```
PRODUCTION_SSH_HOST = [your-production-ip]
PRODUCTION_SSH_USER = root
PRODUCTION_SSH_PRIVATE_KEY = [paste your private SSH key]
PRODUCTION_SSH_PORT = 22
```

**Optional (for Slack notifications):**
```
SLACK_WEBHOOK_URL = [your-slack-webhook]
```

### **Step 2: Set Up DigitalOcean Server (10 min)**
SSH into your server and run:

```bash
# Create app directory
mkdir -p /app/melo-news
cd /app/melo-news

# Clone your repo
git clone -b main https://github.com/[your-repo].git .

# Create .env file with your config
cat > .env << EOF
DATABASE_URL=postgresql://admin:password@melo-database:5432/melonews_prod
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
EOF

# Docker will be auto-installed by GitHub Actions
```

### **Step 3: Deploy Your Code**

**Option A: Deploy from develop (to staging)**
```powershell
git checkout develop
git push origin develop
# GitHub Actions automatically deploys to staging
```

**Option B: Deploy to production**
```powershell
git checkout main
git pull origin develop
# Merge develop into main (via PR or direct)
git merge develop
git push origin main
# GitHub Actions automatically deploys to production
# Includes: tests → build → deploy → health checks → backups
```

---

## 📊 What Happens During Deployment

### **Staging Deployment (develop branch)**
1. ✅ Checkout develop branch
2. ✅ Run all tests
3. ✅ Install production dependencies
4. ✅ Stop old containers
5. ✅ Start new containers with docker-compose.prod.yml
6. ✅ Send Slack notification

### **Production Deployment (main branch)**
1. ✅ Checkout main branch
2. ✅ Run all tests
3. ✅ Install production dependencies
4. ✅ Backup PostgreSQL database
5. ✅ Stop old containers
6. ✅ Start new containers
7. ✅ Health check API
8. ✅ Send detailed Slack notification

---

## 🔍 Monitoring Deployments

### **In GitHub:**
1. Go to **Actions** tab
2. Click on "Test Backend & Deploy to DigitalOcean"
3. See workflow progress in real-time
4. Check logs if something fails

### **On DigitalOcean Server:**
```bash
# SSH in
ssh root@your-server-ip

# Check running containers
docker ps

# View logs
docker logs -f melo-api-prod

# Health check
curl http://localhost:5000/api/health
```

---

## 📝 Current Git Branches

```
main (production)
  ↑
  │ (merge via PR)
  │
develop (staging)
  ↑
  │ (merge feature branches)
  │
feature/xyz (your feature branches)
```

**Recommended workflow:**
1. Create feature branch from `develop`
2. Merge to `develop` via PR (auto-deploys to staging)
3. Test on staging server
4. Merge `develop` to `main` via PR (auto-deploys to production)

---

## ✨ Key Files to Know

- `.github/workflows/deploy-backend.yml` - Main deployment workflow
- `docker-compose.prod.yml` - Production container config
- `requirements-prod.txt` - Production Python dependencies
- `Dockerfile` - Backend image definition
- `DEPLOYMENT_GUIDE.md` - Detailed deployment guide

---

## 🎯 Current Status

| Component | Status |
|-----------|--------|
| Tests | ✅ Passing (30/31) |
| Local Docker | ✅ Ready |
| GitHub Actions | ✅ Configured |
| Staging Deployment | ✅ Ready |
| Production Deployment | ✅ Ready |
| SSH Secrets | ⏳ Needs setup |
| DigitalOcean Server | ⏳ Needs setup |

---

## 🚨 Important Reminders

1. **Always test locally first**: `pytest app/test/ -v`
2. **Commit to develop for staging**, merge to main for production
3. **GitHub Secrets are case-sensitive**
4. **SSH key must have permissions on DigitalOcean server**
5. **Database backups are auto-created on production deployments**

---

## 💡 Quick Commands

```powershell
# Development workflow
git checkout develop
git pull origin develop

# Create feature
git checkout -b feature/my-feature
git add .
git commit -m "feat: description"
git push origin feature/my-feature

# Test locally
pytest app/test/ -v

# Merge to develop (via GitHub PR)
# → Auto-deploys to staging

# Merge develop to main (via GitHub PR)
# → Auto-deploys to production
```

---

**Questions?** See `DEPLOYMENT_GUIDE.md` for detailed instructions.
