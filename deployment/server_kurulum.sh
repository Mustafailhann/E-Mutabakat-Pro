#!/bin/bash
# ==============================================================
# e-Mutabakat Pro - Debian Sunucu Kurulum ve Kısayol Oluşturucu
# Çift tıklayarak çalıştırılabilir masaüstü script
# ==============================================================

set -e

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       e-Mutabakat Pro - Debian Sunucu Kurulumu               ║"
echo "║       Kurum İçi Kullanım için Tam Kurulum                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# ==============================================================
# YAPILANDIRMA
# ==============================================================
INSTALL_DIR="/opt/e-mutabakat-pro"
SERVICE_USER="emutabakat"
SERVICE_NAME="e-mutabakat-pro"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ==============================================================
# ROOT KONTROLÜ
# ==============================================================
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[!] Root yetkisi gerekli. Şifrenizi girin...${NC}"
    exec sudo "$0" "$@"
    exit 1
fi

echo -e "${GREEN}[✓] Root yetkisi alındı${NC}"
echo ""

# ==============================================================
# 1. SİSTEM GÜNCELLEMESİ
# ==============================================================
echo -e "${YELLOW}[1/9] Sistem güncelleniyor...${NC}"
apt update -qq
apt upgrade -y -qq
echo -e "${GREEN}[✓] Sistem güncel${NC}"

# ==============================================================
# 2. GEREKLİ PAKETLER
# ==============================================================
echo -e "${YELLOW}[2/9] Gerekli paketler yükleniyor...${NC}"
apt install -y -qq \
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
    curl \
    default-jre \
    2>/dev/null

echo -e "${GREEN}[✓] Paketler yüklendi${NC}"

# ==============================================================
# 3. SERVİS KULLANICISI
# ==============================================================
echo -e "${YELLOW}[3/9] Servis kullanıcısı oluşturuluyor...${NC}"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /bin/false $SERVICE_USER
fi
echo -e "${GREEN}[✓] Kullanıcı: $SERVICE_USER${NC}"

# ==============================================================
# 4. UYGULAMA DİZİNİ
# ==============================================================
echo -e "${YELLOW}[4/9] Uygulama dizini hazırlanıyor...${NC}"
mkdir -p $INSTALL_DIR/{logs,uploads,output}

