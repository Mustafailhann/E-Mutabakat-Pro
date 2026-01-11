# 🧾 e-Mutabakat Pro

**Türkiye'deki muhasebe profesyonelleri için kapsamlı fatura mutabakat ve KDV iade analiz sistemi.**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Proje Hakkında

e-Mutabakat Pro, Türk vergi mevzuatına uygun olarak e-fatura işleme, KDV iade listesi oluşturma ve YMM (Yeminli Mali Müşavir) denetim raporları hazırlama işlemlerini otomatikleştiren profesyonel bir uygulamadır.

### ✨ Temel Özellikler

- 📄 **E-Fatura İşleme**: XML ve PDF formatındaki e-faturaların otomatik ayrıştırılması
- 📊 **KDV İade Listesi**: GİB formatında Excel çıktıları oluşturma
- 📑 **Satış Fatura Listesi**: Satış faturalarının detaylı raporlanması
- 🔍 **YMM Denetim Raporu**: Kapsamlı mali denetim raporları
- 🌐 **Web Arayüzü**: Modern, responsive web editörü
- 🖥️ **Masaüstü Uygulaması**: Tkinter tabanlı GUI
- 🔐 **Güvenlik**: Kullanıcı yetkilendirme ve audit logging

---

## 🔄 Sistem Mimarisi ve Çalışma Akışı

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              KULLANICI GİRİŞİ                               │
│                         (Web veya Masaüstü Client)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           📁 DOSYA YÜKLEME                                  │
│                   ZIP / RAR / XML / PDF Formatları                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   📄 XML        │         │   📑 PDF        │         │   📦 ZIP/RAR    │
│   Parser        │         │   Parser        │         │   Extractor     │
│                 │         │                 │         │                 │
│ enhanced_xml_   │         │ pdf_invoice_    │         │ Otomatik        │
│ parser.py       │         │ reader.py       │         │ Açma            │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        🔍 FATURA VERİ İŞLEME                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ • ETTN (Fatura No)           • Satıcı/Alıcı Bilgileri               │    │
│  │ • KDV Tutarları              • Fatura Tarihi                        │    │
│  │ • Mal/Hizmet Kalemleri       • Vergi Dairesi                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   📊 KDV İADE   │         │   📋 SATIŞ      │         │   📑 YMM       │
│   LİSTESİ       │         │   FATURA        │         │   DENETİM      │
│                 │         │   LİSTESİ       │         │   RAPORU       │
│ kdv_iade_       │         │                 │         │                │
│ listesi.py      │         │ satis_fatura_   │         │ ymm_audit.py   │
│                 │         │ listesi.py      │         │ ymm_report_    │
│                 │         │                 │         │ generator.py   │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   🌐 WEB        │         │   🌐 WEB        │         │   📄 HTML      │
│   EDITOR        │         │   EDITOR        │         │   RAPOR        │
│                 │         │                 │         │                │
│ kdv_web_        │         │ satis_web_      │         │ Detaylı        │
│ editor.py       │         │ editor.py       │         │ Analiz         │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           📥 ÇIKTI OLUŞTURMA                                │
│                                                                             │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐          │
│  │  EXCEL    │    │   HTML    │    │   JSON    │    │   PDF     │          │
│  │  (.xlsx)  │    │  Rapor    │    │   Data    │    │  Görüntü  │          │
│  └───────────┘    └───────────┘    └───────────┘    └───────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🌐 Kurumsal Dağıtım Mimarisi

```
┌────────────────────────────────────────────────────────────────┐
│                     👥 KULLANICILAR                            │
│              (Masaüstü Kısayolu - Tek Tık Erişim)              │
└─────────────────────────────┬──────────────────────────────────┘
                              │
                              ▼ HTTPS (443)
┌────────────────────────────────────────────────────────────────┐
│                   🔒 CADDY REVERSE PROXY                       │
│  ├─ Otomatik HTTPS (Let's Encrypt)                             │
│  ├─ HSTS, X-Frame-Options, CSP                                 │
│  ├─ Gzip Sıkıştırma                                            │
│  └─ Rate Limit (Login koruma)                                  │
└─────────────────────────────┬──────────────────────────────────┘
                              │ localhost:5000
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                   ⚡ FLASK (WAITRESS)                          │
│  ├─ 8 Thread Production Server                                 │
│  ├─ Session: Secure, HttpOnly, SameSite=Strict                 │
│  └─ Rate Limit: 5 deneme / 5 dk → 15 dk kilit                  │
└─────────────────────────────┬──────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────┐         ┌─────────────────────────┐
│     🗄️ SQLITE       │         │   📝 DOSYA LOG (JSONL)  │
│     users.db        │         │   logs/audit.log        │
│                     │         │   logs/security.log     │
└─────────────────────┘         └─────────────────────────┘
```

---

## 🚀 Kurulum

