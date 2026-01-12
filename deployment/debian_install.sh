#!/bin/bash
# ==============================================================
# e-Mutabakat Pro - Debian/Ubuntu Server Kurulum Scripti
# Kurum İçi (Intranet) Deployment
# ==============================================================

set -e  # Hata durumunda dur

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "=============================================================="
echo "   e-Mutabakat Pro - Debian Server Kurulumu"
echo "   Kurum İçi Kullanım"
echo "=============================================================="
echo -e "${NC}"

# Root kontrolü
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[HATA] Bu script root olarak çalıştırılmalı!${NC}"
    echo "Kullanım: sudo ./debian_install.sh"
    exit 1
fi

# ==============================================================
# 1. KURULUM DİZİNİ
# ==============================================================
INSTALL_DIR="/opt/e-mutabakat-pro"
SERVICE_USER="emutabakat"
SERVICE_NAME="e-mutabakat-pro"

echo -e "${YELLOW}[1/8] Sistem güncelleniyor...${NC}"
apt update && apt upgrade -y

# ==============================================================
# 2. GEREKLİ PAKETLER
# ==============================================================
echo -e "${YELLOW}[2/8] Gerekli paketler yükleniyor...${NC}"
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libffi-dev \
    nginx \
    unrar \
    unzip \
    git \
    curl \
    default-jre  # Java (GİB e-Fatura görüntüleyici için)

# ==============================================================
# 3. SERVİS KULLANICISI OLUŞTUR
# ==============================================================
echo -e "${YELLOW}[3/8] Servis kullanıcısı oluşturuluyor...${NC}"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /bin/false $SERVICE_USER
    echo -e "${GREEN}[OK] Kullanıcı oluşturuldu: $SERVICE_USER${NC}"
else
    echo -e "${GREEN}[OK] Kullanıcı zaten mevcut: $SERVICE_USER${NC}"
fi

# ==============================================================
# 4. UYGULAMA DİZİNİ
# ==============================================================
echo -e "${YELLOW}[4/8] Uygulama dizini hazırlanıyor...${NC}"
mkdir -p $INSTALL_DIR
mkdir -p $INSTALL_DIR/logs
mkdir -p $INSTALL_DIR/uploads
mkdir -p $INSTALL_DIR/output

# Dosyaları kopyala (script'in bulunduğu dizinden)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Kaynak dizin: $PARENT_DIR"

