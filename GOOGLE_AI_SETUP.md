# How to Get Google AI (Gemini) API Key

Google AI offers a **FREE tier** which makes it a great option for this project!

## Step 1: Go to Google AI Studio

Visit: **https://makersuite.google.com/app/apikey**

Or go to: **https://aistudio.google.com/** and click "Get API key"

## Step 2: Sign In

- Sign in with your Google account
- Accept the terms of service

## Step 3: Create API Key

1. Click **"Create API key"** button
2. Choose an existing Google Cloud project or create a new one
3. Your API key will be generated instantly
4. **Copy the API key** (it starts with something like `AIza...`)

## Step 4: Add to .env File

Open your `.env` file and add:

```env
GOOGLE_AI_API_KEY=AIzaSyC...your-actual-key...
GOOGLE_AI_MODEL=gemini-pro
```

## Step 5: Test It

```bash
# Test with preview mode
python main.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --mode preview
```

## ✅ Advantages of Google AI (Gemini)

### 1. **FREE Tier Available**
- 60 requests per minute
- 1 million tokens per day (FREE!)
- Perfect for most YouTube channel needs

### 2. **No Credit Card Required**
- Unlike OpenAI, you can start immediately
- No billing setup needed for free tier

### 3. **Latest Model**
- Gemini Pro is Google's latest AI
- Great for generating creative content
- Comparable quality to GPT-4

### 4. **Already Have Google Account**
- No new account signup needed
- Uses your existing Google credentials

## 📊 Free Tier Limits

| Limit | Free Tier |
|-------|-----------|
| Requests per minute | 60 |
| Tokens per day | 1,000,000 |
| Input tokens per request | 30,720 |
| Output tokens per request | 2,048 |

**For this YouTube SEO tool**: These limits are MORE than enough!
- Each video optimization uses ~1,500-3,000 tokens
- You can optimize **300+ videos per day** on the free tier

## 🔄 Model Options

```env
# Standard model (recommended)
GOOGLE_AI_MODEL=gemini-pro

# For longer content
GOOGLE_AI_MODEL=gemini-1.5-pro

# Faster, less powerful
GOOGLE_AI_MODEL=gemini-1.5-flash
```

## 🆚 Comparison: OpenAI vs Anthropic vs Google AI

| Feature | OpenAI GPT-4 | Anthropic Claude | Google Gemini |
|---------|--------------|------------------|---------------|
| **Free Tier** | ❌ No | ❌ No | ✅ Yes |
| **Quality** | Excellent | Excellent | Very Good |
| **Speed** | Fast | Fast | Very Fast |
| **Cost (paid)** | $0.01/1K tokens | $0.015/1K tokens | $0.00025/1K tokens |
| **Credit Card** | Required | Required | Not Required |

## 🚀 Recommended for YouTube SEO

**Best Choice**: **Google AI (Gemini)** ✅

Why?
1. **FREE** - No credit card needed
2. **Generous limits** - 1M tokens/day
3. **Good quality** - Excellent for SEO content
4. **Fast** - Quick response times
5. **Easy setup** - Just need Google account

## 🔧 Priority Order

The tool checks for API keys in this order:

1. **OpenAI** (if OPENAI_API_KEY is set)
2. **Anthropic** (if ANTHROPIC_API_KEY is set)
3. **Google AI** (if GOOGLE_AI_API_KEY is set)

To use Google AI, simply:
- Don't set OPENAI_API_KEY
- Don't set ANTHROPIC_API_KEY
- Set GOOGLE_AI_API_KEY

Or just set all three and it will use OpenAI by default (you can remove OpenAI key to switch to Google).

## 📝 Example .env Configuration

```env
# Use Google AI (recommended - free!)
GOOGLE_AI_API_KEY=AIzaSyC...your-key...
GOOGLE_AI_MODEL=gemini-pro

# YouTube API (still required)
YOUTUBE_CLIENT_ID=your_id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your_secret

# Optional: Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## 🎓 Additional Resources

- **Google AI Studio**: https://aistudio.google.com/
- **Gemini API Docs**: https://ai.google.dev/docs
- **Pricing**: https://ai.google.dev/pricing
- **Quickstart Guide**: https://ai.google.dev/tutorials/python_quickstart

## ⚡ Quick Test

Test if your API key works:

```python
# test_google_ai.py
import google.generativeai as genai

genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel('gemini-pro')

response = model.generate_content("Write a catchy YouTube title about Python programming")
print(response.text)
```

```bash
python test_google_ai.py
```

---

**That's it!** You now have a FREE AI API key for your YouTube SEO automation tool! 🎉
