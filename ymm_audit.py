# -*- coding: utf-8 -*-
"""
YMM Denetim Modülü - Aylık Mizan Kontrolleri ve Risk Analizi

Bu modül mevcut e-Mutabakat sistemine entegre edilir ve
YMM denetim personeli için kapsamlı kontroller sağlar.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime
import re


class RiskLevel(Enum):
    """Risk seviyeleri"""
    CRITICAL = "Kritik"
    HIGH = "Yüksek"
    MEDIUM = "Orta"
    LOW = "Düşük"
    INFO = "Bilgi"


class FindingType(Enum):
    """Bulgu türleri"""
    TERS_BAKIYE = "Ters Bakiye"
    NAKIT_SINIR = "Nakit Sınır Aşımı"
    ADAT = "Adat Hesaplaması"
    ORTULU_SERMAYE = "Örtülü Sermaye"
    BINEK_KISIT = "Binek Araç Kısıtlaması"
    KDV_UYUMSUZLUK = "KDV Uyumsuzluğu"
    BEYANNAME_FARK = "Beyanname Farkı"
    STOPAJ_FARK = "Stopaj Farkı"
    FATURA_EKSIK = "Fatura Eksikliği"
    KAYIT_HATASI = "Kayıt Hatası"
    BILGI = "Bilgilendirme"  # Bilgi amaçlı bulgular


@dataclass
class AuditFinding:
    """Denetim bulgusu"""
    finding_type: FindingType
    risk_level: RiskLevel
    account_code: str
    description: str
    amount: float = 0.0
    recommended_action: str = ""
    reference: str = ""  # Fatura no, belge no vb.
    

@dataclass
class AccountBalance:
    """Hesap bakiyesi"""
    code: str
    name: str
    debit: float = 0.0
    credit: float = 0.0
    
    @property
    def balance(self) -> float:
        return self.debit - self.credit
    
    @property
    def is_debit_balance(self) -> bool:
        return self.balance > 0
    
    @property
    def is_credit_balance(self) -> bool:
        return self.balance < 0


@dataclass
class MizanData:
    """Mizan verisi"""
    company_name: str = ""
    period: str = ""
    accounts: Dict[str, AccountBalance] = field(default_factory=dict)
    
    def get_account(self, code: str) -> Optional[AccountBalance]:
        """Hesap koduna göre bakiye getir"""
        return self.accounts.get(code)
    
    def get_accounts_starting_with(self, prefix: str) -> List[AccountBalance]:
        """Belirli prefixle başlayan hesapları getir"""
        return [acc for code, acc in self.accounts.items() if code.startswith(prefix)]
    
    def get_total_balance(self, prefix: str) -> float:
        """Belirli hesap grubunun toplam bakiyesi"""
        return sum(acc.balance for acc in self.get_accounts_starting_with(prefix))


@dataclass
class ExecutiveReportData:
    """Yönetici raporu verileri"""
    period: str = ""
    company_name: str = ""
    
    # Özet bilgiler
    total_sales: float = 0.0
    total_purchases: float = 0.0
    gross_profit: float = 0.0
    gross_margin: float = 0.0
    net_profit: float = 0.0
    
    # Kümülatif
    ytd_sales: float = 0.0
    ytd_purchases: float = 0.0
    ytd_gross_profit: float = 0.0
    
    # Top listeler
    top_suppliers: List[Tuple[str, float]] = field(default_factory=list)
    top_customers: List[Tuple[str, float]] = field(default_factory=list)
    top_expenses: List[Tuple[str, float]] = field(default_factory=list)
    top_kdv_entries: List[Tuple[str, float]] = field(default_factory=list)  # 191'deki en yüksek 5
    top_760_pazarlama: List[Tuple[str, float]] = field(default_factory=list)  # Pazarlama Giderleri
    top_770_yonetim: List[Tuple[str, float]] = field(default_factory=list)  # Genel Yönetim Giderleri
    
    # Finansal göstergeler
    current_ratio: float = 0.0
    quick_ratio: float = 0.0
    debt_equity_ratio: float = 0.0
    interest_expense: float = 0.0
    depreciation: float = 0.0
    
    # Nakit akış
    cash_start: float = 0.0
    cash_end: float = 0.0
    net_cash_change: float = 0.0
    
    # KDV
    calculated_vat: float = 0.0
    deductible_vat: float = 0.0
    payable_vat: float = 0.0
    
    # Denetim bulguları
    findings_critical: int = 0
    findings_high: int = 0
    findings_medium: int = 0
    findings_low: int = 0


# Hesap karakterleri (Normal bakiye yönü)
ACCOUNT_CHARACTERS = {
    # Aktif hesaplar - Normal: Borç bakiye
    "100": "D",  # Kasa
    "101": "D",  # Alınan Çekler
    "102": "D",  # Bankalar
    "103": "C",  # Verilen Çekler (Düzenleyici - Alacak)
    "120": "D",  # Alıcılar
    "121": "D",  # Alacak Senetleri
    "122": "C",  # Alacak Senetleri Reeskontu (-)
    "126": "D",  # Verilen Depozitolar
    "127": "D",  # Diğer Ticari Alacaklar
    "128": "D",  # Şüpheli Ticari Alacaklar
    "129": "C",  # Şüpheli Ticari Alacaklar Karşılığı (-)
    "131": "D",  # Ortaklardan Alacaklar
    "132": "D",  # İştiraklerden Alacaklar
    "133": "D",  # Bağlı Ortaklıklardan Alacaklar
    "135": "D",  # Personelden Alacaklar
    "136": "D",  # Diğer Çeşitli Alacaklar
    "150": "D",  # İlk Madde Malzeme
    "151": "D",  # Yarı Mamuller
    "152": "D",  # Mamuller
    "153": "D",  # Ticari Mallar
    "157": "D",  # Diğer Stoklar
    "158": "C",  # Stok Değer Düşüklüğü Karşılığı (-)
    "159": "D",  # Verilen Sipariş Avansları
    "180": "D",  # Gelecek Aylara Ait Giderler
    "181": "D",  # Gelir Tahakkukları
    "190": "D",  # Devreden KDV
    "191": "D",  # İndirilecek KDV
    "192": "D",  # Diğer KDV
    "193": "D",  # Peşin Ödenen Vergiler ve Fonlar
    "250": "D",  # Arazi ve Arsalar
    "251": "D",  # Yeraltı ve Yerüstü Düzenleri
    "252": "D",  # Binalar
    "253": "D",  # Tesis, Makine ve Cihazlar
    "254": "D",  # Taşıtlar
    "255": "D",  # Demirbaşlar
    "256": "D",  # Diğer Maddi Duran Varlıklar
    "257": "C",  # Birikmiş Amortismanlar (-)
    "258": "D",  # Yapılmakta Olan Yatırımlar
    "260": "D",  # Haklar
    "264": "D",  # Özel Maliyetler
    "268": "C",  # Birikmiş Amortismanlar (Maddi Olmayan) (-)
    
    # Pasif hesaplar - Normal: Alacak bakiye
    "300": "C",  # Banka Kredileri
    "301": "C",  # Finansal Kiralama İşlemlerinden Borçlar
    "303": "C",  # Uzun Vadeli Kredilerin Anapara Taksitleri ve Faizleri
    "320": "C",  # Satıcılar
    "321": "C",  # Borç Senetleri
    "322": "C",  # Borç Senetleri Reeskontu (-)
    "326": "C",  # Alınan Depozito ve Teminatlar
    "329": "C",  # Diğer Ticari Borçlar
    "331": "C",  # Ortaklara Borçlar
    "332": "C",  # İştiraklere Borçlar
    "333": "C",  # Bağlı Ortaklıklara Borçlar
    "335": "C",  # Personele Borçlar
    "336": "C",  # Diğer Çeşitli Borçlar
    "340": "C",  # Alınan Sipariş Avansları
    "349": "C",  # Alınan Diğer Avanslar
    "360": "C",  # Ödenecek Vergi ve Fonlar
    "361": "C",  # Ödenecek Sosyal Güvenlik Kesintileri
    "368": "C",  # Vadesi Geçmiş, Ertelenmiş veya Taksitlendirilmiş Vergi
    "370": "C",  # Dönem Karı Vergi ve Diğer Yasal Yükümlülük Karşılıkları
    "371": "D",  # Dönem Karının Peşin Ödenen Vergi ve Diğer Yükümlülükleri (-)
    "372": "C",  # Kıdem Tazminatı Karşılığı
    "373": "C",  # Maliyet Giderleri Karşılığı
    "380": "C",  # Gelecek Aylara Ait Gelirler
    "381": "C",  # Gider Tahakkukları
    "391": "C",  # Hesaplanan KDV
    "392": "C",  # Diğer KDV
    
    # Uzun Vadeli Yabancı Kaynaklar (Sınıf 4)
    "400": "C",  # Banka Kredileri (Uzun Vadeli)
    "420": "C",  # Satıcılar (Uzun Vadeli)
    "421": "C",  # Borç Senetleri (Uzun Vadeli)
    "431": "C",  # Ortaklara Borçlar (Uzun Vadeli)
    "472": "C",  # Kıdem Tazminatı Karşılığı (Uzun Vadeli)
    "480": "C",  # Gelecek Yıllara Ait Gelirler
    
    # Özkaynak - Normal: Alacak bakiye
    "500": "C",  # Sermaye
    "501": "D",  # Ödenmemiş Sermaye (-)
    "502": "C",  # Sermaye Düzeltmesi Olumlu Farkları
    "520": "C",  # Hisse Senedi İhraç Primleri
    "522": "C",  # MDV Yeniden Değerleme Artışları
    "540": "C",  # Yasal Yedekler
    "542": "C",  # Olağanüstü Yedekler
    "549": "C",  # Özel Fonlar
    "570": "C",  # Geçmiş Yıllar Karları
    "580": "D",  # Geçmiş Yıllar Zararları (-)
    "590": "C",  # Dönem Net Karı
    "591": "D",  # Dönem Net Zararı (-)
    
    # Gelir hesapları - Normal: Alacak bakiye
    "600": "C",  # Yurt İçi Satışlar
    "601": "C",  # Yurt Dışı Satışlar
    "602": "C",  # Diğer Gelirler
    "610": "D",  # Satış İskontoları (Düzenleyici)
    "640": "C",  # İştirak Gelirleri
    "642": "C",  # Faiz Gelirleri
    "644": "C",  # Konusu Kalmayan Karşılıklar
    "646": "C",  # Kambiyo Karları
    "649": "C",  # Diğer Olağan Gelir ve Karlar
    
    # Gider hesapları - Normal: Borç bakiye
    "620": "D",  # Satılan Mamuller Maliyeti
    "621": "D",  # Satılan Ticari Mallar Maliyeti
    "622": "D",  # Satılan Hizmet Maliyeti
    "630": "D",  # Araştırma Geliştirme Giderleri
    "631": "D",  # Pazarlama Satış Dağıtım Giderleri
    "632": "D",  # Genel Yönetim Giderleri
    "653": "D",  # Komisyon Giderleri
    "654": "D",  # Karşılık Giderleri
    "656": "D",  # Kambiyo Zararları
    "657": "D",  # Reeskont Faiz Giderleri
    "659": "D",  # Diğer Olağan Gider ve Zararlar
    "660": "D",  # Kısa Vadeli Borçlanma Giderleri
    "661": "D",  # Uzun Vadeli Borçlanma Giderleri
    
    # Maliyet hesapları - Normal: Borç bakiye
    "710": "D",  # Direkt İlk Madde Malzeme
    "720": "D",  # Direkt İşçilik
    "730": "D",  # Genel Üretim Giderleri
    "740": "D",  # Hizmet Üretim Maliyeti
    "750": "D",  # Araştırma Geliştirme Giderleri
    "760": "D",  # Pazarlama Satış Dağıtım Giderleri
    "770": "D",  # Genel Yönetim Giderleri
    "780": "D",  # Finansman Giderleri
}


def get_account_normal_character(account_code: str) -> str:
    """
    Hesap kodunun normal bakiye karakterini döndür.
    D = Borç (Debit), C = Alacak (Credit)
    """
    # Önce tam eşleşme
    if account_code in ACCOUNT_CHARACTERS:
        return ACCOUNT_CHARACTERS[account_code]
    
    # 3 haneli prefix ile eşleşme
    prefix = account_code[:3]
    if prefix in ACCOUNT_CHARACTERS:
        return ACCOUNT_CHARACTERS[prefix]
    
    # Varsayılan: İlk rakama göre
    first_digit = account_code[0] if account_code else "0"
    if first_digit in ["1", "2", "6", "7"]:  # Aktif ve Gider
        return "D"
    elif first_digit in ["3", "4", "5"]:  # Pasif ve Özkaynak
        return "C"
    
    return "D"  # Default


def check_reverse_balance(account: AccountBalance) -> Optional[AuditFinding]:
    """
    Hesabın ters bakiye verip vermediğini kontrol et.
    """
    normal_char = get_account_normal_character(account.code)
    
    # Bakiye kontrolü
    if normal_char == "D" and account.is_credit_balance:
        # Borç bakiyesi vermesi gereken hesap alacak bakiye veriyor
        return AuditFinding(
            finding_type=FindingType.TERS_BAKIYE,
            risk_level=RiskLevel.HIGH,
            account_code=account.code,
            description=f"{account.name} hesabı ters (alacak) bakiye veriyor: {abs(account.balance):,.2f} TL",
            amount=abs(account.balance),
            recommended_action=get_reverse_balance_action(account.code)
        )
    elif normal_char == "C" and account.is_debit_balance:
        # Alacak bakiyesi vermesi gereken hesap borç bakiye veriyor
        return AuditFinding(
            finding_type=FindingType.TERS_BAKIYE,
            risk_level=RiskLevel.HIGH,
            account_code=account.code,
            description=f"{account.name} hesabı ters (borç) bakiye veriyor: {abs(account.balance):,.2f} TL",
            amount=abs(account.balance),
            recommended_action=get_reverse_balance_action(account.code)
        )
    
    return None


def get_reverse_balance_action(account_code: str) -> str:
    """Ters bakiye için önerilen düzeltme aksiyonu"""
    prefix = account_code[:3]
    
    actions = {
        "100": "Kayıt dışı hasılat veya hatalı çıkış kaydı kontrol edilmeli",
        "102": "Banka ekstresi ile mutabakat yapılmalı",
        "103": "Çek vadesinden önce kaydedilmiş veya mükerrer kayıt kontrol edilmeli",
        "120": "Müşteriden alınan avans 340 hesaba virmanlanmalı",
        "121": "Tahsil edilen senetler kontrol edilmeli",
        "150": "Faturasız mal satışı veya stok sayımı yapılmalı",
        "151": "Üretim kayıtları kontrol edilmeli",
        "152": "Mamul stok sayımı yapılmalı",
        "153": "Faturasız mal satışı veya alış faturası eksik kontrol edilmeli",
        "257": "Amortisman tablosu ile mizan karşılaştırılmalı",
        "300": "Fazla ödeme yapılmış, banka ile mutabakat gerekli",
        "320": "Fazla ödeme 159 hesaba virmanlanmalı veya iade alınmalı",
        "321": "Fazla ödeme kontrol edilmeli",
        "360": "Fazla ödeme için mahsup dilekçesi verilmeli veya kayıt hatası düzeltilmeli",
        "361": "Fazla ödeme için SGK ile mutabakat yapılmalı",
        "128": "Şüpheli alacaklar karşılık hesabı (129) ile kontrol edilmeli",
        "129": "Şüpheli alacak karşılığı ayrılmadan önce alacak tahsil edilmiş olabilir",
        "253": "Makine/tesis envanter kaydı ve amortisman tablosu kontrol edilmeli",
        "370": "Dönem karı vergi karşılığı hesaplaması kontrol edilmeli",
        "372": "Kıdem tazminatı hesaplaması ve aktüeryal değerleme kontrol edilmeli",
        "472": "Uzun vadeli kıdem tazminatı karşılığı aktüeryal raporla uyumlu olmalı",
        "500": "Sermaye artırımı veya azaltımı kayıtları kontrol edilmeli",
    }
    
    return actions.get(prefix, "Hesap detayı incelenmeli ve düzeltme kaydı yapılmalı")


# 2024 Binek Araç Kısıtları
VEHICLE_LIMITS_2024 = {
    "monthly_rent_limit": 26000,  # Aylık kira sınırı TL
    "expense_restriction_rate": 0.30,  # %30 KKEG
    "depreciation_limit_1": 790000,  # Amortisman sınırı 1
    "depreciation_limit_2": 1500000,  # Amortisman sınırı 2 (ÖTV+KDV dahil)
}

# Nakit işlem sınırı
CASH_TRANSACTION_LIMIT = 30000  # TL


class YMMAuditEngine:
    """YMM Denetim Motoru"""
    
    def __init__(self):
        self.findings: List[AuditFinding] = []
        self.mizan: Optional[MizanData] = None
        self.executive_report: Optional[ExecutiveReportData] = None
        self.kebir_data: dict = {}  # Kebir verisi (191 Top 5 için)
        self.sales_by_customer: Dict[str, float] = {}  # Müşteri bazlı satış
        self.purchases_by_supplier: Dict[str, float] = {}  # Satıcı bazlı alış
        self.kdv_by_supplier: Dict[str, float] = {}  # Satıcı bazlı KDV (Top 5 KDV için)
        self.invoice_to_supplier: Dict[str, str] = {}  # Fatura no -> Satıcı adı eşleme
        
        # Fatura KDV toplamları (beyanname mutabakatı için)
        self.purchase_kdv_total: float = 0.0  # Alış faturalarından toplam KDV
        self.sales_kdv_total: float = 0.0      # Satış faturalarından toplam KDV
        self.purchase_matrah_total: float = 0.0  # Alış faturalarından toplam matrah
        self.sales_matrah_total: float = 0.0     # Satış faturalarından toplam matrah
        self.purchase_invoice_count: int = 0
        self.sales_invoice_count: int = 0
        
        # Excel Muavin Defter Toplamları (e-Arşiv dahil gerçek tutarlar)
        self.excel_191_total: float = 0.0  # 191 İndirilecek KDV toplamı (Excel'den)
        self.excel_391_total: float = 0.0  # 391 Hesaplanan KDV toplamı (Kebir'den)
    
    def load_invoices_from_zip(self, zip_path: str, invoice_type: str = "sales") -> int:
        """
        ZIP dosyasından faturaları yükle ve firma bazlı topla
        invoice_type: 'sales' veya 'purchase'
        Ayrıca KDV ve matrah toplamlarını sakla (beyanname mutabakatı için)
        """
        import zipfile
        import xml.etree.ElementTree as ET
        
        ns = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
        }
        
        count = 0
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.xml'):
                        try:
                            content = zf.read(name)
                            root = ET.fromstring(content)
                            
                            # Fatura tutarı (KDV dahil toplam)
                            payable = root.find('.//cbc:PayableAmount', ns)
                            amount = float(payable.text) if payable is not None else 0
                            
                            # KDV tutarı (TaxTotal -> TaxAmount)
                            tax_amount_elem = root.find('.//cac:TaxTotal/cbc:TaxAmount', ns)
                            kdv_amount = float(tax_amount_elem.text) if tax_amount_elem is not None else 0
                            
                            # Matrah (TaxableAmount veya LineExtensionAmount)
                            taxable_elem = root.find('.//cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount', ns)
                            if taxable_elem is not None:
                                matrah = float(taxable_elem.text)
                            else:
                                # Alternatif: LineExtensionAmount = Matrah
                                line_ext = root.find('.//cbc:LineExtensionAmount', ns)
                                matrah = float(line_ext.text) if line_ext is not None else (amount - kdv_amount)
                            
                            if invoice_type == "sales":
                                # Alıcı bilgisi
                                party = root.find('.//cac:AccountingCustomerParty/cac:Party/cac:PartyName/cbc:Name', ns)
                                self.sales_kdv_total += kdv_amount
                                self.sales_matrah_total += matrah
                                self.sales_invoice_count += 1
                            else:
                                # Satıcı bilgisi
                                party = root.find('.//cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name', ns)
                                self.purchase_kdv_total += kdv_amount
                                self.purchase_matrah_total += matrah
                                self.purchase_invoice_count += 1
                            
                            party_name = party.text[:40] if party is not None else "Bilinmiyor"
                            
                            if invoice_type == "sales":
                                self.sales_by_customer[party_name] = self.sales_by_customer.get(party_name, 0) + amount
                            else:
                                self.purchases_by_supplier[party_name] = self.purchases_by_supplier.get(party_name, 0) + amount
                                # KDV by supplier (Top 5 KDV için firma bazlı)
                                self.kdv_by_supplier[party_name] = self.kdv_by_supplier.get(party_name, 0) + kdv_amount
                                # Fatura numarası -> Satıcı eşlemesi (gider atribüsyonu için)
                                invoice_id = root.find('.//cbc:ID', ns)
                                if invoice_id is not None and invoice_id.text:
                                    self.invoice_to_supplier[invoice_id.text] = party_name
                            
                            count += 1
                        except Exception:
                            continue
        except Exception as e:
            print(f"ZIP yükleme hatası: {e}")
        
        return count
    
    def load_invoices_from_xml(self, xml_path: str, invoice_type: str = "sales") -> int:
        """
        Tek XML dosyasından fatura yükle
        invoice_type: 'sales' veya 'purchase'
        """
        import xml.etree.ElementTree as ET
        
        ns = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
        }
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Fatura tutarı (KDV dahil toplam)
            payable = root.find('.//cbc:PayableAmount', ns)
            amount = float(payable.text) if payable is not None else 0
            
            # KDV tutarı
            tax_amount_elem = root.find('.//cac:TaxTotal/cbc:TaxAmount', ns)
            kdv_amount = float(tax_amount_elem.text) if tax_amount_elem is not None else 0
            
            # Matrah
            taxable_elem = root.find('.//cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount', ns)
            if taxable_elem is not None:
                matrah = float(taxable_elem.text)
            else:
                line_ext = root.find('.//cbc:LineExtensionAmount', ns)
                matrah = float(line_ext.text) if line_ext is not None else (amount - kdv_amount)
            
            if invoice_type == "sales":
                party = root.find('.//cac:AccountingCustomerParty/cac:Party/cac:PartyName/cbc:Name', ns)
                self.sales_kdv_total += kdv_amount
                self.sales_matrah_total += matrah
                self.sales_invoice_count += 1
            else:
                party = root.find('.//cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name', ns)
                self.purchase_kdv_total += kdv_amount
                self.purchase_matrah_total += matrah
                self.purchase_invoice_count += 1
            
            party_name = party.text[:40] if party is not None else "Bilinmiyor"
            
            if invoice_type == "sales":
                self.sales_by_customer[party_name] = self.sales_by_customer.get(party_name, 0) + amount
            else:
                self.purchases_by_supplier[party_name] = self.purchases_by_supplier.get(party_name, 0) + amount
                self.kdv_by_supplier[party_name] = self.kdv_by_supplier.get(party_name, 0) + kdv_amount
                invoice_id = root.find('.//cbc:ID', ns)
                if invoice_id is not None and invoice_id.text:
                    self.invoice_to_supplier[invoice_id.text] = party_name
            
            return 1
            
        except Exception as e:
            print(f"XML yükleme hatası: {e}")
            return 0
    
    def load_191_from_kebir(self) -> float:
        """
        191 hesabının net borç toplamını Kebir'den hesapla.
        
        Returns:
            Toplam net borç (Debit - Credit) tutarı
        """
        if not self.kebir_data:
            return 0.0
        
        total_debit = 0.0
        total_credit = 0.0
        
        for doc_no, doc_data in self.kebir_data.items():
            for line in doc_data.get('Lines', []):
                acc = line.get('Acc', '')
                if acc.startswith('191'):
                    dc = line.get('DC', 'D')
                    amt = line.get('Amt', 0) or 0
                    
                    if dc == 'D':  # Debit/Borç
                        total_debit += amt
                    else:  # Credit/Alacak
                        total_credit += amt
        
        return total_debit - total_credit
    
    def load_391_from_kebir(self) -> float:
        """
        391 hesabının net alacak toplamını Kebir'den hesapla.
        
        Returns:
            Toplam net alacak (Credit - Debit) tutarı
        """
        if not self.kebir_data:
            return 0.0
        
        total_debit = 0.0
        total_credit = 0.0
        
        for doc_no, doc_data in self.kebir_data.items():
            for line in doc_data.get('Lines', []):
                acc = line.get('Acc', '')
                if acc.startswith('391'):
                    dc = line.get('DC', 'D')
                    amt = line.get('Amt', 0) or 0
                    
                    if dc == 'D':  # Debit/Borç
                        total_debit += amt
                    else:  # Credit/Alacak
                        total_credit += amt
        
        return total_credit - total_debit
    
    def get_top_customers(self, limit: int = 5) -> List[Tuple[str, float]]:
        """En çok satış yapılan müşteriler - Bilinmiyor olanları hariç tut"""
        # Bilinmiyor olanları filtrele
        filtered = {k: v for k, v in self.sales_by_customer.items() if k != "Bilinmiyor"}
        sorted_customers = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
        return sorted_customers[:limit]
    
    def get_top_suppliers(self, limit: int = 5) -> List[Tuple[str, float]]:
        """En çok alım yapılan satıcılar"""
        sorted_suppliers = sorted(self.purchases_by_supplier.items(), key=lambda x: x[1], reverse=True)
        return sorted_suppliers[:limit]
    
    def get_top_kdv_by_supplier(self, limit: int = 5) -> List[Tuple[str, float]]:
        """Top 5 KDV - satıcı bazlı (Fatura verilerinden)"""
        # Alış faturalarından satıcı bazlı KDV topla
        kdv_by_supplier: Dict[str, float] = {}
        
        # Eğer fatura verisi varsa, satıcı bazlı KDV hesapla
        for supplier, amount in self.purchases_by_supplier.items():
            if supplier != "Bilinmiyor":
                # Yaklaşık KDV = Tutar * 0.20 / 1.20 (fatura tutarından)
                kdv_estimate = amount * 0.20 / 1.20
                kdv_by_supplier[supplier] = kdv_estimate
        
        if kdv_by_supplier:
            sorted_kdv = sorted(kdv_by_supplier.items(), key=lambda x: x[1], reverse=True)
            return sorted_kdv[:limit]
        
        # Fallback: Kebir'den belge bazlı (eski yöntem)
        return self.get_top_kdv_entries(limit)
    
    def get_top_expense_by_account(self, account_prefix: str, limit: int = 5) -> List[Tuple[str, float]]:
        """
        Belirli bir gider hesabı için belge bazlı Top 5 çek
        account_prefix: "760" veya "770" gibi
        """
        expense_by_doc = {}
        
        for doc_no, doc_data in self.kebir_data.items():
            lines = doc_data.get("Lines", [])
            for line in lines:
                acc = line.get("Acc", "")
                if acc.startswith(account_prefix):
                    desc = line.get("Desc", doc_no)[:40]
                    amt = float(line.get("Amt", 0))
                    dc = line.get("DC", "D")
                    if dc in ["D", "B"]:  # Borç = gider
                        # Belge bazlı grupla
                        if desc not in expense_by_doc:
                            expense_by_doc[desc] = 0
                        expense_by_doc[desc] += amt
        
        # Fatura verilerinden satıcı adı eşle
        result = []
        for desc, amt in sorted(expense_by_doc.items(), key=lambda x: x[1], reverse=True)[:limit]:
            # Desc genelde belge numarası, satıcı bilgisini al
            supplier_name = self._get_supplier_for_doc(desc)
            result.append((supplier_name if supplier_name else desc, amt))
        
        return result
    
    def _get_supplier_for_doc(self, doc_no: str) -> Optional[str]:
        """Belge numarasından satıcı adı bul (fatura verisinden)"""
        # Direkt eşleşme ara
        if doc_no in self.invoice_to_supplier:
            return self.invoice_to_supplier[doc_no]
        
        # Kısmi eşleşme ara (bazen kebir'de farklı format olabiliyor)
        for inv_id, supplier in self.invoice_to_supplier.items():
            if doc_no in inv_id or inv_id in doc_no:
                return supplier
        
        return None

    
    def load_mizan_from_kebir(self, kebir_data: dict) -> MizanData:
        """Kebir verisinden mizan oluştur"""
        self.kebir_data = kebir_data  # Sakla
        mizan = MizanData()
        
        # Standart hesap adları
        account_names = {
            '100': 'Kasa',
            '102': 'Bankalar',
            '120': 'Alıcılar',
            '150': 'İlk Madde ve Malzeme',
            '191': 'İndirilecek KDV',
            '320': 'Satıcılar',
            '331': 'Ortaklara Borçlar',
            '360': 'Ödenecek Vergi ve Fonlar',
            '391': 'Hesaplanan KDV',
            '600': 'Yurt İçi Satışlar',
            '601': 'Yurt Dışı Satışlar',
            '740': 'Hizmet Üretim Maliyeti',
            '770': 'Genel Yönetim Giderleri'
        }
        
        # Kebir'den hesap bazlı toplam
        for doc_no, doc_data in kebir_data.items():
            lines = doc_data.get("Lines", [])
            for line in lines:
                acc_code = line.get("Acc", "")
                if not acc_code:
                    continue
                
                if acc_code not in mizan.accounts:
                    # Önce standart isim sözlüğüne bak
                    acc_name = account_names.get(acc_code, acc_code)
                    
                    mizan.accounts[acc_code] = AccountBalance(
                        code=acc_code,
                        name=acc_name
                    )
                
                dc = line.get("DC", "D")
                amt = float(line.get("Amt", 0))
                
                if dc in ["D", "B"]:  # Borç
                    mizan.accounts[acc_code].debit += amt
                else:  # Alacak
                    mizan.accounts[acc_code].credit += amt
        
        self.mizan = mizan
        return mizan
    
    def get_top_kdv_entries(self, limit: int = 5) -> List[Tuple[str, float]]:
        """Firma bazında en yüksek 5 KDV kaydı"""
        
        # Önce fatura verisinden firma bazlı KDV topla (tercih edilen)
        if hasattr(self, 'kdv_by_supplier') and self.kdv_by_supplier:
            sorted_kdv = sorted(self.kdv_by_supplier.items(), key=lambda x: x[1], reverse=True)
            return [(name[:40], amt) for name, amt in sorted_kdv[:limit]]
        
        # Fallback: purchases_by_supplier (toplam tutar, KDV değil ama yaklaşık)
        if self.purchases_by_supplier:
            sorted_suppliers = sorted(self.purchases_by_supplier.items(), key=lambda x: x[1], reverse=True)
            # KDV yaklaşık %20 olarak hesapla
            return [(name[:40], amt * 0.20) for name, amt in sorted_suppliers[:limit]]
        
        # Son fallback: Kebir'den (eski yöntem - fatura no gösterir)
        kdv_entries = []
        if hasattr(self, 'ledger_map') and self.ledger_map:
            for doc_no, doc_data in self.ledger_map.items():
                if isinstance(doc_data, dict):
                    lines = doc_data.get("Lines", [])
                    for line in lines:
                        if isinstance(line, dict):
                            acc_code = line.get("Acc", "")
                            if acc_code.startswith("191"):
                                desc = doc_data.get("Desc", doc_no)[:40]
                                amt = float(line.get("Amt", 0) or 0)
                                if amt > 0:
                                    kdv_entries.append((desc, amt))
        
        kdv_entries.sort(key=lambda x: x[1], reverse=True)
        return kdv_entries[:limit]
    
    def run_all_checks(self) -> List[AuditFinding]:
        """Tüm kontrolleri çalıştır"""
        self.findings = []
        
        if not self.mizan:
            return self.findings
        
        # Faz 1: Ters Bakiye Kontrolleri
        self._check_reverse_balances()
        
        # Faz 2: Nakit Kontrolleri
        self._check_cash_controls()
        
        # Faz 3: 30.000 TL Nakit Sınır Kontrolü (VUK 320/323)
        self._check_cash_limit_30k()
        
        # Faz 4: Pasif Hesap Kontrolleri
        self._check_liability_controls()
        
        # Faz 5: Binek Araç Gider Kısıtlaması
        self._check_vehicle_expense_limits()
        
        # Faz 6: KKEG Kontrolü (Yarı Otomatik)
        self._check_kkeg()
        
        return self.findings
    
    def _check_kkeg(self):
        """KKEG (Kanunen Kabul Edilmeyen Gider) kontrolü"""
        try:
            from kkeg_detector import KKEGDetector, KKEGFinding
            
            if not self.kebir_data:
                return
            
            detector = KKEGDetector(year=2024)
            kkeg_findings = detector.detect_from_kebir(self.kebir_data)
            
            # KKEG bulgularını AuditFinding formatına dönüştür
            for kf in kkeg_findings[:20]:  # İlk 20 bulgu
                self.findings.append(AuditFinding(
                    finding_type=FindingType.KAYIT_HATASI,  # veya yeni KKEG tipi
                    risk_level=RiskLevel.MEDIUM if kf.kkeg_rate < 1 else RiskLevel.HIGH,
                    account_code=kf.account_code,
                    description=f"[KKEG] {kf.kkeg_type.value}: {kf.description[:50]}",
                    amount=kf.kkeg_amount,
                    recommended_action=kf.recommendation,
                    reference=kf.legal_reference
                ))
            
            # KKEG bulgularını ayrıca sakla (rapor için)
            self.kkeg_findings = kkeg_findings
            
        except ImportError:
            # KKEG modülü yüklü değilse sessizce geç
            self.kkeg_findings = []
        except Exception as e:
            print(f"KKEG kontrolü hatası: {e}")
            self.kkeg_findings = []
    
    def _check_reverse_balances(self):
        """Ters bakiye kontrollerini çalıştır"""
        for code, account in self.mizan.accounts.items():
            finding = check_reverse_balance(account)
            if finding:
                self.findings.append(finding)
    
    def _check_cash_controls(self):
        """Nakit kontrolleri"""
        # Yüksek kasa bakiyesi kontrolü
        kasa = self.mizan.get_account("100")
        if kasa and kasa.balance > 100000:
            self.findings.append(AuditFinding(
                finding_type=FindingType.ADAT,
                risk_level=RiskLevel.MEDIUM,
                account_code="100",
                description=f"Kasa bakiyesi yüksek: {kasa.balance:,.2f} TL. Adat hesaplaması gerekebilir.",
                amount=kasa.balance,
                recommended_action="Ortak para çekmiş sayılır, aylık adat faturası kesilmelidir."
            ))
        
        # 131 Ortaklardan Alacaklar
        ortaklardan = self.mizan.get_account("131")
        if ortaklardan and ortaklardan.balance > 0:
            self.findings.append(AuditFinding(
                finding_type=FindingType.ADAT,
                risk_level=RiskLevel.HIGH,
                account_code="131",
                description=f"Ortaklardan alacak: {ortaklardan.balance:,.2f} TL. Transfer fiyatlandırması riski.",
                amount=ortaklardan.balance,
                recommended_action="Aylık emsal faiz + %20 KDV'li fatura kesilmelidir."
            ))
    
    def _check_liability_controls(self):
        """Pasif hesap kontrolleri"""
        # 331 Örtülü Sermaye kontrolü
        ortaklara = self.mizan.get_account("331")
        ozsermaye = abs(self.mizan.get_total_balance("5"))  # Özkaynak
        
        if ortaklara and ozsermaye > 0:
            limit = ozsermaye * 3
            if abs(ortaklara.balance) > limit:
                excess = abs(ortaklara.balance) - limit
                self.findings.append(AuditFinding(
                    finding_type=FindingType.ORTULU_SERMAYE,
                    risk_level=RiskLevel.CRITICAL,
                    account_code="331",
                    description=f"Örtülü sermaye tespit edildi. Ortaklara borç ({abs(ortaklara.balance):,.2f}) öz sermayenin 3 katını ({limit:,.2f}) aşıyor.",
                    amount=excess,
                    recommended_action="Aşan kısma ödenen faizler KKEG yapılmalı ve kar dağıtımı stopajı hesaplanmalıdır."
                ))
    
    def _check_cash_limit_30k(self):
        """
        VUK 320/323 - 30.000 TL Nakit İşlem Sınırı Kontrolü
        
        Temel limit aşıldığında Özel Usulsüzlük cezası uygulanır:
        - 7.000 TL'den az: 1.100 TL ceza
        - 7.000-30.000 TL: işlemin %5'i
        - 30.000+ TL: işlemin %5'i + ek yaptırım
        """
        if not self.kebir_data:
            return
        
        violations_count = 0
        total_violation_amount = 0.0
        sample_violations = []  # Örnek 3 ihlal
        
        for doc_no, doc_data in self.kebir_data.items():
            lines = doc_data.get("Lines", [])
            for line in lines:
                acc_code = line.get("Acc", "")
                # 100 Kasa hesabı işlemleri
                if acc_code.startswith("100"):
                    amt = float(line.get("Amt", 0))
                    dc = line.get("DC", "D")
                    
                    # 30.000 TL üzeri nakit işlem
                    if amt >= CASH_TRANSACTION_LIMIT:
                        violations_count += 1
                        total_violation_amount += amt
                        
                        if len(sample_violations) < 3:
                            desc = line.get("Desc", doc_no)[:30]
                            sample_violations.append(f"{desc}: {amt:,.0f} TL")
        
        if violations_count > 0:
            # Tahmini ceza: işlem tutarının %5'i
            estimated_penalty = total_violation_amount * 0.05
            
            sample_text = ", ".join(sample_violations)
            self.findings.append(AuditFinding(
                finding_type=FindingType.NAKIT_SINIR,
                risk_level=RiskLevel.HIGH if violations_count >= 5 else RiskLevel.MEDIUM,
                account_code="100",
                description=f"30.000 TL nakit sınır aşımı: {violations_count} işlem, toplam {total_violation_amount:,.2f} TL. Örnek: {sample_text}",
                amount=estimated_penalty,
                recommended_action=f"VUK 320/323 uyarınca Özel Usulsüzlük cezası riski ~{estimated_penalty:,.0f} TL. Banka havalesi kullanın.",
                reference=f"{violations_count} adet ihlal"
            ))
    
    def _check_vehicle_expense_limits(self):
        """
        Binek Araç Gider Kısıtlaması (2024 Sınırları)
        
        - Aylık kira sınırı: 26.000 TL (aşan kısım %100 KKEG)
        - Gider kısıtlaması: %30 KKEG
        - KDV indirimi: kısıtlı kısım indirilemez
        - Amortisman sınırları: 790.000 TL / 1.500.000 TL
        """
        if not self.mizan:
            return
        
        # 740 veya 770 hesaplarından araç kiralama gideri kontrolü
        # Genellikle 740.XX veya 770.XX alt hesaplarda tutulur
        
        total_vehicle_expense = 0.0
        for code, acc in self.mizan.accounts.items():
            # Araç kira/gider hesapları (taşıt, araç, kira kelimeleri)
            name_lower = acc.name.lower() if acc.name else ""
            if code.startswith(("740", "770", "760")) and acc.debit > 0:
                if any(kw in name_lower for kw in ["taşıt", "araç", "kira", "oto", "binek"]):
                    total_vehicle_expense += acc.debit
        
        # Aylık kira sınırı aşımı kontrolü
        monthly_limit = VEHICLE_LIMITS_2024["monthly_rent_limit"]
        if total_vehicle_expense > monthly_limit:
            excess = total_vehicle_expense - monthly_limit
            kkeg_amount = excess  # Aşan kısım %100 KKEG
            
            self.findings.append(AuditFinding(
                finding_type=FindingType.BINEK_KISIT,
                risk_level=RiskLevel.MEDIUM,
                account_code="770",
                description=f"Binek araç kira gideri: {total_vehicle_expense:,.2f} TL, aylık limit {monthly_limit:,.0f} TL. Aşan kısım: {excess:,.2f} TL",
                amount=kkeg_amount,
                recommended_action="Aşan kısım KKEG olarak dikkate alınmalı. İlgili KDV de indirilemez."
            ))
        
        # 254 Taşıtlar hesabı amortisman kontrolü
        tasitlar = self.mizan.get_account("254")
        if tasitlar and tasitlar.debit > 0:
            limit_1 = VEHICLE_LIMITS_2024["depreciation_limit_1"]  # 790.000 TL
            limit_2 = VEHICLE_LIMITS_2024["depreciation_limit_2"]  # 1.500.000 TL
            
            if tasitlar.debit > limit_2:
                excess = tasitlar.debit - limit_2
                self.findings.append(AuditFinding(
                    finding_type=FindingType.BINEK_KISIT,
                    risk_level=RiskLevel.HIGH,
                    account_code="254",
                    description=f"Binek araç değeri: {tasitlar.debit:,.2f} TL, ÖTV+KDV dahil limit {limit_2:,.0f} TL. Aşan kısım amortismanı KKEG.",
                    amount=excess,
                    recommended_action=f"Araç maliyetinin {limit_2:,.0f} TL'yi aşan kısmına ait amortisman KKEG yapılmalı."
                ))
    
    def generate_executive_report(self) -> ExecutiveReportData:
        """Yönetici raporu oluştur"""
        report = ExecutiveReportData()
        
        if not self.mizan:
            return report
        
        # Satış (600+601+602)
        report.total_sales = abs(self.mizan.get_total_balance("600")) + \
                            abs(self.mizan.get_total_balance("601")) + \
                            abs(self.mizan.get_total_balance("602"))
        
        # Satış maliyeti (620+621+622)
        cost = abs(self.mizan.get_total_balance("620")) + \
               abs(self.mizan.get_total_balance("621")) + \
               abs(self.mizan.get_total_balance("622"))
        
        report.gross_profit = report.total_sales - cost
        report.gross_margin = (report.gross_profit / report.total_sales * 100) if report.total_sales > 0 else 0
        
        # Faiz gideri (780)
        report.interest_expense = abs(self.mizan.get_total_balance("780"))
        
        # KDV
        report.calculated_vat = abs(self.mizan.get_total_balance("391"))
        report.deductible_vat = abs(self.mizan.get_total_balance("191"))
        report.payable_vat = report.calculated_vat - report.deductible_vat
        
        # Nakit
        report.cash_end = self.mizan.get_total_balance("100") + self.mizan.get_total_balance("102")
        
        # Finansal oranlar
        current_assets = self.mizan.get_total_balance("1")  # Dönen varlıklar
        inventory = self.mizan.get_total_balance("15")  # Stoklar
        current_liabilities = abs(self.mizan.get_total_balance("3"))  # Kısa vadeli borçlar
        
        if current_liabilities > 0:
            report.current_ratio = current_assets / current_liabilities
            report.quick_ratio = (current_assets - inventory) / current_liabilities
        
        # Top 5 Satıcı (Fatura verilerinden)
        if self.purchases_by_supplier:
            report.top_suppliers = self.get_top_suppliers(5)
        else:
            # Fallback: mizan alt hesaplarından
            suppliers = []
            for code, acc in self.mizan.accounts.items():
                if code.startswith("320") and len(code) > 3:
                    if abs(acc.balance) > 0:
                        suppliers.append((acc.name[:40], abs(acc.credit)))
            suppliers.sort(key=lambda x: x[1], reverse=True)
            report.top_suppliers = suppliers[:5]
        
        # Top 5 Müşteri (Fatura verilerinden)
        if self.sales_by_customer:
            report.top_customers = self.get_top_customers(5)
        else:
            # Fallback: mizan alt hesaplarından
            customers = []
            for code, acc in self.mizan.accounts.items():
                if code.startswith("120") and len(code) > 3:
                    if abs(acc.balance) > 0:
                        customers.append((acc.name[:40], abs(acc.debit)))
            customers.sort(key=lambda x: x[1], reverse=True)
            report.top_customers = customers[:5]
        
        # Top 5 Gider (7XX hesaplarından - standart hesap adlarıyla)
        EXPENSE_NAMES = {
            "710": "Direkt İlk Madde Malzeme",
            "720": "Direkt İşçilik Giderleri",
            "730": "Genel Üretim Giderleri",
            "740": "Hizmet Üretim Maliyeti",
            "750": "Ar-Ge Giderleri",
            "760": "Pazarlama Satış Dağıtım Giderleri",
            "770": "Genel Yönetim Giderleri",
            "780": "Finansman Giderleri",
        }
        expenses = []
        for code, acc in self.mizan.accounts.items():
            if code.startswith("7") and len(code) == 3:
                if acc.debit > 0:
                    # Standart hesap adı veya ilk 3 hane
                    expense_name = EXPENSE_NAMES.get(code, f"{code} Hesabı")
                    expenses.append((expense_name, acc.debit))
        expenses.sort(key=lambda x: x[1], reverse=True)
        report.top_expenses = expenses[:5]
        
        # Top 5 Pazarlama (760) ve Genel Yönetim (770) - ayrı ayrı
        report.top_760_pazarlama = self.get_top_expense_by_account("760", 5)
        report.top_770_yonetim = self.get_top_expense_by_account("770", 5)
        
        # Top 5 KDV (191 - Fatura satıcı bazlı)
        report.top_kdv_entries = self.get_top_kdv_by_supplier(5)
        
        # Bulgu sayıları
        for finding in self.findings:
            if finding.risk_level == RiskLevel.CRITICAL:
                report.findings_critical += 1
            elif finding.risk_level == RiskLevel.HIGH:
                report.findings_high += 1
            elif finding.risk_level == RiskLevel.MEDIUM:
                report.findings_medium += 1
            else:
                report.findings_low += 1
        
        self.executive_report = report
        return report
    
    # =====================================================
    # BEYANNAME KONTROL FONKSİYONLARI
    # =====================================================
    
    def check_kdv_beyanname(self, kdv_beyanname) -> List[AuditFinding]:
        """
        KDV Beyannamesi ile Mizan mutabakatı kontrolü.
        
        Args:
            kdv_beyanname: KDVBeyanname objesi (beyanname_parser'dan)
        
        Returns:
            Bulunan uyumsuzluk bulguları
        """
        findings = []
        
        if not self.mizan or not kdv_beyanname:
            return findings
        
        # Mizan'dan KDV hesaplarını al
        mizan_hesaplanan = abs(self.mizan.get_total_balance("391"))  # Hesaplanan KDV
        mizan_indirilecek = abs(self.mizan.get_total_balance("191"))  # İndirilecek KDV
        mizan_devreden = abs(self.mizan.get_total_balance("190"))  # Devreden KDV
        
        # Beyannameden değerler
        beyan_hesaplanan = kdv_beyanname.hesaplanan_kdv
        beyan_indirilecek = kdv_beyanname.indirilecek_kdv_toplami
        beyan_devreden = kdv_beyanname.sonraki_doneme_devreden
        
        # Tolerans (1 TL)
        TOL = 1.0
        
        # 1. Hesaplanan KDV kontrolü (391 vs Beyanname)
        fark_hesaplanan = abs(mizan_hesaplanan - beyan_hesaplanan)
        if fark_hesaplanan > TOL:
            findings.append(AuditFinding(
                finding_type=FindingType.KDV_UYUMSUZLUK,
                risk_level=RiskLevel.HIGH if fark_hesaplanan > 1000 else RiskLevel.MEDIUM,
                account_code="391",
                description=f"Hesaplanan KDV uyumsuzluğu: Mizan {mizan_hesaplanan:,.2f} TL, Beyanname {beyan_hesaplanan:,.2f} TL (Fark: {fark_hesaplanan:,.2f} TL)",
                amount=fark_hesaplanan,
                recommended_action="391 hesabı detaylı incelenmeli, satış faturaları ile mutabakat yapılmalı."
            ))
        
        # 2. İndirilecek KDV kontrolü (191 vs Beyanname)
        fark_indirilecek = abs(mizan_indirilecek - beyan_indirilecek)
        if fark_indirilecek > TOL:
            findings.append(AuditFinding(
                finding_type=FindingType.KDV_UYUMSUZLUK,
                risk_level=RiskLevel.HIGH if fark_indirilecek > 1000 else RiskLevel.MEDIUM,
                account_code="191",
                description=f"İndirilecek KDV uyumsuzluğu: Mizan {mizan_indirilecek:,.2f} TL, Beyanname {beyan_indirilecek:,.2f} TL (Fark: {fark_indirilecek:,.2f} TL)",
                amount=fark_indirilecek,
                recommended_action="191 hesabı detaylı incelenmeli, alış faturaları ile mutabakat yapılmalı."
            ))
        
        # 3. Devreden KDV kontrolü (190 vs Beyanname)
        fark_devreden = abs(mizan_devreden - beyan_devreden)
        if fark_devreden > TOL:
            findings.append(AuditFinding(
                finding_type=FindingType.KDV_UYUMSUZLUK,
                risk_level=RiskLevel.MEDIUM,
                account_code="190",
                description=f"Devreden KDV uyumsuzluğu: Mizan {mizan_devreden:,.2f} TL, Beyanname {beyan_devreden:,.2f} TL (Fark: {fark_devreden:,.2f} TL)",
                amount=fark_devreden,
                recommended_action="190 hesabı önceki dönem değerleri ile karşılaştırılmalı."
            ))
        
        self.findings.extend(findings)
        return findings
    
    def check_kdv2_beyanname(self, kdv2_beyanname) -> List[AuditFinding]:
        """
        KDV 2 (Sorumlu Sıfatıyla KDV) Beyannamesi kontrolü.
        
        Kontroller:
        - 360 hesabı ile sorumlu KDV tutarı karşılaştırması
        - Yurt dışı hizmet alımları kontrolü
        
        Args:
            kdv2_beyanname: KDV2Beyanname objesi
            
        Returns:
            Bulunan uyumsuzluk bulguları
        """
        findings = []
        
        if not self.mizan:
            return findings
        
        # 360 hesabından sorumlu sıfatıyla KDV kontrolü
        # 360.01 veya alt hesaplarda tutuluyor olabilir
        sorumlu_kdv_mizan = 0.0
        for code, acc in self.mizan.accounts.items():
            if code.startswith('360'):
                sorumlu_kdv_mizan += abs(acc.balance)
        
        beyan_sorumlu = kdv2_beyanname.hesaplanan_kdv or kdv2_beyanname.odenecek_kdv
        
        if beyan_sorumlu > 0:
            fark = abs(sorumlu_kdv_mizan - beyan_sorumlu)
            tolerance = max(1.0, beyan_sorumlu * 0.01)  # %1 veya 1 TL
            
            if fark > tolerance:
                findings.append(AuditFinding(
                    finding_type=FindingType.BEYANNAME_FARK,
                    risk_level=RiskLevel.MEDIUM,
                    account_code="360",
                    description=f"KDV 2 Farkı: Mizan {sorumlu_kdv_mizan:,.2f} TL, Beyanname {beyan_sorumlu:,.2f} TL",
                    amount=fark,
                    recommended_action="360 hesabı detayları incelenmeli. Stopaj hesaplamaları kontrol edilmeli."
                ))
        
        # Sorumlu matrah kontrolü - yüksek tutarlar için bilgilendirme
        if kdv2_beyanname.sorumlu_matrah > 100000:
            findings.append(AuditFinding(
                finding_type=FindingType.BILGI,
                risk_level=RiskLevel.INFO,
                account_code="360",
                description=f"KDV 2 Sorumlu Matrah: {kdv2_beyanname.sorumlu_matrah:,.2f} TL - Transfer fiyatlandırması riski",
                amount=kdv2_beyanname.sorumlu_matrah,
                recommended_action="Yurt dışı hizmet alımları emsallere uygunluk açısından değerlendirilmeli."
            ))
        
        self.findings.extend(findings)
        return findings
    
    def check_muhtasar(self, muhtasar_beyanname) -> List[AuditFinding]:
        """
        Muhtasar Beyannamesi ile Mizan stopaj kontrolü.
        
        Args:
            muhtasar_beyanname: MuhtasarBeyanname objesi
        
        Returns:
            Bulunan uyumsuzluk bulguları
        """
        findings = []
        
        if not self.mizan or not muhtasar_beyanname:
            return findings
        
        # Mizan'dan 360 hesabı (Ödenecek Vergi ve Fonlar) toplamını al
        mizan_stopaj = abs(self.mizan.get_total_balance("360"))
        beyan_stopaj = muhtasar_beyanname.toplam_stopaj
        
        TOL = 1.0
        fark = abs(mizan_stopaj - beyan_stopaj)
        
        if fark > TOL:
            findings.append(AuditFinding(
                finding_type=FindingType.STOPAJ_FARK,
                risk_level=RiskLevel.HIGH if fark > 1000 else RiskLevel.MEDIUM,
                account_code="360",
                description=f"Muhtasar-Mizan uyumsuzluğu: Mizan 360 bakiyesi {mizan_stopaj:,.2f} TL, Beyanname toplam stopaj {beyan_stopaj:,.2f} TL (Fark: {fark:,.2f} TL)",
                amount=fark,
                recommended_action="360 hesap alt kırılımları (ücret, serbest meslek, kira vb.) tek tek kontrol edilmeli."
            ))
        
        self.findings.extend(findings)
        return findings
    
    def check_fatura_beyanname_mutabakat(self, kdv_beyanname) -> List[AuditFinding]:
        """
        Fatura XML'lerinden hesaplanan KDV toplamları ile KDV Beyannamesi mutabakatı.
        
        Alış Faturaları KDV Toplamı == Beyanname İndirilecek KDV (191)
        Satış Faturaları KDV Toplamı == Beyanname Hesaplanan KDV (391)
        
        Args:
            kdv_beyanname: KDVBeyanname objesi (beyanname_parser'dan)
        
        Returns:
            Bulunan uyumsuzluk bulguları
        """
        findings = []
        
        if not kdv_beyanname:
            return findings
        
        # Tolerans (%5 veya 1000 TL, hangisi büyükse - e-Arşiv/diğer kaynaklardaki farklar için)
        def get_tolerance(value):
            return max(1000.0, abs(value) * 0.05)
        
        # 1. Alış Faturaları KDV vs Beyanname İndirilecek KDV
        # NOT: Beyanname indirilecek_kdv_toplami = dönem içi alışlar + önceki dönem devreden
        # Bu yüzden karşılaştırmada sadece dönem içi kısmı kullanmalıyız
        
        # Beyanname'den önceki dönem devredeni çıkar
        onceki_devreden = getattr(kdv_beyanname, 'onceki_donem_devreden', 0) or 0
        beyan_donem_ici_indirim = kdv_beyanname.indirilecek_kdv_toplami - onceki_devreden
        
        # Excel verisini tercih et (e-Arşiv dahil), yoksa XML'i kullan
        if self.excel_191_total > 0:
            # Excel'den gelen toplam (e-Arşiv dahil tüm belgeler)
            purchase_total = self.excel_191_total
            source_desc = f"Excel (191 Muavin Defter)"
            
            # XML ile Excel arasındaki fark (e-Arşiv vs e-Fatura)
            xml_excel_diff = abs(self.excel_191_total - self.purchase_kdv_total)
            if xml_excel_diff > 1000 and self.purchase_kdv_total > 0:
                # Bilgi amaçlı: XML'de olmayan belgeler (e-Arşiv vb.)
                findings.append(AuditFinding(
                    finding_type=FindingType.BILGI,
                    risk_level=RiskLevel.LOW,
                    account_code="191",
                    description=f"e-Arşiv/Diğer belgeler: Excel toplam {self.excel_191_total:,.2f} TL, XML {self.purchase_kdv_total} adet fatura toplamı {self.purchase_kdv_total:,.2f} TL (Fark: {xml_excel_diff:,.2f} TL)",
                    amount=xml_excel_diff,
                    recommended_action="Bu fark normal: e-Arşiv faturaları, gümrük KDV beyannameleri vb. Excel'de var ancak XML ZIP'te yok.",
                    reference=f"XML fatura sayısı: {self.purchase_invoice_count}"
                ))
        elif self.purchase_kdv_total > 0:
            # Excel yoksa XML toplamını kullan
            purchase_total = self.purchase_kdv_total
            source_desc = f"XML ({self.purchase_invoice_count} fatura)"
        else:
            # Hiç veri yok
            return findings
        
        # Beyanname ile mutabakat
        fark = abs(purchase_total - beyan_donem_ici_indirim)
        tolerance = get_tolerance(beyan_donem_ici_indirim)
        
        if fark > tolerance:
            findings.append(AuditFinding(
                finding_type=FindingType.FATURA_EKSIK,
                risk_level=RiskLevel.HIGH if fark > 50000 else RiskLevel.MEDIUM,
                account_code="191",
                description=f"Alış Mutabakat farkı: {source_desc} → {purchase_total:,.2f} TL, Beyanname Dönem İçi: {beyan_donem_ici_indirim:,.2f} TL (Fark: {fark:,.2f} TL)",
                amount=fark,
                recommended_action="Beyanname ile defter arasında fark var. Kayıt eksiklikleri veya muhasebeleştirme hataları olabilir.",
                reference=f"Beyanname toplam: {kdv_beyanname.indirilecek_kdv_toplami:,.2f} - Önceki dönem: {onceki_devreden:,.2f}"
            ))
        
        
        # 2. Satış Faturaları KDV vs Beyanname Hesaplanan KDV
        beyan_hesaplanan = kdv_beyanname.hesaplanan_kdv
        
        # Kebir 391 toplamını tercih et (tüm satış KDV'si), yoksa XML'i kullan
        if self.excel_391_total > 0:
            # Kebir'den gelen toplam (tüm satış KDV'si)
            sales_total = self.excel_391_total
            source_desc = "Kebir (391 Hesaplanan KDV)"
            
            # XML ile Kebir arasındaki fark (e-Arşiv + diğer)
            xml_kebir_diff = abs(self.excel_391_total - self.sales_kdv_total)
            if xml_kebir_diff > 1000 and self.sales_kdv_total > 0:
                # Bilgi amaçlı: XML'de olmayan satışlar
                findings.append(AuditFinding(
                    finding_type=FindingType.BILGI,
                    risk_level=RiskLevel.LOW,
                    account_code="391",
                    description=f"Dönem sonu/Diğer satışlar: Kebir 391 toplam {self.excel_391_total:,.2f} TL, XML {self.sales_invoice_count} fatura toplamı {self.sales_kdv_total:,.2f} TL (Fark: {xml_kebir_diff:,.2f} TL)",
                    amount=xml_kebir_diff,
                    recommended_action="Bu fark normal: Dönem sonu kayıtları, mahsuplaşmalar vb. Kebir'de var ancak fatura XML'inde yok.",
                    reference=f"XML fatura sayısı: {self.sales_invoice_count}"
                ))
        elif self.sales_kdv_total > 0:
            # Kebir yoksa XML toplamını kullan
            sales_total = self.sales_kdv_total
            source_desc = f"XML ({self.sales_invoice_count} fatura)"
        else:
            # Hiç veri yok
            sales_total = 0
            source_desc = "Veri yok"
        
        # Beyanname ile mutabakat
        if sales_total > 0:
            fark = abs(sales_total - beyan_hesaplanan)
            tolerance = get_tolerance(beyan_hesaplanan)
            
            if fark > tolerance:
                findings.append(AuditFinding(
                    finding_type=FindingType.KDV_UYUMSUZLUK,
                    risk_level=RiskLevel.HIGH if fark > 10000 else RiskLevel.MEDIUM,
                    account_code="391",
                    description=f"Satış Mutabakat farkı: {source_desc} → {sales_total:,.2f} TL, Beyanname Hesaplanan: {beyan_hesaplanan:,.2f} TL (Fark: {fark:,.2f} TL)",
                    amount=fark,
                    recommended_action="Beyanname ile defter arasında fark var. Kayıt eksiklikleri, dönem sonu düzeltmeleri veya farklı KDV oranları kontrol edilmeli.",
                    reference=f"Beyanname hesaplanan KDV: {beyan_hesaplanan:,.2f}"
                ))
        
        self.findings.extend(findings)
        return findings
    
    def load_invoice_comparison_results(self, csv_path: str) -> List[AuditFinding]:
        """
        Fatura-Defter karşılaştırma sonuçlarını yükle ve bulgu oluştur.
        
        Args:
            csv_path: Detayli_Karsilastirma_Raporu.csv dosya yolu
        
        Returns:
            Fatura eksikliği bulguları
        """
        import csv
        import os
        
        findings = []
        
        if not os.path.exists(csv_path):
            return findings
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                kayitsiz_count = 0
                belgesiz_count = 0
                kayitsiz_tutar = 0.0
                belgesiz_tutar = 0.0
                
                for row in reader:
                    durum = row.get('Durum', '')
                    tutar = float(row.get('Tutar_TL_Hesaplanan', 0) or 0)
                    
                    if 'KAYITSIZ' in durum:
                        kayitsiz_count += 1
                        kayitsiz_tutar += tutar
                    elif 'BELGESİZ' in durum:
                        belgesiz_count += 1
                        belgesiz_tutar += tutar
                
                # Kayıtsız faturalar için bulgu
                if kayitsiz_count > 0:
                    findings.append(AuditFinding(
                        finding_type=FindingType.FATURA_EKSIK,
                        risk_level=RiskLevel.CRITICAL,
                        account_code="FATURA",
                        description=f"{kayitsiz_count} adet fatura defterde kayıtlı değil. Toplam tutar: {kayitsiz_tutar:,.2f} TL",
                        amount=kayitsiz_tutar,
                        recommended_action="Kayıtsız faturalar için düzeltme kaydı yapılmalı veya ilgili dönem beyannameleri düzeltilmeli."
                    ))
                
                # Belgesiz defter kayıtları için bulgu
                if belgesiz_count > 0:
                    findings.append(AuditFinding(
                        finding_type=FindingType.FATURA_EKSIK,
                        risk_level=RiskLevel.HIGH,
                        account_code="DEFTER",
                        description=f"{belgesiz_count} adet defter kaydının faturası bulunamadı. Toplam tutar: {belgesiz_tutar:,.2f} TL",
                        amount=belgesiz_tutar,
                        recommended_action="Belgesiz kayıtların fatura veya belge dayanağı araştırılmalı."
                    ))
                
        except Exception as e:
            print(f"CSV okuma hatası: {e}")
        
        self.findings.extend(findings)
        return findings
    
    def compare_mizan_periods(self, aylik_mizan, kumulatif_mizan, donem_ay: int = 10) -> List[AuditFinding]:
        """
        Aylık mizan ile kümülatif mizan karşılaştırması.
        
        Kontroller:
        1. Aylık bakiyeler kümülatif içinde olmalı
        2. Hesap kodları tutarlı olmalı
        3. Büyük sapmalar rapor edilmeli
        
        Args:
            aylik_mizan: Aylık MizanData objesi
            kumulatif_mizan: Kümülatif MizanData objesi
            donem_ay: Hangi ay için karşılaştırma (1-12)
        
        Returns:
            Bulunan tutarsızlık bulguları
        """
        findings = []
        
        if not aylik_mizan or not kumulatif_mizan:
            return findings
        
        # 1. Aylık mizanda olup kümülatifte olmayan hesaplar
        for code, acc in aylik_mizan.accounts.items():
            if code not in kumulatif_mizan.accounts:
                if abs(acc.balance) > 100:  # 100 TL üzeri bakiyeler
                    findings.append(AuditFinding(
                        finding_type=FindingType.BEYANNAME_FARK,
                        risk_level=RiskLevel.MEDIUM,
                        account_code=code,
                        description=f"Hesap {code} aylık mizanda var ({acc.balance:,.2f} TL) ancak kümülatif mizanda yok",
                        amount=abs(acc.balance),
                        recommended_action="Hesap kodlarının tutarlılığı kontrol edilmeli."
                    ))
        
        # 2. Kümülatif bakiyenin aylık bakiyeden düşük olması (mantık hatası)
        for code, kum_acc in kumulatif_mizan.accounts.items():
            if code in aylik_mizan.accounts:
                ayl_acc = aylik_mizan.accounts[code]
                
                # Gelir/gider hesapları için (6xx, 7xx) kümülatif > aylık olmalı
                if code.startswith('6') or code.startswith('7'):
                    if abs(kum_acc.balance) < abs(ayl_acc.balance) * 0.8:  # %20 tolerans
                        findings.append(AuditFinding(
                            finding_type=FindingType.BEYANNAME_FARK,
                            risk_level=RiskLevel.HIGH,
                            account_code=code,
                            description=f"{code} - Kümülatif ({abs(kum_acc.balance):,.2f}) < Aylık ({abs(ayl_acc.balance):,.2f})",
                            amount=abs(ayl_acc.balance) - abs(kum_acc.balance),
                            recommended_action="Kümülatif mizan hesaplama hatası olabilir, kontrol edilmeli."
                        ))
        
        # 3. Kritik hesaplarda büyük sapmalar (100, 102, 320, 321, 360)
        kritik_hesaplar = ['100', '102', '320', '321', '360', '391', '191']
        for code in kritik_hesaplar:
            kum_bal = kumulatif_mizan.get_total_balance(code)
            ayl_bal = aylik_mizan.get_total_balance(code)
            
            # Ay başı kümülatif vs ay sonu tahmin
            beklenen = kum_bal  # Basit kontrol
            if abs(ayl_bal) > abs(beklenen) * 1.5 and abs(ayl_bal) > 10000:
                findings.append(AuditFinding(
                    finding_type=FindingType.BEYANNAME_FARK,
                    risk_level=RiskLevel.MEDIUM,
                    account_code=code,
                    description=f"{code} hesabında anormal değişim: Aylık {ayl_bal:,.2f}, Kümülatif {kum_bal:,.2f}",
                    amount=abs(ayl_bal - kum_bal),
                    recommended_action="Hesap hareketleri detaylı incelenmeli."
                ))
        
        self.findings.extend(findings)
        return findings
    
    def check_kasa_controls(self) -> List[AuditFinding]:
        """
        Kasa hesabı kontrolleri:
        1. Negatif kasa bakiyesi (imkansız)
        2. Yüksek kasa bakiyesi (vergi riski)
        3. Kasa hareketleri analizi
        """
        findings = []
        
        if not self.mizan:
            return findings
        
        kasa_bakiye = self.mizan.get_total_balance("100")
        
        # 1. Negatif kasa bakiyesi
        if kasa_bakiye < 0:
            findings.append(AuditFinding(
                finding_type=FindingType.KASA_FAZLASI,
                risk_level=RiskLevel.CRITICAL,
                account_code="100",
                description=f"Negatif kasa bakiyesi: {kasa_bakiye:,.2f} TL - bu imkansızdır, kayıt hatası mevcut",
                amount=abs(kasa_bakiye),
                recommended_action="Kasa hesabı hareketleri detaylı incelenmeli, eksik tahsilat/tediye kayıtları kontrol edilmeli."
            ))
        
        # 2. Yüksek kasa bakiyesi (100.000 TL üzeri)
        if kasa_bakiye > 100000:
            findings.append(AuditFinding(
                finding_type=FindingType.KASA_FAZLASI,
                risk_level=RiskLevel.MEDIUM,
                account_code="100",
                description=f"Yüksek kasa bakiyesi: {kasa_bakiye:,.2f} TL - vergi incelemesinde örtülü sermaye riski",
                amount=kasa_bakiye,
                recommended_action="Yüksek nakit tutulması yerine bankaya aktarılması önerilir."
            ))
        
        self.findings.extend(findings)
        return findings
    
    def check_amortisman(self) -> List[AuditFinding]:
        """
        Amortisman kontrolleri:
        1. 257 Birikmiş Amortisman hesabı
        2. 258 Birikmiş Amortisman (Özel Tükenme) hesabı
        3. Amortisman gider kaydı kontrolü
        """
        findings = []
        
        if not self.mizan:
            return findings
        
        # Sabit kıymet varlığı
        duran_varlik_257 = abs(self.mizan.get_total_balance("253"))  # Tesis Makine
        duran_varlik_254 = abs(self.mizan.get_total_balance("254"))  # Taşıtlar
        duran_varlik_255 = abs(self.mizan.get_total_balance("255"))  # Demirbaşlar
        
        toplam_duran = duran_varlik_257 + duran_varlik_254 + duran_varlik_255
        
        # Birikmiş amortisman
        birikmis_257 = abs(self.mizan.get_total_balance("257"))
        
        # Amortisman gideri (770.xx veya 730.xx altında)
        amortisman_gider = abs(self.mizan.get_total_balance("770"))
        
        # Kontroller
        if toplam_duran > 50000 and birikmis_257 == 0:
            findings.append(AuditFinding(
                finding_type=FindingType.BEYANNAME_FARK,
                risk_level=RiskLevel.HIGH,
                account_code="257",
                description=f"Duran varlık ({toplam_duran:,.2f} TL) var ancak amortisman ayrılmamış",
                amount=toplam_duran,
                recommended_action="VUK'a göre amortisman ayrılması zorunludur. Eksik amortisman hesaplanmalı."
            ))
        
        self.findings.extend(findings)
        return findings
    
    def check_kkeg(self) -> List[AuditFinding]:
        """
        Kanunen Kabul Edilmeyen Giderler (KKEG) kontrolü:
        - Temsil ve ağırlama
        - Ceza ve tazminatlar
        - Örtülü kazanç dağıtımı
        """
        findings = []
        
        if not self.mizan:
            return findings
        
        # Temsil ve ağırlama giderleri (genellikle 760.xx altında)
        # Bu hesaplar şirkete göre değişebilir
        
        # Genel gider hesapları kontrolü
        # 689 - Diğer Olağandışı Giderler (ceza, tazminat olabilir)
        diger_olagandisi = abs(self.mizan.get_total_balance("689"))
        if diger_olagandisi > 10000:
            findings.append(AuditFinding(
                finding_type=FindingType.BEYANNAME_FARK,
                risk_level=RiskLevel.MEDIUM,
                account_code="689",
                description=f"Diğer Olağandışı Giderler: {diger_olagandisi:,.2f} TL - KKEG içerebilir",
                amount=diger_olagandisi,
                recommended_action="Ceza, tazminat, bağış gibi KKEG kalemleri ayrıştırılmalı."
            ))
        
        self.findings.extend(findings)
        return findings
    
    def check_iliskili_taraf(self) -> List[AuditFinding]:
        """
        İlişkili taraf işlemleri kontrolü:
        - 131/231 Ortaklardan alacaklar
        - 331/431 Ortaklara borçlar
        - Transfer fiyatlandırması riski
        """
        findings = []
        
        if not self.mizan:
            return findings
        
        # Ortaklardan alacaklar
        ortaklardan_alacak_131 = abs(self.mizan.get_total_balance("131"))
        ortaklardan_alacak_231 = abs(self.mizan.get_total_balance("231"))
        toplam_ortak_alacak = ortaklardan_alacak_131 + ortaklardan_alacak_231
        
        # Ortaklara borçlar
        ortaklara_borc_331 = abs(self.mizan.get_total_balance("331"))
        ortaklara_borc_431 = abs(self.mizan.get_total_balance("431"))
        toplam_ortak_borc = ortaklara_borc_331 + ortaklara_borc_431
        
        # Öz sermaye
        oz_sermaye = abs(self.mizan.get_total_balance("500")) + abs(self.mizan.get_total_balance("520"))
        
        # Kontrolller
        if toplam_ortak_alacak > 100000:
            findings.append(AuditFinding(
                finding_type=FindingType.ORTULU_SERMAYE,
                risk_level=RiskLevel.HIGH,
                account_code="131/231",
                description=f"Ortaklardan alacak: {toplam_ortak_alacak:,.2f} TL - örtülü kazanç dağıtımı riski",
                amount=toplam_ortak_alacak,
                recommended_action="Ortaklardan alacaklara faiz hesaplanmalı veya temettü olarak değerlendirilmeli."
            ))
        
        # Örtülü sermaye kontrolü (borç > öz sermaye x 3)
        if oz_sermaye > 0 and toplam_ortak_borc > oz_sermaye * 3:
            findings.append(AuditFinding(
                finding_type=FindingType.ORTULU_SERMAYE,
                risk_level=RiskLevel.CRITICAL,
                account_code="331/431",
                description=f"Örtülü sermaye riski: Ortak borcu ({toplam_ortak_borc:,.2f}) > Öz sermaye x 3 ({oz_sermaye * 3:,.2f})",
                amount=toplam_ortak_borc - oz_sermaye * 3,
                recommended_action="KVK 12. madde gereği örtülü sermaye faizi KKEG'dir."
            ))
        
        self.findings.extend(findings)
        return findings
    
    def run_extended_checks(self) -> List[AuditFinding]:
        """Tüm ek kontrolleri çalıştır"""
        self.check_kasa_controls()
        self.check_amortisman()
        self.check_kkeg()
        self.check_iliskili_taraf()
        return self.findings
    
    # ==================== YMM ROBOT EK KONTROLLER ====================
    
    def check_satis_hasilat(self) -> List[AuditFinding]:
        """
        Satış hasılatı kontrolü:
        - 600 Yurtiçi Satışlar
        - 601 Yurtdışı Satışlar
        - 602 Diğer Gelirler
        - Satış faturaları ile karşılaştırma
        """
        findings = []
        
        if not self.mizan:
            return findings
        
        # Satış hesapları
        satis_600 = abs(self.mizan.get_total_balance("600"))
        satis_601 = abs(self.mizan.get_total_balance("601"))
        satis_602 = abs(self.mizan.get_total_balance("602"))
        toplam_satis = satis_600 + satis_601 + satis_602
        
        # Satış iadeleri
        iade_610 = abs(self.mizan.get_total_balance("610"))
        iade_611 = abs(self.mizan.get_total_balance("611"))
        
        # İade oranı kontrolü (%10 üzeri anormal)
        if toplam_satis > 0:
            iade_orani = (iade_610 + iade_611) / toplam_satis * 100
            if iade_orani > 10:
                findings.append(AuditFinding(
                    finding_type=FindingType.BEYANNAME_FARK,
                    risk_level=RiskLevel.MEDIUM,
                    account_code="610/611",
                    description=f"Yüksek iade oranı: %{iade_orani:.1f} (İade: {iade_610 + iade_611:,.2f} / Satış: {toplam_satis:,.2f})",
                    amount=iade_610 + iade_611,
                    recommended_action="Satış iade sebepleri incelenmeli, sahte fatura riski değerlendirilmeli."
                ))
        
        # KDV hesaplanan vs satış tutarı
        kdv_391 = abs(self.mizan.get_total_balance("391"))
        beklenen_kdv = toplam_satis * 0.20  # Ortalama %20 KDV varsayımı
        
        if toplam_satis > 100000 and kdv_391 > 0:
            kdv_fark = abs(kdv_391 - beklenen_kdv) / beklenen_kdv * 100 if beklenen_kdv > 0 else 0
            if kdv_fark > 30:  # %30'dan fazla sapma
                findings.append(AuditFinding(
                    finding_type=FindingType.KDV_UYUMSUZLUK,
                    risk_level=RiskLevel.MEDIUM,
                    account_code="391",
                    description=f"KDV-Satış oranı anormal: Satış {toplam_satis:,.2f}, KDV {kdv_391:,.2f} (%{kdv_391/toplam_satis*100:.1f})",
                    amount=abs(kdv_391 - beklenen_kdv),
                    recommended_action="Farklı KDV oranlarında satışlar veya istisna satışlar kontrol edilmeli."
                ))
        
        self.findings.extend(findings)
        return findings
    
    def check_maliyet(self) -> List[AuditFinding]:
        """
        Maliyet kontrolü:
        - 620 Satılan Mamuller Maliyeti
        - 621 Satılan Ticari Mallar Maliyeti
        - 622 Satılan Hizmet Maliyeti
        - Brüt kar marjı analizi
        """
        findings = []
        
        if not self.mizan:
            return findings
        
        # Satış
        toplam_satis = abs(self.mizan.get_total_balance("600")) + abs(self.mizan.get_total_balance("601"))
        
        # Maliyet
        maliyet_620 = abs(self.mizan.get_total_balance("620"))
        maliyet_621 = abs(self.mizan.get_total_balance("621"))
        maliyet_622 = abs(self.mizan.get_total_balance("622"))
        toplam_maliyet = maliyet_620 + maliyet_621 + maliyet_622
        
        # Brüt kar marjı
        if toplam_satis > 100000:
            brut_kar = toplam_satis - toplam_maliyet
            brut_kar_marji = brut_kar / toplam_satis * 100 if toplam_satis > 0 else 0
            
            # Negatif brüt kar
            if brut_kar < 0:
                findings.append(AuditFinding(
                    finding_type=FindingType.BEYANNAME_FARK,
                    risk_level=RiskLevel.CRITICAL,
                    account_code="620-622",
                    description=f"Negatif brüt kar: Satış {toplam_satis:,.2f}, Maliyet {toplam_maliyet:,.2f} = Zarar {brut_kar:,.2f}",
                    amount=abs(brut_kar),
                    recommended_action="Maliyet hesaplaması veya stok değerlemesi kontrol edilmeli."
                ))
            
            # Çok düşük brüt kar marjı (%5 altı)
            elif brut_kar_marji < 5 and toplam_satis > 500000:
                findings.append(AuditFinding(
                    finding_type=FindingType.BEYANNAME_FARK,
                    risk_level=RiskLevel.MEDIUM,
                    account_code="620-622",
                    description=f"Düşük brüt kar marjı: %{brut_kar_marji:.1f} - sektör ortalaması altında olabilir",
                    amount=toplam_satis * 0.10 - brut_kar,  # %10 olması gereken kar
                    recommended_action="Transfer fiyatlandırması veya örtülü kazanç dağıtımı riski değerlendirilmeli."
                ))
        
        self.findings.extend(findings)
        return findings
    
    def check_personel_gider(self) -> List[AuditFinding]:
        """
        Personel gideri kontrolü:
        - 770 Genel Yönetim Giderleri (personel payı)
        - 360.01 Ödenecek SGK Primleri
        - 361 Ödenecek Sosyal Güvenlik Kesintileri
        - Personel sayısı tahmini
        """
        findings = []
        
        if not self.mizan:
            return findings
        
        # Personel giderleri (tahmini olarak 770'in %40'ı)
        gyk_770 = abs(self.mizan.get_total_balance("770"))
        
        # SGK prim borcu
        sgk_360 = abs(self.mizan.get_total_balance("360"))
        sgk_361 = abs(self.mizan.get_total_balance("361"))
        
        # Muhtasar stopaj kontrolü yapılacaksa burada
        # Şimdilik sadece oransal kontrol
        
        if gyk_770 > 100000 and sgk_360 == 0 and sgk_361 == 0:
            findings.append(AuditFinding(
                finding_type=FindingType.STOPAJ_FARK,
                risk_level=RiskLevel.HIGH,
                account_code="360/361",
                description=f"Yüksek GYG ({gyk_770:,.2f} TL) var ancak SGK tahakkuku yok",
                amount=gyk_770 * 0.20,  # Tahmini SGK tutarı
                recommended_action="Personel giderleri varsa SGK prim tahakkuklarının yapılması gerekir."
            ))
        
        self.findings.extend(findings)
        return findings
    
    def check_vergi_tahakkuk(self) -> List[AuditFinding]:
        """
        Vergi tahakkuk kontrolü:
        - 360 Ödenecek Vergi ve Fonlar
        - 371 Dönem Karının Peşin Ödenen Vergileri (Geçici Vergi)
        - 193 Peşin Ödenen Vergiler
        """
        findings = []
        
        if not self.mizan:
            return findings
        
        # Ödenecek vergiler
        odenecek_360 = abs(self.mizan.get_total_balance("360"))
        
        # Geçici vergi
        gecici_371 = abs(self.mizan.get_total_balance("371"))
        pesin_193 = abs(self.mizan.get_total_balance("193"))
        
        # Gelir tablosu hesapları
        toplam_satis = abs(self.mizan.get_total_balance("600")) + abs(self.mizan.get_total_balance("601"))
        toplam_maliyet = abs(self.mizan.get_total_balance("620")) + abs(self.mizan.get_total_balance("621"))
        toplam_gider = abs(self.mizan.get_total_balance("760")) + abs(self.mizan.get_total_balance("770"))
        
        tahmini_kar = toplam_satis - toplam_maliyet - toplam_gider
        
        # Kar var ama geçici vergi yok
        if tahmini_kar > 100000 and gecici_371 == 0 and pesin_193 == 0:
            findings.append(AuditFinding(
                finding_type=FindingType.BEYANNAME_FARK,
                risk_level=RiskLevel.HIGH,
                account_code="371/193",
                description=f"Tahmini kar ({tahmini_kar:,.2f} TL) var ancak geçici vergi tahakkuku yok",
                amount=tahmini_kar * 0.25,  # %25 kurumlar vergisi
                recommended_action="Geçici vergi beyannamesi ve tahakkuk kontrolü yapılmalı."
            ))
        
        self.findings.extend(findings)
        return findings
    
    def check_hesap_denkligi(self) -> List[AuditFinding]:
        """
        Hesap denkliği kontrolü:
        - Toplam Aktif = Toplam Pasif
        - Borç = Alacak toplamları
        """
        findings = []
        
        if not self.mizan:
            return findings
        
        toplam_borc = 0
        toplam_alacak = 0
        
        for code, acc in self.mizan.accounts.items():
            toplam_borc += acc.debit
            toplam_alacak += acc.credit
        
        fark = abs(toplam_borc - toplam_alacak)
        
        if fark > 1:  # 1 TL tolerans
            findings.append(AuditFinding(
                finding_type=FindingType.BEYANNAME_FARK,
                risk_level=RiskLevel.CRITICAL,
                account_code="GENEL",
                description=f"Mizan dengesizliği: Borç {toplam_borc:,.2f} ≠ Alacak {toplam_alacak:,.2f} (Fark: {fark:,.2f})",
                amount=fark,
                recommended_action="Mizan dengesi sağlanmalı, hata araştırılmalı."
            ))
        
        self.findings.extend(findings)
        return findings
    
    def check_cari_yaslandirma(self) -> List[AuditFinding]:
        """
        Cari hesap yaşlandırma kontrolü:
        - 120 Alıcılar (yüksek bakiye riski)
        - 320 Satıcılar (yüksek bakiye riski)
        - 121 Alacak Senetleri
        - 321 Borç Senetleri
        """
        findings = []
        
        if not self.mizan:
            return findings
        
        # Alıcılar
        alicilar_120 = abs(self.mizan.get_total_balance("120"))
        alacak_senet = abs(self.mizan.get_total_balance("121"))
        
        # Satıcılar
        saticilar_320 = abs(self.mizan.get_total_balance("320"))
        borc_senet = abs(self.mizan.get_total_balance("321"))
        
        # Satışa oranla alıcı bakiyesi (yüksek ise tahsilat problemi)
        toplam_satis = abs(self.mizan.get_total_balance("600")) + abs(self.mizan.get_total_balance("601"))
        
        if toplam_satis > 0 and alicilar_120 > toplam_satis * 0.5:
            # Alıcı bakiyesi satışın %50'sinden fazla
            findings.append(AuditFinding(
                finding_type=FindingType.BEYANNAME_FARK,
                risk_level=RiskLevel.MEDIUM,
                account_code="120",
                description=f"Yüksek alıcı bakiyesi: {alicilar_120:,.2f} TL (Satışın %{alicilar_120/toplam_satis*100:.0f}'i)",
                amount=alicilar_120,
                recommended_action="Alacak yaşlandırması yapılmalı, şüpheli alacak karşılığı değerlendirilmeli."
            ))
        
        # Şüpheli alacak karşılığı kontrolü
        supheli_129 = abs(self.mizan.get_total_balance("129"))
        if alicilar_120 > 500000 and supheli_129 == 0:
            findings.append(AuditFinding(
                finding_type=FindingType.BEYANNAME_FARK,
                risk_level=RiskLevel.LOW,
                account_code="129",
                description=f"Yüksek alıcı ({alicilar_120:,.2f} TL) var ancak şüpheli alacak karşılığı ayrılmamış",
                amount=alicilar_120 * 0.05,  # %5 karşılık önerisi
                recommended_action="VUK 323. madde kapsamında şüpheli alacak değerlendirmesi yapılmalı."
            ))
        
        self.findings.extend(findings)
        return findings
    
    def run_full_ymm_audit(self) -> List[AuditFinding]:
        """
        TAM YMM AYLIK DENETİM
        Tüm kontrolleri sırasıyla çalıştırır
        """
        # Standart kontroller
        self.run_all_checks()
        
        # Ek kontroller
        self.run_extended_checks()
        
        # YMM Robot kontrolleri
        self.check_satis_hasilat()
        self.check_maliyet()
        self.check_personel_gider()
        self.check_vergi_tahakkuk()
        self.check_hesap_denkligi()
        self.check_cari_yaslandirma()
        
        return self.findings
