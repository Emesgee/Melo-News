# GitHub Actions Deployment Guide for Melo-News

## 📋 Overview

This guide explains how to set up GitHub Actions for continuous deployment to DigitalOcean with separate **staging** and **production** environments.

---

## 🔐 Required GitHub Secrets

Add these secrets to your GitHub repository: Settings → Secrets and variables → Actions

### **Staging Secrets** (for `develop` branch)
```
STAGING_SSH_HOST          = Your staging server IP (e.g., 192.168.1.100)
STAGING_SSH_USER          = SSH username (default: root)
STAGING_SSH_PRIVATE_KEY   = Your private SSH key content
STAGING_SSH_PORT          = SSH port (default: 22)
```

### **Production Secrets** (for `main` branch)
```
PRODUCTION_SSH_HOST       = Your production server IP
PRODUCTION_SSH_USER       = SSH username (default: root)
PRODUCTION_SSH_PRIVATE_KEY = Your private SSH key content
PRODUCTION_SSH_PORT       = SSH port (default: 22)
```

### **Optional: Slack Notifications**
```
SLACK_WEBHOOK_URL         = Your Slack webhook URL for deployment notifications
```

---

## 🚀 How to Get Your SSH Key

### On your local machine (Windows):
```powershell
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096 -f $env:USERPROFILE\.ssh\id_rsa

# Read the private key
Get-Content $env:USERPROFILE\.ssh\id_rsa -Raw | Set-Clipboard
# Now paste it into GitHub Secrets as PRODUCTION_SSH_PRIVATE_KEY
```

### On DigitalOcean Server:
```bash
# Add your public key to authorized_keys
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

---

## 📝 Production Server Setup

Run these commands on your DigitalOcean production server:

```bash
# 1. Create app directory
sudo mkdir -p /app/melo-news
cd /app/melo-news

# 2. Clone repository (use deploy key)
git clone -b main https://github.com/yourusername/melo-news.git .

# 3. Create backups directory
sudo mkdir -p /backups
sudo chown ubuntu:ubuntu /backups

# 4. Create .env file
cat > .env << EOF
ENVIRONMENT=production
DATABASE_URL=postgresql://admin:your_password@melo-database:5432/melonews_prod
AZURE_STORAGE_CONNECTION_STRING=your_azure_connection_string
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
DB_USER=admin
DB_PASSWORD=your_secure_password
DB_NAME=melonews_prod
EOF

# 5. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 6. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 7. Start services (first time)
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🔄 Git Workflow

### **For Development (Staging)**
```bash
# Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/my-feature

# Make changes and commit
git add .
git commit -m "feat: add my feature"
git push origin feature/my-feature

# Create PR to develop
# Once merged → **auto-deploys to staging**
```

### **For Production**
```bash
# Merge develop to main (via PR)
git checkout main
git pull origin main
git merge develop
git push origin main

# **Auto-deploys to production** when merged to main
# GitHub Actions will:
# ✅ Run all tests
# ✅ Build Docker images
# ✅ Deploy to production server
# ✅ Run health checks
# ✅ Create database backup
# ✅ Send Slack notification
```

---

## ✅ Deployment Process

### **When you push to `develop`:**
1. ✅ Tests run on Ubuntu
2. ✅ Code deploys to **staging server**
3. ✅ docker-compose.prod.yml runs on staging
4. ✅ Slack notification sent

### **When you push to `main`:**
1. ✅ Tests run on Ubuntu
2. ✅ Code deploys to **production server**
3. ✅ Database automatically backed up
4. ✅ Health checks run
5. ✅ Slack notification sent

---

## 🛠️ Manual Deployment (if needed)

If you need to manually trigger deployment:

1. Go to **Actions** tab in GitHub
2. Click **"Test Backend & Deploy to DigitalOcean"**
3. Click **"Run workflow"**
4. Select branch: `main` or `develop`
5. Click **"Run workflow"**

---

## 📊 Monitoring

### **Check DigitalOcean Server:**
```bash
# SSH into server
ssh -p 22 root@your_production_ip

# View running containers
docker ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f melo-api

# Health check
curl http://localhost:5000/api/health
```

### **GitHub Actions:**
- Go to **Actions** tab to see deployment history
- Click on workflow run to see detailed logs
- Check Slack channel for notifications

---

## 🔒 Security Best Practices

1. **Never commit secrets** - Use GitHub Secrets instead
2. **Rotate SSH keys** - Update quarterly
3. **Use strong database password** - Update in production .env
4. **Enable 2FA** on GitHub account
5. **Keep backups** - Automated daily via docker-compose backup command
6. **Monitor logs** - Check error logs regularly

---

## ❓ Troubleshooting

### Deployment stuck?
```bash
# Check GitHub Actions logs in Actions tab
# Look for specific error messages
```

### Docker not starting?
```bash
docker-compose -f docker-compose.prod.yml logs postgres
docker-compose -f docker-compose.prod.yml restart
```

### SSH connection refused?
```bash
# Check:
1. SSH_HOST is correct
2. SSH_PORT is correct (default 22)
3. SSH user has permission
4. Private key is correct
```

---

## 📞 Questions?

Refer to:
- GitHub Actions Docs: https://docs.github.com/en/actions
- Docker Compose: https://docs.docker.com/compose/
- DigitalOcean: https://www.digitalocean.com/docs
