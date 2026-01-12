#!/bin/bash
# ==============================================================
# e-Mutabakat Pro - Statik IP Yapılandırma Scripti
# Debian/Ubuntu için yerel ağda sabit IP atama
# ==============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "=============================================================="
echo "   e-Mutabakat Pro - Statik IP Yapılandırması"
echo "=============================================================="
echo -e "${NC}"

# Root kontrolü
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[HATA] Bu script root olarak çalıştırılmalı!${NC}"
    exit 1
fi

# Mevcut ağ bilgileri
echo -e "${YELLOW}Mevcut ağ yapılandırması:${NC}"
ip addr show
echo ""

# Varsayılan gateway
DEFAULT_GW=$(ip route | grep default | awk '{print $3}' | head -1)
# Mevcut IP
CURRENT_IP=$(hostname -I | awk '{print $1}')
# Ağ arayüzü
INTERFACE=$(ip route | grep default | awk '{print $5}' | head -1)

echo -e "${GREEN}Algılanan değerler:${NC}"
echo "  Arayüz: $INTERFACE"
echo "  Mevcut IP: $CURRENT_IP"
echo "  Gateway: $DEFAULT_GW"
echo ""

# Kullanıcıdan IP bilgisi al
read -p "Atanacak statik IP [örn: 192.168.1.100]: " STATIC_IP
STATIC_IP=${STATIC_IP:-192.168.1.100}

read -p "Alt ağ maskesi (CIDR) [24]: " NETMASK
NETMASK=${NETMASK:-24}

read -p "Gateway [${DEFAULT_GW}]: " GATEWAY
GATEWAY=${GATEWAY:-$DEFAULT_GW}

read -p "DNS sunucusu [8.8.8.8]: " DNS
DNS=${DNS:-8.8.8.8}

echo ""
echo -e "${YELLOW}Yapılandırılacak değerler:${NC}"
echo "  IP: $STATIC_IP/$NETMASK"
echo "  Gateway: $GATEWAY"
echo "  DNS: $DNS"
echo ""
read -p "Devam etmek istiyor musunuz? [e/H]: " CONFIRM

if [[ ! "$CONFIRM" =~ ^[eEyY]$ ]]; then
    echo "İptal edildi."
    exit 0
fi

# ==============================================================
# NETPLAN (Ubuntu 18.04+) veya /etc/network/interfaces (Debian)
# ==============================================================

if [ -d "/etc/netplan" ]; then
    # Ubuntu Netplan
    echo -e "${YELLOW}Netplan yapılandırması oluşturuluyor...${NC}"
    
    # Mevcut yapılandırmayı yedekle
    cp -r /etc/netplan /etc/netplan.backup.$(date +%Y%m%d%H%M%S) 2>/dev/null || true
    
    cat > /etc/netplan/01-static-ip.yaml << EOF
# e-Mutabakat Pro - Statik IP Yapılandırması
network:
  version: 2
  renderer: networkd
  ethernets:
    $INTERFACE:
      dhcp4: no
      addresses:
        - $STATIC_IP/$NETMASK
      gateway4: $GATEWAY
      nameservers:
        addresses: [$DNS]
EOF

    chmod 600 /etc/netplan/01-static-ip.yaml
    
    echo -e "${GREEN}[OK] Netplan yapılandırması oluşturuldu${NC}"
    echo ""
    echo -e "${YELLOW}Yapılandırmayı uygulamak için:${NC}"
    echo "  sudo netplan apply"
    echo ""
    echo -e "${RED}[UYARI] Yapılandırma uygulandığında bağlantınız kesilebilir!${NC}"
    echo "Yeni IP üzerinden bağlanmanız gerekecek: $STATIC_IP"
    
else
    # Debian /etc/network/interfaces
    echo -e "${YELLOW}interfaces dosyası yapılandırılıyor...${NC}"
    
    # Yedekle
    cp /etc/network/interfaces /etc/network/interfaces.backup.$(date +%Y%m%d%H%M%S)
    
    cat > /etc/network/interfaces << EOF
# e-Mutabakat Pro - Statik IP Yapılandırması
# Oluşturulma: $(date)

# Loopback
auto lo
iface lo inet loopback

# Birincil ağ arayüzü - Statik IP
auto $INTERFACE
iface $INTERFACE inet static
    address $STATIC_IP
    netmask 255.255.255.0
    gateway $GATEWAY
    dns-nameservers $DNS
EOF

    echo -e "${GREEN}[OK] interfaces dosyası güncellendi${NC}"
    echo ""
    echo -e "${YELLOW}Yapılandırmayı uygulamak için:${NC}"
    echo "  sudo systemctl restart networking"
    echo "  veya"
    echo "  sudo ifdown $INTERFACE && sudo ifup $INTERFACE"
    echo ""
    echo -e "${RED}[UYARI] Yapılandırma uygulandığında bağlantınız kesilebilir!${NC}"
    echo "Yeni IP üzerinden bağlanmanız gerekecek: $STATIC_IP"
fi

echo ""
echo -e "${GREEN}=============================================================="
echo "   YAPILANDIRMA TAMAMLANDI"
echo "==============================================================${NC}"
echo ""
echo -e "${YELLOW}Önemli Notlar:${NC}"
echo "1. Router/DHCP sunucusunda bu IP'yi rezerve edin"
echo "2. Firewall'da gerekli portları açın: 80, 443"
echo "3. Diğer cihazlardan http://$STATIC_IP ile erişin"
echo ""