# Proje dosyalarını kopyala
cp -r "$PROJECT_DIR"/*.py "$INSTALL_DIR/" 2>/dev/null || true
cp -r "$PROJECT_DIR"/templates "$INSTALL_DIR/" 2>/dev/null || true
cp -r "$PROJECT_DIR"/static "$INSTALL_DIR/" 2>/dev/null || true
cp -r "$PROJECT_DIR"/gib_viewer_extracted "$INSTALL_DIR/" 2>/dev/null || true

echo -e "${GREEN}[✓] Dosyalar kopyalandı${NC}"

# ==============================================================
# 5. PYTHON ORTAMI
# ==============================================================
echo -e "${YELLOW}[5/9] Python ortamı hazırlanıyor...${NC}"
cd $INSTALL_DIR

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip -q
pip install -q \
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
    werkzeug \
    bcrypt

deactivate
echo -e "${GREEN}[✓] Python bağımlılıkları yüklendi${NC}"

# ==============================================================
# 6. İZİNLER
# ==============================================================
echo -e "${YELLOW}[6/9] İzinler ayarlanıyor...${NC}"
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
chmod -R 755 $INSTALL_DIR
chmod -R 775 $INSTALL_DIR/{logs,uploads,output}
echo -e "${GREEN}[✓] İzinler ayarlandı${NC}"

# ==============================================================
# 7. SYSTEMD SERVİSİ
# ==============================================================
echo -e "${YELLOW}[7/9] Systemd servisi oluşturuluyor...${NC}"

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
ExecStart=$INSTALL_DIR/venv/bin/gunicorn --workers 4 --threads 2 --bind 127.0.0.1:5000 --timeout 120 web_app:app
Restart=always
RestartSec=10
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME -q
systemctl restart $SERVICE_NAME
echo -e "${GREEN}[✓] Servis başlatıldı${NC}"

# ==============================================================
# 8. NGİNX
# ==============================================================
echo -e "${YELLOW}[8/9] Nginx yapılandırılıyor...${NC}"

SERVER_IP=$(hostname -I | awk '{print $1}')

cat > /etc/nginx/sites-available/e-mutabakat-pro << EOF
server {
    listen 80;
    server_name $SERVER_IP localhost _;
    client_max_body_size 500M;
    
    location /static/ {
        alias $INSTALL_DIR/static/;
        expires 7d;
    }
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
}
EOF

ln -sf /etc/nginx/sites-available/e-mutabakat-pro /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
nginx -t -q && systemctl restart nginx
echo -e "${GREEN}[✓] Nginx yapılandırıldı${NC}"

# ==============================================================
# 9. MASAÜSTÜ KISAYOLLARI
# ==============================================================
echo -e "${YELLOW}[9/9] Masaüstü kısayolları oluşturuluyor...${NC}"

# Root kullanıcı masaüstü
ROOT_DESKTOP="/root/Desktop"
mkdir -p "$ROOT_DESKTOP"

# Başlatma kısayolu
cat > "$ROOT_DESKTOP/e-Mutabakat-Baslat.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=e-Mutabakat Pro Başlat
Comment=Sunucuyu başlat ve tarayıcıda aç
Icon=web-browser
Exec=bash -c "systemctl start $SERVICE_NAME && sleep 2 && xdg-open http://localhost"
Terminal=false
Categories=Office;Finance;
EOF

# Durdurma kısayolu
cat > "$ROOT_DESKTOP/e-Mutabakat-Durdur.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=e-Mutabakat Pro Durdur
Comment=Sunucuyu durdur
Icon=system-shutdown
Exec=bash -c "systemctl stop $SERVICE_NAME && notify-send 'e-Mutabakat Pro' 'Sunucu durduruldu'"
Terminal=false
Categories=Office;Finance;
EOF

# Yönetim scripti
cat > "$ROOT_DESKTOP/e-Mutabakat-Yonetim.sh" << 'SCRIPT'
#!/bin/bash
# e-Mutabakat Pro Yönetim Menüsü

while true; do
    clear
    echo "╔══════════════════════════════════════╗"
    echo "║   e-Mutabakat Pro - Yönetim Menüsü   ║"
    echo "╠══════════════════════════════════════╣"
    echo "║  1. Sunucuyu Başlat                  ║"
    echo "║  2. Sunucuyu Durdur                  ║"
    echo "║  3. Sunucuyu Yeniden Başlat          ║"
    echo "║  4. Durum Göster                     ║"
    echo "║  5. Logları Görüntüle                ║"
    echo "║  6. Tarayıcıda Aç                    ║"
    echo "║  7. Çıkış                            ║"
    echo "╚══════════════════════════════════════╝"
    echo ""
    read -p "Seçiminiz [1-7]: " choice
    
    case $choice in
        1) sudo systemctl start e-mutabakat-pro; echo "Başlatıldı!"; sleep 2;;
        2) sudo systemctl stop e-mutabakat-pro; echo "Durduruldu!"; sleep 2;;
        3) sudo systemctl restart e-mutabakat-pro; echo "Yeniden başlatıldı!"; sleep 2;;
        4) sudo systemctl status e-mutabakat-pro; read -p "Devam için Enter...";;
        5) sudo journalctl -u e-mutabakat-pro -n 50; read -p "Devam için Enter...";;
        6) xdg-open http://localhost 2>/dev/null || sensible-browser http://localhost;;
        7) exit 0;;
        *) echo "Geçersiz seçim!"; sleep 1;;
    esac
done
SCRIPT

chmod +x "$ROOT_DESKTOP"/*.desktop 2>/dev/null || true
chmod +x "$ROOT_DESKTOP/e-Mutabakat-Yonetim.sh"

# Tüm kullanıcılar için /usr/share/applications'a ekle
cat > /usr/share/applications/e-mutabakat-pro.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=e-Mutabakat Pro
Comment=e-Fatura ve Defter Mutabakat Sistemi
Icon=accessories-calculator
Exec=xdg-open http://localhost
Terminal=false
Categories=Office;Finance;
EOF

echo -e "${GREEN}[✓] Kısayollar oluşturuldu${NC}"

# ==============================================================
# KURULUM TAMAMLANDI
# ==============================================================
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗"
echo -e "║              KURULUM BAŞARIYLA TAMAMLANDI!                   ║"
echo -e "╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Sunucu IP Adresi: ${YELLOW}$SERVER_IP${NC}"
echo ""
echo -e "${BLUE}Erişim Adresleri:${NC}"
echo "  • Sunucu üzerinden: http://localhost"
echo "  • Ağ üzerinden:     http://$SERVER_IP"
echo ""
echo -e "${BLUE}Giriş:${NC}"
echo "  İlk kullanıcı: admin panelinden oluşturun"
echo "  veya IT yöneticinizden bilgi alın"
echo ""
echo -e "${BLUE}Masaüstü Kısayolları:${NC}"
echo "  • e-Mutabakat-Baslat.desktop   → Sunucuyu başlat"
echo "  • e-Mutabakat-Durdur.desktop   → Sunucuyu durdur"
echo "  • e-Mutabakat-Yonetim.sh       → Yönetim menüsü"
echo ""
echo -e "${BLUE}Servis Komutları:${NC}"
echo "  sudo systemctl status $SERVICE_NAME"
echo "  sudo systemctl restart $SERVICE_NAME"
echo ""
echo -e "${YELLOW}İstemciler için bu IP'yi kullanın: $SERVER_IP${NC}"
echo ""

# Tarayıcıda aç
read -p "Şimdi tarayıcıda açılsın mı? [E/h]: " OPEN_BROWSER
if [[ ! "$OPEN_BROWSER" =~ ^[hHnN]$ ]]; then
    xdg-open "http://localhost" 2>/dev/null || sensible-browser "http://localhost" 2>/dev/null || echo "Tarayıcı açılamadı"
fi
