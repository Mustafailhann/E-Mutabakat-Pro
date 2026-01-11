import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import ssl

# SSL sertifika hatasını atlamak için context (Gerekirse)
ssl_context = ssl._create_unverified_context()

def get_tcmb_rate(date_obj, currency_code):
    # VUK Kuru: İşlem tarihinden bir önceki günün efektif/döviz alış kuru
    target_date = date_obj - timedelta(days=1)
    
    # Retry logic for weekends/holidays (go back up to 5 days)
    for _ in range(5):
        day_str = target_date.strftime("%d%m%Y")
        year_m_str = target_date.strftime("%Y%m")
        url = f"https://www.tcmb.gov.tr/kurlar/{year_m_str}/{day_str}.xml"
        
        try:
            with urllib.request.urlopen(url, context=ssl_context, timeout=5) as response:
                if response.getcode() == 200:
                    xml_content = response.read()
                    root = ET.fromstring(xml_content)
                    for curr in root.findall("Currency"):
                        if curr.attrib.get("CurrencyCode") == currency_code:
                            # ForexBuying (Döviz Alış)
                            rate = curr.find("ForexBuying").text
                            if rate:
                                return float(rate), target_date.strftime("%d.%m.%Y")
                    return None, None
        except Exception as e:
            # print(f"URL Hata ({day_str}): {e}")
            pass
            
        target_date -= timedelta(days=1)
        
    return None, None
