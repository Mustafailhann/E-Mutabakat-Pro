# -*- coding: utf-8 -*-
"""
İhraç Kayıtlı Teslim Modülü
KDV Kanunu 11/1-c - Tecil-Terkin Sistemi

İhraç kayıtlı satışlarda:
- Satıcı KDV hesaplar ama ödemez (tecil)
- 1 ay içinde ihracat yapılırsa terkin
- Yapılmazsa gecikme zammı ile ödenir
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json
import os


@dataclass
class IhracKayitliSatis:
    """İhraç kayıtlı satış kaydı"""
    id: str
    
    # Fatura bilgileri
    fatura_no: str
    fatura_tarihi: str
    
    # Satıcı (bizim mükellef)
    satici_vkn: str
    satici_unvan: str
    
    # Alıcı (ihracatçı)
    alici_vkn: str
    alici_unvan: str
    
    # Tutar bilgileri
    kdv_haric_tutar: float
    kdv_orani: float
    kdv_tutari: float  # Tecil edilen KDV
    
    # Mal bilgileri
    mal_cinsi: str
    miktar: float
    birim: str
    
    # İhracat durumu
    ihracat_durumu: str = "bekliyor"  # "bekliyor", "tamamlandi", "iptal", "gecikti"
    ihracat_tarihi: str = ""
    gcb_no: str = ""
    gcb_tarihi: str = ""
    
    # Süre kontrolü
    son_ihracat_tarihi: str = ""  # Fatura tarihinden 1 ay sonra
    kalan_gun: int = 0
    
    # Terkin durumu
    terkin_durumu: str = "bekliyor"  # "bekliyor", "terkin", "odendi"
    terkin_tarihi: str = ""
    
    def hesapla_son_tarih(self):
        """Son ihracat tarihini hesapla (fatura tarihinden 1 ay sonra)"""
        try:
            fatura_dt = datetime.strptime(self.fatura_tarihi, "%d.%m.%Y")
        except:
            try:
                fatura_dt = datetime.strptime(self.fatura_tarihi, "%Y-%m-%d")
            except:
                return
        
        # 1 ay sonra
        son_tarih = fatura_dt + timedelta(days=30)
        self.son_ihracat_tarihi = son_tarih.strftime("%d.%m.%Y")
        
        # Kalan gün
        bugun = datetime.now()
        if son_tarih > bugun:
            self.kalan_gun = (son_tarih - bugun).days
        else:
            self.kalan_gun = -(bugun - son_tarih).days  # Negatif = gecikmiş


@dataclass
class TecilTerkinOzet:
    """Dönem tecil-terkin özeti"""
    donem: str
    toplam_satis: int = 0
    toplam_kdv: float = 0.0
    bekleyen_satis: int = 0
    bekleyen_kdv: float = 0.0
    tamamlanan_satis: int = 0
    terkin_kdv: float = 0.0
    geciken_satis: int = 0
    geciken_kdv: float = 0.0
    kritik_uyarilar: List[str] = field(default_factory=list)


class IhracKayitliYonetici:
    """
    İhraç Kayıtlı Satış Yöneticisi
    
    KDV Kanunu 11/1-c gereği:
    - Satıcı ihraç kayıtlı fatura keser
    - KDV tecil edilir (1 ay için)
    - İhracat yapılırsa terkin
    - Yapılmazsa gecikme zammı ile ödeme
    """
    
    def __init__(self, veri_klasoru: str = "data"):
        self.veri_klasoru = veri_klasoru
        self.satislar: List[IhracKayitliSatis] = []
        self._yukle()
    
    def _yukle(self):
        """Verileri yükle"""
        dosya = os.path.join(self.veri_klasoru, "ihrac_kayitli_satislar.json")
        if os.path.exists(dosya):
            try:
                with open(dosya, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for s in data:
                        satis = IhracKayitliSatis(**s)
                        satis.hesapla_son_tarih()
                        self.satislar.append(satis)
            except:
                pass
    
    def _kaydet(self):
        """Verileri kaydet"""
        os.makedirs(self.veri_klasoru, exist_ok=True)
        dosya = os.path.join(self.veri_klasoru, "ihrac_kayitli_satislar.json")
        with open(dosya, 'w', encoding='utf-8') as f:
            data = []
            for s in self.satislar:
                data.append({
                    'id': s.id,
                    'fatura_no': s.fatura_no,
                    'fatura_tarihi': s.fatura_tarihi,
                    'satici_vkn': s.satici_vkn,
                    'satici_unvan': s.satici_unvan,
                    'alici_vkn': s.alici_vkn,
                    'alici_unvan': s.alici_unvan,
                    'kdv_haric_tutar': s.kdv_haric_tutar,
                    'kdv_orani': s.kdv_orani,
                    'kdv_tutari': s.kdv_tutari,
                    'mal_cinsi': s.mal_cinsi,
                    'miktar': s.miktar,
                    'birim': s.birim,
                    'ihracat_durumu': s.ihracat_durumu,
                    'ihracat_tarihi': s.ihracat_tarihi,
                    'gcb_no': s.gcb_no,
                    'gcb_tarihi': s.gcb_tarihi,
                    'son_ihracat_tarihi': s.son_ihracat_tarihi,
                    'kalan_gun': s.kalan_gun,
                    'terkin_durumu': s.terkin_durumu,
                    'terkin_tarihi': s.terkin_tarihi
                })
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def satis_ekle(self, satis: IhracKayitliSatis) -> str:
        """Yeni ihraç kayıtlı satış ekle"""
        satis.hesapla_son_tarih()
        self.satislar.append(satis)
        self._kaydet()
        return satis.id
    
    def ihracat_tamamla(
        self, 
        satis_id: str, 
        gcb_no: str, 
        gcb_tarihi: str
    ) -> bool:
        """İhracatı tamamla ve terkin işlemini başlat"""
        for s in self.satislar:
            if s.id == satis_id:
                s.ihracat_durumu = "tamamlandi"
                s.gcb_no = gcb_no
                s.gcb_tarihi = gcb_tarihi
                s.ihracat_tarihi = gcb_tarihi
                s.terkin_durumu = "terkin"
                s.terkin_tarihi = datetime.now().strftime("%d.%m.%Y")
                self._kaydet()
                return True
        return False
    
    def gecikme_kontrol(self) -> List[IhracKayitliSatis]:
        """Süresi geçmiş satışları bul"""
        geciken = []
        bugun = datetime.now()
        
        for s in self.satislar:
            if s.ihracat_durumu == "bekliyor" and s.son_ihracat_tarihi:
                try:
                    son_tarih = datetime.strptime(s.son_ihracat_tarihi, "%d.%m.%Y")
                    if bugun > son_tarih:
                        s.ihracat_durumu = "gecikti"
                        s.kalan_gun = -(bugun - son_tarih).days
                        geciken.append(s)
                except:
                    pass
        
        if geciken:
            self._kaydet()
        
        return geciken
    
    def donem_ozeti(self, donem: str = None) -> TecilTerkinOzet:
        """Dönem bazlı tecil-terkin özeti"""
        if donem is None:
            donem = datetime.now().strftime("%Y-%m")
        
        ozet = TecilTerkinOzet(donem=donem)
        
        for s in self.satislar:
            # Dönem kontrolü
            try:
                fatura_dt = datetime.strptime(s.fatura_tarihi, "%d.%m.%Y")
                fatura_donem = fatura_dt.strftime("%Y-%m")
            except:
                try:
                    fatura_dt = datetime.strptime(s.fatura_tarihi, "%Y-%m-%d")
                    fatura_donem = fatura_dt.strftime("%Y-%m")
                except:
                    continue
            
            if fatura_donem != donem:
                continue
            
            ozet.toplam_satis += 1
            ozet.toplam_kdv += s.kdv_tutari
            
            if s.ihracat_durumu == "bekliyor":
                ozet.bekleyen_satis += 1
                ozet.bekleyen_kdv += s.kdv_tutari
                
                if s.kalan_gun <= 7 and s.kalan_gun > 0:
                    ozet.kritik_uyarilar.append(
                        f"⚠️ {s.fatura_no}: {s.kalan_gun} gün kaldı!"
                    )
            
            elif s.ihracat_durumu == "tamamlandi":
                ozet.tamamlanan_satis += 1
                ozet.terkin_kdv += s.kdv_tutari
            
            elif s.ihracat_durumu == "gecikti":
                ozet.geciken_satis += 1
                ozet.geciken_kdv += s.kdv_tutari
                ozet.kritik_uyarilar.append(
                    f"❌ {s.fatura_no}: {abs(s.kalan_gun)} gün gecikti!"
                )
        
        return ozet
    
    def rapor(self, donem: str = None) -> Dict:
        """Detaylı rapor oluştur"""
        ozet = self.donem_ozeti(donem)
        
        return {
            "donem": ozet.donem,
            "tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
            
            "ozet": {
                "toplam_satis": ozet.toplam_satis,
                "toplam_kdv": round(ozet.toplam_kdv, 2),
                "bekleyen_satis": ozet.bekleyen_satis,
                "bekleyen_kdv": round(ozet.bekleyen_kdv, 2),
                "tamamlanan_satis": ozet.tamamlanan_satis,
                "terkin_kdv": round(ozet.terkin_kdv, 2),
                "geciken_satis": ozet.geciken_satis,
                "geciken_kdv": round(ozet.geciken_kdv, 2)
            },
            
            "kritik_uyarilar": ozet.kritik_uyarilar,
            
            "satislar": [
                {
                    "id": s.id,
                    "fatura_no": s.fatura_no,
                    "fatura_tarihi": s.fatura_tarihi,
                    "alici": s.alici_unvan,
                    "tutar": s.kdv_haric_tutar,
                    "kdv": s.kdv_tutari,
                    "durum": s.ihracat_durumu,
                    "kalan_gun": s.kalan_gun,
                    "gcb_no": s.gcb_no
                }
                for s in self.satislar
            ]
        }


# ==================== TEST ====================

if __name__ == "__main__":
    print("=== İhraç Kayıtlı Teslim Test ===\n")
    
    yonetici = IhracKayitliYonetici(veri_klasoru="data/test_ihrac_kayitli")
    
    # Test satış ekle
    from uuid import uuid4
    
    satis = IhracKayitliSatis(
        id=str(uuid4())[:8].upper(),
        fatura_no="IKT2025000001",
        fatura_tarihi="01.01.2025",
        satici_vkn="1234567890",
        satici_unvan="TEST İMALATÇI LTD.ŞTİ.",
        alici_vkn="9876543210",
        alici_unvan="TEST İHRACATÇI A.Ş.",
        kdv_haric_tutar=100000,
        kdv_orani=20,
        kdv_tutari=20000,
        mal_cinsi="Tekstil Ürünleri",
        miktar=1000,
        birim="AD"
    )
    
    yonetici.satis_ekle(satis)
    
    # Özet
    ozet = yonetici.donem_ozeti("2025-01")
    print(f"Dönem: {ozet.donem}")
    print(f"Toplam Satış: {ozet.toplam_satis}")
    print(f"Toplam Tecil KDV: {ozet.toplam_kdv:,.2f} TL")
    print(f"Bekleyen: {ozet.bekleyen_satis}")
    print(f"Geciken: {ozet.geciken_satis}")
    
    print("\n✅ Test tamamlandı!")
