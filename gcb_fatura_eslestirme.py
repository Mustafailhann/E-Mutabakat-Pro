# -*- coding: utf-8 -*-
"""
GÇB-Fatura Eşleştirme Modülü
Gümrük Çıkış Beyannameleri ile Satış Faturalarını Eşleştir

İhracat KDV iadesi için zorunlu kontrol:
- GÇB tutarı ile fatura tutarı uyumu
- GÇB tarihi ile fatura tarihi uyumu
- Eksik/fazla GÇB tespiti
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json
import os
import re


@dataclass
class GumrukBeyannamesi:
    """Gümrük Çıkış Beyannamesi"""
    beyanname_no: str
    beyanname_tarihi: str
    tescil_tarihi: str
    cikis_tarihi: str
    
    # Firma bilgileri
    ihracatci_vkn: str
    ihracatci_unvan: str
    
    # Tutar bilgileri
    fob_bedel: float
    doviz_cinsi: str
    kur: float
    tl_tutari: float
    
    # Fatura bilgileri (varsa)
    fatura_no: str = ""
    fatura_tarihi: str = ""
    
    # Ürün bilgileri
    gtip_kodu: str = ""
    urun_tanimi: str = ""
    miktar: float = 0.0
    birim: str = ""
    
    # Eşleştirme durumu
    eslestirildi: bool = False
    eslestirilen_faturalar: List[str] = field(default_factory=list)


@dataclass
class GCBEslestirmeSonucu:
    """GÇB-Fatura eşleştirme sonucu"""
    gcb_no: str
    gcb_tarihi: str
    gcb_tutari: float
    
    fatura_no: str
    fatura_tarihi: str
    fatura_tutari: float
    
    eslestirme_tipi: str  # "tam", "kismi", "tutar_uyumsuz", "manuel"
    tutar_farki: float
    tutar_farki_yuzde: float
    uyari: str = ""


class GCBFaturaEslestirici:
    """
    GÇB ve Satış Faturası Eşleştirici
    
    İhracat KDV iadesi kontrolü için:
    - Fatura numarasına göre otomatik eşleştirme
    - Tutar karşılaştırması
    - Tarih kontrolü
    - Eksik/fazla tespit
    """
    
    # Tolerans değerleri
    TUTAR_TOLERANS_TL = 100  # 100 TL'ye kadar fark kabul
    TUTAR_TOLERANS_YUZDE = 1  # %1'e kadar fark kabul
    
    def __init__(self, veri_klasoru: str = "data"):
        self.veri_klasoru = veri_klasoru
        self.gcbler: List[GumrukBeyannamesi] = []
        self.eslestirmeler: List[GCBEslestirmeSonucu] = []
        self._yukle()
    
    def _yukle(self):
        """Verileri yükle"""
        dosya = os.path.join(self.veri_klasoru, "gcb_verileri.json")
        if os.path.exists(dosya):
            try:
                with open(dosya, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for g in data:
                        self.gcbler.append(GumrukBeyannamesi(**g))
            except:
                pass
    
    def _kaydet(self):
        """Verileri kaydet"""
        os.makedirs(self.veri_klasoru, exist_ok=True)
        dosya = os.path.join(self.veri_klasoru, "gcb_verileri.json")
        with open(dosya, 'w', encoding='utf-8') as f:
            data = []
            for g in self.gcbler:
                data.append({
                    'beyanname_no': g.beyanname_no,
                    'beyanname_tarihi': g.beyanname_tarihi,
                    'tescil_tarihi': g.tescil_tarihi,
                    'cikis_tarihi': g.cikis_tarihi,
                    'ihracatci_vkn': g.ihracatci_vkn,
                    'ihracatci_unvan': g.ihracatci_unvan,
                    'fob_bedel': g.fob_bedel,
                    'doviz_cinsi': g.doviz_cinsi,
                    'kur': g.kur,
                    'tl_tutari': g.tl_tutari,
                    'fatura_no': g.fatura_no,
                    'fatura_tarihi': g.fatura_tarihi,
                    'gtip_kodu': g.gtip_kodu,
                    'urun_tanimi': g.urun_tanimi,
                    'miktar': g.miktar,
                    'birim': g.birim,
                    'eslestirildi': g.eslestirildi,
                    'eslestirilen_faturalar': g.eslestirilen_faturalar
                })
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def gcb_ekle(self, gcb: GumrukBeyannamesi):
        """GÇB ekle"""
        self.gcbler.append(gcb)
        self._kaydet()
    
    def gcb_listele(self) -> List[GumrukBeyannamesi]:
        """Tüm GÇB'leri listele"""
        return self.gcbler
    
    def eslestir(
        self, 
        satis_faturalari: List[Dict]
    ) -> Dict:
        """
        GÇB'leri satış faturalarıyla eşleştir
        
        Returns:
            {
                "eslestirilen": [...],
                "eslestirmeyen_gcb": [...],
                "eslestirmeyen_fatura": [...],
                "tutar_uyumsuz": [...],
                "ozet": {...}
            }
        """
        sonuc = {
            "eslestirilen": [],
            "eslestirmeyen_gcb": [],
            "eslestirmeyen_fatura": [],
            "tutar_uyumsuz": [],
            "ozet": {}
        }
        
        eslestirilen_faturalar = set()
        
        for gcb in self.gcbler:
            eslesme_bulundu = False
            
            for fatura in satis_faturalari:
                fatura_no = fatura.get('seri', '') + fatura.get('sira_no', '')
                
                # 1. GÇB içinde fatura numarası var mı?
                if gcb.fatura_no and self._fatura_no_esles(gcb.fatura_no, fatura_no):
                    eslesme = self._eslestirme_olustur(gcb, fatura)
                    sonuc["eslestirilen"].append(eslesme)
                    eslestirilen_faturalar.add(fatura_no)
                    gcb.eslestirildi = True
                    gcb.eslestirilen_faturalar.append(fatura_no)
                    eslesme_bulundu = True
                    
                    # Tutar kontrolü
                    if eslesme.tutar_farki_yuzde > self.TUTAR_TOLERANS_YUZDE:
                        sonuc["tutar_uyumsuz"].append(eslesme)
                    break
            
            # 2. Fatura numarası yoksa tutar ve tarih ile eşleştir
            if not eslesme_bulundu:
                for fatura in satis_faturalari:
                    fatura_no = fatura.get('seri', '') + fatura.get('sira_no', '')
                    if fatura_no in eslestirilen_faturalar:
                        continue
                    
                    fatura_tutari = float(fatura.get('kdv_haric_tutar', 0))
                    
                    # Tutar yakın mı?
                    if self._tutar_yakin_mi(gcb.tl_tutari, fatura_tutari):
                        # Tarih uygun mu?
                        if self._tarih_uygun_mu(gcb.beyanname_tarihi, fatura.get('tarih', '')):
                            eslesme = self._eslestirme_olustur(gcb, fatura)
                            eslesme.eslestirme_tipi = "tutar_tarih"
                            sonuc["eslestirilen"].append(eslesme)
                            eslestirilen_faturalar.add(fatura_no)
                            gcb.eslestirildi = True
                            gcb.eslestirilen_faturalar.append(fatura_no)
                            eslesme_bulundu = True
                            break
            
            if not eslesme_bulundu:
                sonuc["eslestirmeyen_gcb"].append({
                    "gcb_no": gcb.beyanname_no,
                    "gcb_tarihi": gcb.beyanname_tarihi,
                    "gcb_tutari": gcb.tl_tutari,
                    "mesaj": "Eşleşen satış faturası bulunamadı"
                })
        
        # Eşleşmeyen faturaları bul
        for fatura in satis_faturalari:
            fatura_no = fatura.get('seri', '') + fatura.get('sira_no', '')
            if fatura_no not in eslestirilen_faturalar:
                # Sadece ihracat faturalarını kontrol et
                alici_ulke = fatura.get('alici_ulke', 'TR')
                if alici_ulke != 'TR':
                    sonuc["eslestirmeyen_fatura"].append({
                        "fatura_no": fatura_no,
                        "fatura_tarihi": fatura.get('tarih', ''),
                        "fatura_tutari": fatura.get('kdv_haric_tutar', 0),
                        "mesaj": "GÇB bulunamadı"
                    })
        
        # Özet
        toplam_gcb = len(self.gcbler)
        eslestirilen = len(sonuc["eslestirilen"])
        
        sonuc["ozet"] = {
            "toplam_gcb": toplam_gcb,
            "eslestirilen": eslestirilen,
            "eslestirmeyen_gcb": len(sonuc["eslestirmeyen_gcb"]),
            "eslestirmeyen_fatura": len(sonuc["eslestirmeyen_fatura"]),
            "tutar_uyumsuz": len(sonuc["tutar_uyumsuz"]),
            "basari_orani": round(eslestirilen / toplam_gcb * 100, 1) if toplam_gcb > 0 else 0
        }
        
        self._kaydet()
        return sonuc
    
    def _fatura_no_esles(self, gcb_fatura: str, fatura_no: str) -> bool:
        """Fatura numaralarını karşılaştır"""
        # Normalize et
        g = re.sub(r'[^A-Z0-9]', '', gcb_fatura.upper())
        f = re.sub(r'[^A-Z0-9]', '', fatura_no.upper())
        
        return g == f or g in f or f in g
    
    def _tutar_yakin_mi(self, gcb_tutar: float, fatura_tutar: float) -> bool:
        """Tutarlar yakın mı kontrol et"""
        if gcb_tutar == 0 or fatura_tutar == 0:
            return False
        
        fark = abs(gcb_tutar - fatura_tutar)
        
        # Mutlak tolerans
        if fark <= self.TUTAR_TOLERANS_TL:
            return True
        
        # Yüzde tolerans
        yuzde = fark / max(gcb_tutar, fatura_tutar) * 100
        return yuzde <= self.TUTAR_TOLERANS_YUZDE
    
    def _tarih_uygun_mu(self, gcb_tarihi: str, fatura_tarihi: str) -> bool:
        """GÇB tarihi fatura tarihinden sonra veya aynı mı"""
        try:
            gcb_dt = self._parse_tarih(gcb_tarihi)
            fatura_dt = self._parse_tarih(fatura_tarihi)
            
            if gcb_dt and fatura_dt:
                # GÇB, faturadan önce olamaz (max 30 gün erken olabilir)
                from datetime import timedelta
                return gcb_dt >= fatura_dt - timedelta(days=30)
        except:
            pass
        
        return True  # Tarih parse edilemezse kabul et
    
    def _parse_tarih(self, tarih_str: str) -> Optional[datetime]:
        """Tarih parse et"""
        if not tarih_str:
            return None
        
        for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                return datetime.strptime(tarih_str, fmt)
            except:
                continue
        return None
    
    def _eslestirme_olustur(self, gcb: GumrukBeyannamesi, fatura: Dict) -> GCBEslestirmeSonucu:
        """Eşleştirme sonucu oluştur"""
        fatura_tutari = float(fatura.get('kdv_haric_tutar', 0))
        tutar_farki = abs(gcb.tl_tutari - fatura_tutari)
        tutar_farki_yuzde = tutar_farki / max(gcb.tl_tutari, fatura_tutari) * 100 if max(gcb.tl_tutari, fatura_tutari) > 0 else 0
        
        uyari = ""
        if tutar_farki_yuzde > self.TUTAR_TOLERANS_YUZDE:
            uyari = f"⚠️ Tutar farkı: {tutar_farki:,.2f} TL ({tutar_farki_yuzde:.1f}%)"
        
        return GCBEslestirmeSonucu(
            gcb_no=gcb.beyanname_no,
            gcb_tarihi=gcb.beyanname_tarihi,
            gcb_tutari=gcb.tl_tutari,
            fatura_no=fatura.get('seri', '') + fatura.get('sira_no', ''),
            fatura_tarihi=fatura.get('tarih', ''),
            fatura_tutari=fatura_tutari,
            eslestirme_tipi="tam" if tutar_farki_yuzde <= self.TUTAR_TOLERANS_YUZDE else "tutar_uyumsuz",
            tutar_farki=tutar_farki,
            tutar_farki_yuzde=round(tutar_farki_yuzde, 2),
            uyari=uyari
        )
    
    def rapor(self, eslestirme_sonucu: Dict) -> str:
        """Eşleştirme raporu oluştur"""
        ozet = eslestirme_sonucu.get("ozet", {})
        
        rapor = f"""
╔════════════════════════════════════════════════════════════╗
║           GÇB - FATURA EŞLEŞTİRME RAPORU                   ║
╠════════════════════════════════════════════════════════════╣
║  Toplam GÇB:           {ozet.get('toplam_gcb', 0):>5}                              ║
║  Eşleştirilen:         {ozet.get('eslestirilen', 0):>5}  ✅                         ║
║  Eşleşmeyen GÇB:       {ozet.get('eslestirmeyen_gcb', 0):>5}  ❌                         ║
║  Eşleşmeyen Fatura:    {ozet.get('eslestirmeyen_fatura', 0):>5}  ⚠️                          ║
║  Tutar Uyumsuz:        {ozet.get('tutar_uyumsuz', 0):>5}  ⚠️                          ║
╠════════════════════════════════════════════════════════════╣
║  Başarı Oranı:         {ozet.get('basari_orani', 0):>5.1f}%                           ║
╚════════════════════════════════════════════════════════════╝
"""
        return rapor


