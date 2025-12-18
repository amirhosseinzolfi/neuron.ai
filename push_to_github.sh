#!/bin/bash

# Blue Psychology Test - GitHub Push Script
# This script helps push changes to GitHub

echo "=========================================="
echo "Blue Psychology Test - GitHub Push"
echo "=========================================="
echo ""

# Check if we're in a git repository
if [ ! -d .git ]; then
    echo "❌ Error: Not a git repository"
    exit 1
fi

# Show current status
echo "📊 Current Git Status:"
git status --short | head -10
echo ""

# Show remote
echo "🔗 Remote Repository:"
git remote -v
echo ""

# Show last commit
echo "📝 Last Commit:"
git log -1 --oneline
echo ""

echo "=========================================="
echo "Push Options:"
echo "=========================================="
echo "1. Push with HTTPS (requires GitHub token)"
echo "2. Push with SSH (requires SSH key setup)"
echo "3. Show setup instructions"
echo "4. Exit"
echo ""

read -p "Select option (1-4): " option

case $option in
    1)
        echo ""
        echo "📌 HTTPS Push Instructions:"
        echo "1. Generate a Personal Access Token at:"
        echo "   https://github.com/settings/tokens"
        echo "2. Select scopes: repo (full control)"
        echo "3. Use token as password when prompted"
        echo ""
        read -p "Press Enter to continue with push..."
        git push origin main
        ;;
    2)
        echo ""
        echo "🔑 Switching to SSH remote..."
        git remote set-url origin git@github.com:amirhosseinzolfi/blue-psychology-test.git
        echo "✅ Remote updated to SSH"
        echo ""
        echo "Pushing to GitHub..."
        git push origin main
        ;;
    3)
        echo ""
        echo "=========================================="
        echo "GitHub Authentication Setup"
        echo "=========================================="
        echo ""
        echo "Option 1: HTTPS with Personal Access Token"
        echo "-------------------------------------------"
        echo "1. Go to: https://github.com/settings/tokens"
        echo "2. Click 'Generate new token (classic)'"
        echo "3. Select scopes: repo (full control)"
        echo "4. Generate and copy the token"
        echo "5. Use token as password when pushing"
        echo ""
        echo "Option 2: SSH Key Setup"
        echo "-------------------------------------------"
        echo "1. Generate SSH key:"
        echo "   ssh-keygen -t ed25519 -C 'your_email@example.com'"
        echo "2. Start SSH agent:"
        echo "   eval \"\$(ssh-agent -s)\""
        echo "3. Add key:"
        echo "   ssh-add ~/.ssh/id_ed25519"
        echo "4. Copy public key:"
        echo "   cat ~/.ssh/id_ed25519.pub"
        echo "5. Add to GitHub:"
        echo "   https://github.com/settings/keys"
        echo "6. Test connection:"
        echo "   ssh -T git@github.com"
        echo ""
        ;;
    4)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "❌ Invalid option"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✅ Done!"
echo "=========================================="
