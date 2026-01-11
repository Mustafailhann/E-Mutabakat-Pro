import os
import zipfile
import xml.etree.ElementTree as ET
import csv
from io import BytesIO
from datetime import datetime
import json
from tcmb_helper import get_tcmb_rate
import html_kebir_parser

# --- Yapılandırma ---
WORK_DIR = r"c:\Users\Asus\Desktop\agent ff"
LEDGER_XML = os.path.join(WORK_DIR, "9980735761-202510-K-000000_nosign.xml")
INVOICE_ZIPS = {
    "Gelen": os.path.join(WORK_DIR, "Gelen e-Fatura.zip"),
    "Giden": os.path.join(WORK_DIR, "Giden e-Fatura.zip"),
    "e-Arsiv": os.path.join(WORK_DIR, "e-Arsiv.zip")
}
OUTPUT_FILE = os.path.join(WORK_DIR, "Detayli_Karsilastirma_Raporu.csv")

# Namespaces (e-Defter ve UBL)
NS_XBRL = {'xbrl': 'http://www.xbrl.org/2003/instance', 'gl-cor': 'http://www.xbrl.org/int/gl/cor/2006-10-25', 'gl-bus': 'http://www.xbrl.org/int/gl/bus/2006-10-25'}

def normalize_float(val):
    try:
        return float(val)
    except:
        return 0.0

def normalize_date(date_str):
    # YYYY-MM-DD formatını bekliyoruz
    if not date_str: return ""
    return date_str.split("T")[0]

def parse_ledger_advanced(xml_path):
    print(f"Defter analiz ediliyor (Detaylı): {xml_path}")
    if not os.path.exists(xml_path):
        print("HATA: Defter dosyası bulunamadı!")
        return {}, None

    ledger_docs = {} 
    my_vkn = None
    
    try:
        context = ET.iterparse(xml_path, events=("start", "end"))
        
        for event, elem in context:
            # VKN Tespiti (xbrli:identifier)
            if event == "end" and elem.tag.endswith("identifier"):
                if not my_vkn: 
                     my_vkn = elem.text.strip() if elem.text else None
                     print(f"Defter Sahibi VKN: {my_vkn}")

            if event == "end" and elem.tag.endswith("entryDetail"):
                doc_num = elem.find(".//{http://www.xbrl.org/int/gl/cor/2006-10-25}documentNumber")
                
                if doc_num is not None and doc_num.text:
                    d_no = doc_num.text.strip()
                    
                    amt_node = elem.find(".//{http://www.xbrl.org/int/gl/cor/2006-10-25}amount")
                    amt = normalize_float(amt_node.text) if amt_node is not None else 0.0
                    
                    dc_node = elem.find(".//{http://www.xbrl.org/int/gl/cor/2006-10-25}debitCreditCode")
                    dc = dc_node.text if dc_node is not None else ""
                    
                    acc_node = elem.find(".//{http://www.xbrl.org/int/gl/cor/2006-10-25}accountMainID")
                    acc_code = acc_node.text.strip() if acc_node is not None else ""
                    
                    date_node = elem.find(".//{http://www.xbrl.org/int/gl/cor/2006-10-25}postingDate")
                    p_date = date_node.text if date_node is not None else ""
                    
                    # Belge Türü (invoice, receipt, check vs)
                    dtype_node = elem.find(".//{http://www.xbrl.org/int/gl/cor/2006-10-25}documentType")
                    d_type = dtype_node.text.strip() if dtype_node is not None else "other"
                    
                    # Açıklama (documentDescription)
                    desc_node = elem.find(".//{http://www.xbrl.org/int/gl/cor/2006-10-25}entryComment")
                    desc = desc_node.text.strip() if desc_node is not None else ""


                    if d_no not in ledger_docs:
                        ledger_docs[d_no] = {
                            "TotalDebit": 0.0, 
                            "Date": p_date,
                            "Type": d_type,
                            "Desc": desc,
                            "Accounts": set(),
                            "TaxTotal": 0.0, 
                            "Lines": [] 
                        }
                    
                    ledger_docs[d_no]["Accounts"].add(acc_code)
                    
                    ledger_docs[d_no]["Lines"].append({
                        "Acc": acc_code,
                        "DC": dc,
                        "Amt": amt,
                        "Desc": desc
                    })
                    
                    if dc == "D": 
                        ledger_docs[d_no]["TotalDebit"] += amt
                    
                    if acc_code.startswith("191") or acc_code.startswith("391"):
                        ledger_docs[d_no]["TaxTotal"] += amt

                elem.clear()
                
        print(f"Defterden {len(ledger_docs)} belge çıkarıldı.")
        return ledger_docs, my_vkn

    except Exception as e:
        print(f"Defter okuma hatası: {e}")
        return {}, None


