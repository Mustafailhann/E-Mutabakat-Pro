# e-Mutabakat Pro - Debian Server Kurulum Rehberi
## Kurum İçi (Intranet) Deployment - Dinamik IP Çözümü

---

## 🌐 Dinamik IP Sorunu ve Çözümler

Kurumunuzun dış IP'si dinamik olsa bile, **kurum içi kullanım** için bu sorun şöyle çözülür:

### Seçenek 1: Yerel Ağda Sabit IP (Önerilen)
```
Router/DHCP ayarlarından sunucunun MAC adresine IP rezervasyonu yapın.
Örnek: Sunucu MAC = AA:BB:CC:DD:EE:FF → IP: 192.168.1.100
```

### Seçenek 2: Hostname ile Erişim
```
Sunucuya hostname verin: e-mutabakat.local
Çalışanlar http://e-mutabakat.local ile erişir
```

### Seçenek 3: Dışarıdan Erişim Gerekirse (Dynamic DNS)
- No-IP, DuckDNS gibi ücretsiz DDNS servisleri
- Kendi domaininize DDNS client kurulumu

---

## 🖥️ Sunucu Gereksinimleri

| Gereksinim | Minimum | Önerilen |
|------------|---------|----------|
| CPU | 2 çekirdek | 4 çekirdek |
| RAM | 2 GB | 4 GB |
| Disk | 20 GB | 50 GB SSD |
| OS | Debian 11+ / Ubuntu 20.04+ | Debian 12 |

---

## 📦 Hızlı Kurulum

### 1. Proje Dosyalarını Sunucuya Kopyalayın

```bash
# Yerel bilgisayardan (Windows PowerShell)
scp -r "C:\Users\mustafa\Documents\EMutabakat_Pro_Source_1" kullanici@sunucu-ip:/tmp/

# veya USB ile
# veya Git ile
git clone <repo-url> /tmp/EMutabakat_Pro_Source_1
```

### 2. Kurulum Scriptini Çalıştırın

```bash
# Sunucuya SSH ile bağlanın
ssh kullanici@sunucu-ip

# Script'i çalıştırın
cd /tmp/EMutabakat_Pro_Source_1/deployment
chmod +x debian_install.sh
sudo ./debian_install.sh
```

---

## 🔧 Manuel Kurulum (Adım Adım)

### Adım 1: Sistem Güncelleme
```bash
sudo apt update && sudo apt upgrade -y
```

### Adım 2: Gerekli Paketler
```bash
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    build-essential libxml2-dev libxslt1-dev nginx unrar default-jre
```

### Adım 3: Uygulama Dizini
```bash
sudo mkdir -p /opt/e-mutabakat-pro
sudo cp -r /tmp/EMutabakat_Pro_Source_1/* /opt/e-mutabakat-pro/
```

### Adım 4: Python Ortamı
```bash
cd /opt/e-mutabakat-pro
sudo python3 -m venv venv
sudo ./venv/bin/pip install -r deployment/requirements.txt
```

### Adım 5: Servis Kullanıcısı
```bash
sudo useradd --system --no-create-home emutabakat
sudo chown -R emutabakat:emutabakat /opt/e-mutabakat-pro
```

### Adım 6: Systemd Servisi
```bash
sudo nano /etc/systemd/system/e-mutabakat-pro.service
```

İçerik:
```ini
[Unit]
Description=e-Mutabakat Pro
After=network.target

[Service]
Type=simple
User=emutabakat
WorkingDirectory=/opt/e-mutabakat-pro
Environment="PATH=/opt/e-mutabakat-pro/venv/bin"
Environment="FLASK_ENV=production"
ExecStart=/opt/e-mutabakat-pro/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5000 web_app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable e-mutabakat-pro
sudo systemctl start e-mutabakat-pro
```

### Adım 7: Nginx Reverse Proxy
```bash
sudo nano /etc/nginx/sites-available/e-mutabakat-pro
```

İçerik:
```nginx
server {
    listen 80;
    server_name _;
    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/e-mutabakat-pro /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔒 Statik IP Yapılandırması

### Debian (interfaces)
```bash
sudo nano /etc/network/interfaces
```

```
auto eth0
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1
    dns-nameservers 8.8.8.8
```

### Ubuntu (Netplan)
```bash
sudo nano /etc/netplan/01-static.yaml
```

```yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: no
      addresses: [192.168.1.100/24]
      gateway4: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8]
```

```bash
sudo netplan apply
```

---

## 👥 Kullanıcı Erişimi

Tüm kurum çalışanları tarayıcıdan erişebilir:

```
http://192.168.1.100
veya
http://sunucu-hostname
```

**Giriş:**
- İlk kullanıcıyı admin panelinden oluşturun
- veya IT yöneticinizden bilgi alın

---

## 🔧 Yönetim Komutları

```bash
# Servis durumu
sudo systemctl status e-mutabakat-pro

# Servisi yeniden başlat
sudo systemctl restart e-mutabakat-pro

# Logları izle
sudo journalctl -u e-mutabakat-pro -f

# Nginx logları
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## 🔥 Firewall Ayarları

```bash
# UFW ile
sudo ufw allow 80/tcp
sudo ufw allow 22/tcp
sudo ufw enable

# veya iptables ile
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
```

---

## 📊 Mimari Diyagram

```
┌─────────────────────────────────────────────────────────────┐
│                 KURUM İÇİ AĞ (192.168.1.0/24)               │
│                                                              │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│   │ Çalışan PC  │     │ Çalışan PC  │     │ Çalışan PC  │   │
│   │ 192.168.1.x │     │ 192.168.1.y │     │ 192.168.1.z │   │
│   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘   │
│          │                   │                   │           │
│          └───────────────────┴───────────────────┘           │
│                              │                               │
│                              ▼ HTTP (80)                     │
│                    ┌─────────────────────┐                   │
│                    │   DEBIAN SUNUCU     │                   │
│                    │   192.168.1.100     │                   │
│                    │                     │                   │
│                    │  ┌───────────────┐  │                   │
│                    │  │     NGINX     │  │                   │
│                    │  │   (Port 80)   │  │                   │
│                    │  └───────┬───────┘  │                   │
│                    │          │          │                   │
│                    │          ▼          │                   │
│                    │  ┌───────────────┐  │                   │
│                    │  │   GUNICORN    │  │                   │
│                    │  │  (Port 5000)  │  │                   │
│                    │  └───────┬───────┘  │                   │
│                    │          │          │                   │
│                    │          ▼          │                   │
│                    │  ┌───────────────┐  │                   │
│                    │  │  FLASK APP    │  │                   │
│                    │  │ e-Mutabakat   │  │                   │
│                    │  └───────────────┘  │                   │
│                    │                     │                   │
│                    │  📁 /opt/e-mutabakat-pro               │
│                    │     ├── uploads/                        │
│                    │     ├── logs/                           │
│                    │     └── users.db                        │
│                    └─────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

---

## ❓ Sorun Giderme

### Servis başlamıyor
```bash
sudo journalctl -u e-mutabakat-pro --no-pager -n 50
```

### 502 Bad Gateway
```bash
# Gunicorn çalışıyor mu?
sudo systemctl status e-mutabakat-pro

# Port dinleniyor mu?
sudo ss -tlnp | grep 5000
```

### İzin hataları
```bash
sudo chown -R emutabakat:emutabakat /opt/e-mutabakat-pro
sudo chmod -R 755 /opt/e-mutabakat-pro
```