# ==================== TEST ====================

if __name__ == "__main__":
    print("=== GÇB-Fatura Eşleştirme Test ===\n")
    
    eslestirici = GCBFaturaEslestirici(veri_klasoru="data/test_gcb")
    
    # Test GÇB
    gcb1 = GumrukBeyannamesi(
        beyanname_no="25060TR00001234",
        beyanname_tarihi="15.01.2025",
        tescil_tarihi="14.01.2025",
        cikis_tarihi="16.01.2025",
        ihracatci_vkn="1234567890",
        ihracatci_unvan="TEST İHRACAT A.Ş.",
        fob_bedel=10000,
        doviz_cinsi="USD",
        kur=32.5,
        tl_tutari=325000,
        fatura_no="ABC2025000001"
    )
    eslestirici.gcb_ekle(gcb1)
    
    # Test faturalar
    faturalar = [
        {
            "seri": "ABC",
            "sira_no": "2025000001",
            "tarih": "10.01.2025",
            "kdv_haric_tutar": 325000,
            "alici_ulke": "DE"
        },
        {
            "seri": "ABC",
            "sira_no": "2025000002",
            "tarih": "12.01.2025",
            "kdv_haric_tutar": 150000,
            "alici_ulke": "FR"
        }
    ]
    
    sonuc = eslestirici.eslestir(faturalar)
    
    print(eslestirici.rapor(sonuc))
    
    print("\n✅ Test tamamlandı!")
