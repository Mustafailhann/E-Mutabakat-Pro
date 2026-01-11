# -*- coding: utf-8 -*-
"""
Birim Dönüşüm Modülü
Farklı birimleri birbirine dönüştür (ADET ↔ KOLİ, KG ↔ TON vb.)
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import json
import os


@dataclass
class BirimDonusum:
    """Birim dönüşüm kuralı"""
    kaynak_birim: str
    hedef_birim: str
    carpan: float  # 1 kaynak = X hedef
    aciklama: str = ""


class BirimDonusturucu:
    """
    Birim Dönüştürücü
    
    Örnek:
        1 KOLİ = 12 ADET
        1 TON = 1000 KG
        1 KG = 1000 GR
    """
    
    # Varsayılan dönüşümler (sistem tanımlı)
    VARSAYILAN_DONUSUMLER = {
        # Ağırlık
        ("KG", "GR"): 1000,
        ("TON", "KG"): 1000,
        ("TON", "GR"): 1000000,
        
        # Uzunluk
        ("MT", "CM"): 100,
        ("MT", "MM"): 1000,
        ("KM", "MT"): 1000,
        
        # Alan
        ("M2", "CM2"): 10000,
        
        # Hacim
        ("LT", "ML"): 1000,
        ("M3", "LT"): 1000,
        
        # Zaman
        ("SAAT", "DAK"): 60,
        ("DAK", "SN"): 60,
    }
    
    # Birim kod eşleştirmesi (normalize)
    BIRIM_ESLESTIRME = {
        "AD": "ADET", "PCS": "ADET", "PC": "ADET",
        "KL": "KOLI", "BOX": "KOLI", "BX": "KOLI",
        "KGM": "KG", "KILOGRAM": "KG",
        "LTR": "LT", "LITRE": "LT",
        "MTR": "MT", "METRE": "MT", "M": "MT",
        "MTK": "M2", "METREKARE": "M2",
        "TNE": "TON", "T": "TON",
        "PKT": "PAKET", "PK": "PAKET",
        "ST": "SET", "TAKIM": "SET",
    }
    
    def __init__(self, veri_klasoru: str = "data"):
        self.veri_klasoru = veri_klasoru
        self.ozel_donusumler: Dict[Tuple[str, str], BirimDonusum] = {}
        self._yukle()
    
    def _yukle(self):
        """Özel dönüşümleri yükle"""
        dosya = os.path.join(self.veri_klasoru, "birim_donusumleri.json")
        if os.path.exists(dosya):
            try:
                with open(dosya, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for d in data:
                        key = (d['kaynak_birim'], d['hedef_birim'])
                        self.ozel_donusumler[key] = BirimDonusum(**d)
            except:
                pass
    
    def _kaydet(self):
        """Özel dönüşümleri kaydet"""
        os.makedirs(self.veri_klasoru, exist_ok=True)
        dosya = os.path.join(self.veri_klasoru, "birim_donusumleri.json")
        with open(dosya, 'w', encoding='utf-8') as f:
            data = [
                {
                    'kaynak_birim': d.kaynak_birim,
                    'hedef_birim': d.hedef_birim,
                    'carpan': d.carpan,
                    'aciklama': d.aciklama
                }
                for d in self.ozel_donusumler.values()
            ]
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def normalize_birim(self, birim: str) -> str:
        """Birim kodunu normalize et"""
        birim = birim.upper().strip()
        return self.BIRIM_ESLESTIRME.get(birim, birim)
    
    def donusum_ekle(
        self, 
        kaynak: str, 
        hedef: str, 
        carpan: float,
        aciklama: str = ""
    ):
        """
        Özel birim dönüşümü ekle
        
        Örnek: 
            donusum_ekle("KOLI", "ADET", 12, "1 koli = 12 adet")
        """
        kaynak = self.normalize_birim(kaynak)
        hedef = self.normalize_birim(hedef)
        
        donusum = BirimDonusum(
            kaynak_birim=kaynak,
            hedef_birim=hedef,
            carpan=carpan,
            aciklama=aciklama
        )
        
        self.ozel_donusumler[(kaynak, hedef)] = donusum
        
        # Ters dönüşümü de ekle
        ters = BirimDonusum(
            kaynak_birim=hedef,
            hedef_birim=kaynak,
            carpan=1 / carpan,
            aciklama=f"Ters: {aciklama}"
        )
        self.ozel_donusumler[(hedef, kaynak)] = ters
        
        self._kaydet()
    
    def donustur(
        self, 
        miktar: float, 
        kaynak_birim: str, 
        hedef_birim: str
    ) -> Optional[Tuple[float, str]]:
        """
        Miktarı bir birimden diğerine dönüştür
        
        Returns:
            (dönüştürülmüş miktar, açıklama) veya None
        """
        kaynak = self.normalize_birim(kaynak_birim)
        hedef = self.normalize_birim(hedef_birim)
        
        # Aynı birimse dönüşüm gerekli değil
        if kaynak == hedef:
            return (miktar, "Aynı birim")
        
        # Önce özel dönüşümlere bak
        if (kaynak, hedef) in self.ozel_donusumler:
            d = self.ozel_donusumler[(kaynak, hedef)]
            return (miktar * d.carpan, d.aciklama or f"1 {kaynak} = {d.carpan} {hedef}")
        
        # Varsayılan dönüşümlere bak
        if (kaynak, hedef) in self.VARSAYILAN_DONUSUMLER:
            carpan = self.VARSAYILAN_DONUSUMLER[(kaynak, hedef)]
            return (miktar * carpan, f"1 {kaynak} = {carpan} {hedef}")
        
        # Ters dönüşüm
        if (hedef, kaynak) in self.VARSAYILAN_DONUSUMLER:
            carpan = 1 / self.VARSAYILAN_DONUSUMLER[(hedef, kaynak)]
            return (miktar * carpan, f"1 {kaynak} = {carpan} {hedef}")
        
        # Dönüşüm bulunamadı
        return None
    
    def uyumlu_mu(
        self, 
        miktar1: float, 
        birim1: str, 
        miktar2: float, 
        birim2: str,
        tolerans_yuzde: float = 5
    ) -> Tuple[bool, str]:
        """
        İki miktar/birim çifti uyumlu mu kontrol et
        
        Returns:
            (uyumlu_mu, açıklama)
        """
        birim1 = self.normalize_birim(birim1)
        birim2 = self.normalize_birim(birim2)
        
        # Aynı birimse direkt karşılaştır
        if birim1 == birim2:
            fark = abs(miktar1 - miktar2) / max(miktar1, miktar2) * 100 if max(miktar1, miktar2) > 0 else 0
            uyumlu = fark <= tolerans_yuzde
            return (uyumlu, f"{miktar1} {birim1} vs {miktar2} {birim2} - Fark: %{fark:.1f}")
        
        # Dönüşüm dene
        donusum = self.donustur(miktar1, birim1, birim2)
        
        if donusum:
            donusturulmus, aciklama = donusum
            fark = abs(donusturulmus - miktar2) / max(donusturulmus, miktar2) * 100 if max(donusturulmus, miktar2) > 0 else 0
            uyumlu = fark <= tolerans_yuzde
            return (uyumlu, f"{miktar1} {birim1} = {donusturulmus} {birim2} vs {miktar2} {birim2} - Fark: %{fark:.1f}")
        
        # Dönüşüm bulunamadı
        return (False, f"Birim dönüşümü bulunamadı: {birim1} → {birim2}")
    
    def listele(self) -> Dict:
        """Tüm dönüşümleri listele"""
        return {
            "varsayilan": {
                f"{k[0]} → {k[1]}": v 
                for k, v in self.VARSAYILAN_DONUSUMLER.items()
            },
            "ozel": {
                f"{k[0]} → {k[1]}": {
                    "carpan": d.carpan,
                    "aciklama": d.aciklama
                }
                for k, d in self.ozel_donusumler.items()
            }
        }


# ==================== TEST ====================

if __name__ == "__main__":
    print("=== Birim Dönüşüm Test ===\n")
    
    donusturucu = BirimDonusturucu(veri_klasoru="data/test_birim")
    
    # Özel dönüşüm ekle
    donusturucu.donusum_ekle("KOLI", "ADET", 12, "Standart koli = 12 adet")
    donusturucu.donusum_ekle("PALET", "KOLI", 80, "1 palet = 80 koli")
    
    # Test: Dönüştürme
    testler = [
        (100, "KG", "TON"),
        (5, "KOLI", "ADET"),
        (960, "ADET", "KOLI"),
        (2000, "GRAM", "KG"),  # Bilinmiyor
    ]
    
    print("Dönüştürme Testleri:")
    print("-" * 50)
    for miktar, kaynak, hedef in testler:
        sonuc = donusturucu.donustur(miktar, kaynak, hedef)
        if sonuc:
            print(f"  {miktar} {kaynak} = {sonuc[0]} {hedef} ({sonuc[1]})")
        else:
            print(f"  {miktar} {kaynak} → {hedef}: Dönüşüm bulunamadı")
    
    # Test: Uyumluluk
    print("\nUyumluluk Testleri:")
    print("-" * 50)
    
    uyum_testleri = [
        (10, "KOLI", 120, "ADET"),
        (10, "KOLI", 100, "ADET"),  # Uyumsuz
        (5, "KG", 5000, "GR"),
    ]
    
    for m1, b1, m2, b2 in uyum_testleri:
        uyumlu, aciklama = donusturucu.uyumlu_mu(m1, b1, m2, b2)
        emoji = "✅" if uyumlu else "❌"
        print(f"  {emoji} {m1} {b1} vs {m2} {b2}: {aciklama}")
    
    print("\n✅ Test tamamlandı!")
