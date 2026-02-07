# AI-Powered Upload System - Setup Guide

## Overview
This system uses Azure AI services to automatically analyze images and videos, then auto-fills the upload form.

## Features
✅ **Image Analysis** - Uses Azure Computer Vision to:
- Generate descriptive titles
- Extract relevant tags
- Detect objects and scenes
- OCR text in images
- Identify locations

✅ **Video Analysis** - Uses Azure Speech + Vision to:
- Transcribe audio to text
- Analyze video frames
- Extract keywords from speech
- Detect locations from context

✅ **Smart Auto-fill** - Automatically populates:
- Title (from AI-generated caption)
- Tags (from detected objects/scenes)
- Subject/Description (from caption + transcription)
- City & Country (from detected text/context)

## Setup Instructions

### 1. Install Required Packages
```bash
cd Melo-News
pip install -r requirements_ai.txt
```

### 2. Install FFmpeg (for video processing)
**Windows:**
```bash
choco install ffmpeg
# Or download from: https://ffmpeg.org/download.html
```

**Mac:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

### 3. Create Azure Resources

#### Option A: Azure Portal (Recommended)
1. Go to [Azure Portal](https://portal.azure.com)
2. Create these resources:
   - **Computer Vision** (for image analysis)
   - **Speech Services** (for audio transcription)
   - **OpenAI** (optional, for better location detection)

3. For each resource:
   - Click "Keys and Endpoint"
   - Copy Key 1 and Endpoint URL

#### Option B: Azure CLI (Advanced)
```bash
# Login
az login

# Create resource group
az group create --name melo-news-ai --location eastus

# Create Computer Vision
az cognitiveservices account create \
  --name melo-vision \
  --resource-group melo-news-ai \
  --kind ComputerVision \
  --sku S1 \
  --location eastus

# Create Speech Services
az cognitiveservices account create \
  --name melo-speech \
  --resource-group melo-news-ai \
  --kind SpeechServices \
  --sku S0 \
  --location eastus

# Get keys
az cognitiveservices account keys list \
  --name melo-vision \
  --resource-group melo-news-ai
```

### 4. Configure Environment Variables
Copy `.env.ai.example` to your main `.env` file and add:

```bash
# Azure Computer Vision
AZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_VISION_KEY=your-key-here

# Azure Speech
AZURE_SPEECH_KEY=your-key-here
AZURE_SPEECH_REGION=eastus

# Azure OpenAI (optional)
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

### 5. Restart Backend Server
```bash
python main.py
```

## Usage

### Frontend (Automatic)
1. User selects image or video
2. System automatically sends to `/api/ai/analyze`
3. AI analyzes the media
4. Form fields auto-populate
5. User reviews and edits if needed
6. User clicks Submit

### Backend API
```bash
POST /api/ai/analyze
Content-Type: multipart/form-data

file: <image or video file>
```

**Response:**
```json
{
  "title": "Crowd gathering at city square",
  "tags": "people, protest, city, outdoor, crowd",
  "subject": "Large gathering of people in urban setting",
  "city": "Gaza",
  "country": "Palestine",
  "confidence": 0.87,
  "detected_text": "Gaza City Hall"
}
```

## Cost Optimization

### Free Tier Limits
- Computer Vision: 5,000 transactions/month free
- Speech-to-Text: 5 hours/month free
- OpenAI: No free tier (pay per use)

### Recommendations
1. **Start without OpenAI** - Basic location detection still works
2. **Use caching** - Store analysis results for 24 hours
3. **Batch processing** - Analyze during off-peak hours
4. **Set limits** - Max 100 analyses per day

### Monthly Cost Estimate
- Small app (100 uploads/month): ~$5-10/month
- Medium app (1,000 uploads/month): ~$50-75/month
- Large app (10,000 uploads/month): ~$400-500/month

## Fallback Mode
If Azure services are not configured, the system will:
- Still accept file uploads
- Use basic filename/metadata
- Require manual form filling
- Show message: "AI analysis unavailable - using fallback"

## Alternative Solutions

### 1. Google Cloud Vision (Similar pricing)
- Pros: Good accuracy, easy setup
- Cons: Requires different SDK

### 2. AWS Rekognition + Transcribe
- Pros: Integrated with AWS ecosystem
- Cons: More complex setup

### 3. Open Source (Free)
- **BLIP** (image captioning) - Run locally
- **Whisper** (speech recognition) - Run locally
- **spaCy** (NLP) - Run locally
- Pros: No API costs
- Cons: Requires GPU, slower, less accurate

### 4. Hybrid Approach (Recommended)
- Use Azure for production
- Use local models for development
- Cache results to minimize API calls

## Testing

### Test with Sample Files
```bash
# Test image analysis
curl -X POST http://localhost:8000/api/ai/analyze \
  -F "file=@sample_image.jpg"

# Test video analysis
curl -X POST http://localhost:8000/api/ai/analyze \
  -F "file=@sample_video.mp4"
```

### Expected Output
- Title: Descriptive caption
- Tags: 5-8 relevant keywords
- Subject: 1-2 sentence description
- City/Country: Detected from context
- Confidence: 0.6-0.9 (60-90%)

## Troubleshooting

### "Azure Vision not configured"
- Check `.env` file has correct keys
- Verify endpoint URL is correct
- Test API key in Azure Portal

### "FFmpeg not found"
- Install FFmpeg (see step 2)
- Add to system PATH
- Restart terminal

### "Low confidence scores"
- Normal for low-quality images
- Improve image resolution
- Use better lighting
- Ensure text is readable

### "Location not detected"
- Add Azure OpenAI for better detection
- Use manual city/country fields
- Add location in image text

## Future Enhancements
- [ ] Multi-language support
- [ ] Batch upload analysis
- [ ] Custom model training
- [ ] Face detection (optional)
- [ ] Sentiment analysis
- [ ] Image similarity search

## Security Notes
- API keys are sensitive - never commit to git
- Use Azure Key Vault for production
- Rotate keys every 90 days
- Monitor usage in Azure Portal
- Set spending limits

## Support
For issues:
1. Check Azure Portal for API errors
2. Review backend logs
3. Test API keys manually
4. Contact Azure Support if needed
