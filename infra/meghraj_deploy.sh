#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# SHIELD Platform — MeghRaj / NIC Cloud Production Deployment Script
# Target OS: Ubuntu 22.04 / 24.04 LTS (MeghRaj Standard Image)
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

echo "🛡️ Starting SHIELD Platform Production Deployment for MeghRaj / NIC Cloud..."

# 1. ROOT CHECK
if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: Please execute as root (sudo ./meghraj_deploy.sh)"
  exit 1
fi

# 2. FIREWALL HARDENING
echo "🔒 Configuring UFW Firewall for Police Enclave..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # Admin SSH (Restrict to police VPN CIDR in production)
ufw allow 80/tcp   # HTTP -> HTTPS redirect
ufw allow 443/tcp  # HTTPS Secure Enclave
ufw --force enable

# 3. INSTALL SYSTEM DEPENDENCIES
echo "📦 Installing system packages..."
apt-get update -y
apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    openssl \
    fail2ban \
    ufw \
    jq

# 4. SECURE ENVIRONMENT VARIABLES GENERATION
echo "🔑 Generating Cryptographically Secure Enclave Secrets..."
INSTALL_DIR="/opt/shield"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

DB_PASS=$(openssl rand -hex 32)
REDIS_PASS=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 64)
FERNET_KEY=$(python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())" 2>/dev/null || openssl rand -base64 32)
MINIO_ROOT_KEY=$(openssl rand -hex 24)
MINIO_SECRET_KEY=$(openssl rand -hex 32)

cat <<EOF > "$INSTALL_DIR/.env"
# SHIELD Production Enclave Configuration
ENVIRONMENT=production
DEBUG=false
POSTGRES_DB=shielddb
POSTGRES_USER=shield_app
POSTGRES_PASSWORD=$DB_PASS
REDIS_PASSWORD=$REDIS_PASS
SECRET_KEY=$JWT_SECRET
FIELD_ENCRYPTION_KEY=$FERNET_KEY
MINIO_ACCESS_KEY=$MINIO_ROOT_KEY
MINIO_SECRET_KEY=$MINIO_SECRET_KEY
ALLOWED_ORIGINS=https://shield.gov.in,https://app.shield.gov.in
EOF

chmod 600 "$INSTALL_DIR/.env"
echo "✅ Secrets generated and secured at $INSTALL_DIR/.env (chmod 600)"

# 5. DOCKER & COMPOSE INSTALLATION
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker Engine..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# 6. FAIL2BAN HARDENING (Anti-Brute-Force)
cat <<EOF > /etc/fail2ban/jail.d/shield.local
[sshd]
enabled = true
port = 22
maxretry = 3
findtime = 600
bantime = 86400
EOF
systemctl restart fail2ban

echo "✅ MeghRaj Infrastructure Provisioned Successfully!"
echo "Next: Deploy Docker stack with: cd /opt/shield/infra && docker compose up -d"
