#!/bin/bash

# Path to the downloaded Volt Dashboard repository
VOLT_SRC=~/Downloads/flask-volt-dashboard
# Path to your Flask app directory
PROJECT_ROOT=/home/bcherrington/Projects/Pycharm/admin-assistant/app

# Copy static assets
echo "Copying Volt static assets..."
mkdir -p "$PROJECT_ROOT/static/assets"
cp -r "$VOLT_SRC/static/assets/." "$PROJECT_ROOT/static/assets/"

# Copy templates (layouts, includes, home, accounts, etc.)
echo "Copying Volt templates..."
cp -r "$VOLT_SRC/templates/includes" "$PROJECT_ROOT/templates/"
cp -r "$VOLT_SRC/templates/layouts" "$PROJECT_ROOT/templates/"
cp -r "$VOLT_SRC/templates/home" "$PROJECT_ROOT/templates/"
cp -r "$VOLT_SRC/templates/accounts" "$PROJECT_ROOT/templates/"

# Optionally copy error pages or other templates
if [ -f "$VOLT_SRC/templates/page-404.html" ]; then
    cp "$VOLT_SRC/templates/page-404.html" "$PROJECT_ROOT/templates/"
fi
if [ -f "$VOLT_SRC/templates/page-500.html" ]; then
    cp "$VOLT_SRC/templates/page-500.html" "$PROJECT_ROOT/templates/"
fi

echo "Volt Dashboard integration complete!" 