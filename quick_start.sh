#!/bin/bash
# Quick Start Script for Telegram Backup Tool

echo "=========================================="
echo "Telegram Group Backup & Recovery Tool"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

echo "✓ Python 3 is installed"

# Check if .env file exists
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo ""
    echo "📝 Please edit the .env file with your Telegram API credentials:"
    echo "   1. Go to https://my.telegram.org"
    echo "   2. Get your API_ID and API_HASH"
    echo "   3. Edit .env and fill in your credentials"
    echo ""
    read -p "Press Enter after you've updated the .env file..."
fi

# Load environment variables from .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if credentials are set
if [ -z "$TELEGRAM_API_ID" ] || [ -z "$TELEGRAM_API_HASH" ] || [ -z "$TELEGRAM_PHONE" ]; then
    echo "❌ Telegram credentials not set in .env file"
    exit 1
fi

echo "✓ Telegram credentials loaded"

# Check if dependencies are installed
echo ""
echo "Checking dependencies..."
if ! python3 -c "import telethon" &> /dev/null; then
    echo "⚠️  Dependencies not installed. Installing..."
    pip3 install -r requirements.txt
else
    echo "✓ Dependencies are installed"
fi

echo ""
echo "=========================================="
echo "Setup complete! Choose an option:"
echo "=========================================="
echo ""
echo "1) Retrieve deleted messages (within 48 hours)"
echo "2) Backup current messages"
echo "3) Restore messages to new group"
echo "4) Exit"
echo ""

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo ""
        python3 1_retrieve_deleted_messages.py
        ;;
    2)
        echo ""
        python3 2_backup_current_messages.py
        ;;
    3)
        echo ""
        python3 3_restore_messages.py
        ;;
    4)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
