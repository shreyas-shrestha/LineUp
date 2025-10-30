#!/bin/bash
# Static site - no build needed
# Remove .venv if it was created by auto-detection
if [ -d ".venv" ]; then
  echo "Removing auto-created .venv directory..."
  rm -rf .venv
fi
echo "Static site deployment complete"
exit 0

