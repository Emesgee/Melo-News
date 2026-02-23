# Git Flow Implementation Guide for Melo-News

Quick implementation guide specific to the Melo-News project.

---

## Project-Specific Setup

### Initialize Git Flow (Optional but Recommended)

```bash
# Install git-flow
# Windows with Chocolatey:
choco install gitflow-avh

# Initialize in your project
git flow init

# Press Enter for all defaults, or choose your naming convention:
# Branch name for production releases: [main]
# Branch name for "next release" development: [develop]
# Feature branches? [feature/]
# Release branches? [release/]
# Hotfix branches? [hotfix/]
```

### Project-Specific Considerations

#### Current Stack
- **Backend**: Python (Flask/FastAPI)
- **Database**: PostgreSQL (Docker)
- **Message Queue**: Kafka
- **Search**: Geosearch/ElasticSearch
- **Frontend**: HTML/CSS/JavaScript
- **DevOps**: Docker & Docker Compose
- **Cloud**: Azure (optional)

#### Development Environments

**Local Development**
```bash
# Start all services
docker-compose up -d

# Run app (from Melo-News directory)
python main.py

# Run tests
pytest tests/
```

**Staging** 
- Automated deployment from `develop` branch
- Full testing suite runs
- Database migrations applied

**Production**
- Stable releases from `main` branch
- Tagged with semantic versions
- Requires hotfix process for updates

---

## Feature Development Workflow for Melo-News

### Example: Implementing Search Optimization Feature

```bash
# 1. Start feature development
git checkout develop
git pull origin develop
git checkout -b feature/search-optimization

# 2. Work on code
# - Update models.py
# - Modify search/routes.py
# - Add test_search_component.py tests

# 3. Commit regularly
git add app/search/routes.py
git commit -m "feat(search): implement advanced geosearch functionality"

git add app/models.py
git commit -m "refactor(database): optimize query indexes for search"

git add tests/test_search_component.py
git commit -m "test(search): add unit tests for geosearch"

# 4. Regular syncing
git fetch origin
git rebase origin/develop

# 5. Push to GitHub
git push origin feature/search-optimization

# 6. Create PR for review
# Go to GitHub, compare develop...feature/search-optimization
```

### Feature Types and Branch Examples

**API Features**
```bash
git checkout -b feature/api-news-endpoints
# Modify: app/auth/routes.py, app/ai_analyzer/routes.py
```

**Database Schema Changes**
```bash
git checkout -b feature/schema-media-types
# Modify: app/models.py, create migration file
# Update: migrate.sh
```

**Frontend Features**
```bash
git checkout -b feature/homepage-redesign
# Modify: app/frontend/, app/templates/
```

**DevOps/Infrastructure**
```bash
git checkout -b feature/azure-storage-integration
# Modify: docker-compose.yaml, modules/azure_handler.py
```

**Documentation**
```bash
git checkout -b feature/api-documentation
# Create/Update: docs/api-reference.md
```

---

## Release Process for Melo-News

### Prepare Release (from develop)

```bash
# Example: Releasing v1.2.0
git checkout develop
git pull origin develop

git checkout -b release/v1.2.0

# Update version files
# In package.json or setup.py:
# "version": "1.2.0"

# In docker-compose.yaml (if versioning):
# image: melo-news:v1.2.0

# Update CHANGELOG.md
# Add release notes with features, fixes, improvements

git commit -m "chore(release): prepare v1.2.0 release"
git push -u origin release/v1.2.0
```

### Release Testing

```bash
# Checkout release branch
git checkout release/v1.2.0

# Run full test suite
pytest tests/
npm test  # if frontend tests exist

# Test Docker build
docker-compose build

# Manual QA testing
# - Test search functionality
# - Verify map rendering
# - Check upload/processing
# - Validate database operations
```

### Merge to Production

```bash
# Create PR: release/v1.2.0 → main
# After approval:

git checkout main
git pull origin main
git merge --no-ff release/v1.2.0

# Create tag
git tag -a v1.2.0 -m "Release v1.2.0: Add search optimization and UI improvements"

git push origin main --tags

# Merge back to develop
git checkout develop
git pull origin develop
git merge --no-ff release/v1.2.0
git push origin develop

# Cleanup
git branch -d release/v1.2.0
git push origin --delete release/v1.2.0
```

---

## Hotfix Process for Melo-News

### Critical Issues Requiring Hotfix

```bash
# Example: Critical database connection bug
git checkout main
git pull origin main

git checkout -b hotfix/db-connection-critical

# Make minimal fix
# File: modules/database.py
# Change connection timeout handling

git commit -m "fix(critical): resolve database connection timeout issue"
git push -u origin hotfix/db-connection-critical
```

### Deploy Hotfix

