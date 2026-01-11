import os
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO

def search_ettn(zips, target_ettn):
    for zp in zips:
        if not os.path.exists(zp): continue
        print(f"Searching in {zp}...")
        with zipfile.ZipFile(zp, "r") as z:
            for name in z.namelist():
                if name.endswith(".zip"):
                    with z.open(name) as f:
                        with zipfile.ZipFile(BytesIO(f.read())) as sub_z:
                            for sn in sub_z.namelist():
                                if sn.endswith(".xml"):
                                    content = sub_z.read(sn).decode('utf-8', 'ignore')
                                    if target_ettn in content:
                                        print(f"FOUND: {zp} -> {name} -> {sn}")
                                        return content
                elif name.endswith(".xml"):
                    content = z.read(name).decode('utf-8', 'ignore')
                    if target_ettn in content:
                        print(f"FOUND: {zp} -> {name}")
                        return content
    return None

def analyze_xml(content):
    root = ET.fromstring(content)
    # Find Party nodes
    parties = root.findall(".//{*}Party")
    for i, party in enumerate(parties):
        print(f"\nParty {i+1} Structure:")
        for elem in party.iter():
            tag = elem.tag.split('}')[-1]
            text = (elem.text.strip() if elem.text else "")
            if text:
                print(f"  {tag}: {text}")
        
    # Find TaxTotal nodes
    taxes = root.findall(".//{*}TaxTotal")
    for i, tax in enumerate(taxes):
        print(f"\nTaxTotal {i+1}:")
        for elem in tax.iter():
            tag = elem.tag.split('}')[-1]
            text = (elem.text.strip() if elem.text else "")
            if text:
                print(f"  {tag}: {text}")

if __name__ == "__main__":
    ZIPS = ["Gelen e-Fatura.zip", "Giden e-Fatura.zip", "e-Arsiv.zip"]
    ETTN = "2f249a0b-9fc7-48e2-b162-b6280f51edb4"
    content = search_ettn(ZIPS, ETTN)
    if content:
        analyze_xml(content)
    else:
        print("ETTN not found in any ZIP.")
