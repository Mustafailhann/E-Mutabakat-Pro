# -*- coding: utf-8 -*-
"""
KDV İade Validasyon Raporu
İade öncesi otomatik kontrol ve risk değerlendirmesi
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import json
import os


@dataclass
class KontrolKalemi:
    """Tek bir kontrol kalemi"""
    kod: str
    baslik: str
    aciklama: str
    durum: str  # "basarili", "uyari", "hata"
    puan: int  # 0-100
    detay: str = ""


@dataclass
class ValidasyonRaporu:
    """Validasyon raporu"""
    rapor_id: str
    olusturma_tarihi: str
    mukellef_vkn: str
    mukellef_unvan: str
    donem: str
    iade_turu: str  # ihracat, ihrac_kayitli, tevkifat, indirimli_oran
    
    # Kontrol sonuçları
    kontroller: List[KontrolKalemi] = field(default_factory=list)
    
    # Özet
    toplam_puan: int = 0
    basarili_kontrol: int = 0
    uyari_kontrol: int = 0
    hata_kontrol: int = 0
    
    # Risk seviyesi
    risk_seviyesi: str = ""  # "dusuk", "orta", "yuksek", "kritik"
    
    # Tavsiyeler
    tavsiyeler: List[str] = field(default_factory=list)


class KDVIadeValidator:
    """
    KDV İade Validatör
    
    İade öncesi tüm kontrolleri yapar:
    - Belge kontrolleri
    - Tutar kontrolleri
    - Mevzuat uyumu
    - Risk değerlendirmesi
    """
    
    def __init__(self, veri_klasoru: str = "data"):
        self.veri_klasoru = veri_klasoru
    
    def validate(
        self,
        mukellef_vkn: str,
        mukellef_unvan: str,
        donem: str,
        iade_turu: str,
        veriler: Dict
    ) -> ValidasyonRaporu:
        """
        Kapsamlı validasyon yap
        """
        rapor = ValidasyonRaporu(
            rapor_id=datetime.now().strftime("%Y%m%d%H%M%S"),
            olusturma_tarihi=datetime.now().strftime("%d.%m.%Y %H:%M"),
            mukellef_vkn=mukellef_vkn,
            mukellef_unvan=mukellef_unvan,
            donem=donem,
            iade_turu=iade_turu
        )
        
        # Temel kontroller
        self._kontrol_beyanname(rapor, veriler)
        self._kontrol_faturalar(rapor, veriler)
        self._kontrol_yuklenilen(rapor, veriler)
        self._kontrol_azami_iade(rapor, veriler)
        self._kontrol_toplam_tutarlilik(rapor, veriler)
        
        # İade türüne özel kontroller
        if iade_turu == "ihracat":
            self._kontrol_gcb(rapor, veriler)
        elif iade_turu == "ihrac_kayitli":
            self._kontrol_tecil_terkin(rapor, veriler)
        elif iade_turu == "tevkifat":
            self._kontrol_tevkifat(rapor, veriler)
        
        # Sonuç hesapla
        self._sonuc_hesapla(rapor)
        
        return rapor
    
    def _kontrol_beyanname(self, rapor: ValidasyonRaporu, veriler: Dict):
        """Beyanname kontrolü"""
        beyanname = veriler.get("beyanname", {})
        
        if beyanname.get("donem") == rapor.donem:
            rapor.kontroller.append(KontrolKalemi(
                kod="BYN001",
                baslik="Beyanname Dönemi",
                aciklama="Beyanname dönemi iade dönemiyle eşleşiyor",
                durum="basarili",
                puan=100
            ))
        else:
            rapor.kontroller.append(KontrolKalemi(
                kod="BYN001",
                baslik="Beyanname Dönemi",
                aciklama="Beyanname dönemi iade dönemiyle eşleşmiyor!",
                durum="hata",
                puan=0,
                detay=f"Beyanname: {beyanname.get('donem')}, İade: {rapor.donem}"
            ))
        
        # Devreden KDV kontrolü
        devreden = beyanname.get("devreden_kdv", 0)
        if devreden > 0:
            rapor.kontroller.append(KontrolKalemi(
                kod="BYN002",
                baslik="Devreden KDV",
                aciklama=f"Devreden KDV: {devreden:,.2f} TL",
                durum="basarili",
                puan=100
            ))
    
    def _kontrol_faturalar(self, rapor: ValidasyonRaporu, veriler: Dict):
        """Fatura kontrolleri"""
        satis_faturalari = veriler.get("satis_faturalari", [])
        alis_faturalari = veriler.get("alis_faturalari", [])
        
        # Satış fatura sayısı
        satis_sayisi = len(satis_faturalari)
        if satis_sayisi > 0:
            rapor.kontroller.append(KontrolKalemi(
                kod="FAT001",
                baslik="Satış Faturaları",
                aciklama=f"{satis_sayisi} adet satış faturası mevcut",
                durum="basarili",
                puan=100
            ))
        else:
            rapor.kontroller.append(KontrolKalemi(
                kod="FAT001",
                baslik="Satış Faturaları",
                aciklama="Hiç satış faturası bulunamadı!",
                durum="hata",
                puan=0
            ))
        
        # Alış fatura sayısı
        alis_sayisi = len(alis_faturalari)
        if alis_sayisi > 0:
            rapor.kontroller.append(KontrolKalemi(
                kod="FAT002",
                baslik="Alış Faturaları",
                aciklama=f"{alis_sayisi} adet alış faturası mevcut",
                durum="basarili",
                puan=100
            ))
        else:
            rapor.kontroller.append(KontrolKalemi(
                kod="FAT002",
                baslik="Alış Faturaları",
                aciklama="Hiç alış faturası bulunamadı!",
                durum="hata",
                puan=0
            ))
    
    def _kontrol_yuklenilen(self, rapor: ValidasyonRaporu, veriler: Dict):
        """Yüklenilen KDV kontrolleri"""
        yuklenilen = veriler.get("yuklenilen_kdv", {})
        
        dogrudan = yuklenilen.get("dogrudan", 0)
        genel_gider = yuklenilen.get("genel_gider", 0)
        atik = yuklenilen.get("atik", 0)
        toplam = dogrudan + genel_gider + atik
        
        if toplam > 0:
            rapor.kontroller.append(KontrolKalemi(
                kod="YUK001",
                baslik="Yüklenilen KDV Hesaplaması",
                aciklama=f"Toplam yüklenilen: {toplam:,.2f} TL",
                durum="basarili",
                puan=100,
                detay=f"1. Doğrudan: {dogrudan:,.2f} | 2. G.Gider: {genel_gider:,.2f} | 3. ATİK: {atik:,.2f}"
            ))
        else:
            rapor.kontroller.append(KontrolKalemi(
                kod="YUK001",
                baslik="Yüklenilen KDV Hesaplaması",
                aciklama="Yüklenilen KDV hesaplanmamış!",
                durum="hata",
                puan=0
            ))
        
        # 3 unsur kontrolü
        if dogrudan > 0 and genel_gider > 0:
            rapor.kontroller.append(KontrolKalemi(
                kod="YUK002",
                baslik="3 Unsur Tamamlığı",
                aciklama="Doğrudan ve genel gider yüklenimi yapılmış",
                durum="basarili",
                puan=100
            ))
        elif dogrudan > 0:
            rapor.kontroller.append(KontrolKalemi(
                kod="YUK002",
                baslik="3 Unsur Tamamlığı",
                aciklama="Sadece doğrudan yüklenim var, genel gider eksik",
                durum="uyari",
                puan=60
            ))
    
    def _kontrol_azami_iade(self, rapor: ValidasyonRaporu, veriler: Dict):
        """Azami iade kontrolü"""
        ihracat_bedeli = veriler.get("ihracat_bedeli", 0)
        yuklenilen = veriler.get("yuklenilen_kdv", {})
        toplam_yuklenilen = sum(yuklenilen.values()) if isinstance(yuklenilen, dict) else yuklenilen
        
        azami_iade = ihracat_bedeli * 0.20
        
        if toplam_yuklenilen <= azami_iade:
            oran = (toplam_yuklenilen / azami_iade * 100) if azami_iade > 0 else 0
            rapor.kontroller.append(KontrolKalemi(
                kod="AZM001",
                baslik="Azami İade Kontrolü",
                aciklama=f"Yüklenilen ({toplam_yuklenilen:,.2f}) ≤ Azami ({azami_iade:,.2f})",
                durum="basarili",
                puan=100,
                detay=f"Kullanım oranı: %{oran:.1f}"
            ))
        else:
            fazla = toplam_yuklenilen - azami_iade
            rapor.kontroller.append(KontrolKalemi(
                kod="AZM001",
                baslik="Azami İade Kontrolü",
                aciklama=f"Azami iade tutarı aşıldı! Fazla: {fazla:,.2f} TL",
                durum="hata",
                puan=0
            ))
    
    def _kontrol_toplam_tutarlilik(self, rapor: ValidasyonRaporu, veriler: Dict):
        """Toplam tutarlılık kontrolü"""
        yuklenilen = veriler.get("yuklenilen_kdv", {})
        toplam_yuklenilen = sum(yuklenilen.values()) if isinstance(yuklenilen, dict) else yuklenilen
        indirilecek = veriler.get("indirilecek_kdv", 0)
        
        if toplam_yuklenilen <= indirilecek:
            rapor.kontroller.append(KontrolKalemi(
                kod="TOP001",
                baslik="Toplam Tutarlılık",
                aciklama=f"Yüklenilen ({toplam_yuklenilen:,.2f}) ≤ İndirilecek ({indirilecek:,.2f})",
                durum="basarili",
                puan=100
            ))
        else:
            rapor.kontroller.append(KontrolKalemi(
                kod="TOP001",
                baslik="Toplam Tutarlılık",
                aciklama=f"Yüklenilen, indirilecek KDV'yi aşıyor!",
                durum="hata",
                puan=0
            ))
    
    def _kontrol_gcb(self, rapor: ValidasyonRaporu, veriler: Dict):
        """GÇB kontrolleri (ihracat için)"""
        gcbler = veriler.get("gcbler", [])
        satis_faturalari = veriler.get("satis_faturalari", [])
        
        eslestirilen = sum(1 for g in gcbler if g.get("eslestirildi"))
        
        if len(gcbler) > 0:
            oran = eslestirilen / len(gcbler) * 100
            if oran >= 100:
                durum = "basarili"
                puan = 100
            elif oran >= 80:
                durum = "uyari"
                puan = 80
            else:
                durum = "hata"
                puan = 50
            
            rapor.kontroller.append(KontrolKalemi(
                kod="GCB001",
                baslik="GÇB-Fatura Eşleştirme",
                aciklama=f"{eslestirilen}/{len(gcbler)} GÇB eşleştirildi (%{oran:.0f})",
                durum=durum,
                puan=puan
            ))
    
    def _kontrol_tecil_terkin(self, rapor: ValidasyonRaporu, veriler: Dict):
        """Tecil-terkin kontrolleri (ihraç kayıtlı için)"""
        ihrac_kayitli = veriler.get("ihrac_kayitli", [])
        
        geciken = [s for s in ihrac_kayitli if s.get("ihracat_durumu") == "gecikti"]
        
        if len(geciken) == 0:
            rapor.kontroller.append(KontrolKalemi(
                kod="TEC001",
                baslik="Tecil-Terkin Süresi",
                aciklama="Tüm ihraç kayıtlı satışlar süresinde",
                durum="basarili",
                puan=100
            ))
        else:
            rapor.kontroller.append(KontrolKalemi(
                kod="TEC001",
                baslik="Tecil-Terkin Süresi",
                aciklama=f"{len(geciken)} adet ihraç kayıtlı satışın süresi geçmiş!",
                durum="hata",
                puan=0
            ))
    
    def _kontrol_tevkifat(self, rapor: ValidasyonRaporu, veriler: Dict):
        """Tevkifat kontrolleri"""
        tevkifat_faturalari = veriler.get("tevkifat_faturalari", [])
        
        if len(tevkifat_faturalari) > 0:
            toplam = sum(f.get("tevkifat_kdv", 0) for f in tevkifat_faturalari)
            rapor.kontroller.append(KontrolKalemi(
                kod="TEV001",
                baslik="Tevkifat Faturaları",
                aciklama=f"{len(tevkifat_faturalari)} fatura, {toplam:,.2f} TL tevkifat",
                durum="basarili",
                puan=100
            ))
    
    def _sonuc_hesapla(self, rapor: ValidasyonRaporu):
        """Sonuç ve risk hesapla"""
        if not rapor.kontroller:
            return
        
        toplam_puan = 0
        for k in rapor.kontroller:
            toplam_puan += k.puan
            if k.durum == "basarili":
                rapor.basarili_kontrol += 1
            elif k.durum == "uyari":
                rapor.uyari_kontrol += 1
            else:
                rapor.hata_kontrol += 1
        
        rapor.toplam_puan = toplam_puan // len(rapor.kontroller)
        
        # Risk seviyesi
        if rapor.hata_kontrol > 0:
            if rapor.hata_kontrol > 2:
                rapor.risk_seviyesi = "kritik"
            else:
                rapor.risk_seviyesi = "yuksek"
        elif rapor.uyari_kontrol > 0:
            rapor.risk_seviyesi = "orta"
        else:
            rapor.risk_seviyesi = "dusuk"
        
        # Tavsiyeler
        if rapor.hata_kontrol > 0:
            rapor.tavsiyeler.append("❌ Hatalı kontrolleri düzeltin")
        if rapor.uyari_kontrol > 0:
            rapor.tavsiyeler.append("⚠️ Uyarıları inceleyin")
        if rapor.risk_seviyesi in ["yuksek", "kritik"]:
            rapor.tavsiyeler.append("🔍 İade öncesi detaylı inceleme yapın")
    
    def rapor_dict(self, rapor: ValidasyonRaporu) -> Dict:
        """Raporu dict olarak döndür"""
        return {
            "rapor_id": rapor.rapor_id,
            "tarih": rapor.olusturma_tarihi,
            "mukellef": {
                "vkn": rapor.mukellef_vkn,
                "unvan": rapor.mukellef_unvan
            },
            "donem": rapor.donem,
            "iade_turu": rapor.iade_turu,
            "ozet": {
                "puan": rapor.toplam_puan,
                "basarili": rapor.basarili_kontrol,
                "uyari": rapor.uyari_kontrol,
                "hata": rapor.hata_kontrol,
                "risk": rapor.risk_seviyesi
            },
            "kontroller": [
                {
                    "kod": k.kod,
                    "baslik": k.baslik,
                    "aciklama": k.aciklama,
                    "durum": k.durum,
                    "puan": k.puan,
                    "detay": k.detay
                }
                for k in rapor.kontroller
            ],
            "tavsiyeler": rapor.tavsiyeler
        }
    
    def rapor_html(self, rapor: ValidasyonRaporu) -> str:
        """HTML rapor oluştur"""
        risk_renk = {
            "dusuk": "#4CAF50",
            "orta": "#FF9800", 
            "yuksek": "#f44336",
            "kritik": "#9C27B0"
        }
        
        kontrol_rows = ""
        for k in rapor.kontroller:
            renk = {"basarili": "#e8f5e9", "uyari": "#fff3e0", "hata": "#ffebee"}.get(k.durum, "#fff")
            emoji = {"basarili": "✅", "uyari": "⚠️", "hata": "❌"}.get(k.durum, "")
            kontrol_rows += f"""
            <tr style="background: {renk}">
                <td>{k.kod}</td>
                <td><b>{k.baslik}</b></td>
                <td>{k.aciklama}</td>
                <td style="text-align:center">{emoji}</td>
                <td style="text-align:center">{k.puan}</td>
            </tr>
            """
        
        return f"""
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>📋 KDV İADE VALİDASYON RAPORU</h2>
            <p><b>Mükellef:</b> {rapor.mukellef_unvan} ({rapor.mukellef_vkn})</p>
            <p><b>Dönem:</b> {rapor.donem} | <b>İade Türü:</b> {rapor.iade_turu.upper()}</p>
            <p><b>Tarih:</b> {rapor.olusturma_tarihi}</p>
            
            <div style="background: {risk_renk.get(rapor.risk_seviyesi, '#ccc')}; color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin:0">Risk Seviyesi: {rapor.risk_seviyesi.upper()}</h3>
                <p style="margin:5px 0 0 0">Genel Puan: {rapor.toplam_puan}/100</p>
            </div>
            
            <h3>Kontrol Sonuçları</h3>
            <table style="width:100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #2E74B5; color: white;">
                        <th style="padding:10px">Kod</th>
                        <th style="padding:10px">Kontrol</th>
                        <th style="padding:10px">Açıklama</th>
                        <th style="padding:10px">Durum</th>
                        <th style="padding:10px">Puan</th>
                    </tr>
                </thead>
                <tbody>
                    {kontrol_rows}
                </tbody>
            </table>
            
            <h3>Özet</h3>
            <p>✅ Başarılı: {rapor.basarili_kontrol} | ⚠️ Uyarı: {rapor.uyari_kontrol} | ❌ Hata: {rapor.hata_kontrol}</p>
            
            {'<h3>Tavsiyeler</h3><ul>' + ''.join(f'<li>{t}</li>' for t in rapor.tavsiyeler) + '</ul>' if rapor.tavsiyeler else ''}
        </div>
        """


# ==================== TEST ====================

if __name__ == "__main__":
    print("=== KDV İade Validasyon Test ===\n")
    
    validator = KDVIadeValidator()
    
    # Test verisi
    veriler = {
        "beyanname": {"donem": "2025-01", "devreden_kdv": 50000},
        "satis_faturalari": [{"id": "1"}, {"id": "2"}],
        "alis_faturalari": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
        "yuklenilen_kdv": {"dogrudan": 30000, "genel_gider": 5000, "atik": 2000},
        "ihracat_bedeli": 500000,
        "indirilecek_kdv": 80000,
        "gcbler": [{"eslestirildi": True}, {"eslestirildi": True}]
    }
    
    rapor = validator.validate(
        mukellef_vkn="1234567890",
        mukellef_unvan="TEST A.Ş.",
        donem="2025-01",
        iade_turu="ihracat",
        veriler=veriler
    )
    
    print(f"Rapor ID: {rapor.rapor_id}")
    print(f"Toplam Puan: {rapor.toplam_puan}/100")
    print(f"Risk Seviyesi: {rapor.risk_seviyesi.upper()}")
    print(f"Kontroller: ✅{rapor.basarili_kontrol} ⚠️{rapor.uyari_kontrol} ❌{rapor.hata_kontrol}")
    
    print("\n✅ Test tamamlandı!")