def parse_invoice_xml_advanced(content):
    try:
        # Tespiti zor olan karakter kodlamaları için ön kontrol
        if isinstance(content, bytes):
            # Try to detect encoding from XML declaration if possible or default to turkish
            try:
                # Basic sniff
                sniff = content[:100].decode('ascii', errors='ignore')
                if 'encoding="ISO-8859-9"' in sniff.upper() or 'encoding="WINDOWS-1254"' in sniff.upper():
                    content = content.decode('iso-8859-9')
                else:
                    content = content.decode('utf-8-sig') # Handle BOM
            except:
                content = content.decode('iso-8859-9', errors='ignore')

        root = ET.fromstring(content)
        # Namespace independent search helper
        def find_text(keywords, element=None):
            el = element if element is not None else root
            for e in el.iter():
                for kw in keywords:
                    if e.tag.endswith(kw):
                        txt = (e.text or "").strip()
                        if txt: return txt
            return None
            
        def find_element(keywords, element=None):
            el = element if element is not None else root
            for e in el.iter():
                for kw in keywords:
                    if e.tag.endswith(kw):
                        return e
            return None

        # Fatura No
        fatura_no = find_text(["CBC:ID", "}ID"]) # Genellikle root level ID
        if not fatura_no: fatura_no = "Bilinmiyor"
        
        # Para Birimi (Currency)
        curr_code = "TRY"
        
        # 1. DocumentCurrencyCode ara
        dcc_node = find_element(["DocumentCurrencyCode"])
        if dcc_node is not None and dcc_node.text:
            curr_code = dcc_node.text.strip()
        else:
            # 2. PayableAmount currencyID attribute ara
            pay_amt_node = find_element(["PayableAmount"])
            if pay_amt_node is not None:
                for k, v in pay_amt_node.attrib.items():
                    if "currencyID" in k:
                        curr_code = v
                        break
        
        # Kur (XML içindeki)
        calc_rate_val = None
        rate_source = "XML (Varsayılan)" if curr_code == "TRY" else ""
        
        # PricingExchangeRate -> CalculationRate
        for er in root.iter():
            if er.tag.endswith("PricingExchangeRate"):
                src = find_text(["SourceCurrencyCode"], er)
                tgt = find_text(["TargetCurrencyCode"], er)
                rate = find_text(["CalculationRate"], er)
                
                if rate and tgt == "TRY":
                    calc_rate_val = float(rate)
                    rate_source = "XML (PricingExchangeRate)"
                    break
        
        date_str = find_text(["IssueDate"])
        normalized_date = normalize_date(date_str)
        
        # Tutar (PayableAmount = Ödenecek/Net, TaxInclusiveAmount = Brüt)
        pay_amt_node = find_element(["PayableAmount"])
        pay_amt = normalize_float(pay_amt_node.text) if pay_amt_node is not None else 0.0
        
        tax_inc_amt = 0.0
        tax_inc_node = find_element(["TaxInclusiveAmount"])
        if tax_inc_node is not None:
             tax_inc_amt = normalize_float(tax_inc_node.text)
        
        if tax_inc_amt == 0.0:
             tax_inc_amt = pay_amt
             
        # Gelişmiş Bilgi Çekme (ETTN, Senaryo, Tip)
        ettn = find_text(["UUID"]) or "-"
        scenario = find_text(["ProfileID"]) or "-"
        inv_type_ubl = find_text(["InvoiceTypeCode"]) or "SATIS"
        
        vat_tax = 0.0
        withholding_tax = 0.0
        other_tax = 0.0  # Konaklama, Damga vb.
        
        # 1. Ana KDV (TaxTotal -> TaxSubtotal) - TaxTypeCode'a göre ayır
        for tt in root.findall("{*}TaxTotal"):
            for ts in tt.findall("{*}TaxSubtotal"):
                tax_amt_node = ts.find("{*}TaxAmount")
                tax_amt = normalize_float(tax_amt_node.text) if tax_amt_node is not None else 0.0
                
                # TaxTypeCode bul
                tax_cat = ts.find("{*}TaxCategory")
                tax_scheme = tax_cat.find("{*}TaxScheme") if tax_cat is not None else None
                tax_type_code_node = tax_scheme.find("{*}TaxTypeCode") if tax_scheme is not None else None
                tax_type_code = tax_type_code_node.text if tax_type_code_node is not None else ""
                
                # 0015 = KDV (Katma Değer Vergisi)
                # 9015 = Konaklama Vergisi
                # 0003 = Damga Vergisi
                # vb.
                if tax_type_code == "0015":
                    vat_tax += tax_amt
                else:
                    other_tax += tax_amt
        
        # Fallback: TaxSubtotal yoksa header TaxAmount'u kullan (eski format)
        if vat_tax == 0.0 and other_tax == 0.0:
            for tt in root.findall("{*}TaxTotal"):
                has_subtotal = tt.find("{*}TaxSubtotal") is not None
                if not has_subtotal:
                    tax_amt_node = tt.find("{*}TaxAmount")
                    if tax_amt_node is not None:
                        vat_tax += normalize_float(tax_amt_node.text)
        
        # 2. Tevkifat / Stopaj (WithholdingTaxTotal)
        for wtt in root.findall("{*}WithholdingTaxTotal"): 
            tax_amt_node = wtt.find("{*}TaxAmount")
            if tax_amt_node is not None:
                withholding_tax += normalize_float(tax_amt_node.text)
        
        total_tax = vat_tax + withholding_tax + other_tax

        # Matrah ve İskonto (LegalMonetaryTotal)
        tax_excl_amt = 0.0
        discount_amt = 0.0
        monetary_total = find_element(["LegalMonetaryTotal"])
        if monetary_total is not None:
            tax_excl_amt = normalize_float(find_text(["TaxExclusiveAmount"], monetary_total))
            discount_amt = normalize_float(find_text(["AllowanceTotalAmount"], monetary_total))
        
        if tax_excl_amt == 0.0:
            tax_excl_amt = tax_inc_amt - total_tax
             
        # İsim ve VKN Tespiti
        def get_party_info(party_node_name):
            node = find_element([party_node_name])
            if node is None: return {}
            # Party node search (robust)
            party = find_element(["Party"], node)
            if party is None: return {}
            
            # Name Extraction (UBL-TR Priority)
            # 1. RegistrationName from PartyLegalEntity (Official Name)
            name = None
            legal_ent = party.find("{*}PartyLegalEntity")
            if legal_ent is not None:
                name = find_text(["RegistrationName"], legal_ent)
            
            # 2. Name from PartyName (Trading Name)
            if not name:
                name = find_text(["PartyName", "Name"], party)
            
            # 3. Fallback to Bilinmiyor
            if not name: name = "Bilinmiyor"
            
            # Address
            addr = party.find("{*}PostalAddress")
            address_str = ""
            city = ""
            subdivision = ""
            if addr is not None:
                street = find_text(["StreetName"], addr)
                bldg = find_text(["BuildingNumber"], addr)
                subdivision = find_text(["CitySubdivisionName"], addr)
                city = find_text(["CityName"], addr)
                address_str = f"{street} No:{bldg}" if bldg else (street if street else "")
            
            # Tax Office
            tax_office = ""
            pts = party.find("{*}PartyTaxScheme")
            if pts is not None:
                ts = pts.find("{*}TaxScheme")
                if ts is not None:
                    tax_office = find_text(["Name"], ts)

            # VKN/TCKN
            vkn = ""
            for p_id in party.findall("{*}PartyIdentification"):
                id_val = find_text(["ID"], p_id)
                if id_val and len(id_val) >= 10: # VKN or TCKN
                    vkn = id_val
                    break
            
            return {
                "Name": name, 
                "VKN": vkn, 
                "Address": address_str, 
                "City": city, 
                "Sub": subdivision,
                "TaxOffice": tax_office
            }
        
        # Ekstra Alanlar (Notlar, İrsaliye, Sipariş, Ödeme)
        notes = []
        for n in root.findall("{*}Note"):
            if n.text: notes.append(n.text)
            
        despatches = []
        for ddr in root.findall("{*}DespatchDocumentReference"):
            d_id = find_text(["ID"], ddr)
            d_date = find_text(["IssueDate"], ddr)
            if d_id: despatches.append(f"{d_id} ({d_date})")

        orders = []
        for ore in root.findall("{*}OrderReference"):
            o_id = find_text(["ID"], ore)
            o_date = find_text(["IssueDate"], ore)
            if o_id: orders.append(f"{o_id} ({o_date})")
            
        payment_means = []
        for pm in root.findall("{*}PaymentMeans"):
             pay_channel = find_text(["PaymentChannelCode"], pm)
             pay_account = pm.find("{*}PayeeFinancialAccount")
             acc_info = ""
             if pay_account is not None:
                 iban = find_text(["ID"], pay_account)
                 curr = find_text(["CurrencyCode"], pay_account)
                 note = find_text(["PaymentNote"], pay_account)
                 if iban: acc_info = f"IBAN: {iban} {curr or ''} {note or ''}"
             
             if acc_info: payment_means.append(acc_info)
             elif pay_channel: payment_means.append(f"Kanal: {pay_channel}")

        # Döviz Kuru (Exchange Rate)
        exchange_rate = 0.0
        ex_node = root.find("{*}PricingExchangeRate")
        if ex_node is not None:
            exchange_rate = normalize_float(find_text(["CalculationRate"], ex_node))
        
        if exchange_rate == 0.0:
            ex_node = root.find("{*}PaymentExchangeRate")
            if ex_node is not None:
                exchange_rate = normalize_float(find_text(["CalculationRate"], ex_node))

        # Matrah ve İskonto (LegalMonetaryTotal) - Re-read for PayableAmount
        payable_amt = 0.0
        monetary_total = find_element(["LegalMonetaryTotal"])
        if monetary_total is not None:
            payable_amt = normalize_float(find_text(["PayableAmount"], monetary_total))

        # Akıllı Vergi Kontrolü
        if total_tax == 0.0 and payable_amt > tax_excl_amt:
            calc_diff = payable_amt - tax_excl_amt
            if calc_diff > 0.01: 
                total_tax = calc_diff
                vat_tax = calc_diff

        supp_info = get_party_info("AccountingSupplierParty")
        cust_info = get_party_info("AccountingCustomerParty")

        # Satır Kalemleri (Items)
        items = []
        for line in root.findall(".//{*}InvoiceLine"):
            item_node = line.find("{*}Item")
            item_name = find_text(["Name"], item_node) if item_node is not None else ""
            item_desc = find_text(["Description"], item_node) if item_node is not None else ""
            full_desc = item_name
            if item_desc and item_desc != item_name:
                full_desc += f" ({item_desc})"
            
            qty = normalize_float(find_text(["InvoicedQuantity"], line))
            unit = ""
            qty_node = line.find("{*}InvoicedQuantity")
            if qty_node is not None: unit = qty_node.attrib.get("unitCode", "Adet")
            
            price_node = line.find("{*}Price")
            price = normalize_float(find_text(["PriceAmount"], price_node)) if price_node is not None else 0.0
            line_amt = normalize_float(find_text(["LineExtensionAmount"], line))
            
            # KDV Oranı
            tax_rate = 0.0
            line_tax = line.find("{*}TaxTotal")
            if line_tax is not None:
                sub = line_tax.find("{*}TaxSubtotal")
                if sub is not None:
                    tax_category = sub.find("{*}TaxCategory")
                    if tax_category is not None:
                         tax_rate = normalize_float(find_text(["Percent"], tax_category))
                         if tax_rate == 0: # Try subtotal level
                              tax_rate = normalize_float(find_text(["Percent"], sub))

            items.append({
                "Description": full_desc if full_desc else "Genel Hizmet/Ürün",
                "Quantity": qty,
                "Unit": unit,
                "Price": price,
                "VATRate": tax_rate,
                "Total": line_amt
            })

        return {
            "No": fatura_no,
            "Date": normalized_date,
            "Amount": pay_amt,          # Net (Orjinal Döviz)
            "GrossAmount": tax_inc_amt, # Brüt (Orjinal Döviz)
            "TaxExclAmount": tax_excl_amt,
            "Discount": discount_amt,
            "Currency": curr_code,
            "Tax": vat_tax,   # Sadece gerçek KDV (0015), diğer vergiler hariç
            "VKN": cust_info.get("VKN", supp_info.get("VKN", "")),
            "ETTN": ettn,
            "Scenario": scenario,
            "Type": inv_type_ubl,
            "Sender": supp_info,
            "Receiver": cust_info,
            "Items": items,
            "XmlRate": calc_rate_val,
            "RateSource": rate_source,
            "Notes": notes,
            "Despatches": despatches,
            "Orders": orders,
            "PaymentMeans": payment_means,
            "ExchangeRate": exchange_rate
        }
    except Exception as e:
        print(f"Parsing Error: {e}")
        return None

