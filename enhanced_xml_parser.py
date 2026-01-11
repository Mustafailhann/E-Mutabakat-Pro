# -*- coding: utf-8 -*-
"""
Enhanced XML Parser - Merkezi UBL-TR XML Parsing Modülü
Tüm GİB e-belge formatlarını parse eder (e-F atura, e-Arşiv, İrsaliye, vb.)
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# UBL-TR Namespaces
NS = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
    'n1': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
    'despatch': 'urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2',
    'receipt': 'urn:oasis:names:specification:ubl:schema:xsd:ReceiptAdvice-2',
}


def normalize_float(val) -> float:
    """Güvenli float dönüşümü"""
    try:
        if isinstance(val, str):
            return float(val.replace(',', '.'))
        return float(val)
    except:
        return 0.0


def normalize_date(date_str: str) -> str:
    """Tarih formatını normalize et"""
    if not date_str:
        return ""
    return date_str.split("T")[0]


def parse_ubl_invoice(xml_content: bytes) -> Dict:
    """
    UBL-TR formatındaki e-fatura XML'ini parse et.
    
    Args:
        xml_content: XML içeriği (bytes)
    
    Returns:
        Fatura bilgilerini içeren dict
    """
    try:
        root = ET.fromstring(xml_content)
        
        # Helper fonksiyon: namespace-aware text alma
        def get_text(xpath: str, default: str = "", element=None) -> str:
            el = element if element is not None else root
            found = el.find(xpath, NS)
            return found.text.strip() if found is not None and found.text else default
        
        # Helper fonksiyon: element bulma
        def find_element(xpath: str, element=None):
            el = element if element is not None else root
            return el.find(xpath, NS)
        
        # Temel bilgiler
        invoice_data = {
            # ETTN / UUID
            'ettn': get_text('.//cbc:UUID'),
            'uuid': get_text('.//cbc:UUID'),
            
            # Fatura bilgileri
            'invoice_no': get_text('.//cbc:ID'),
            'invoice_date': get_text('.//cbc:IssueDate'),
            'invoice_time': get_text('.//cbc:IssueTime'),
            
            # Profil ve tip
            'profile_id': get_text('.//cbc:ProfileID'),
            'invoice_type_code': get_text('.//cbc:InvoiceTypeCode'),
            'customization_id': get_text('.//cbc:CustomizationID'),
            
            # Para birimi
            'currency': get_text('.//cbc:DocumentCurrencyCode', 'TRY'),
        }
        
        # Tedarikçi (Satıcı) bilgileri
        supplier_party = find_element('.//cac:AccountingSupplierParty/cac:Party')
        if supplier_party is not None:
            invoice_data['supplier_name'] = get_text('.//cac:PartyName/cbc:Name', element=supplier_party)
            invoice_data['supplier_vkn'] = get_text('.//cac:PartyIdentification/cbc:ID[@schemeID="VKN"]', element=supplier_party) or \
                                           get_text('.//cac:PartyIdentification/cbc:ID[@schemeID="TCKN"]', element=supplier_party) or \
                                           get_text('.//cac:PartyIdentification/cbc:ID', element=supplier_party)
            invoice_data['supplier_tax_office'] = get_text('.//cac:PartyTaxScheme/cac:TaxScheme/cbc:Name', element=supplier_party)
            
            # Adres bilgileri
            address = find_element('.//cac:PostalAddress', element=supplier_party)
            if address is not None:
                invoice_data['supplier_address'] = {
                    'street': get_text('.//cbc:StreetName', element=address),
                    'building': get_text('.//cbc:BuildingNumber', element=address),
                    'city_subdivision': get_text('.//cbc:CitySubdivisionName', element=address),
                    'city': get_text('.//cbc:CityName', element=address),
                    'postal_zone': get_text('.//cbc:PostalZone', element=address),
                    'country': get_text('.//cac:Country/cbc:Name', element=address)
                }
        
        # Müşteri (Alıcı) bilgileri
        customer_party = find_element('.//cac:AccountingCustomerParty/cac:Party')
        if customer_party is not None:
            invoice_data['customer_name'] = get_text('.//cac:PartyName/cbc:Name', element=customer_party)
            invoice_data['customer_vkn'] = get_text('.//cac:PartyIdentification/cbc:ID[@schemeID="VKN"]', element=customer_party) or \
                                           get_text('.//cac:PartyIdentification/cbc:ID[@schemeID="TCKN"]', element=customer_party) or \
                                           get_text('.//cac:PartyIdentification/cbc:ID', element=customer_party)
            invoice_data['customer_tax_office'] = get_text('.//cac:PartyTaxScheme/cac:TaxScheme/cbc:Name', element=customer_party)
            
            # Adres bilgileri
            address = find_element('.//cac:PostalAddress', element=customer_party)
            if address is not None:
                invoice_data['customer_address'] = {
                    'street': get_text('.//cbc:StreetName', element=address),
                    'building': get_text('.//cbc:BuildingNumber', element=address),
                    'city_subdivision': get_text('.//cbc:CitySubdivisionName', element=address),
                    'city': get_text('.//cbc:CityName', element=address),
                    'postal_zone': get_text('.//cbc:PostalZone', element=address),
                    'country': get_text('.//cac:Country/cbc:Name', element=address)
                }
        
        # Tutar bilgileri
        monetary_total = find_element('.//cac:LegalMonetaryTotal')
        if monetary_total is not None:
            invoice_data['line_extension_amount'] = normalize_float(get_text('.//cbc:LineExtensionAmount', element=monetary_total))
            invoice_data['tax_exclusive_amount'] = normalize_float(get_text('.//cbc:TaxExclusiveAmount', element=monetary_total))
            invoice_data['tax_inclusive_amount'] = normalize_float(get_text('.//cbc:TaxInclusiveAmount', element=monetary_total))
            invoice_data['allowance_total_amount'] = normalize_float(get_text('.//cbc:AllowanceTotalAmount', element=monetary_total))
            invoice_data['payable_amount'] = normalize_float(get_text('.//cbc:PayableAmount', element=monetary_total))
        
        # Vergi bilgileri
        tax_total = find_element('.//cac:TaxTotal')
        if tax_total is not None:
            invoice_data['tax_amount'] = normalize_float(get_text('.//cbc:TaxAmount', element=tax_total))
            
            # KDV oranlarına göre gruplama
            tax_subtotals = root.findall('.//cac:TaxTotal/cac:TaxSubtotal', NS)
            invoice_data['tax_breakdown'] = []
            for subtotal in tax_subtotals:
                tax_category = find_element('.//cac:TaxCategory', element=subtotal)
                if tax_category is not None:
                    invoice_data['tax_breakdown'].append({
                        'percent': normalize_float(get_text('.//cbc:Percent', element=tax_category)),
                        'taxable_amount': normalize_float(get_text('.//cbc:TaxableAmount', element=subtotal)),
                        'tax_amount': normalize_float(get_text('.//cbc:TaxAmount', element=subtotal)),
                        'tax_scheme_name': get_text('.//cac:TaxScheme/cbc:Name', element=tax_category)
                    })
        
        # Tevkifat bilgileri
        withholding_total = find_element('.//cac:WithholdingTaxTotal')
        if withholding_total is not None:
            invoice_data['withholding_amount'] = normalize_float(get_text('.//cbc:TaxAmount', element=withholding_total))
        else:
            invoice_data['withholding_amount'] = 0.0
        
        # Kalem bilgileri
        invoice_lines = root.findall('.//cac:InvoiceLine', NS)
        invoice_data['lines'] = []
        for line in invoice_lines:
            line_data = {
                'id': get_text('.//cbc:ID', element=line),
                'name': get_text('.//cac:Item/cbc:Name', element=line),
                'quantity': normalize_float(get_text('.//cbc:InvoicedQuantity', element=line)),
                'unit_code': get_text('.//cbc:InvoicedQuantity/@unitCode', element=line),
                'price': normalize_float(get_text('.//cac:Price/cbc:PriceAmount', element=line)),
                'line_extension_amount': normalize_float(get_text('.//cbc:LineExtensionAmount', element=line)),
            }
            invoice_data['lines'].append(line_data)
        
        # Notlar
        invoice_data['notes'] = []
        notes = root.findall('.//cbc:Note', NS)
        for note in notes:
            if note.text:
                invoice_data['notes'].append(note.text.strip())
        
        # KDV Dönemi hesaplama (YYYY/MM formatında)
        if invoice_data['invoice_date']:
            try:
                dt = datetime.strptime(invoice_data['invoice_date'], '%Y-%m-%d')
                invoice_data['kdv_period'] = dt.strftime('%Y/%m')
                invoice_data['invoice_date_formatted'] = dt.strftime('%d.%m.%Y')
            except:
                invoice_data['kdv_period'] = ""
                invoice_data['invoice_date_formatted'] = invoice_data['invoice_date']
        
        return invoice_data
        
    except Exception as e:
        print(f"[ERROR] XML parse hatası: {e}")
        return {}


def extract_invoice_summary(invoice_data: Dict) -> str:
    """
    Fatura verilerinden özet bilgi çıkar.
    
    Returns:
        Özet string (kullanıcı dostu)
    """
    summary_parts = []
    
    if invoice_data.get('profile_id'):
        summary_parts.append(f"Senaryo: {invoice_data['profile_id']}")
    
    if invoice_data.get('invoice_type_code'):
        summary_parts.append(f"Tip: {invoice_data['invoice_type_code']}")
    
    if invoice_data.get('invoice_no'):
        summary_parts.append(f"No: {invoice_data['invoice_no']}")
    
    if invoice_data.get('invoice_date'):
        summary_parts.append(f"Tarih: {invoice_data.get('invoice_date_formatted', invoice_data['invoice_date'])}")
    
    if invoice_data.get('supplier_name'):
        summary_parts.append(f"Satıcı: {invoice_data['supplier_name']}")
    
    if invoice_data.get('customer_name'):
        summary_parts.append(f"Alıcı: {invoice_data['customer_name']}")
    
    if invoice_data.get('payable_amount'):
        currency = invoice_data.get('currency', 'TRY')
        summary_parts.append(f"Tutar: {invoice_data['payable_amount']:,.2f} {currency}")
    
    return " | ".join(summary_parts)


if __name__ == "__main__":
    print("Enhanced XML Parser modülü yüklendi.")
    print("Kullanım: from enhanced_xml_parser import parse_ubl_invoice")
