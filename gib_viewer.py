"""
GIB e-Fatura Görüntüleyici - Enhanced XSLT Transformer
Uses the official GIB XSLT stylesheets to transform UBL-TR invoice XMLs to HTML.
Supports automatic XSLT selection based on document type and metadata extraction.
"""

import os
from lxml import etree
from typing import Dict, Optional, Tuple
from pathlib import Path

# Path to the GIB XSLT stylesheets
XSLT_DIR = os.path.join(os.path.dirname(__file__), "gib_viewer_extracted")
JAR_CONTENT_DIR = os.path.join(XSLT_DIR, "jar_content")

# XSLT stylesheet paths
XSLT_INVOICE = os.path.join(JAR_CONTENT_DIR, "default.xslt")  # Kapsamlı e-Fatura şablonu (200KB)
XSLT_DESPATCH = os.path.join(JAR_CONTENT_DIR, "despatchadvice.xslt")  # İrsaliye
XSLT_RECEIPT = os.path.join(JAR_CONTENT_DIR, "receiptadvice.xslt")  # Müstahsil
XSLT_MUSTAHSIL = os.path.join(JAR_CONTENT_DIR, "mustahsil.xslt")  # Müstahsil Makbuzu

# Fallback XSLT (basit versiyon)
XSLT_SIMPLE = os.path.join(XSLT_DIR, "default.xslt")

# UBL-TR Namespaces
NS = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:Common BasicComponents-2',
    'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
    'n1': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
    'despatch': 'urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2',
    'receipt': 'urn:oasis:names:specification:ubl:schema:xsd:ReceiptAdvice-2',
}


def detect_document_type(xml_doc: etree._Element) -> str:
    """
    XML dokümanının tipini belirle.
    
    Returns:
        'invoice', 'despatch', 'receipt', 'mustahsil'
    """
    root_tag = xml_doc.tag
    
    if 'Invoice' in root_tag:
        return 'invoice'
    elif 'DespatchAdvice' in root_tag:
        return 'despatch'
    elif 'ReceiptAdvice' in root_tag:
        return 'receipt'
    elif 'Mustahsil' in root_tag or 'MMK' in root_tag:
        return 'mustahsil'
    
    return 'invoice'  # Default


def select_xslt_template(xml_doc: etree._Element) -> str:
    """
    XML içeriğine göre uygun XSLT şablonunu seç.
    
    Args:
        xml_doc: Parsed XML document
        
    Returns:
        XSLT dosya yolu
    """
    doc_type = detect_document_type(xml_doc)
    
    xslt_map = {
        'invoice': XSLT_INVOICE,
        'despatch': XSLT_DESPATCH,
        'receipt': XSLT_RECEIPT,
        'mustahsil': XSLT_MUSTAHSIL,
    }
    
    xslt_path = xslt_map.get(doc_type, XSLT_INVOICE)
    
    # Dosya yoksa fallback kullan
    if not os.path.exists(xslt_path):
        print(f"[WARNING] XSLT bulunamadı: {xslt_path}, fallback kullanılıyor")
        return XSLT_SIMPLE
    
    return xslt_path