import rarfile

# Configure UnRAR path - try to find it in common locations
def configure_unrar():
    # If unrar is already in path, usually no need. But check Program Files just in case.
    potential_paths = [
        r"C:\Program Files\WinRAR\UnRAR.exe",
        r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
        r"UnRAR.exe" # Current dir
    ]
    for p in potential_paths:
        if os.path.exists(p):
            rarfile.UNRAR_TOOL = p
            return True
    return False

configure_unrar()

def parse_single_file(file_path, file_name, label):
    """Tekil dosya veya arşiv içindeki dosya verisini işler"""
    data = None
    try:
        content = None
        if file_name.lower().endswith(".xml") or file_name.lower().endswith(".ubl"): # Parsing .ubl too
             if isinstance(file_path, str): # Disk path
                with open(file_path, 'rb') as f:
                    content = f.read()
             else: # BytesIO or similar from archive
                 content = file_path.read()
            
             if content:
                data = parse_invoice_xml_advanced(content)
                if data:
                    data["Type"] = label
                    data["File"] = file_name
    except Exception as e:
        print(f"Hata ({file_name}): {e}")
    return data

def process_inputs(input_paths, log_callback=print):
    invoices = []
    
    def process_archive(archive_obj, archive_label):
        for name in archive_obj.namelist():
            if name.lower().endswith(".xml") or name.lower().endswith(".ubl"):
                with archive_obj.open(name) as f:
                    data = parse_single_file(f, name, archive_label)
                    if data: invoices.append(data)
            elif name.lower().endswith(".zip"):
                try:
                    z_file_data = archive_obj.read(name)
                    z_data = BytesIO(z_file_data)
                    with zipfile.ZipFile(z_data) as sub_z:
                        process_archive(sub_z, archive_label)
                except Exception as e:
                    log_callback(f"İç ZIP hata ({name}): {e}")

    for label, path in input_paths.items():
        if not path or not os.path.exists(path):
            log_callback(f"UYARI: Dosya bulunamadı -> {path}")
            continue
            
        log_callback(f"İşleniyor ({label}): {os.path.basename(path)}")
        ext = os.path.splitext(path)[1].lower()
        
        try:
            if ext == ".xml":
                data = parse_single_file(path, os.path.basename(path), label)
                if data: invoices.append(data)
                
            elif ext == ".zip":
                try:
                    with zipfile.ZipFile(path, 'r') as z:
                        process_archive(z, label)
                except zipfile.BadZipFile:
                    log_callback(f"HATA: Bozuk ZIP dosyası -> {path}")

            elif ext == ".rar":
                try:
                    if not configure_unrar():
                        log_callback("KRİTİK UYARI: RAR desteği için UnRAR.exe bulunamadı!")
                    
                    with rarfile.RarFile(path, 'r') as r:
                         process_archive(r, label)
                except Exception as e:
                     log_callback(f"RAR okuma hatası ({os.path.basename(path)}): {str(e)}")
                     
        except Exception as e:
            log_callback(f"Dosya genel hatası ({path}): {e}")
            
    return invoices