### Gereksinimler

- Python 3.9+
- pip (Python paket yöneticisi)

### Adım Adım Kurulum

```bash
# 1. Repoyu klonla
git clone https://github.com/Mustafailhann/e-mutabakat-pro.git
cd e-mutabakat-pro

# 2. Virtual environment oluştur
python -m venv .venv

# 3. Virtual environment'ı aktifleştir
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 4. Bağımlılıkları yükle
pip install flask flask-login waitress openpyxl lxml pdfplumber
```

### Uygulamayı Çalıştırma

```bash
# Web uygulaması (geliştirme)
python web_app.py

# Web uygulaması (production - Waitress)
python -c "from waitress import serve; from web_app import app; serve(app, host='0.0.0.0', port=5000, threads=8)"

# Masaüstü uygulaması
python e_mutabakat_pro.py
```

---

## 📁 Proje Yapısı

```
e-mutabakat-pro/
├── 📄 web_app.py              # Flask web uygulaması ana modülü
├── 📄 e_mutabakat_pro.py      # Tkinter masaüstü uygulaması
├── 📄 config.py               # Konfigürasyon ayarları
│
├── 🔍 Ayrıştırıcılar (Parsers)
│   ├── enhanced_xml_parser.py # XML fatura ayrıştırıcı
│   ├── pdf_invoice_reader.py  # PDF fatura okuyucu
│   ├── beyanname_parser.py    # Beyanname ayrıştırıcı
│   └── mizan_parser.py        # Mizan ayrıştırıcı
│
├── 📊 KDV ve Fatura Modülleri
│   ├── kdv_iade_listesi.py    # KDV iade listesi oluşturucu
│   ├── kdv_web_editor.py      # Web tabanlı KDV editörü
│   ├── satis_fatura_listesi.py# Satış fatura listesi
│   ├── satis_web_editor.py    # Web tabanlı satış editörü
│   └── export_gib_excel.py    # GİB Excel export
│
├── 📑 YMM Denetim Modülleri
│   ├── ymm_audit.py           # YMM denetim ana modülü
│   ├── ymm_report_generator.py# Rapor oluşturucu
│   ├── ymm_auditor_report.py  # Denetçi raporu
│   └── ymm_report_helpers.py  # Yardımcı fonksiyonlar
│
├── 🔐 Güvenlik
│   ├── auth.py                # Kimlik doğrulama
│   ├── database.py            # Veritabanı işlemleri
│   └── audit_logger.py        # Güvenlik loglama
│
├── 🌐 Web Arayüzü
│   ├── templates/             # HTML şablonları
│   │   ├── login.html
│   │   ├── index.html
│   │   ├── admin.html
│   │   └── profile.html
│   └── static/                # CSS, JS dosyaları
│
├── 🚀 Kurulum ve Dağıtım
│   ├── server_install.bat     # Sunucu kurulum scripti
│   ├── client_install.bat     # İstemci kurulum scripti
│   ├── start_server.bat       # Sunucu başlatma
│   ├── Caddyfile              # Caddy reverse proxy config
│   └── nginx.conf             # Nginx alternatif config
│
└── 📚 Dokümantasyon
    ├── README.md              # Bu dosya
    └── DEPLOYMENT.md          # Dağıtım kılavuzu
```

---

## 🔐 Güvenlik Özellikleri

| Katman | Özellik |
|--------|---------|
| 🌐 Ağ | HTTPS zorunlu, HTTP→HTTPS yönlendirme |
| 🔒 Caddy | HSTS, CSP, X-Frame-Options |
| ⚡ Flask | Session Secure/HttpOnly/SameSite |
| 🔑 Login | 5 başarısız → 15 dk kilit |
| 📝 Log | Tüm giriş/çıkış JSONL formatında |
| 🛡️ Firewall | 443 açık, 5000 dışarıya kapalı |

---

## 📸 Ekran Görüntüleri

### Web Arayüzü
*Ana sayfa ve dosya yükleme ekranı*

### KDV Editörü
*İnteraktif KDV fatura düzenleme arayüzü*

### Rapor Çıktısı
*Otomatik oluşturulan Excel ve HTML raporlar*

---

## 🤝 Katkıda Bulunma

1. Bu repoyu fork'layın
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Değişikliklerinizi commit'leyin (`git commit -m 'Add some AmazingFeature'`)
4. Branch'inizi push'layın (`git push origin feature/AmazingFeature`)
5. Pull Request oluşturun

---

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakınız.

---

## 👨‍💻 Geliştirici

**Mustafa İlhan**

- GitHub: [@Mustafailhann](https://github.com/Mustafailhann)

---

## 📞 Destek

Herhangi bir sorun veya öneriniz için [GitHub Issues](https://github.com/Mustafailhann/e-mutabakat-pro/issues) sayfasını kullanabilirsiniz.