def extract_metadata(xml_doc: etree._Element) -> Dict[str, any]:
    """
    XML'den metadata bilgilerini çıkar.
    
    Returns:
        Dict with: ettn, invoice_no, invoice_date, profile_id, invoice_type, 
                   supplier_name, supplier_vkn, customer_name, customer_vkn,
                   currency, total_amount, tax_amount
    """
    metadata = {}
    
    # Helper function to safely get text
    def get_text(xpath: str, default: str = "") -> str:
        elem = xml_doc.find(xpath, NS)
        return elem.text.strip() if elem is not None and elem.text else default
    
    try:
        # ETTN (UUID)
        metadata['ettn'] = get_text('.//cbc:UUID')
        
        # Fatura No
        metadata['invoice_no'] = get_text('.//cbc:ID')
        
        # Fatura Tarihi
        metadata['invoice_date'] = get_text('.//cbc:IssueDate')
        metadata['invoice_time'] = get_text('.//cbc:IssueTime')
        
        # Profil ve Tip
        metadata['profile_id'] = get_text('.//cbc:ProfileID')
        metadata['invoice_type_code'] = get_text('.//cbc:InvoiceTypeCode')
        
        # Tedarikçi (Satıcı) Bilgileri
        metadata['supplier_name'] = get_text('.//cac:AccountingSupplierParty//cac:PartyName/cbc:Name')
        metadata['supplier_vkn'] = get_text('.//cac:AccountingSupplierParty//cac:PartyIdentification/cbc:ID')
        metadata['supplier_tax_office'] = get_text('.//cac:AccountingSupplierParty//cac:PartyTaxScheme/cac:TaxScheme/cbc:Name')
        
        # Müşteri (Alıcı) Bilgileri
        metadata['customer_name'] = get_text('.//cac:AccountingCustomerParty//cac:PartyName/cbc:Name')
        metadata['customer_vkn'] = get_text('.//cac:AccountingCustomerParty//cac:PartyIdentification/cbc:ID')
        metadata['customer_tax_office'] = get_text('.//cac:AccountingCustomerParty//cac:PartyTaxScheme/cac:TaxScheme/cbc:Name')
        
        # Para Birimi
        metadata['currency'] = get_text('.//cbc:DocumentCurrencyCode', 'TRY')
        
        # Tutar Bilgileri
        metadata['line_extension_amount'] = get_text('.//cac:LegalMonetaryTotal/cbc:LineExtensionAmount')
        metadata['tax_exclusive_amount'] = get_text('.//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount')
        metadata['tax_inclusive_amount'] = get_text('.//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount')
        metadata['payable_amount'] = get_text('.//cac:LegalMonetaryTotal/cbc:PayableAmount')
        metadata['tax_amount'] = get_text('.//cac:TaxTotal/cbc:TaxAmount')
        
        # Tevkifat
        withholding = get_text('.//cac:WithholdingTaxTotal/cbc:TaxAmount')
        metadata['withholding_amount'] = withholding if withholding else '0'
        
        # Senaryo türü belirleme
        profile = metadata['profile_id'].upper()
        if 'EARSIV' in profile:
            metadata['scenario'] = 'e-Arşiv Fatura'
        elif 'TICARIFATURA' in profile:
            metadata['scenario'] = 'e-Fatura'
        elif 'YOLCUBERABERFATURA' in profile:
            metadata['scenario'] = 'Yolcu Beraber Fatura'
        else:
            metadata['scenario'] = metadata['profile_id']
        
        # Fatura türü açıklaması
        inv_type = metadata['invoice_type_code']
        type_map = {
            'SATIS': 'Satış Faturası',
            'IADE': 'İade Faturası',
            'TEVKIFAT': 'Tevkifatlı Fatura',
            'ISTISNA': 'İstisna Faturası',
            'OZELMATRAH': 'Özel Matrah Faturası',
            'IHRACKAYITLI': 'İhraç Kayıtlı Fatura',
        }
        metadata['invoice_type_name'] = type_map.get(inv_type, inv_type)
        
    except Exception as e:
        print(f"[WARNING] Metadata extraction error: {e}")
    
    return metadata


def transform_invoice_to_html(xml_content: str, xslt_path: str = None) -> Tuple[str, Dict]:
    """
    Transform an invoice XML to HTML using the GIB XSLT stylesheet.
    
    Args:
        xml_content: The invoice XML as a string
        xslt_path: Optional path to a custom XSLT file. If None, auto-selects based on document type
        
    Returns:
        Tuple of (HTML string, metadata dict)
    """
    try:
        # Parse XML
        xml_doc = etree.fromstring(xml_content.encode('utf-8'))
        
        # Extract metadata
        metadata = extract_metadata(xml_doc)
        
        # Select XSLT if not provided
        if xslt_path is None:
            xslt_path = select_xslt_template(xml_doc)
            print(f"[INFO] Using XSLT: {Path(xslt_path).name}")
        
        # Parse XSLT
        xslt_doc = etree.parse(xslt_path)
        transform = etree.XSLT(xslt_doc)
        
        # Apply transformation
        result = transform(xml_doc)
        html_output = str(result)
        
        return html_output, metadata
        
    except Exception as e:
        print(f"[ERROR] XSLT transformation failed: {e}")
        # Fallback: return basic HTML with error
        error_html = f"""
        <html>
        <head><title>XML Görüntüleme Hatası</title></head>
        <body>
            <h1>XML Dönüştürme Hatası</h1>
            <p>Hata: {str(e)}</p>
            <h2>Ham XML İçeriği:</h2>
            <pre style="background: #f5f5f5; padding: 20px; overflow: auto;">
{xml_content[:5000]}
            </pre>
        </body>
        </html>
        """
        return error_html, {}


def transform_invoice_file(xml_path: str, output_path: str = None) -> Tuple[str, Dict]:
    """
    Transform an invoice XML file to HTML.
    
    Args:
        xml_path: Path to the invoice XML file
        output_path: Optional path to save the HTML output
        
    Returns:
        Tuple of (HTML string or output path, metadata dict)
    """
    with open(xml_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    html_output, metadata = transform_invoice_to_html(xml_content)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        return output_path, metadata
    
    return html_output, metadata


if __name__ == "__main__":
    # Test with a sample invoice
    import sys
    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
        html, meta = transform_invoice_file(xml_file)
        
        print("\n=== METADATA ===")
        for key, value in meta.items():
            print(f"{key}: {value}")
        
        print("\n=== HTML (first 1000 chars) ===")
        print(html[:1000])
    else:
        print("Usage: python gib_viewer.py <invoice.xml>")
