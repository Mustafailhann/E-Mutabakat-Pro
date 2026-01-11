# -*- coding: utf-8 -*-
"""
KKEG Tespit Modülü - Kanunen Kabul Edilmeyen Gider Kontrolü

Bu modül kebir ve fatura verilerinden KKEG olabilecek giderleri tespit eder.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum


class KKEGType(Enum):
    """KKEG Türleri"""
    TEMSIL_AGIRLAMA = "Temsil ve Ağırlama Giderleri"
    KISISEL_GIDER = "Kişisel Gider"
    CEZA_TAZMINAT = "Ceza ve Tazminatlar"
    GECIKME_FAIZI = "Gecikme Faizi/Zammı"
    BINEK_ARAC = "Binek Araç Kısıtlaması"
    OZEL_ILETISIM = "Özel İletişim Vergisi"
    BAGIŞ_YARDIM = "Bağış ve Yardımlar (Limitsiz)"
    FINANSMAN_GIDERI = "Finansman Gider Kısıtlaması"
    ORTULU_KAZANC = "Örtülü Kazanç Dağıtımı"
    DOKUMANTE_EDILMEMIS = "Belgesiz Gider"
    SEYAHAT_KONAKLAMA = "Seyahat ve Konaklama"
    DIGER = "Diğer KKEG"


@dataclass
class KKEGFinding:
    """KKEG Bulgusu"""
    kkeg_type: KKEGType
    account_code: str
    description: str
    amount: float
    kkeg_amount: float  # KKEG olarak eklenmesi gereken tutar
    kkeg_rate: float  # KKEG oranı (örn: 0.30 = %30)
    legal_reference: str  # Yasal dayanak
    document_no: str = ""
    recommendation: str = ""


# KKEG Anahtar Kelime Sözlüğü
KKEG_KEYWORDS = {
    KKEGType.TEMSIL_AGIRLAMA: [
        "temsil", "ağırlama", "davet", "kokteyl", "resepsiyon",
        "hediye", "promosyon", "tanıtım", "reklam", "sponsorluk",
        "ikram", "ziyafet", "kutlama", "organizasyon"
    ],
    KKEGType.KISISEL_GIDER: [
        "kişisel", "özel", "ev", "konut", "daire",
        "ortak", "patron", "müdür", "yönetici",
        "eş", "çocuk", "aile", "şahsi"
    ],
    KKEGType.CEZA_TAZMINAT: [
        "ceza", "para cezası", "idari para", "trafik cezası",
        "vergi cezası", "sgk ceza", "gecikme cezası",
        "tazminat", "ihbar tazminatı", "kıdem tazminatı",
        "iş mahkemesi", "dava", "mahkeme"
    ],
    KKEGType.GECIKME_FAIZI: [
        "gecikme faizi", "gecikme zammı", "temerrüt faizi",
        "sgk gecikme", "vergi gecikme", "pişmanlık zammı",
        "tecil faizi", "yıllık gecikme"
    ],
    KKEGType.SEYAHAT_KONAKLAMA: [
        "otel", "konaklama", "pansiyon", "apart",
        "uçak", "uçuş", "bilet", "thy", "pegasus", "anadolujet",
        "taksi", "uber", "transfer", "araç kiralama",
        "yemek", "restoran", "lokanta", "cafe", "kahvaltı",
        "seyahat", "gezi", "tur", "tatil"
    ],
    KKEGType.BAGIŞ_YARDIM: [
        "bağış", "yardım", "hayır", "dernek", "vakıf",
        "okul", "cami", "hastane", "sosyal yardım",
        "afet", "deprem", "sel"
    ],
    KKEGType.OZEL_ILETISIM: [
        "öiv", "özel iletişim", "iletişim vergisi",
        "cep telefonu", "mobil", "gsm"
    ],
    KKEGType.BINEK_ARAC: [
        "binek", "otomobil", "araç kirası", "araç kiralama",
        "rent a car", "oto kiralama", "taşıt kirası",
        "akaryakıt", "benzin", "mazot", "motorin",
        "otopark", "köprü", "otoyol", "hgs", "ogs"
    ],
    KKEGType.ORTULU_KAZANC: [
        "ilişkili taraf", "grup şirketi", "bağlı ortaklık",
        "transfer fiyatı", "emsallere uygun",
        "holding", "ana şirket"
    ]
}

# Hesap kodu bazlı KKEG riski
KKEG_RISK_ACCOUNTS = {
    # Yüksek riskli hesaplar
    "760": {"risk": "HIGH", "type": KKEGType.TEMSIL_AGIRLAMA, "desc": "Pazarlama Giderleri"},
    "770": {"risk": "MEDIUM", "type": KKEGType.KISISEL_GIDER, "desc": "Genel Yönetim Giderleri"},
    "689": {"risk": "HIGH", "type": KKEGType.CEZA_TAZMINAT, "desc": "Diğer Olağandışı Giderler"},
    "659": {"risk": "MEDIUM", "type": KKEGType.DIGER, "desc": "Diğer Olağan Giderler"},
    "780": {"risk": "MEDIUM", "type": KKEGType.FINANSMAN_GIDERI, "desc": "Finansman Giderleri"},
    "654": {"risk": "MEDIUM", "type": KKEGType.CEZA_TAZMINAT, "desc": "Karşılık Giderleri"},
}

# Binek araç limitleri (yıl bazlı)
BINEK_LIMITS = {
    2024: {
        "monthly_rent": 26000,
        "cost_with_tax": 1500000,
        "cost_without_tax": 790000,
        "kkeg_rate": 0.30
    },
    2025: {
        "monthly_rent": 33000,
        "cost_with_tax": 2050000,
        "cost_without_tax": 1100000,
        "kkeg_rate": 0.30
    }
}


class KKEGDetector:
    """KKEG Tespit Motoru"""
    
    def __init__(self, year: int = 2024):
        self.year = year
        self.findings: List[KKEGFinding] = []
        self.binek_limits = BINEK_LIMITS.get(year, BINEK_LIMITS[2024])
    
    def detect_from_kebir(self, kebir_data: dict, invoice_data: list = None, employee_names: list = None) -> List[KKEGFinding]:
        """
        Kebir verisinden KKEG tespit et
        
        Args:
            kebir_data: Kebir verileri (doc_no -> Lines)
            invoice_data: Fatura listesi (parse edilmiş XML'ler)
            employee_names: Muhtasardan çekilen çalışan isimleri
        """
        self.findings = []  # Her çağrıda sıfırla
        self.invoice_data = invoice_data or []
        self.employee_names = [n.upper() for n in (employee_names or [])]
        
        # Fatura indeksi oluştur (hızlı arama için)
        self.invoice_index = {}
        for inv in self.invoice_data:
            inv_no = inv.get('No', '')
            if inv_no:
                self.invoice_index[inv_no] = inv
        
        # İşlenmiş belgeler - her belge için tek risk
        processed_docs = set()
        
        for doc_no, doc_data in kebir_data.items():
            lines = doc_data.get('Lines', [])
            
            # Bu belge için en yüksek tutarlı gider satırını bul
            max_expense_line = None
            max_amount = 0
            
            for line in lines:
                acc_code = line.get('Acc', '')
                desc = line.get('Desc', '')
                amt = float(line.get('Amt', 0) or 0)
                dc = line.get('DC', 'D')
                
                # Sadece borç kayıtlarını kontrol et
                if dc not in ['D', 'B'] or amt <= 0:
                    continue
                
                # Sadece GİDER hesaplarını kontrol et (600-799 arası)
                # 102 (Banka), 191 (İndirilecek KDV), 320 (Borçlar) gibi hesapları ATLA
                acc_prefix = int(acc_code[:3]) if acc_code[:3].isdigit() else 0
                if acc_prefix < 600 or acc_prefix >= 800:
                    continue
                
                # En yüksek tutarlı gider satırını bul (yevmiye temsili)
                if amt > max_amount:
                    max_amount = amt
                    max_expense_line = line
            
            # Bu belge için tek bir risk kaydı yap
            if max_expense_line and doc_no not in processed_docs:
                acc_code = max_expense_line.get('Acc', '')
                desc = max_expense_line.get('Desc', '')
                amt = float(max_expense_line.get('Amt', 0) or 0)
                
                # Fatura eşleştirmesi yap
                matched_invoice = self._match_invoice(doc_no, desc)
                
                # Seyahat/konaklama ise çalışan kontrolü yap
                # Fatura olmasa bile açıklamadaki isim kontrol edilir
                if self._is_travel_expense(desc):
                    if self._check_employee_match(matched_invoice, desc):
                        # Çalışan eşleşti - KKEG DEĞİL
                        processed_docs.add(doc_no)
                        continue
                
                # Hesap kodu bazlı risk kontrolü
                self._check_account_risk(acc_code, desc, amt, doc_no)
                
                # Anahtar kelime taraması
                self._check_keywords(acc_code, desc, amt, doc_no)
                
                # Binek araç kontrolü
                self._check_binek_arac(acc_code, desc, amt, doc_no)

                
                processed_docs.add(doc_no)
        
        return self.findings
    
    def _match_invoice(self, doc_no: str, desc: str) -> dict:
        """Belge numarasına göre fatura eşleştir"""
        # Direkt eşleşme
        if doc_no in self.invoice_index:
            return self.invoice_index[doc_no]
        
        # Açıklamadaki fatura numarası ara
        for inv_no, inv in self.invoice_index.items():
            if inv_no in desc or inv_no in doc_no:
                return inv
        
        return None
    
    def _is_travel_expense(self, desc: str) -> bool:
        """Seyahat/konaklama gideri mi kontrol et"""
        travel_keywords = KKEG_KEYWORDS.get(KKEGType.SEYAHAT_KONAKLAMA, [])
        desc_lower = desc.lower()
        return any(kw in desc_lower for kw in travel_keywords)
    
    def _check_employee_match(self, invoice: dict, desc: str) -> bool:
        """
        Fatura veya açıklamadaki isim çalışan listesiyle eşleşiyor mu?
        True = çalışan eşleşti, KKEG DEĞİL
        """
        if not self.employee_names:
            return False
        
        # Fatura içeriğinden isim al
        texts_to_check = []
        
        # Fatura açıklaması/notları
        if invoice:
            texts_to_check.append(invoice.get('Description', ''))
            texts_to_check.append(invoice.get('Note', ''))
            texts_to_check.append(invoice.get('CustomerName', ''))
            
            # Fatura kalemleri
            for line in invoice.get('Lines', []):
                texts_to_check.append(line.get('Name', ''))
                texts_to_check.append(line.get('Description', ''))
        
        # Kebir açıklaması da dahil
        texts_to_check.append(desc)
        
        combined_text = ' '.join(t.upper() for t in texts_to_check if t)
        
        # Çalışan isimleriyle karşılaştır
        for emp_name in self.employee_names:
            # Tam eşleşme veya isim parçaları
            if emp_name in combined_text:
                return True
            
            # Ad Soyad parçalı eşleşme
            name_parts = emp_name.split()
            if len(name_parts) >= 2:
                # En az ad ve soyad eşleşmeli
                matches = sum(1 for part in name_parts if part in combined_text)
                if matches >= 2:
                    return True
        
        return False
    
    def _check_account_risk(self, acc_code: str, desc: str, amt: float, doc_no: str):
        """Hesap koduna göre risk kontrolü"""
        prefix = acc_code[:3]
        
        # Mükerrer belge kontrolü - aynı belge zaten eklenmişse atla
        if self._is_duplicate(acc_code, doc_no):
            return
        
        if prefix in KKEG_RISK_ACCOUNTS:
            risk_info = KKEG_RISK_ACCOUNTS[prefix]
            
            # Risk seviyesine göre KKEG oranı
            if risk_info["risk"] == "HIGH":
                kkeg_rate = 0.50  # Yüksek riskli: %50 potansiyel KKEG
            else:  # MEDIUM
                kkeg_rate = 0.25  # Orta riskli: %25 potansiyel KKEG
            
            self.findings.append(KKEGFinding(
                kkeg_type=risk_info["type"],
                account_code=acc_code,
                description=f"{risk_info['desc']}: {desc[:50]}",
                amount=amt,
                kkeg_amount=amt * kkeg_rate,
                kkeg_rate=kkeg_rate,
                legal_reference="GVK 40, KVK 11",
                document_no=doc_no,
                recommendation=f"Manuel inceleme gerekli - Potansiyel KKEG: %{int(kkeg_rate*100)}"
            ))
    
    def _check_keywords(self, acc_code: str, desc: str, amt: float, doc_no: str):
        """Anahtar kelime taraması"""
        desc_lower = desc.lower()
        
        for kkeg_type, keywords in KKEG_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in desc_lower:
                    # Mükerrer kayıt kontrolü
                    if not self._is_duplicate(acc_code, doc_no, kkeg_type):
                        finding = self._create_finding(kkeg_type, acc_code, desc, amt, doc_no, keyword)
                        if finding:
                            self.findings.append(finding)
                    break
    
    def _check_binek_arac(self, acc_code: str, desc: str, amt: float, doc_no: str):
        """Binek araç gider kısıtlaması kontrolü"""
        desc_lower = desc.lower()
        
        # Binek araç kirası kontrolü
        binek_keywords = ["binek", "rent a car", "araç kiralama", "oto kiralama", "taşıt kirası"]
        
        for keyword in binek_keywords:
            if keyword in desc_lower:
                monthly_limit = self.binek_limits["monthly_rent"]
                
                if amt > monthly_limit:
                    excess = amt - monthly_limit
                    kkeg_amt = excess * self.binek_limits["kkeg_rate"]
                    
                    self.findings.append(KKEGFinding(
                        kkeg_type=KKEGType.BINEK_ARAC,
                        account_code=acc_code,
                        description=f"Binek araç kirası limit aşımı: {desc[:40]}",
                        amount=amt,
                        kkeg_amount=kkeg_amt,
                        kkeg_rate=self.binek_limits["kkeg_rate"],
                        legal_reference=f"GVK 40/5 - Aylık limit: {monthly_limit:,.0f} TL",
                        document_no=doc_no,
                        recommendation=f"Limit aşan {excess:,.2f} TL'nin %30'u = {kkeg_amt:,.2f} TL KKEG"
                    ))
                else:
                    # Limit altında ama yine de %30 KKEG
                    kkeg_amt = amt * self.binek_limits["kkeg_rate"]
                    self.findings.append(KKEGFinding(
                        kkeg_type=KKEGType.BINEK_ARAC,
                        account_code=acc_code,
                        description=f"Binek araç gideri (KKEG): {desc[:40]}",
                        amount=amt,
                        kkeg_amount=kkeg_amt,
                        kkeg_rate=self.binek_limits["kkeg_rate"],
                        legal_reference="GVK 40/5 - Binek giderlerinin %30'u KKEG",
                        document_no=doc_no,
                        recommendation=f"Tutarın %30'u = {kkeg_amt:,.2f} TL KKEG yazılmalı"
                    ))
                break
    
    def _create_finding(self, kkeg_type: KKEGType, acc_code: str, desc: str, 
                        amt: float, doc_no: str, matched_keyword: str) -> Optional[KKEGFinding]:
        """KKEG bulgusu oluştur"""
        
        # KKEG türüne göre oran ve referans belirle
        kkeg_config = {
            KKEGType.TEMSIL_AGIRLAMA: {
                "rate": 0.50, "ref": "GVK 40/1 - Temsil ağırlama sınırı",
                "rec": "Yıllık hasılatın %0.5'i sınırı kontrol edilmeli, aşan kısım KKEG"
            },
            KKEGType.CEZA_TAZMINAT: {
                "rate": 1.0, "ref": "KVK 11/1-d - Cezalar gider yazılamaz",
                "rec": "Ceza ve tazminatlar tamamen KKEG"
            },
            KKEGType.GECIKME_FAIZI: {
                "rate": 1.0, "ref": "KVK 11/1-d - Gecikme faizi KKEG",
                "rec": "SGK/Vergi gecikme faizleri tamamen KKEG"
            },
            KKEGType.SEYAHAT_KONAKLAMA: {
                "rate": 1.0, "ref": "GVK 40 - İşle ilgili olmalı",
                "rec": "İş ilgisi belgelenmezse tamamen KKEG - belge kontrol edin"
            },
            KKEGType.BAGIŞ_YARDIM: {
                "rate": 1.0, "ref": "KVK 10/1-c - Bağış indirimi sınırı",
                "rec": "Kurum kazancının %5'i aşan kısım KKEG"
            },
            KKEGType.OZEL_ILETISIM: {
                "rate": 1.0, "ref": "ÖİV Kanunu - Gider yazılamaz",
                "rec": "ÖİV tamamen KKEG"
            },
            KKEGType.KISISEL_GIDER: {
                "rate": 1.0, "ref": "KVK 11/1-a - Kişisel harcamalar",
                "rec": "Ortakların kişisel giderleri tamamen KKEG"
            },
            KKEGType.ORTULU_KAZANC: {
                "rate": 1.0, "ref": "KVK 13 - Transfer fiyatlandırması",
                "rec": "Emsallere uygunluk analizi yapılmalı - potansiyel KKEG"
            }
        }
        
        config = kkeg_config.get(kkeg_type, {"rate": 0.0, "ref": "Manuel inceleme", "rec": "KKEG analizi gerekli"})
        
        return KKEGFinding(
            kkeg_type=kkeg_type,
            account_code=acc_code,
            description=f"[{matched_keyword}] {desc[:45]}",
            amount=amt,
            kkeg_amount=amt * config["rate"],
            kkeg_rate=config["rate"],
            legal_reference=config["ref"],
            document_no=doc_no,
            recommendation=config["rec"]
        )
    
    def _is_duplicate(self, acc_code: str, doc_no: str, kkeg_type: KKEGType = None) -> bool:
        """Mükerrer kayıt kontrolü - Aynı belge+hesap birden fazla eklenmemeli"""
        for f in self.findings:
            # Aynı belge numarası ve hesap kodu varsa mükerrer
            if f.account_code == acc_code and f.document_no == doc_no:
                return True
        return False
    
    def get_summary(self) -> Dict[str, float]:
        """KKEG özeti"""
        summary = {
            "total_amount": sum(f.amount for f in self.findings),
            "total_kkeg": sum(f.kkeg_amount for f in self.findings),
            "finding_count": len(self.findings),
            "by_type": {}
        }
        
        for f in self.findings:
            type_name = f.kkeg_type.value
            if type_name not in summary["by_type"]:
                summary["by_type"][type_name] = {"count": 0, "amount": 0, "kkeg": 0}
            summary["by_type"][type_name]["count"] += 1
            summary["by_type"][type_name]["amount"] += f.amount
            summary["by_type"][type_name]["kkeg"] += f.kkeg_amount
        
        return summary


def generate_kkeg_report_html(findings: List[KKEGFinding], kebir_data: dict = None) -> str:
    """KKEG bulgularını HTML rapor olarak oluştur"""
    if not findings:
        return '<p style="color:#27ae60;">✅ KKEG riski tespit edilmedi.</p>'
    
    # Türe göre grupla
    by_type = {}
    for f in findings:
        type_name = f.kkeg_type.value
        if type_name not in by_type:
            by_type[type_name] = []
        by_type[type_name].append(f)
    
    html_parts = []
    
    for type_name, type_findings in by_type.items():
        total_amt = sum(f.amount for f in type_findings)
        total_kkeg = sum(f.kkeg_amount for f in type_findings)
        
        rows = ""
        for f in type_findings:  # Tüm kayıtları göster
            # Belge numarasından fatura/yevmiye linklerini oluştur
            doc_no_safe = f.document_no.replace("'", "\\'").replace('"', '\\"') if f.document_no else ""
            
            rows += f'''
            <tr>
                <td><span style="font-family:monospace; background:#eee; padding:2px 6px; border-radius:3px;">{f.account_code}</span></td>
                <td title="{f.description}">{f.description[:50]}</td>
                <td style="text-align:right; font-family:monospace;">{f.amount:,.2f}</td>
                <td style="text-align:right; font-family:monospace; color:#e74c3c; font-weight:bold;">{f.kkeg_amount:,.2f}</td>
                <td style="font-size:11px;">{f.legal_reference}</td>
                <td style="text-align:center; white-space:nowrap;">
                    <button onclick="showInvoice('{doc_no_safe}')" style="background:#3498db; color:white; border:none; padding:3px 8px; border-radius:4px; cursor:pointer; font-size:11px; margin-right:3px;" title="Faturayı Görüntüle">📄</button>
                    <button onclick="showJournalEntry('{doc_no_safe}')" style="background:#27ae60; color:white; border:none; padding:3px 8px; border-radius:4px; cursor:pointer; font-size:11px;" title="Yevmiye Kaydı">📋</button>
                </td>
            </tr>
            '''
        
        html_parts.append(f'''
        <div style="margin-bottom:20px;">
            <h4 style="color:#1e3a5f; margin:10px 0;">⚠️ {type_name} ({len(type_findings)} kayıt)</h4>
            <div style="display:flex; gap:15px; margin-bottom:10px;">
                <span style="background:#fff3e0; padding:5px 10px; border-radius:5px;">
                    Toplam: <strong>{total_amt:,.2f} TL</strong>
                </span>
                <span style="background:#ffebee; padding:5px 10px; border-radius:5px;">
                    KKEG: <strong style="color:#e74c3c;">{total_kkeg:,.2f} TL</strong>
                </span>
            </div>
            <div style="max-height:400px; overflow-y:auto; border:1px solid #ddd; border-radius:6px;">
                <table style="width:100%; border-collapse:collapse; font-size:12px;">
                    <thead style="position:sticky; top:0; background:#f5f5f5;">
                        <tr>
                            <th style="padding:8px; text-align:left; border-bottom:1px solid #ddd;">Hesap</th>
                            <th style="padding:8px; text-align:left; border-bottom:1px solid #ddd;">Açıklama</th>
                            <th style="padding:8px; text-align:right; border-bottom:1px solid #ddd;">Tutar</th>
                            <th style="padding:8px; text-align:right; border-bottom:1px solid #ddd;">KKEG</th>
                            <th style="padding:8px; text-align:left; border-bottom:1px solid #ddd;">Dayanak</th>
                            <th style="padding:8px; text-align:center; border-bottom:1px solid #ddd;">İşlem</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </div>
        ''')
    
    # Toplam özet
    grand_total = sum(f.amount for f in findings)
    grand_kkeg = sum(f.kkeg_amount for f in findings)
    
    summary = f'''
    <div style="background:linear-gradient(135deg, #1e3a5f, #3d5a80); color:white; padding:15px; border-radius:8px; margin-bottom:20px;">
        <h3 style="margin:0 0 10px;">📊 KKEG Özeti</h3>
        <div style="display:flex; gap:30px;">
            <div>
                <div style="font-size:12px; opacity:0.8;">Toplam Riskli Tutar</div>
                <div style="font-size:24px; font-weight:bold;">{grand_total:,.2f} TL</div>
            </div>
            <div>
                <div style="font-size:12px; opacity:0.8;">Tahmini KKEG</div>
                <div style="font-size:24px; font-weight:bold; color:#ff6b6b;">{grand_kkeg:,.2f} TL</div>
            </div>
            <div>
                <div style="font-size:12px; opacity:0.8;">Bulgu Sayısı</div>
                <div style="font-size:24px; font-weight:bold;">{len(findings)}</div>
            </div>
        </div>
    </div>
    
    <!-- Fatura/Yevmiye Modal -->
    <div id="docModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:1000;">
        <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); background:white; padding:20px; border-radius:10px; max-width:90%; max-height:80%; overflow:auto;">
            <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
                <h3 id="modalTitle" style="margin:0;">Belge Detayı</h3>
                <button onclick="closeModal()" style="background:#e74c3c; color:white; border:none; padding:5px 15px; border-radius:5px; cursor:pointer;">✕ Kapat</button>
            </div>
            <div id="modalContent" style="min-width:500px;"></div>
        </div>
    </div>
    
    <script>
    // Kebir verisi (JSON olarak aktarıldı)
    var kebirData = {kebir_json};
    
    function showInvoice(docNo) {{
        document.getElementById('modalTitle').textContent = '📄 Fatura: ' + docNo;
        
        var content = '<div style="padding:10px;">';
        content += '<p><strong>Belge No:</strong> ' + docNo + '</p>';
        content += '<p style="color:#666;">Not: Fatura XML görüntülemesi için <strong>Fatura-Defter Mutabakat</strong> raporunu kullanın.</p>';
        content += '<p style="margin-top:15px;">Bu belgeye ait defter kaydını görmek için <strong>Yevmiye</strong> butonuna tıklayın.</p>';
        content += '</div>';
        
        document.getElementById('modalContent').innerHTML = content;
        document.getElementById('docModal').style.display = 'block';
    }}
    
    function showJournalEntry(docNo) {{
        document.getElementById('modalTitle').textContent = '📋 Yevmiye Kaydı: ' + docNo;
        
        var content = '<table style="width:100%; border-collapse:collapse;">';
        content += '<thead><tr style="background:#1e3a5f; color:white;">';
        content += '<th style="padding:10px; border:1px solid #ddd;">Hesap Kodu</th>';
        content += '<th style="padding:10px; border:1px solid #ddd;">Açıklama</th>';
        content += '<th style="padding:10px; border:1px solid #ddd; text-align:right;">Borç</th>';
        content += '<th style="padding:10px; border:1px solid #ddd; text-align:right;">Alacak</th>';
        content += '</tr></thead><tbody>';
        
        var found = false;
        
        // Kebir verisinde bu belgeyi ara
        for (var key in kebirData) {{
            if (key.indexOf(docNo) !== -1 || docNo.indexOf(key) !== -1) {{
                var doc = kebirData[key];
                if (doc && doc.Lines) {{
                    found = true;
                    for (var i = 0; i < doc.Lines.length; i++) {{
                        var line = doc.Lines[i];
                        var debit = (line.DC === 'D' || line.DC === 'B') ? line.Amt : 0;
                        var credit = (line.DC === 'C' || line.DC === 'A') ? line.Amt : 0;
                        
                        content += '<tr style="background:' + (i % 2 === 0 ? '#fff' : '#f9f9f9') + ';">';
                        content += '<td style="padding:8px; border:1px solid #ddd; font-family:monospace;">' + (line.Acc || '') + '</td>';
                        content += '<td style="padding:8px; border:1px solid #ddd;">' + (line.Desc || '').substring(0, 50) + '</td>';
                        content += '<td style="padding:8px; border:1px solid #ddd; text-align:right; font-family:monospace;">' + (debit > 0 ? debit.toLocaleString('tr-TR', {{minimumFractionDigits:2}}) : '-') + '</td>';
                        content += '<td style="padding:8px; border:1px solid #ddd; text-align:right; font-family:monospace;">' + (credit > 0 ? credit.toLocaleString('tr-TR', {{minimumFractionDigits:2}}) : '-') + '</td>';
                        content += '</tr>';
                    }}
                }}
                break;
            }}
        }}
        
        if (!found) {{
            content += '<tr><td colspan="4" style="padding:15px; text-align:center; color:#666;">';
            content += 'Belge No: <strong>' + docNo + '</strong><br><br>';
            content += 'Bu belge numarası kebir verisinde bulunamadı.';
            content += '</td></tr>';
        }}
        
        content += '</tbody></table>';
        document.getElementById('modalContent').innerHTML = content;
        document.getElementById('docModal').style.display = 'block';
    }}
    
    function closeModal() {{
        document.getElementById('docModal').style.display = 'none';
    }}
    
    document.getElementById('docModal').addEventListener('click', function(e) {{
        if (e.target === this) closeModal();
    }});
    </script>
    '''
    
    # Kebir verisini JSON'a dönüştür
    import json
    kebir_json_str = "{}"
    if kebir_data:
        try:
            kebir_json_str = json.dumps(kebir_data, ensure_ascii=False, default=str)
        except:
            kebir_json_str = "{}"
    
    # Placeholder'ı kebir JSON ile değiştir
    summary = summary.replace('{kebir_json}', kebir_json_str)
    
    return summary + ''.join(html_parts)


if __name__ == "__main__":
    # Test
    print("KKEG Tespit Modülü yüklendi.")
    detector = KKEGDetector(year=2024)
    print(f"Binek araç aylık kira sınırı: {detector.binek_limits['monthly_rent']:,} TL")
