#!/bin/bash
# Run ONCE on fresh Vultr VPS (Ubuntu 24.04).
# Usage: ./vps-setup.sh <github-repo-url>
set -e

REPO_URL=$1

if [ -z "$REPO_URL" ]; then
  echo "Usage: $0 <github-repo-url>"
  echo "Example: $0 https://github.com/myorg/interhack-2026.git"
  exit 1
fi

# Update system
apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg git

# Install Docker
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl enable docker
systemctl start docker

# Clone repo
git clone "$REPO_URL" /opt/interhack-2026
chmod +x /opt/interhack-2026/scripts/*.sh

# Open firewall ports
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo ""
echo "Done. Next steps:"
echo "  1. Add deploy SSH public key to ~/.ssh/authorized_keys"
echo "  2. cd /opt/interhack-2026 && ./scripts/init-ssl.sh <domain> <email>"
echo "  3. Add GitHub Secrets and push to main"