# Python dosyalarını kopyala
cp -r $PARENT_DIR/*.py $INSTALL_DIR/ 2>/dev/null || true
cp -r $PARENT_DIR/templates $INSTALL_DIR/ 2>/dev/null || true
cp -r $PARENT_DIR/static $INSTALL_DIR/ 2>/dev/null || true
cp -r $PARENT_DIR/gib_viewer_extracted $INSTALL_DIR/ 2>/dev/null || true

echo -e "${GREEN}[OK] Dosyalar kopyalandı${NC}"

# ==============================================================
# 5. PYTHON VIRTUAL ENVIRONMENT
# ==============================================================
echo -e "${YELLOW}[5/8] Python sanal ortamı oluşturuluyor...${NC}"
cd $INSTALL_DIR

python3 -m venv venv
source venv/bin/activate

# Pip güncelle
pip install --upgrade pip

# Gerekli paketler
pip install \
    flask \
    flask-login \
    waitress \
    gunicorn \
    openpyxl \
    lxml \
    pdfplumber \
    qrcode \
    Pillow \
    requests \
    rarfile \
    python-dateutil \
    werkzeug

deactivate

echo -e "${GREEN}[OK] Python bağımlılıkları yüklendi${NC}"

# ==============================================================
# 6. İZİNLER
# ==============================================================
echo -e "${YELLOW}[6/8] Dosya izinleri ayarlanıyor...${NC}"
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
chmod -R 755 $INSTALL_DIR
chmod -R 775 $INSTALL_DIR/logs
chmod -R 775 $INSTALL_DIR/uploads
chmod -R 775 $INSTALL_DIR/output

# ==============================================================
# 7. SYSTEMD SERVİSİ
# ==============================================================
echo -e "${YELLOW}[7/8] Systemd servisi oluşturuluyor...${NC}"

cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=e-Mutabakat Pro Flask Application
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="FLASK_ENV=production"
Environment="PYTHONPATH=$INSTALL_DIR"
ExecStart=$INSTALL_DIR/venv/bin/gunicorn --workers 4 --threads 2 --bind 127.0.0.1:5000 --timeout 120 web_app:app
Restart=always
RestartSec=10

# Güvenlik
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$INSTALL_DIR/logs $INSTALL_DIR/uploads $INSTALL_DIR/output $INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

echo -e "${GREEN}[OK] Servis oluşturuldu ve başlatıldı${NC}"

# ==============================================================
# 8. NGİNX REVERSE PROXY
# ==============================================================
echo -e "${YELLOW}[8/8] Nginx yapılandırılıyor...${NC}"

# Sunucu IP'sini al
SERVER_IP=$(hostname -I | awk '{print $1}')

cat > /etc/nginx/sites-available/e-mutabakat-pro << EOF
# e-Mutabakat Pro - Nginx Reverse Proxy
# Kurum İçi (Intranet) Kullanım

upstream e_mutabakat {
    server 127.0.0.1:5000;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    
    # Sunucu adları (kurum içi erişim)
    server_name $SERVER_IP localhost e-mutabakat.local _;
    
    # Max dosya boyutu (500MB)
    client_max_body_size 500M;
    
    # Timeout ayarları
    proxy_connect_timeout 300;
    proxy_send_timeout 300;
    proxy_read_timeout 300;
    send_timeout 300;
    
    # Loglar
    access_log /var/log/nginx/e-mutabakat-access.log;
    error_log /var/log/nginx/e-mutabakat-error.log;
    
    # Güvenlik başlıkları
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Gzip sıkıştırma
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;
    
    # Static dosyalar (nginx'ten servis et)
    location /static/ {
        alias $INSTALL_DIR/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
    
    # Ana uygulama
    location / {
        proxy_pass http://e_mutabakat;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        
        # Buffering ayarları
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # Upload endpoint için özel ayar
    location /upload {
        proxy_pass http://e_mutabakat;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        
        # Büyük dosyalar için
        client_body_timeout 600;
        proxy_read_timeout 600;
    }
}
EOF

# Site'ı aktif et
ln -sf /etc/nginx/sites-available/e-mutabakat-pro /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Nginx config test
nginx -t

# Nginx'i yeniden başlat
systemctl restart nginx
systemctl enable nginx

echo -e "${GREEN}[OK] Nginx yapılandırıldı${NC}"

# ==============================================================
# KURULUM TAMAMLANDI
# ==============================================================
echo ""
echo -e "${GREEN}=============================================================="
echo "   KURULUM TAMAMLANDI!"
echo "==============================================================${NC}"
echo ""
echo -e "${BLUE}Sunucu IP Adresi: ${GREEN}$SERVER_IP${NC}"
echo ""
echo -e "${YELLOW}Erişim Adresleri:${NC}"
echo "  - http://$SERVER_IP"
echo "  - http://localhost (sunucu üzerinden)"
echo ""
echo -e "${YELLOW}Giriş:${NC}"
echo "  İlk kullanıcıyı admin panelinden oluşturun"
echo "  veya IT yöneticinizden bilgi alın"
echo ""
echo -e "${YELLOW}Servis Yönetimi:${NC}"
echo "  sudo systemctl status $SERVICE_NAME"
echo "  sudo systemctl restart $SERVICE_NAME"
echo "  sudo systemctl stop $SERVICE_NAME"
echo ""
echo -e "${YELLOW}Log Görüntüleme:${NC}"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo "  sudo tail -f /var/log/nginx/e-mutabakat-error.log"
echo ""
echo -e "${YELLOW}Dinamik IP Notu:${NC}"
echo "  Kurum içi ağda sabit yerel IP atamak için:"
echo "  1. Router/DHCP'den MAC adresine IP rezervasyonu yapın"
echo "  2. Veya /etc/network/interfaces ile statik IP atayın"
echo ""
