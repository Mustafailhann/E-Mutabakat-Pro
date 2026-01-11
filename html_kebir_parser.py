# -*- coding: utf-8 -*-
"""
HTML Kebir Parser - Muhasebe programından dışa aktarılmış Kebir HTML dosyalarını parse eder.
LBS veya benzer muhasebe yazılımlarının HTML rapor çıktılarını okur.
"""

import re
import os
from html.parser import HTMLParser
from datetime import datetime


class KebirHTMLParser(HTMLParser):
    """Kebir HTML dosyasını parse eden sınıf."""
    
    def __init__(self):
        super().__init__()
        self.entries = []  # Tüm kayıtlar
        self.current_account = None  # Aktif hesap kodu ve adı
        self.current_account_code = None
        self.current_entry = {}
        self.current_div_class = None
        self.current_text = ""
        self.company_name = None
        self.company_code = None
        self.report_date = None
        self.devir_borc = 0.0
        self.devir_alacak = 0.0
        
        # Geçici değerler (CSS class'a göre alan haritalama)
        self.temp_values = {}
        
    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'div':
            attr_dict = dict(attrs)
            self.current_div_class = attr_dict.get('class', '')
            self.current_text = ""
            
    def handle_endtag(self, tag):
        if tag.lower() == 'div' and self.current_div_class:
            self._process_div_content()
            self.current_div_class = None
            self.current_text = ""
            
    def handle_data(self, data):
        if self.current_div_class:
            self.current_text += data
            
    def _decode_html_entities(self, text):
        """HTML entity'lerini decode et."""
        # &#305; -> ı, &#351; -> ş, &#252; -> ü, vb.
        import html
        return html.unescape(text)
    
    def _parse_amount(self, text):
        """Tutarı parse et (Türk formatı: 1.234,56)"""
        if not text:
            return 0.0
        text = text.strip().replace('.', '').replace(',', '.')
        try:
            return float(text)
        except:
            return 0.0
    
    def _parse_date(self, text):
        """Tarihi parse et (01.10.2025 formatı)"""
        if not text:
            return None
        text = text.strip()
        try:
            return datetime.strptime(text, "%d.%m.%Y").strftime("%Y-%m-%d")
        except:
            return text
            
    def _process_div_content(self):
        """DIV içeriğini işle ve uygun alana eşle."""
        text = self._decode_html_entities(self.current_text.strip())
        cls = self.current_div_class
        
        if not text:
            return
            
        # Şirket kodu tespiti - (35) formatı
        if cls == 'style6':
            match = re.search(r'(\d+)', text)
            if match:
                self.company_code = match.group(1)
                
        # Şirket adı - style8 veya style9
        if cls in ('style8', 'style9') and 'SAN' in text.upper() or 'TİC' in text.upper() or 'LTD' in text.upper() or 'A.Ş' in text.upper():
            if not self.company_name:
                self.company_name = text
                
        # Hesap kodu ve adı - style12 (kod), style14 (ad)
        if cls == 'style12' and text.isdigit():
            self.current_account_code = text
            
        if cls == 'style14' and self.current_account_code:
            self.current_account = f"{self.current_account_code} - {text}"
            
        # Devreden bakiyeler - style55, style58
        if cls == 'style55' and 'Devreden' not in text:
            self.devir_borc = self._parse_amount(text)
            
        if cls == 'style58' and 'Devreden' not in text:
            self.devir_alacak = self._parse_amount(text)
            
        # Kayıt verileri - satır bazlı
        # style29: Tarih (Borç tarafı)
        # style30: Fiş Türü
        # style31: Fiş No
        # style32: Yevmiye No
        # style33: Açıklama
        # style34: Borç Tutarı
        # style35: Borç Bakiye
        # style37: Tarih (Alacak tarafı)
        # style38: Fiş Türü (Alacak)
        # style39: Fiş No (Alacak)
        # style40: Yevmiye No (Alacak)
        # style41: Açıklama (Alacak)
        # style42: Alacak Tutarı
        
        # Veri satırları (style29-style42)
        if cls == 'style29':  # Tarih (Borç)
            self.temp_values['tarih_borc'] = self._parse_date(text)
        elif cls == 'style30':  # Fiş Türü (Borç)
            self.temp_values['fis_turu_borc'] = text
        elif cls == 'style31':  # Fiş No (Borç)
            self.temp_values['fis_no_borc'] = text
        elif cls == 'style32':  # Yevmiye No (Borç)
            self.temp_values['yev_no_borc'] = text
        elif cls == 'style33':  # Açıklama (Borç)
            self.temp_values['aciklama_borc'] = text
            # Fatura numarası açıklamadan çıkarma (Borç tarafı için de)
            invoice_match = re.search(r'([A-Z]{3}\d{13})', text)
            if invoice_match:
                self.temp_values['fatura_no_borc'] = invoice_match.group(1)
            # Cari hesap adı
            parts = text.split(',')
            if len(parts) >= 4:
                self.temp_values['cari_unvan_borc'] = parts[3].strip()
        elif cls == 'style34':  # Borç Tutarı
            self.temp_values['borc'] = self._parse_amount(text)
            
        # Alacak tarafı
        elif cls == 'style37':  # Tarih (Alacak)
            self.temp_values['tarih'] = self._parse_date(text)
        elif cls == 'style38':  # Fiş Türü (Alacak)
            self.temp_values['fis_turu'] = text
        elif cls == 'style39':  # Fiş No (Alacak)
            self.temp_values['fis_no'] = text
            # Fatura numarası çıkarma - EMK2025000003066 formatı
            invoice_match = re.search(r'([A-Z]{3}\d{13})', text)
            if invoice_match:
                self.temp_values['fatura_no'] = invoice_match.group(1)
        elif cls == 'style40':  # Yevmiye No
            self.temp_values['yev_no'] = text
        elif cls == 'style41':  # Açıklama (Alacak)
            self.temp_values['aciklama'] = text
            # Fatura numarası açıklamadan çıkarma
            invoice_match = re.search(r'([A-Z]{3}\d{13})', text)
            if invoice_match:
                self.temp_values['fatura_no'] = invoice_match.group(1)
            # Cari hesap adı
            parts = text.split(',')
            if len(parts) >= 4:
                self.temp_values['cari_unvan'] = parts[3].strip()
        elif cls == 'style42':  # Alacak Tutarı
            alacak = self._parse_amount(text)
            if alacak > 0:
                self.temp_values['alacak'] = alacak
                # Kayıt tamamlandı, entries'e ekle
                self._finalize_entry()
                
        elif cls == 'style35':  # Borç Bakiye - bir kaydın sonu olabilir
            if 'borc' in self.temp_values and self.temp_values.get('borc', 0) > 0:
                self.temp_values['bakiye'] = self._parse_amount(text)
                self._finalize_entry_borc()
        
        elif cls == 'style36':  # Alacak Bakiye - tek taraflı borç kaydının sonu olabilir (191 KDV gibi)
            # Eğer borç var ama alacak yok ve henüz finalize edilmemişse
            if 'borc' in self.temp_values and self.temp_values.get('borc', 0) > 0:
                if 'alacak' not in self.temp_values or self.temp_values.get('alacak', 0) == 0:
                    self.temp_values['bakiye'] = self._parse_amount(text)
                    self._finalize_entry_borc()

    def _finalize_entry(self):
        """Alacak tarafı kaydını tamamla."""
        if self.current_account and self.temp_values:
            entry = {
                'hesap': self.current_account,
                'hesap_kodu': self.current_account_code,
                'tarih': self.temp_values.get('tarih', ''),
                'fis_turu': self.temp_values.get('fis_turu', ''),
                'fis_no': self.temp_values.get('fis_no', ''),
                'yev_no': self.temp_values.get('yev_no', ''),
                'aciklama': self.temp_values.get('aciklama', ''),
                'fatura_no': self.temp_values.get('fatura_no', ''),
                'cari_unvan': self.temp_values.get('cari_unvan', ''),
                'borc': self.temp_values.get('borc', 0.0),
                'alacak': self.temp_values.get('alacak', 0.0),
                'dc': 'C' if self.temp_values.get('alacak', 0) > 0 else 'D'
            }
            self.entries.append(entry)
        self.temp_values = {}
        
    def _finalize_entry_borc(self):
        """Borç tarafı kaydını tamamla."""
        if self.current_account and self.temp_values:
            entry = {
                'hesap': self.current_account,
                'hesap_kodu': self.current_account_code,
                'tarih': self.temp_values.get('tarih_borc', ''),
                'fis_turu': self.temp_values.get('fis_turu_borc', ''),
                'fis_no': self.temp_values.get('fis_no_borc', ''),
                'yev_no': self.temp_values.get('yev_no_borc', ''),
                'aciklama': self.temp_values.get('aciklama_borc', ''),
                'fatura_no': self.temp_values.get('fatura_no_borc', ''),
                'cari_unvan': self.temp_values.get('cari_unvan_borc', ''),
                'borc': self.temp_values.get('borc', 0.0),
                'alacak': 0.0,
                'dc': 'D'
            }
            self.entries.append(entry)
        self.temp_values = {}


