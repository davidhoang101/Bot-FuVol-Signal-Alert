#!/bin/bash

# Script để push code lên GitHub
# Sử dụng: ./push_to_github.sh <github-username> <repo-name>

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: ./push_to_github.sh <github-username> <repo-name>"
    echo "Example: ./push_to_github.sh dunghoangminh futu_vol_alert"
    exit 1
fi

GITHUB_USER=$1
REPO_NAME=$2
REPO_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"

echo "🚀 Setting up remote repository..."
git remote add origin $REPO_URL 2>/dev/null || git remote set-url origin $REPO_URL

echo "📤 Pushing code to GitHub..."
git branch -M main
git push -u origin main

echo "✅ Done! Your code is now on GitHub:"
echo "   $REPO_URL"

