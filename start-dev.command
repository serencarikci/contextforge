#!/bin/bash
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
cd /Users/denizyetis/Projects/contextforge-enterprise-ai
bash ./scripts/dev-up.sh
echo
echo "Press Enter to close..."
read -r _
