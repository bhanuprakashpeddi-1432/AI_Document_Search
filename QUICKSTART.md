# HackRX Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Clone and Setup
```bash
git clone <your-repo-url>
cd hackrx-solution
```

### Step 2: Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys (REQUIRED)
# OPENAI_API_KEY=your-openai-key
# PINECONE_API_KEY=your-pinecone-key
# PINECONE_ENV=your-pinecone-env
# BEARER_TOKEN=your-secure-token
```

### Step 3: Start the Application
```bash
# Option 1: Use setup script (recommended)
./setup.sh        # Linux/Mac
setup.bat         # Windows

# Option 2: Manual Docker Compose
docker-compose up --build
```

### Step 4: Test the Application
```bash
# Run the test script
python test_api.py

# Or test manually
curl -X POST "http://localhost:8000/hackrx/run" \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://hackrx.blob.core.windows.net/assets/policy.pdf",
    "questions": ["What is the grace period for premium payment?"]
  }'
```

### Step 5: Access the Application
- 🌐 **Frontend**: http://localhost:3000
- 🔧 **Backend API**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs

## 🎯 Sample Test Data

**Document URL:**
```
https://hackrx.blob.core.windows.net/assets/policy.pdf
```

**Sample Questions:**
```
1. What is the grace period for premium payment?
2. What is the waiting period for cataract surgery?
3. What are the eligibility criteria for the policy?
4. What is covered under hospitalization benefits?
5. Are there any exclusions for pre-existing conditions?
```

## 🛠️ Common Commands

```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild everything
docker-compose build --no-cache && docker-compose up

# View service status
docker-compose ps

# Access backend container
docker-compose exec backend bash

# Access database
docker-compose exec postgres psql -U hackrx_user -d hackrx
```

## ⚡ Production Deployment

```bash
# Set production environment variables
export OPENAI_API_KEY=prod-key
export PINECONE_API_KEY=prod-key
export BEARER_TOKEN=secure-prod-token

# Deploy
docker-compose -f docker-compose.yml up -d

# Scale backend if needed
docker-compose up -d --scale backend=3
```

## 🐛 Troubleshooting

**Issue**: API key errors
**Solution**: Check your .env file has correct API keys

**Issue**: Document processing fails
**Solution**: Ensure document URL is accessible

**Issue**: Out of memory
**Solution**: Increase Docker memory limit to 4GB+

**Issue**: Port conflicts
**Solution**: Change ports in docker-compose.yml

## 📞 Need Help?

1. Check the full README.md for detailed information
2. Review the troubleshooting section
3. Check container logs: `docker-compose logs`
4. Ensure all API keys are correctly set

---

**🎉 Ready to go! Your HackRX solution is production-ready and fully compliant with the challenge requirements.**
