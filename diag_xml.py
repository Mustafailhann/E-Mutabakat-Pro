import os
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO

def normalize_float(val):
    try:
        return float(val)
    except:
        return 0.0

def normalize_date(date_str):
    if not date_str: return ""
    return date_str.split("T")[0]

def parse_invoice_xml_advanced(content):
    try:
        root = ET.fromstring(content)
        def find_text(keywords, element=None):
            el = element if element is not None else root
            for e in el.iter():
                for kw in keywords:
                    if e.tag.endswith(kw):
                        return e.text
            return None
            
        def find_element(keywords, element=None):
            el = element if element is not None else root
            for e in el.iter():
                for kw in keywords:
                    if e.tag.endswith(kw):
                        return e
            return None

        fatura_no = find_text(["CBC:ID", "}ID"]) or "Bilinmiyor"
        
        # Missing elements in the original code
        ettn = find_text(["UUID"]) or "-"
        scenario = find_text(["ProfileID"]) or "-"
        inv_type_ubl = find_text(["InvoiceTypeCode"]) or "SATIS"
        
        monetary_total = find_element(["LegalMonetaryTotal"])
        tax_excl_amt = 0.0
        discount_amt = 0.0
        if monetary_total is not None:
            tax_excl_amt = normalize_float(find_text(["TaxExclusiveAmount"], monetary_total))
            discount_amt = normalize_float(find_text(["AllowanceTotalAmount"], monetary_total))

        curr_code = "TRY"
        dcc_node = find_element(["DocumentCurrencyCode"])
        if dcc_node is not None and dcc_node.text:
            curr_code = dcc_node.text.strip()
        
        # Simplified for diag
        return {
            "No": fatura_no,
            "ETTN": ettn,
            "Scenario": scenario,
            "InvType": inv_type_ubl,
            "TaxExcl": tax_excl_amt,
            "Discount": discount_amt,
            "Currency": curr_code
        }
    except Exception as e:
        print(f"Parsing Error: {e}")
        return None

def diag_zips(zip_paths):
    for label, path in zip_paths.items():
        print(f"Checking {label}: {path}")
        if not os.path.exists(path):
            print(f"MISSING: {path}")
            continue
        
        count = 0
        with zipfile.ZipFile(path, 'r') as z:
            for name in z.namelist():
                if name.lower().endswith(".xml"):
                    count += 1
                    if count <= 2:
                        with z.open(name) as f:
                            data = parse_invoice_xml_advanced(f.read())
                            print(f"  Example {count}: {name} -> {data}")
        print(f"  Total XML files: {count}")

if __name__ == "__main__":
    WORK_DIR = r"c:\Users\Asus\Desktop\agent ff"
    ZIPS = {
        "Gelen": os.path.join(WORK_DIR, "Gelen e-Fatura.zip"),
        "Giden": os.path.join(WORK_DIR, "Giden e-Fatura.zip"),
        "e-Arsiv": os.path.join(WORK_DIR, "e-Arsiv.zip")
    }
    diag_zips(ZIPS)