def parse_html_kebir(html_path, encoding='windows-1254'):
    """
    HTML Kebir dosyasını parse eder ve e-Defter formatına uyumlu çıktı döndürür.
    
    Returns:
        ledger_docs: dict - Belge numarasına göre gruplandırılmış defter kayıtları
        my_vkn: str - Şirket VKN'si (tespit edilebilirse)
    """
    print(f"HTML Kebir analiz ediliyor: {html_path}")
    
    if not os.path.exists(html_path):
        print("HATA: Kebir dosyası bulunamadı!")
        return {}, None
    
    try:
        # Dosyayı oku
        with open(html_path, 'rb') as f:
            content = f.read()
        
        # Encoding'i tespit et veya varsayılanı kullan
        try:
            text = content.decode(encoding)
        except:
            try:
                text = content.decode('utf-8')
            except:
                text = content.decode('latin-1')
        
        # Parse et
        parser = KebirHTMLParser()
        parser.feed(text)
        
        print(f"Şirket: {parser.company_name}")
        print(f"Toplam {len(parser.entries)} kayıt bulundu.")
        
        # e-Defter formatına dönüştür
        ledger_docs = {}
        
        for entry in parser.entries:
            # Belge numarası olarak fiş_no veya fatura_no kullan
            doc_num = entry.get('fatura_no') or entry.get('fis_no') or ''
            
            if not doc_num:
                continue
                
            if doc_num not in ledger_docs:
                ledger_docs[doc_num] = {
                    "TotalDebit": 0.0,
                    "Date": entry.get('tarih', ''),
                    "Type": "invoice" if entry.get('fatura_no') else "other",
                    "Desc": entry.get('aciklama', ''),
                    "Accounts": set(),
                    "TaxTotal": 0.0,
                    "Lines": []
                }
            
            acc_code = entry.get('hesap_kodu', '')
            ledger_docs[doc_num]["Accounts"].add(acc_code)
            
            # Tutar bilgisi
            borc_amt = entry.get('borc', 0) or 0
            alacak_amt = entry.get('alacak', 0) or 0
            
            ledger_docs[doc_num]["Lines"].append({
                "Acc": acc_code,
                "DC": entry.get('dc', 'D'),
                "Amt": borc_amt or alacak_amt,
                "Desc": entry.get('aciklama', '')
            })
            
            # Fatura tutarı belirleme:
            # HTML Kebir'de aynı fatura birden fazla hesapta görünebilir (çift kayıt)
            # Gerçek fatura tutarını bulmak için öncelik sırası:
            # 1. 320 (Satıcılar) - Alış faturası ana hesabı
            # 2. 120 (Alıcılar) - Satış faturası ana hesabı  
            # 3. 100 (Kasa), 102 (Banka) - Ödeme hesapları
            
            # Öncelik sırası (yüksek = daha önemli)
            priority_map = {
                '320': 100,  # Satıcılar - en yüksek öncelik (alış faturası)
                '120': 100,  # Alıcılar - en yüksek öncelik (satış faturası)
                '100': 80,   # Kasa
                '102': 80,   # Banka
                '300': 70,   # Banka Kredileri
                '159': 60,   # Verilen Sipariş Avansları
            }
            
            current_priority = ledger_docs[doc_num].get("_priority", 0)
            acc_prefix = acc_code[:3] if len(acc_code) >= 3 else acc_code
            new_priority = priority_map.get(acc_prefix, 0)
            
            if entry.get('dc') == 'D':
                ledger_docs[doc_num]["TotalDebit"] += borc_amt
                # 120 Alıcılar hesabında borç = satış faturası tutarı
                if acc_prefix == '120' and new_priority > current_priority:
                    ledger_docs[doc_num]["InvoiceAmount"] = borc_amt
                    ledger_docs[doc_num]["_priority"] = new_priority
            else:
                # Alacak tarafı - 320/100/102 hesaplarında = alış faturası tutarı
                if new_priority > current_priority and alacak_amt > 0:
                    ledger_docs[doc_num]["InvoiceAmount"] = alacak_amt
                    ledger_docs[doc_num]["_priority"] = new_priority
            
            # KDV hesapları
            if acc_code.startswith('191') or acc_code.startswith('391'):
                ledger_docs[doc_num]["TaxTotal"] += borc_amt or alacak_amt
        
        # TotalDebit hesapla - InvoiceAmount varsa onu kullan
        for doc_num, doc_data in ledger_docs.items():
            if "InvoiceAmount" in doc_data and doc_data["InvoiceAmount"] > 0:
                doc_data["TotalDebit"] = doc_data["InvoiceAmount"]
            elif doc_data.get("TotalDebit", 0) == 0:
                # Fallback: En yüksek tutarı bul
                max_amt = 0
                for line in doc_data.get("Lines", []):
                    if line.get("Amt", 0) > max_amt:
                        max_amt = line["Amt"]
                if max_amt > 0:
                    doc_data["TotalDebit"] = max_amt
            
            # Temizlik - internal fields
            doc_data.pop("_priority", None)
            doc_data.pop("InvoiceAmount", None)
        
        print(f"Defterden {len(ledger_docs)} belge çıkarıldı.")
        return ledger_docs, None
        
    except Exception as e:
        print(f"HTML Kebir okuma hatası: {e}")
        import traceback
        traceback.print_exc()
        return {}, None


