# -*- coding: utf-8 -*-
"""
Ürün Eşleştirme Modülü
Satış faturası kalemleri ile alış faturası kalemlerini eşleştirme
1 nolu yüklenilen KDV hesaplaması için temel modül

Özellikler:
- Fuzzy matching ile benzerlik hesaplama
- AI destekli akıllı eşleştirme
- İşlem günlüğü ile tam şeffaflık
- YMM mevzuat kontrolleri
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
import json
import os
from datetime import datetime

# AI ve Log entegrasyonu
try:
    from ai_advisor import AIAdvisor
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

try:
    from islem_gunlugu import get_log, IslemGunlugu
    LOG_AVAILABLE = True
except ImportError:
    LOG_AVAILABLE = False


# ==================== VERİ MODELLERİ ====================

@dataclass
class FaturaKalemi:
    """Fatura kalemi (satış veya alış)"""
    fatura_no: str
    fatura_tarihi: str
    kalem_sira: int
    urun_kodu: str
    urun_adi: str
    miktar: float
    birim: str
    birim_fiyat: float
    tutar: float  # KDV hariç
    kdv_orani: float
    kdv_tutari: float
    firma_unvan: str = ""
    firma_vkn: str = ""
    fatura_tipi: str = "alis"  # "alis" veya "satis"
    
    @property
    def toplam(self) -> float:
        return self.tutar + self.kdv_tutari


@dataclass
class Eslestirme:
    """Satış-Alış kalem eşleştirmesi"""
    satis_kalemi: FaturaKalemi
    alis_kalemi: FaturaKalemi
    eslestirme_tipi: str  # "otomatik", "benzerlik", "manuel"
    benzerlik_orani: float  # 0-100
    eslestirme_tarihi: str = ""
    kullanici_onayi: bool = False
    
    def __post_init__(self):
        if not self.eslestirme_tarihi:
            self.eslestirme_tarihi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class EslestirmeSonuc:
    """Eşleştirme sonucu - yüklenilen KDV hesabı için"""
    satis_fatura_no: str
    satis_kalemi: str
    yuklenilen_kdv: float
    alis_faturalari: List[Dict]  # Eşleşen alış faturaları detayı
    eslestirme_durumu: str  # "tam", "kismi", "eslesmedi"


# ==================== BENZERLİK HESAPLAMA ====================

class UrunEslestirici:
    """Ürün adı benzerliği ile eşleştirme"""
    
    # Yaygın birim dönüşümleri
    BIRIM_ESDEĞERLERI = {
        "ADET": ["AD", "ADET", "PCS", "PC"],
        "KOLİ": ["KL", "KOLİ", "KOLI", "BOX", "BX"],
        "KİLOGRAM": ["KG", "KGM", "KILOGRAM"],
        "LİTRE": ["LT", "LTR", "LITRE"],
        "METRE": ["MT", "MTR", "METRE", "M"],
        "METREKARE": ["M2", "MTK", "METREKARE"],
        "TON": ["TON", "TNE", "T"],
        "PAKET": ["PK", "PKT", "PAKET"],
        "SET": ["SET", "ST", "TAKIM"],
    }
    
    # Benzerlik eşikleri
    ESIK_TAM_ESLESME = 95  # %95+ = otomatik eşleştir
    ESIK_BENZERLIK = 70    # %70+ = kullanıcıya sor
    ESIK_MINIMUM = 50      # %50 altı = eşleşme yok
    
    def __init__(self, veri_klasoru: str = "data", ai_api_key: str = None):
        self.veri_klasoru = veri_klasoru
        self.eslestirmeler: List[Eslestirme] = []
        self.eslestirme_gecmisi: Dict[str, str] = {}  # urun_adi -> eslestirilmis_urun
        
        # AI desteği
        self.ai: Optional[AIAdvisor] = None
        if AI_AVAILABLE:
            self.ai = AIAdvisor(ai_api_key)
        
        # İşlem günlüğü
        self.log: Optional[IslemGunlugu] = None
        if LOG_AVAILABLE:
            self.log = get_log()
        
        self._yukle()
    
    def _log(self, mesaj: str, detay: Dict = None, seviye: str = "bilgi"):
        """Güvenli loglama"""
        if self.log:
            if seviye == "bilgi":
                self.log.bilgi(mesaj, detay, "eslestirme")
            elif seviye == "uyari":
                self.log.uyari(mesaj, detay, "eslestirme")
            elif seviye == "hata":
                self.log.hata(mesaj, detay, "eslestirme")
    
    def _yukle(self):
        """Önceki eşleştirmeleri yükle"""
        dosya = os.path.join(self.veri_klasoru, "eslestirme_gecmisi.json")
        if os.path.exists(dosya):
            try:
                with open(dosya, 'r', encoding='utf-8') as f:
                    self.eslestirme_gecmisi = json.load(f)
            except:
                pass
    
    def _kaydet(self):
        """Eşleştirme geçmişini kaydet"""
        os.makedirs(self.veri_klasoru, exist_ok=True)
        dosya = os.path.join(self.veri_klasoru, "eslestirme_gecmisi.json")
        with open(dosya, 'w', encoding='utf-8') as f:
            json.dump(self.eslestirme_gecmisi, f, ensure_ascii=False, indent=2)
    
    def benzerlik_hesapla(self, metin1: str, metin2: str) -> float:
        """
        İki metin arasındaki benzerlik oranını hesapla (0-100)
        """
        if not metin1 or not metin2:
            return 0.0
        
        # Normalize et
        m1 = metin1.upper().strip()
        m2 = metin2.upper().strip()
        
        # Birebir eşleşme
        if m1 == m2:
            return 100.0
        
        # Birisi diğerini içeriyor mu?
        if m1 in m2 or m2 in m1:
            return 85.0
        
        # SequenceMatcher ile benzerlik
        ratio = SequenceMatcher(None, m1, m2).ratio() * 100
        
        return round(ratio, 2)
    
    def birim_uyumlu_mu(self, birim1: str, birim2: str) -> bool:
        """
        İki birim uyumlu mu kontrol et
        """
        b1 = birim1.upper().strip()
        b2 = birim2.upper().strip()
        
        if b1 == b2:
            return True
        
        # Eşdeğer birimler
        for grup in self.BIRIM_ESDEĞERLERI.values():
            if b1 in grup and b2 in grup:
                return True
        
        return False
    
    def eslestirme_ara(
        self, 
        satis_kalemi: FaturaKalemi, 
        alis_kalemleri: List[FaturaKalemi]
    ) -> List[Tuple[FaturaKalemi, float, str]]:
        """
        Satış kalemi için eşleşebilecek alış kalemlerini bul
        
        Returns:
            List of (alis_kalemi, benzerlik_orani, eslestirme_tipi)
        """
        sonuclar = []
        
        # Önce geçmiş eşleştirmelere bak
        if satis_kalemi.urun_adi in self.eslestirme_gecmisi:
            eslestirilmis = self.eslestirme_gecmisi[satis_kalemi.urun_adi]
            for alis in alis_kalemleri:
                if alis.urun_adi == eslestirilmis:
                    sonuclar.append((alis, 100.0, "gecmis"))
        
        # Tüm alış kalemlerini tara
        for alis in alis_kalemleri:
            benzerlik = self.benzerlik_hesapla(satis_kalemi.urun_adi, alis.urun_adi)
            
            # Ürün kodu varsa ve eşleşiyorsa bonus
            if (satis_kalemi.urun_kodu and alis.urun_kodu and 
                satis_kalemi.urun_kodu.upper() == alis.urun_kodu.upper()):
                benzerlik = max(benzerlik, 95.0)
            
            # Minimum eşik kontrolü
            if benzerlik >= self.ESIK_MINIMUM:
                if benzerlik >= self.ESIK_TAM_ESLESME:
                    eslestirme_tipi = "otomatik"
                elif benzerlik >= self.ESIK_BENZERLIK:
                    eslestirme_tipi = "benzerlik"
                else:
                    eslestirme_tipi = "dusuk_benzerlik"
                
                sonuclar.append((alis, benzerlik, eslestirme_tipi))
        
        # Benzerliğe göre sırala
        sonuclar.sort(key=lambda x: x[1], reverse=True)
        
        # Loglama
        self._log(
            f"'{satis_kalemi.urun_adi}' için {len(sonuclar)} aday bulundu",
            {"satis": satis_kalemi.urun_adi, "aday_sayisi": len(sonuclar)}
        )
        
        return sonuclar
    
    def ai_eslestirme_kontrol(
        self, 
        satis_urun: str, 
        alis_urun: str
    ) -> Dict:
        """
        AI ile iki ürünün aynı olup olmadığını kontrol et
        
        Returns:
            {"is_match": bool, "confidence": float, "reason": str, "from_ai": bool}
        """
        if not self.ai:
            self._log("AI mevcut değil, yerel kontrol yapılacak", seviye="uyari")
            return {
                "is_match": None,
                "confidence": 0,
                "reason": "AI modülü yüklenmemiş",
                "from_ai": False
            }
        
        self._log(f"AI sorgusu: '{satis_urun}' vs '{alis_urun}'")
        
        result = self.ai.check_product_match(satis_urun, alis_urun)
        
        if result["success"]:
            # Loglama
            if self.log:
                self.log.ai_oneri(
                    satis_urun, 
                    alis_urun, 
                    result["confidence"],
                    result["reason"]
                )
        
        return result

    
    def eslestir(
        self, 
        satis_kalemi: FaturaKalemi, 
        alis_kalemi: FaturaKalemi,
        eslestirme_tipi: str = "manuel"
    ) -> Eslestirme:
        """
        Satış ve alış kalemini eşleştir
        """
        benzerlik = self.benzerlik_hesapla(satis_kalemi.urun_adi, alis_kalemi.urun_adi)
        
        eslestirme = Eslestirme(
            satis_kalemi=satis_kalemi,
            alis_kalemi=alis_kalemi,
            eslestirme_tipi=eslestirme_tipi,
            benzerlik_orani=benzerlik,
            kullanici_onayi=(eslestirme_tipi == "manuel")
        )
        
        self.eslestirmeler.append(eslestirme)
        
        # Geçmişe ekle (gelecekte otomatik eşleştirme için)
        self.eslestirme_gecmisi[satis_kalemi.urun_adi] = alis_kalemi.urun_adi
        self._kaydet()
        
        return eslestirme
    
    def toplu_eslestir(
        self, 
        satis_kalemleri: List[FaturaKalemi], 
        alis_kalemleri: List[FaturaKalemi],
        sadece_otomatik: bool = False
    ) -> Dict:
        """
        Tüm satış kalemlerini alış kalemleriyle eşleştir
        
        Returns:
            {
                "otomatik": [...],  # Otomatik eşleşenler
                "onerilen": [...],  # Kullanıcı onayı bekleyenler
                "eslesmedi": [...]  # Eşleşme bulunamayanlar
            }
        """
        sonuc = {
            "otomatik": [],
            "onerilen": [],
            "eslesmedi": []
        }
        
        kullanilmis_alis = set()  # FIFO için kullanılan alış kalemleri
        
        for satis in satis_kalemleri:
            eslesme_adaylari = self.eslestirme_ara(satis, alis_kalemleri)
            
            # Kullanılmamış adayları filtrele
            eslesme_adaylari = [
                (alis, benzerlik, tip) 
                for alis, benzerlik, tip in eslesme_adaylari
                if id(alis) not in kullanilmis_alis
            ]
            
            if not eslesme_adaylari:
                sonuc["eslesmedi"].append({
                    "satis": satis,
                    "mesaj": "Eşleşen alış kalemi bulunamadı"
                })
                continue
            
            en_iyi = eslesme_adaylari[0]
            alis, benzerlik, tip = en_iyi
            
            if tip == "otomatik" or tip == "gecmis":
                # Otomatik eşleştir
                eslestirme = self.eslestir(satis, alis, "otomatik")
                sonuc["otomatik"].append({
                    "eslestirme": eslestirme,
                    "benzerlik": benzerlik
                })
                kullanilmis_alis.add(id(alis))
            else:
                # Kullanıcı onayı gerekli
                if not sadece_otomatik:
                    sonuc["onerilen"].append({
                        "satis": satis,
                        "adaylar": eslesme_adaylari[:5],  # En iyi 5 aday
                        "en_iyi_benzerlik": benzerlik
                    })
                else:
                    sonuc["eslesmedi"].append({
                        "satis": satis,
                        "mesaj": f"Benzerlik düşük: {benzerlik}%"
                    })
        
        return sonuc
    
    def yuklenilen_kdv_hesapla(
        self, 
        satis_kalemi: FaturaKalemi,
        eslestirmeler: List[Eslestirme]
    ) -> EslestirmeSonuc:
        """
        Bir satış kalemi için yüklenilen KDV hesapla
        """
        ilgili_eslesmeler = [
            e for e in eslestirmeler 
            if e.satis_kalemi.fatura_no == satis_kalemi.fatura_no
            and e.satis_kalemi.kalem_sira == satis_kalemi.kalem_sira
        ]
        
        if not ilgili_eslesmeler:
            return EslestirmeSonuc(
                satis_fatura_no=satis_kalemi.fatura_no,
                satis_kalemi=satis_kalemi.urun_adi,
                yuklenilen_kdv=0.0,
                alis_faturalari=[],
                eslestirme_durumu="eslesmedi"
            )
        
        toplam_yuklenilen = 0.0
        alis_detay = []
        
        for eslesme in ilgili_eslesmeler:
            alis = eslesme.alis_kalemi
            
            # KISMI EŞLEŞME: Miktar oranına göre KDV hesapla
            # Örn: 10 adet satıldı, alışta 100 adet var → %10'u
            if alis.miktar > 0:
                oran = min(satis_kalemi.miktar / alis.miktar, 1.0)
            else:
                oran = 1.0
            
            isabet_eden_kdv = alis.kdv_tutari * oran
            toplam_yuklenilen += isabet_eden_kdv
            
            alis_detay.append({
                "fatura_no": alis.fatura_no,
                "fatura_tarihi": alis.fatura_tarihi,
                "urun_adi": alis.urun_adi,
                "miktar": alis.miktar,
                "birim": alis.birim,
                "kullanilan_miktar": satis_kalemi.miktar,
                "kdv_tutari": alis.kdv_tutari,
                "isabet_eden_kdv": round(isabet_eden_kdv, 2),
                "firma": alis.firma_unvan
            })
        
        return EslestirmeSonuc(
            satis_fatura_no=satis_kalemi.fatura_no,
            satis_kalemi=satis_kalemi.urun_adi,
            yuklenilen_kdv=round(toplam_yuklenilen, 2),
            alis_faturalari=alis_detay,
            eslestirme_durumu="tam" if len(ilgili_eslesmeler) > 0 else "kismi"
        )


# ==================== YARDIMCI FONKSİYONLAR ====================

def fatura_verisinden_kalemler(fatura_verisi: Dict, fatura_tipi: str = "alis") -> List[FaturaKalemi]:
    """
    Fatura verisindeki 'kalemler' listesinden FaturaKalemi listesi oluştur
    """
    kalemler = []
    
    raw_kalemler = fatura_verisi.get('kalemler', [])
    
    for k in raw_kalemler:
        kalem = FaturaKalemi(
            fatura_no=fatura_verisi.get('seri', '') + fatura_verisi.get('sira_no', ''),
            fatura_tarihi=fatura_verisi.get('tarih', ''),
            kalem_sira=k.get('sira', 0),
            urun_kodu=k.get('urun_kodu', ''),
            urun_adi=k.get('urun_adi', ''),
            miktar=float(k.get('miktar', 0)),
            birim=k.get('birim', 'AD'),
            birim_fiyat=float(k.get('birim_fiyat', 0)),
            tutar=float(k.get('tutar', 0)),
            kdv_orani=float(k.get('kdv_orani', 20)),
            kdv_tutari=float(k.get('kdv_tutari', 0)),
            firma_unvan=fatura_verisi.get('satici_unvan', '') if fatura_tipi == "alis" else fatura_verisi.get('alici_unvan', ''),
            firma_vkn=fatura_verisi.get('satici_vkn', '') if fatura_tipi == "alis" else fatura_verisi.get('alici_vkn', ''),
            fatura_tipi=fatura_tipi
        )
        kalemler.append(kalem)
    
    return kalemler


# ==================== YMM KONTROL MEKANİZMALARI ====================

@dataclass
class KontrolSonucu:
    """YMM kontrol sonucu"""
    basarili: bool
    kod: str  # "mukerrer", "azami_asim", "donem_hatasi", "toplam_asim"
    mesaj: str
    detay: Dict = field(default_factory=dict)


class YMMKontrolleri:
    """
    YMM Mevzuat Kontrolleri
    
    KDV iade talebinde bulunmadan önce yapılması gereken kontroller:
    1. Mükerrerlik: Aynı alış faturası birden fazla kullanılmamalı
    2. Azami İade: Yüklenilen KDV, ihracat bedeli × %20'yi geçemez
    3. Dönem: Alış tarihi, satış tarihinden önce olmalı
    4. Toplam: Yüklenilen KDV toplamı, indirilecek KDV'yi geçemez
    """
    
    # Azami iade oranları
    AZAMI_IADE_ORANI = 0.20  # İhracat için %20
    GENEL_KDV_ORANI = 0.20   # Genel KDV oranı %20
    
    def __init__(self):
        self.hatalar: List[KontrolSonucu] = []
        self.uyarilar: List[KontrolSonucu] = []
    
    def temizle(self):
        """Önceki kontrol sonuçlarını temizle"""
        self.hatalar = []
        self.uyarilar = []
    
    # ==================== 1. MÜKERRERLİK KONTROLÜ ====================
    
    def mukerrerlik_kontrol(
        self, 
        eslestirmeler: List[Eslestirme]
    ) -> List[KontrolSonucu]:
        """
        Aynı alış faturası kaleminin birden fazla satışa yüklenip yüklenmediğini kontrol et
        
        Kural: Bir alış faturası kalemi SADECE BİR KEZ yüklenebilir
        (Veya toplam yüklenilen miktar, alış miktarını geçemez)
        """
        sonuclar = []
        
        # Alış kalemine göre grupla
        alis_kullanim: Dict[str, List[Eslestirme]] = {}
        
        for e in eslestirmeler:
            alis_key = f"{e.alis_kalemi.fatura_no}#{e.alis_kalemi.kalem_sira}"
            if alis_key not in alis_kullanim:
                alis_kullanim[alis_key] = []
            alis_kullanim[alis_key].append(e)
        
        # Birden fazla kullanılanları bul
        for alis_key, kullanim_listesi in alis_kullanim.items():
            if len(kullanim_listesi) > 1:
                toplam_miktar = sum(e.satis_kalemi.miktar for e in kullanim_listesi)
                alis_miktar = kullanim_listesi[0].alis_kalemi.miktar
                
                if toplam_miktar > alis_miktar:
                    # Kritik hata: Stok aşımı
                    sonuc = KontrolSonucu(
                        basarili=False,
                        kod="mukerrer_asim",
                        mesaj=f"⛔ MÜKERRER AŞIM: {alis_key} alış kalemi {len(kullanim_listesi)} satışa yüklenmiş, "
                              f"toplam {toplam_miktar} > alış miktarı {alis_miktar}",
                        detay={
                            "alis_fatura": alis_key,
                            "kullanim_sayisi": len(kullanim_listesi),
                            "toplam_yuklenilen_miktar": toplam_miktar,
                            "alis_miktari": alis_miktar,
                            "satis_faturalari": [e.satis_kalemi.fatura_no for e in kullanim_listesi]
                        }
                    )
                    sonuclar.append(sonuc)
                    self.hatalar.append(sonuc)
                else:
                    # Uyarı: Birden fazla kullanım ama miktar aşımı yok
                    sonuc = KontrolSonucu(
                        basarili=True,
                        kod="mukerrer_uyari",
                        mesaj=f"⚠️ UYARI: {alis_key} alış kalemi {len(kullanim_listesi)} satışa yüklenmiş (miktar uygun)",
                        detay={
                            "alis_fatura": alis_key,
                            "kullanim_sayisi": len(kullanim_listesi)
                        }
                    )
                    sonuclar.append(sonuc)
                    self.uyarilar.append(sonuc)
        
        return sonuclar
    
    # ==================== 2. AZAMİ İADE KONTROLÜ ====================
    
    def azami_iade_kontrol(
        self,
        ihracat_bedeli: float,
        yuklenilen_kdv: float,
        kdv_orani: float = 0.20
    ) -> KontrolSonucu:
        """
        Yüklenilen KDV'nin azami iade tutarını aşıp aşmadığını kontrol et
        
        Kural: Azami İade = İhracat Bedeli × Genel KDV Oranı (%18 veya %20)
               Yüklenilen KDV bu tutarı aşamaz
        """
        azami_iade = ihracat_bedeli * kdv_orani
        
        if yuklenilen_kdv > azami_iade:
            fazla = yuklenilen_kdv - azami_iade
            sonuc = KontrolSonucu(
                basarili=False,
                kod="azami_asim",
                mesaj=f"⛔ AZAMİ İADE AŞIMI: Yüklenilen KDV {yuklenilen_kdv:,.2f} TL > "
                      f"Azami iade {azami_iade:,.2f} TL (İhracat {ihracat_bedeli:,.2f} × %{int(kdv_orani*100)}). "
                      f"Fazla: {fazla:,.2f} TL",
                detay={
                    "ihracat_bedeli": ihracat_bedeli,
                    "yuklenilen_kdv": yuklenilen_kdv,
                    "azami_iade": azami_iade,
                    "fazla_tutar": fazla,
                    "kdv_orani": kdv_orani
                }
            )
            self.hatalar.append(sonuc)
        else:
            kullanilan_oran = (yuklenilen_kdv / azami_iade * 100) if azami_iade > 0 else 0
            sonuc = KontrolSonucu(
                basarili=True,
                kod="azami_ok",
                mesaj=f"✅ Azami iade kontrolü: {yuklenilen_kdv:,.2f} TL ≤ {azami_iade:,.2f} TL "
                      f"(Kullanım: %{kullanilan_oran:.1f})",
                detay={
                    "ihracat_bedeli": ihracat_bedeli,
                    "yuklenilen_kdv": yuklenilen_kdv,
                    "azami_iade": azami_iade,
                    "kullanilan_oran": kullanilan_oran
                }
            )
        
        return sonuc
    
    # ==================== 3. DÖNEM KONTROLÜ ====================
    
    def donem_kontrol(
        self,
        eslestirmeler: List[Eslestirme]
    ) -> List[KontrolSonucu]:
        """
        Alış tarihinin satış tarihinden önce olup olmadığını kontrol et
        
        Kural: Alış Tarihi ≤ Satış Tarihi (mantıken önce alınmalı sonra satılmalı)
        """
        sonuclar = []
        
        for e in eslestirmeler:
            try:
                # Tarihleri parse et (DD.MM.YYYY formatı)
                alis_tarih = self._parse_tarih(e.alis_kalemi.fatura_tarihi)
                satis_tarih = self._parse_tarih(e.satis_kalemi.fatura_tarihi)
                
                if alis_tarih is None or satis_tarih is None:
                    continue
                
                if alis_tarih > satis_tarih:
                    sonuc = KontrolSonucu(
                        basarili=False,
                        kod="donem_hatasi",
                        mesaj=f"⛔ DÖNEM HATASI: Alış ({e.alis_kalemi.fatura_tarihi}) satıştan ({e.satis_kalemi.fatura_tarihi}) sonra! "
                              f"Fatura: {e.alis_kalemi.fatura_no} → {e.satis_kalemi.fatura_no}",
                        detay={
                            "alis_fatura": e.alis_kalemi.fatura_no,
                            "alis_tarih": e.alis_kalemi.fatura_tarihi,
                            "satis_fatura": e.satis_kalemi.fatura_no,
                            "satis_tarih": e.satis_kalemi.fatura_tarihi
                        }
                    )
                    sonuclar.append(sonuc)
                    self.hatalar.append(sonuc)
            except Exception as ex:
                pass  # Tarih parse hatası - atla
        
        return sonuclar
    
    def _parse_tarih(self, tarih_str: str) -> Optional[datetime]:
        """Tarih string'ini datetime'a çevir"""
        if not tarih_str:
            return None
        
        for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                return datetime.strptime(tarih_str, fmt)
            except:
                continue
        return None
    
    # ==================== 4. TOPLAM KONTROL ====================
    
    def toplam_kontrol(
        self,
        yuklenilen_toplam: float,
        indirilecek_kdv_toplam: float
    ) -> KontrolSonucu:
        """
        Yüklenilen KDV toplamının indirilecek KDV'yi aşıp aşmadığını kontrol et
        
        Kural: Σ Yüklenilen KDV ≤ Σ İndirilecek KDV
        (Yüklendiğinden fazlası talep edilemez)
        """
        if yuklenilen_toplam > indirilecek_kdv_toplam:
            fazla = yuklenilen_toplam - indirilecek_kdv_toplam
            sonuc = KontrolSonucu(
                basarili=False,
                kod="toplam_asim",
                mesaj=f"⛔ TOPLAM AŞIM: Yüklenilen {yuklenilen_toplam:,.2f} TL > "
                      f"İndirilecek KDV {indirilecek_kdv_toplam:,.2f} TL. Fazla: {fazla:,.2f} TL",
                detay={
                    "yuklenilen_toplam": yuklenilen_toplam,
                    "indirilecek_toplam": indirilecek_kdv_toplam,
                    "fazla": fazla
                }
            )
            self.hatalar.append(sonuc)
        else:
            kullanim = (yuklenilen_toplam / indirilecek_kdv_toplam * 100) if indirilecek_kdv_toplam > 0 else 0
            sonuc = KontrolSonucu(
                basarili=True,
                kod="toplam_ok",
                mesaj=f"✅ Toplam kontrol: Yüklenilen {yuklenilen_toplam:,.2f} TL ≤ "
                      f"İndirilecek {indirilecek_kdv_toplam:,.2f} TL (Kullanım: %{kullanim:.1f})",
                detay={
                    "yuklenilen_toplam": yuklenilen_toplam,
                    "indirilecek_toplam": indirilecek_kdv_toplam,
                    "kullanim_orani": kullanim
                }
            )
        
        return sonuc
    
    # ==================== 5. TAM VALİDASYON ====================
    
    def tam_validasyon(
        self,
        eslestirmeler: List[Eslestirme],
        ihracat_bedeli: float,
        indirilecek_kdv_toplam: float,
        kdv_orani: float = 0.20
    ) -> Dict:
        """
        Tüm YMM kontrollerini çalıştır ve özet rapor döndür
        """
        self.temizle()
        
        # Yüklenilen KDV toplamını hesapla
        yuklenilen_toplam = sum(
            e.alis_kalemi.kdv_tutari * min(e.satis_kalemi.miktar / e.alis_kalemi.miktar, 1.0)
            if e.alis_kalemi.miktar > 0 else e.alis_kalemi.kdv_tutari
            for e in eslestirmeler
        )
        
        # Kontrolleri çalıştır
        mukerrer_sonuc = self.mukerrerlik_kontrol(eslestirmeler)
        azami_sonuc = self.azami_iade_kontrol(ihracat_bedeli, yuklenilen_toplam, kdv_orani)
        donem_sonuc = self.donem_kontrol(eslestirmeler)
        toplam_sonuc = self.toplam_kontrol(yuklenilen_toplam, indirilecek_kdv_toplam)
        
        # Özet oluştur
        toplam_hata = len(self.hatalar)
        toplam_uyari = len(self.uyarilar)
        
        return {
            "basarili": toplam_hata == 0,
            "ozet": {
                "eslestirme_sayisi": len(eslestirmeler),
                "yuklenilen_kdv": round(yuklenilen_toplam, 2),
                "ihracat_bedeli": ihracat_bedeli,
                "azami_iade": round(ihracat_bedeli * kdv_orani, 2),
                "indirilecek_kdv": indirilecek_kdv_toplam,
                "hata_sayisi": toplam_hata,
                "uyari_sayisi": toplam_uyari
            },
            "hatalar": [{"kod": h.kod, "mesaj": h.mesaj, "detay": h.detay} for h in self.hatalar],
            "uyarilar": [{"kod": u.kod, "mesaj": u.mesaj, "detay": u.detay} for u in self.uyarilar],
            "kontroller": {
                "mukerrerlik": [{"basarili": s.basarili, "mesaj": s.mesaj} for s in mukerrer_sonuc],
                "azami_iade": {"basarili": azami_sonuc.basarili, "mesaj": azami_sonuc.mesaj},
                "donem": [{"basarili": s.basarili, "mesaj": s.mesaj} for s in donem_sonuc],
                "toplam": {"basarili": toplam_sonuc.basarili, "mesaj": toplam_sonuc.mesaj}
            }
        }


# ==================== TEST ====================

if __name__ == "__main__":
    print("=== Ürün Eşleştirme Modülü Test ===\n")
    
    eslestirici = UrunEslestirici()
    
    # Test: Benzerlik hesaplama
    test_cases = [
        ("LAPTOP ASUS X515", "LAPTOP ASUS X515", "Birebir"),
        ("LAPTOP ASUS X515", "ASUS X515 LAPTOP", "Kelime sırası farklı"),
        ("LAPTOP ASUS X515", "DİZÜSTÜ BİLGİSAYAR ASUS", "Farklı tanım"),
        ("BİSKÜVİ", "UN", "Farklı ürün"),
    ]
    
    print("Benzerlik Testleri:")
    print("-" * 60)
    for m1, m2, aciklama in test_cases:
        oran = eslestirici.benzerlik_hesapla(m1, m2)
        print(f"{aciklama}:")
        print(f"  '{m1}' vs '{m2}' = {oran}%")
    
    # Test: Birim uyumluluğu
    print("\nBirim Uyumluluk Testleri:")
    print("-" * 60)
    birim_testleri = [
        ("AD", "ADET"),
        ("KG", "KGM"),
        ("AD", "KOLİ"),
    ]
    
    for b1, b2 in birim_testleri:
        uyumlu = eslestirici.birim_uyumlu_mu(b1, b2)
        print(f"  {b1} <-> {b2}: {'✅ Uyumlu' if uyumlu else '❌ Uyumsuz'}")
    
    print("\n✅ Modül testi tamamlandı!")
