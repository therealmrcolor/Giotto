#!/bin/bash

# Script per pulire i file macOS che causano problemi con Git
# Esegui questo script periodicamente per mantenere il repository pulito

echo "🧹 Pulizia file macOS..."

# Rimuovi tutti i file Icon e .DS_Store
find . -name "Icon*" -type f -delete 2>/dev/null
find . -name ".DS_Store" -type f -delete 2>/dev/null
find . -name "._*" -type f -delete 2>/dev/null
find . -name "Thumbs.db" -type f -delete 2>/dev/null
find . -name "ehthumbs.db" -type f -delete 2>/dev/null

echo "✅ Pulizia completata!"
echo "📁 Repository pulito dai file macOS problematici"

# Mostra lo stato di Git
git status --porcelain