def parse_html_kebir_detailed(html_path, encoding='windows-1254'):
    """
    HTML Kebir dosyasını parse eder ve detaylı liste döndürür.
    Mutabakat için hesap bazlı detaylı çıktı sağlar.
    
    Returns:
        entries: list - Tüm kayıtların listesi
        summary: dict - Özet bilgiler
    """
    print(f"HTML Kebir (detaylı) analiz ediliyor: {html_path}")
    
    if not os.path.exists(html_path):
        print("HATA: Kebir dosyası bulunamadı!")
        return [], {}
    
    try:
        with open(html_path, 'rb') as f:
            content = f.read()
        
        try:
            text = content.decode(encoding)
        except:
            try:
                text = content.decode('utf-8')
            except:
                text = content.decode('latin-1')
        
        parser = KebirHTMLParser()
        parser.feed(text)
        
        summary = {
            'company_name': parser.company_name,
            'company_code': parser.company_code,
            'total_entries': len(parser.entries),
            'devir_borc': parser.devir_borc,
            'devir_alacak': parser.devir_alacak
        }
        
        return parser.entries, summary
        
    except Exception as e:
        print(f"HTML Kebir okuma hatası: {e}")
        return [], {}


# Test
if __name__ == "__main__":
    test_path = r"c:\Users\Asus\Desktop\RAD EYLÜL EKİM\Yeni klasör\10 2025 Dönem Kebir.HTM"
    if os.path.exists(test_path):
        ledger_docs, vkn = parse_html_kebir(test_path)
        print(f"\nÖrnek belgeler:")
        for i, (doc_num, data) in enumerate(list(ledger_docs.items())[:5]):
            print(f"  {doc_num}: {data.get('Date')} - {data.get('TotalDebit'):.2f} TL")
