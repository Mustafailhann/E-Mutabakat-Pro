# e-Mutabakat Pro - Kurumsal Dağıtım Mimarisi

## Mimari Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     KULLANICILAR                            │
│              (Masaüstü Kısayolu - Tek Tık)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼ HTTPS (443)
┌─────────────────────────────────────────────────────────────┐
│                 CADDY REVERSE PROXY                         │
│  ├─ Otomatik HTTPS (Let's Encrypt)                          │
│  ├─ HSTS, X-Frame-Options, CSP                              │
│  ├─ Gzip sıkıştırma                                         │
│  └─ Rate limit (login)                                      │
└─────────────────────┬───────────────────────────────────────┘
                      │ localhost:5000
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  FLASK (WAITRESS)                           │
│  ├─ 8 thread production server                              │
│  ├─ Session: Secure, HttpOnly, SameSite=Strict              │
│  └─ Rate limit: 5 deneme / 5 dk → 15 dk kilit               │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌──────────┴──────────┐
          ▼                     ▼
┌─────────────────┐   ┌─────────────────────────┐
│    SQLITE       │   │    DOSYA LOG (JSONL)    │
│   users.db      │   │  logs/audit.log         │
│                 │   │  logs/security.log      │
└─────────────────┘   └─────────────────────────┘
```

---

## Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `server_install.bat` | Sunucu kurulumu (venv, pip, config, firewall) |
| `client_install.bat` | İstemci kısayol oluşturucu |
| `start_server.bat` | Waitress server başlatıcı |
| `install_service.bat` | NSSM Windows servisi |
| `Caddyfile` | Reverse proxy config |
| `config.py` | Flask production ayarları |
| `audit_logger.py` | Güvenlik loglama + rate limit |

---

## Kurulum

### Sunucu
```
1. server_install.bat (Yönetici olarak)
2. Caddy indir → caddy.exe'yi PATH'e ekle
3. Caddyfile'da domain düzenle
4. start_server.bat veya install_service.bat
```

### İstemci
```
1. client_install.bat içinde SERVER_URL düzenle
2. Her kullanıcı PC'de client_install.bat çalıştır
3. Masaüstü kısayoluna tıkla → Tarayıcı açılır
```

---

## Güvenlik

| Katman | Özellik |
|--------|---------|
| Ağ | HTTPS zorunlu, HTTP→HTTPS redirect |
| Caddy | HSTS, CSP, X-Frame-Options |
| Flask | Session Secure/HttpOnly/SameSite |
| Login | 5 başarısız → 15 dk kilit |
| Log | Tüm giriş/çıkış JSONL'de |
| Firewall | 443 açık, 5000 dışarıya kapalı |
