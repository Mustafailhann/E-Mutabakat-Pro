# -*- coding: utf-8 -*-
"""
İşlem Günlüğü (Audit Log) Sistemi
YMM şeffaflık gereksinimi için tüm eşleştirme ve kontrol işlemlerini kaydeder
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
import json
import os


@dataclass
class LogKaydi:
    """Tek bir log kaydı"""
    timestamp: str
    islem_tipi: str  # "eslestirme", "kontrol", "ai_sorgu", "kullanici_onay", "hata"
    seviye: str  # "INFO", "WARNING", "ERROR", "DEBUG"
    mesaj: str
    detay: Dict = field(default_factory=dict)
    kullanici: str = ""
    oturum_id: str = ""


class IslemGunlugu:
    """
    YMM Şeffaflık İşlem Günlüğü
    
    Her işlemi kaydeder:
    - Eşleştirme denemeleri
    - AI sorguları ve yanıtları
    - Kullanıcı onayları
    - Kontrol sonuçları
    - Hatalar ve uyarılar
    """
    
    def __init__(self, log_klasoru: str = "data/logs"):
        self.log_klasoru = log_klasoru
        self.kayitlar: List[LogKaydi] = []
        self.oturum_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._aktif_log_dosyasi = None
        
        os.makedirs(log_klasoru, exist_ok=True)
    
    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    # ==================== LOG METOTLARI ====================
    
    def bilgi(self, mesaj: str, detay: Dict = None, islem_tipi: str = "genel"):
        """INFO seviyesinde log kaydı"""
        self._kaydet("INFO", islem_tipi, mesaj, detay or {})
    
    def uyari(self, mesaj: str, detay: Dict = None, islem_tipi: str = "genel"):
        """WARNING seviyesinde log kaydı"""
        self._kaydet("WARNING", islem_tipi, mesaj, detay or {})
    
    def hata(self, mesaj: str, detay: Dict = None, islem_tipi: str = "genel"):
        """ERROR seviyesinde log kaydı"""
        self._kaydet("ERROR", islem_tipi, mesaj, detay or {})
    
    def debug(self, mesaj: str, detay: Dict = None, islem_tipi: str = "genel"):
        """DEBUG seviyesinde log kaydı"""
        self._kaydet("DEBUG", islem_tipi, mesaj, detay or {})
    
    def _kaydet(self, seviye: str, islem_tipi: str, mesaj: str, detay: Dict):
        kayit = LogKaydi(
            timestamp=self._timestamp(),
            islem_tipi=islem_tipi,
            seviye=seviye,
            mesaj=mesaj,
            detay=detay,
            oturum_id=self.oturum_id
        )
        self.kayitlar.append(kayit)
        
        # Konsola yazdır
        emoji = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}.get(seviye, "📋")
        print(f"[{kayit.timestamp}] {emoji} {mesaj}")
    
    # ==================== ÖZEL LOG METOTLARI ====================
    
    def eslestirme_basla(self, satis_urun: str, satis_fatura: str):
        """Eşleştirme işlemi başladığında"""
        self.bilgi(
            f"Eşleştirme başladı: '{satis_urun}'",
            {"satis_fatura": satis_fatura, "satis_urun": satis_urun},
            "eslestirme"
        )
    
    def eslestirme_adayi(self, alis_urun: str, benzerlik: float, kaynak: str):
        """Eşleştirme adayı bulunduğunda"""
        self.bilgi(
            f"Aday bulundu: '{alis_urun}' (%{benzerlik:.1f}) [{kaynak}]",
            {"alis_urun": alis_urun, "benzerlik": benzerlik, "kaynak": kaynak},
            "eslestirme"
        )
    
    def ai_sorgu(self, soru: str, yanit: str, cache_hit: bool):
        """AI sorgusu yapıldığında"""
        kaynak = "önbellek" if cache_hit else "API"
        self.bilgi(
            f"AI sorgusu [{kaynak}]: {soru[:50]}...",
            {"soru": soru, "yanit": yanit, "cache_hit": cache_hit},
            "ai_sorgu"
        )
    
    def ai_oneri(self, satis: str, alis: str, guven: float, oneri: str):
        """AI eşleştirme önerisi"""
        self.bilgi(
            f"AI önerisi: '{satis}' → '{alis}' (%{guven:.0f})",
            {"satis": satis, "alis": alis, "guven": guven, "aciklama": oneri},
            "ai_sorgu"
        )
    
    def kullanici_onayi(self, satis: str, alis: str, onaylandi: bool, kullanici: str = ""):
        """Kullanıcı onay/red işlemi"""
        durum = "ONAYLADI" if onaylandi else "REDDETTİ"
        self.bilgi(
            f"Kullanıcı {durum}: '{satis}' → '{alis}'",
            {"satis": satis, "alis": alis, "onaylandi": onaylandi, "kullanici": kullanici},
            "kullanici_onay"
        )
    
    def eslestirme_tamamlandi(self, satis: str, alis: str, yuklenilen_kdv: float):
        """Eşleştirme tamamlandığında"""
        self.bilgi(
            f"Eşleştirme kayıt: '{satis}' → '{alis}' | Yüklenilen: {yuklenilen_kdv:,.2f} TL",
            {"satis": satis, "alis": alis, "yuklenilen_kdv": yuklenilen_kdv},
            "eslestirme"
        )
    
    def ymm_kontrol(self, kontrol_adi: str, basarili: bool, mesaj: str):
        """YMM kontrol sonucu"""
        seviye = "INFO" if basarili else "ERROR"
        emoji = "✅" if basarili else "❌"
        self._kaydet(
            seviye, "kontrol",
            f"{emoji} {kontrol_adi}: {mesaj}",
            {"kontrol": kontrol_adi, "basarili": basarili}
        )
    
    # ==================== RAPOR ====================
    
    def ozet_rapor(self) -> Dict:
        """Oturum özet raporu"""
        toplam = len(self.kayitlar)
        seviyeler = {}
        islem_tipleri = {}
        
        for k in self.kayitlar:
            seviyeler[k.seviye] = seviyeler.get(k.seviye, 0) + 1
            islem_tipleri[k.islem_tipi] = islem_tipleri.get(k.islem_tipi, 0) + 1
        
        return {
            "oturum_id": self.oturum_id,
            "toplam_kayit": toplam,
            "seviyeler": seviyeler,
            "islem_tipleri": islem_tipleri,
            "baslangic": self.kayitlar[0].timestamp if self.kayitlar else "",
            "bitis": self.kayitlar[-1].timestamp if self.kayitlar else ""
        }
    
    def son_kayitlar(self, adet: int = 20) -> List[Dict]:
        """Son N kaydı döndür"""
        return [
            {
                "zaman": k.timestamp,
                "tip": k.islem_tipi,
                "seviye": k.seviye,
                "mesaj": k.mesaj
            }
            for k in self.kayitlar[-adet:]
        ]
    
    def dosyaya_kaydet(self, dosya_adi: str = None):
        """Logları JSON dosyasına kaydet"""
        if dosya_adi is None:
            dosya_adi = f"log_{self.oturum_id}.json"
        
        dosya_yolu = os.path.join(self.log_klasoru, dosya_adi)
        
        data = {
            "oturum_id": self.oturum_id,
            "olusturma": datetime.now().isoformat(),
            "kayitlar": [
                {
                    "timestamp": k.timestamp,
                    "islem_tipi": k.islem_tipi,
                    "seviye": k.seviye,
                    "mesaj": k.mesaj,
                    "detay": k.detay
                }
                for k in self.kayitlar
            ]
        }
        
        with open(dosya_yolu, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.bilgi(f"Log dosyası kaydedildi: {dosya_yolu}", {"dosya": dosya_yolu}, "sistem")
        return dosya_yolu
    
    def html_rapor(self) -> str:
        """HTML formatında log raporu"""
        rows = []
        for k in self.kayitlar:
            renk = {
                "INFO": "#e3f2fd",
                "WARNING": "#fff3e0",
                "ERROR": "#ffebee",
                "DEBUG": "#f3e5f5"
            }.get(k.seviye, "#ffffff")
            
            emoji = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}.get(k.seviye, "📋")
            
            rows.append(f"""
                <tr style="background: {renk}">
                    <td style="font-family: monospace; font-size: 11px;">{k.timestamp}</td>
                    <td>{emoji} {k.seviye}</td>
                    <td>{k.islem_tipi}</td>
                    <td>{k.mesaj}</td>
                </tr>
            """)
        
        return f"""
        <div style="font-family: Arial, sans-serif;">
            <h3>📋 İşlem Günlüğü (Oturum: {self.oturum_id})</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <thead>
                    <tr style="background: #2E74B5; color: white;">
                        <th style="padding: 8px; text-align: left;">Zaman</th>
                        <th style="padding: 8px; text-align: left;">Seviye</th>
                        <th style="padding: 8px; text-align: left;">Tip</th>
                        <th style="padding: 8px; text-align: left;">Mesaj</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
            <p style="color: #666; font-size: 11px; margin-top: 10px;">
                Toplam {len(self.kayitlar)} kayıt
            </p>
        </div>
        """


# Global log instance
_global_log: Optional[IslemGunlugu] = None


def get_log() -> IslemGunlugu:
    """Global log instance döndür"""
    global _global_log
    if _global_log is None:
        _global_log = IslemGunlugu()
    return _global_log


def reset_log():
    """Global log'u sıfırla"""
    global _global_log
    _global_log = IslemGunlugu()


# ==================== TEST ====================

if __name__ == "__main__":
    print("=== İşlem Günlüğü Test ===\n")
    
    log = IslemGunlugu()
    
    # Test logları
    log.eslestirme_basla("LAPTOP ASUS X515", "SAT2025001")
    log.eslestirme_adayi("LAPTOP ASUS X515JA", 92.5, "fuzzy")
    log.ai_sorgu("Bu iki ürün aynı mı?", "Evet, aynı model laptop.", False)
    log.ai_oneri("LAPTOP ASUS", "ASUS LAPTOP", 88, "Aynı ürün görünüyor")
    log.kullanici_onayi("LAPTOP ASUS", "ASUS LAPTOP", True, "ymm_user")
    log.eslestirme_tamamlandi("LAPTOP ASUS", "ASUS LAPTOP", 3200.00)
    log.ymm_kontrol("Mükerrerlik", True, "Mükerrer yüklenme yok")
    log.ymm_kontrol("Azami İade", False, "Azami iade tutarı aşıldı!")
    
    print("\n" + "="*60)
    print("ÖZET RAPOR:")
    print(json.dumps(log.ozet_rapor(), indent=2, ensure_ascii=False))
    
    # HTML rapor test
    print("\n✅ Test tamamlandı!")
