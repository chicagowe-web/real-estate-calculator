#!/bin/bash
################################################################################
# Hermes Code Sync Script for Remote Deployments
#
# Purpose: Sync Hermes source code from main repo to remote deployments
# Usage: Run via cron on remote machines (e.g., garage-core)
#
# Typical cron entry:
#   0 2 * * * /home/garage_core/hermes/scripts/sync-from-main.sh >> /var/log/hermes-sync.log 2>&1
#
# This script:
# 1. Fetches latest changes from origin
# 2. Checks if code actually changed
# 3. Updates to latest version
# 4. Restarts Hermes services if needed
# 5. Logs all actions
################################################################################

set -e  # Exit on error

# Configuration
HERMES_DIR="${HERMES_DIR:-.}"
REPO_BRANCH="${REPO_BRANCH:-master}"
LOG_FILE="/var/log/hermes-sync.log"
RESTART_SERVICES="${RESTART_SERVICES:-true}"

# Colors for output (disable in cron)
if [ -t 1 ]; then
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    NC='\033[0m'
else
    GREEN=''
    YELLOW=''
    RED=''
    NC=''
fi

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${YELLOW}[INFO]${NC} $*" | tee -a "$LOG_FILE"
}

# Verify we're in a git repository
if [ ! -d "$HERMES_DIR/.git" ]; then
    error "Not a git repository: $HERMES_DIR/.git not found"
    exit 1
fi

cd "$HERMES_DIR"

log "=== Starting Hermes code sync ==="
info "Repository: $HERMES_DIR"
info "Branch: $REPO_BRANCH"

# Step 1: Fetch latest from origin
log "Fetching latest changes from origin..."
if ! git fetch origin "$REPO_BRANCH" 2>&1 | tee -a "$LOG_FILE"; then
    error "Failed to fetch from origin"
    exit 1
fi
success "Fetch completed"

# Step 2: Check if code actually changed
log "Checking for changes..."
if git diff --quiet HEAD origin/$REPO_BRANCH; then
    info "No changes detected - code is up to date"
    log "=== Sync completed (no changes) ==="
    exit 0
fi

# Changes detected
info "Changes detected - updating code"
echo "Changes:"
git diff --name-only HEAD origin/$REPO_BRANCH | tee -a "$LOG_FILE" | sed 's/^/  - /'

# Step 3: Update to latest version
log "Updating to latest version..."
if ! git reset --hard origin/$REPO_BRANCH 2>&1 | tee -a "$LOG_FILE"; then
    error "Failed to update to latest version"
    exit 1
fi
success "Code updated to latest version"

# Step 4: Restart services if configured
if [ "$RESTART_SERVICES" = "true" ]; then
    log "Restarting Hermes services..."

    # Restart FastAPI server if running
    if systemctl is-active --quiet hermes-api; then
        info "Restarting hermes-api service..."
        if systemctl restart hermes-api 2>&1 | tee -a "$LOG_FILE"; then
            success "hermes-api restarted"
        else
            error "Failed to restart hermes-api"
        fi
    else
        info "hermes-api service not active (skipping restart)"
    fi

    # Restart any other Hermes-related services
    for service in hermes-* hermes; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            info "Restarting $service service..."
            if systemctl restart "$service" 2>&1 | tee -a "$LOG_FILE"; then
                success "$service restarted"
            else
                error "Failed to restart $service"
            fi
        fi
    done
fi

log "=== Sync completed successfully ==="
success "Hermes code is now up to date"