def check_account_compliance(inv_type, acc_list, tax_match):
    notes = []
    accounts = set(acc_list)
    
    if inv_type in ["Giden", "e-Arsiv"]:
        if not any(a.startswith(p) for a in accounts for p in ["600","601","602"]): 
            notes.append("600/601/602 Yok")
        if not any(a.startswith("391") for a in accounts):
            if tax_match:
                notes.append("391 Yok")
        if not any(a.startswith(p) for a in accounts for p in ["120","100","102"]):
            notes.append("120/100/102 Yok")
            
    elif inv_type == "Gelen":
        if not any(a.startswith("191") for a in accounts):
             if tax_match:
                notes.append("191 Yok")
        if not any(a.startswith(p) for a in accounts for p in ["320","100","102"]):
            notes.append("320/100/102 Yok")
            
    elif inv_type == "Kendi Kendine":
        # Hem alış hem satış hesapları olmalı
        # Ancak bu fonksiyonu run_analysis içinde manuel handle ediyoruz, burası sadece fallback.
        pass
    return "; ".join(notes)

def run_analysis(ledger_paths_input, zip_paths=INVOICE_ZIPS, output_dir=WORK_DIR, log_callback=print):
    log_callback("=== Gelişmiş Kur Kontrollü Analiz Başlatılıyor ===")
    
    # Handle multiple ledger paths (list or string)
    ledger_paths = []
    if isinstance(ledger_paths_input, str):
        ledger_paths = [p.strip() for p in ledger_paths_input.split(";") if p.strip()]
    else:
        ledger_paths = ledger_paths_input

    # 1. Defterleri Oku ve Birleştir
    merged_ledger_map = {}
    master_vkn = None
    
    for l_path in ledger_paths:
        log_callback(f"Defter Okunuyor: {os.path.basename(l_path)}")
        
        # Dosya uzantısına göre parser seç
        ext = os.path.splitext(l_path)[1].lower()
        if ext in ('.htm', '.html'):
            # HTML Kebir dosyası
            log_callback(f"  -> HTML Kebir formatı algılandı")
            l_map, l_vkn = html_kebir_parser.parse_html_kebir(l_path)
        else:
            # XML (e-Defter) formatı
            l_map, l_vkn = parse_ledger_advanced(l_path)
        
        if not master_vkn and l_vkn:
            master_vkn = l_vkn
        elif master_vkn and l_vkn and master_vkn != l_vkn:
             log_callback(f"UYARI: Defterler arası VKN uyuşmazlığı! ({master_vkn} vs {l_vkn})")

        # Merge logic
        for doc_no, entry in l_map.items():
            if doc_no in merged_ledger_map:
                # Duplicate doc number across files? Rare but possible.
                # If identical, skip. If different, maybe suffix?
                # For now, simplistic overwrite or skip. Let's keep first one but warn?
                pass
            else:
                merged_ledger_map[doc_no] = entry

    log_callback(f"Toplam Birleştirilen Defter Kaydı: {len(merged_ledger_map)} - VKN: {master_vkn}")
    
    # 2. İkincil Eşleşme için generic map
    ledger_generic_map = {} 
    for doc_no, data in merged_ledger_map.items():
        key = f"{data['Date']}|{int(data['TotalDebit'])}" 
        if key not in ledger_generic_map: ledger_generic_map[key] = []
        ledger_generic_map[key].append(doc_no)

    # Faturaları tek bir havuzda topla
    inv_list = process_inputs(zip_paths, log_callback)
    log_callback(f"Toplam Fatura Sayısı: {len(inv_list)}")
    
    results = []
    unmatched = set(merged_ledger_map.keys())
    
    import json
    
    # Use merged map for everything below
    ledger_map = merged_ledger_map
    my_vkn = master_vkn
    
    print(f"DEBUG: Loaded {len(inv_list)} invoices.")
    # Debug specific invoice
    if any(i["No"] == "SFM2025000000817" for i in inv_list):
         print("DEBUG: SFM2025000000817 is in inv_list")
    else:
         print("DEBUG: SFM2025000000817 is NOT in inv_list")
         
    for inv in inv_list:
        # TİP BELİRLEME (OTOMATİK)
        inv_type = "Bilinmiyor"
        supp_vkn = inv.get("SupplierVKN")
        cust_vkn = inv.get("CustomerVKN")
        
        is_self_invoice = False
        
        if my_vkn:
            if supp_vkn == my_vkn and cust_vkn == my_vkn:
                inv_type = "Kendi Kendine"
                is_self_invoice = True
            elif supp_vkn == my_vkn:
                inv_type = "Giden"
            elif cust_vkn == my_vkn:
                inv_type = "Gelen"
            else:
                inv_type = inv.get("Type", "Genel") # Fallback
        else:
            inv_type = inv.get("Type", "Genel") # VKN bulunamazsa eski metot

        # 1. Döviz TL Çevrimi
        curr = inv["Currency"]
        orig_amt = inv["GrossAmount"]
        try_amt = orig_amt
        rate_used = 1.0
        rate_src = inv["RateSource"] or "Manuel"
        
        if curr != "TRY":
            if inv["XmlRate"]:
                rate_used = inv["XmlRate"]
                rate_src = "XML"
            else:
                date_obj = datetime.strptime(inv["Date"], "%Y-%m-%d")
                tcmb_rate, tcmb_date = get_tcmb_rate(date_obj, curr)
                if tcmb_rate:
                    rate_used = tcmb_rate
                    rate_src = f"TCMB (VUK - {tcmb_date})"
                else:
                    rate_src = "BULUNAMADI"
            try_amt = orig_amt * rate_used

        # 2. Eşleştirme
        ledger_entry = None
        match_method = ""
        inv_no = inv["No"]
        
        if inv_no in ledger_map:
            match_method = "Fatura No"
            ledger_entry = ledger_map[inv_no]
            if inv_no in unmatched: unmatched.remove(inv_no)
        else:
            key = f"{inv['Date']}|{int(try_amt)}"
            if key in ledger_generic_map:
                cand = ledger_generic_map[key][0]
                match_method = f"Alternatif ({cand})"
                ledger_entry = ledger_map[cand]
                if cand in unmatched: unmatched.remove(cand)
        
        # 3. Kıyaslama
        status = ""
        diff = 0.0
        acc_notes = ""
        led_amt = 0.0
        json_lines = ""
        
        # KDV Hesaplama (Ledger eşleşmesinden ÖNCE yapılmalı)
        inv_tax = inv["Tax"]
        try_tax = inv_tax
        
        if curr != "TRY":
            try_tax = inv_tax * rate_used
        
        if ledger_entry:
            led_amt = ledger_entry["TotalDebit"]
            try:
                json_lines = json.dumps(ledger_entry.get("Lines", []), ensure_ascii=False)
            except:
                json_lines = "[]"
                
            diff = try_amt - led_amt
            if abs(diff) > 2.0:
                status = "Tutar Farkı"
            else:
                status = "Eşleşti"
                
            has_tax = inv["Tax"] > 0
            
            # Compliance Check (Smart)
            if is_self_invoice:
                # Hem 191/150 hem de 391/600 hesaplarını kontrol etmeli
                # Basitçe: Hesap listesinde herhangi biri var mı?
                l_accs = list(ledger_entry["Accounts"])
                has_sales = any(a.startswith(p) for a in l_accs for p in ["600","601","391"])
                has_purch = any(a.startswith(p) for a in l_accs for p in ["150","151","152","153","770","191"])
                
                notes = []
                if not has_sales: notes.append("Satış Kaydı Eksik (391/600)")
                if not has_purch: notes.append("Alış Kaydı Eksik (191/150)")
                acc_notes = "; ".join(notes)
            else:
                acc_notes = check_account_compliance(inv_type, list(ledger_entry["Accounts"]), has_tax)
            
            # KDV Tutar Kontrolü
            led_tax = ledger_entry.get("TaxTotal", 0.0)
            # try_tax zaten yukarıda hesaplandı
                
            tax_diff = try_tax - led_tax
            
            if abs(tax_diff) > 2.0: 
                acc_notes = f"[KDV TUTAR FARKI: {tax_diff:.2f}] " + acc_notes
                if "Eşleşti" in status:
                    status = "KDV Hatası"
                elif "Tutar Farkı" in status:
                    status += " + KDV Hatası"
            
        else:
            status = "KAYITSIZ (Defterde Yok)"
            # try_tax = 0.0  <-- BU HATALIYDI! Fatura KDV'si sabittir.
            led_tax = 0.0
            tax_diff = try_tax # Defterde olmadığı için fark kdv'nin tamamıdır

        results.append({
            "Fatura_No": inv_no,
            "Tarih": inv["Date"],
            "Tip": inv_type, # AUTO DETECTED TYPE
            "Para_Birimi": curr,
            "Tutar_Orj": orig_amt,
            "Kur": rate_used,
            "Kur_Kaynagi": rate_src,
            "Tutar_TL_Hesaplanan": try_amt,
            "Tutar_Defter": led_amt,
            "Fark": diff,
            "Fatura_KDV": try_tax,
            "Fatura_KDV_Orj": inv_tax,  # Orijinal para birimindeki KDV
            "Defter_KDV": led_tax,
            "KDV_Fark": tax_diff,
            "Durum": status,
            "Hesap_Notlari": acc_notes,
            "Dosya": inv["File"],
            "Yevmiye_Detay": json_lines,
            "Sender": json.dumps(inv.get("Sender", {}), ensure_ascii=False),
            "Receiver": json.dumps(inv.get("Receiver", {}), ensure_ascii=False),
            "ETTN": inv.get("ETTN", ""),
            "Scenario": inv.get("Scenario", ""),
            "InvType": inv.get("Type", ""),
            "TaxExcl": inv.get("TaxExclAmount", 0),
            "Discount": inv.get("Discount", 0),
            "Items": json.dumps(inv.get("Items", []), ensure_ascii=False),
            "ExchangeRate": inv.get("ExchangeRate", 0.0),
            "Notes": json.dumps(inv.get("Notes", []), ensure_ascii=False),
            "Despatches": json.dumps(inv.get("Despatches", []), ensure_ascii=False),
            "Orders": json.dumps(inv.get("Orders", []), ensure_ascii=False),
            "PaymentMeans": json.dumps(inv.get("PaymentMeans", []), ensure_ascii=False)
        })
        
    # Belgesizler
    unmatched_list = []
    
    other_documents = 0 # Fiş, Dekont vb.
    
    for doc_no in unmatched:
        # Defter verisi
        l_entry = ledger_map[doc_no]
        l_accs = l_entry["Accounts"]
        
        # Filtreleme: Belgesiz Fatura mı yoksa Diğer mi?
        
        # 1. Kural: Sadece 6xx, 7xx, 15x, 25x hesapları içerenler potansiyel fatura eksiğidir.
        critical_prefixes = ("6", "7", "15", "25", "320", "120", "191", "391") # Cari ve KDV'yi de ekleyelim
        has_critical = any(a.startswith(critical_prefixes) for a in l_accs)
        
        is_invoice_candidate = True
        
        if not has_critical:
             is_invoice_candidate = False # Kritik hesap yoksa adaylıktan düşür
        else:
             # Kritik hesap var (6/7/15/25), ancak istisnalar var mı?
             # YMM Filtresi: Fatura gerektirmeyen finansal/değerleme işlemleri elenir (KDV yoksa).
             # Kasa(100), Çek(101/103), Banka(102/300), Diğer Hazır(108), Senet(121/321)
             # Avans(159), Personel(335), Vergi(360/361), Kambiyo(645/646/656), Finansman(780)
             
             excluded_prefixes = (
                 "100", "101", "102", "103", "108", 
                 "121", 
                 "159", 
                 "300", "321", "335", "360", "361", 
                 "645", "646", "656", 
                 "780"
             )
             
             has_excluded = any(a.startswith(excluded_prefixes) for a in l_accs)
             has_vat = any(a.startswith("191") or a.startswith("391") for a in l_accs)
             
             if has_excluded and not has_vat:
                 is_invoice_candidate = False
             else:
                 is_invoice_candidate = True
        
        status = ""
        if is_invoice_candidate:
            if l_entry["TotalDebit"] < 2.0: # 2 TL altı ihmal
                 other_documents += 1
                 continue
            else:
                 status = "BELGESİZ (Fatura Yok)"
                 
                 # Lines serialize
                 try:
                    json_lines = json.dumps(l_entry.get("Lines", []), ensure_ascii=False)
                 except:
                    json_lines = "[]"
                 
                 unmatched_list.append({
                    "Fatura_No": doc_no,
                    "Tarih": l_entry["Date"],
                    "Tip": f"Defter ({l_entry['Type']})",
                    "Para_Birimi": "TRY",
                    "Tutar_Orj": 0,
                    "Kur": 1,
                    "Kur_Kaynagi": "",
                    "Tutar_TL_Hesaplanan": 0,
                    "Tutar_Defter": l_entry["TotalDebit"],
                    "Fark": -l_entry["TotalDebit"],
                    "Fatura_KDV": 0.0,
                    "Defter_KDV": 0.0,
                    "KDV_Fark": 0.0,
                    "Durum": status,
                    "Hesap_Notlari": f"Hesaplar: {','.join(list(l_accs))}",
                    "Dosya": "ZGM Defter",
                    "Yevmiye_Detay": json_lines,
                    "Sender": "{}",
                    "Receiver": "{}",
                    "ETTN": "",
                    "Scenario": "",
                    "InvType": "",
                    "TaxExcl": 0,
                    "Discount": 0,
                    "Items": "[]",
                    "ExchangeRate": 0.0,
                    "Notes": "[]",
                    "Despatches": "[]",
                    "Orders": "[]",
                    "PaymentMeans": "[]"
                })
        else:
            other_documents += 1

    # Raporlama
    full_results = results + unmatched_list
    
    # CSV Kaydet
    csv_path = os.path.join(output_dir, "Detayli_Karsilastirma_Raporu.csv")
    keys = full_results[0].keys() if full_results else []
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(full_results)
        
    # Özet İstatistikleri
    summary = {}
    for r in full_results:
        s = r["Durum"]
        summary[s] = summary.get(s, 0) + 1
        
    print(f"Rapor Hazır: {csv_path}")
    print(f"Özet: {summary}")
    
    log_callback(f"Rapor Hazırlandı: {csv_path}")
    log_callback(f"Özet İstatistikler: {summary}")
    
    return summary, csv_path

# Standalone execution
if __name__ == "__main__":
    run_analysis(LEDGER_XML)
