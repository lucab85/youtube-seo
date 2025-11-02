#!/bin/bash

# YouTube SEO Metadata Generator - Setup Script

echo "=================================="
echo "YouTube SEO Tool - Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "⚠️  Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Download spaCy model
echo ""
echo "Downloading spaCy language model..."
python -m spacy download en_core_web_sm

# Create config directory
echo ""
echo "Creating config directory..."
mkdir -p config

# Copy .env.example to .env if not exists
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created - please edit it with your API keys"
else
    echo "⚠️  .env file already exists"
fi

# Initialize database
echo ""
echo "Initializing database..."
python src/utils/db_setup.py

if [ $? -ne 0 ]; then
    echo "❌ Database initialization failed"
    exit 1
fi

echo ""
echo "=================================="
echo "✅ Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys:"
echo "   - YouTube OAuth credentials (from Google Cloud Console)"
echo "   - OpenAI or Anthropic API key"
echo "   - (Optional) Slack webhook URL and/or email settings"
echo ""
echo "2. Download OAuth credentials from Google Cloud Console:"
echo "   - Save as config/client_secrets.json"
echo ""
echo "3. Run your first optimization:"
echo "   python main.py --url 'https://www.youtube.com/watch?v=VIDEO_ID' --mode preview"
echo ""
echo "4. For batch processing:"
echo "   cp videos.csv.example videos.csv"
echo "   # Edit videos.csv with your video URLs"
echo "   python main.py --batch videos.csv"
echo ""