```bash
# Approve and merge to main
git checkout main
git pull origin main
git merge --no-ff hotfix/db-connection-critical

# Tag as patch version
git tag -a v1.1.1 -m "Hotfix: critical database connection bug"
git push origin main --tags

# Merge back to develop
git checkout develop
git pull origin develop
git merge --no-ff hotfix/db-connection-critical
git push origin develop

# Cleanup
git branch -d hotfix/db-connection-critical
git push origin --delete hotfix/db-connection-critical
```

---

## Commit Message Examples for Melo-News

### Feature Commits

```
feat(search): implement geospatial query optimization

Refactored the search module to use PostGIS extensions
for improved performance on location-based queries.

- Added spatial index on news locations
- Optimized query execution time by 40%
- Added caching layer for frequent searches

Fixes #89
```

```
feat(upload): support video file processing

Users can now upload video files with automatic
format conversion and thumbnail generation.

- Added support for MP4, WebM formats
- Integrated FFmpeg for transcoding
- Generate preview thumbnails
```

### Bug Fix Commits

```
fix(map): resolve popup positioning on mobile

Fixed issue where map popups were positioned
off-screen on mobile devices due to viewport
calculation errors.

Fixes #145
```

```
fix(database): handle null values in location data

Prevented crashes when processing news items with
missing geolocation data.

- Added null checks in location_detector module
- Default to country-level location if city unavailable
- Log warnings for missing location data
```

### Refactoring Commits

```
refactor(models): simplify news model schema

Consolidated duplicate fields and improved
overall database schema efficiency.

- Removed legacy columns
- Unified status field naming
- Updated all references
```

### Documentation Commits

```
docs(readme): update installation instructions

- Added Python version requirement (3.8+)
- Updated Docker compose commands
- Added troubleshooting section
- Updated API endpoints documentation

Fixes #112
```

### DevOps Commits

```
chore(docker): upgrade PostgreSQL to v14

- Updated postgres image version
- Migrated database schema
- Tested with existing data

BREAKING CHANGE: Requires manual migration for existing databases
```

---

## GitHub Configuration for Melo-News

### Protect Branches

1. Go to **Settings** → **Branches** → **Add rule**
2. For pattern `main`:
   - ✅ Require pull request reviews before merging (2 reviewers)
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Include administrators

3. For pattern `develop`:
   - ✅ Require pull request reviews before merging (1 reviewer)
   - ✅ Require status checks to pass before merging
   - ✅ Allow auto-delete of head branches

### Auto-Delete Head Branches

Configure in GitHub settings to automatically delete feature branches after PR merge.

### Status Checks Required

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest
      - name: Run tests
        run: pytest tests/
```

---

## Team Roles and Responsibilities

### Feature Owner
- Creates feature branches
- Keeps branch updated with develop
- Creates PR with description
- Addresses review comments

### Code Reviewers
- Review for logic, style, tests
- Run tests locally
- Approve or request changes
- Merge PR when approved

### Release Manager
- Prepares release branch
- Creates release notes
- Coordinates final testing
- Manages version tagging

### DevOps Lead
- Monitors CI/CD pipelines
- Manages deployments
- Handles infrastructure changes
- Coordinates hotfixes

---

## Common Workflows Quick Reference

### Start Work on New Feature
```bash
git checkout develop && git pull origin develop
git checkout -b feature/my-feature
# Make changes and commit
git push -u origin feature/my-feature
# Create PR on GitHub
```

### Update Feature from Latest Develop
```bash
git fetch origin
git rebase origin/develop
git push origin feature/my-feature --force-with-lease
```

### Fix Last Commit Message
```bash
git commit --amend -m "new message"
git push origin feature/my-feature --force-with-lease
```

### Undo Last Commit (Not Pushed)
```bash
git reset --soft HEAD~1
```

### View All Branches
```bash
git branch -a
```

### Clean Up Old Branches
```bash
git branch -d branch-name           # Delete local
git push origin --delete branch-name # Delete remote
git fetch origin --prune              # Clean up tracking branches
```

---

## Troubleshooting

### Merge Conflicts

```bash
# During rebase
git rebase origin/develop
# Fix conflicts in files
git add .
git rebase --continue

# Or abort
git rebase --abort
```

### Accidental Commits

```bash
# Undo last commit, keep changes
git reset --soft HEAD~1

# Undo last commit, discard changes
git reset --hard HEAD~1

# Move last commit to different branch
git reset HEAD~1
git checkout -b new-branch
git commit -m "moved commit"
```

### Wrong Branch

```bash
# Save work if on wrong branch
git stash

# Switch to correct branch
git checkout correct-branch
git stash pop
```

---

## Additional Resources

- [Git Documentation](https://git-scm.com/doc)
- [GitHub Help](https://help.github.com/)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

**Last Updated**: February 19, 2026
**For**: Melo-News Project
