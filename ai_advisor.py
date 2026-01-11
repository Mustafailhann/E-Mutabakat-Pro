# -*- coding: utf-8 -*-
"""
AI Denetim Danışmanı - Google Gemini API Entegrasyonu

Akıllı önbellekleme ile minimum API çağrısı yapar.
KKEG, vergi ve denetim sorularına yanıt verir.
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path


# API yapılandırması
DEFAULT_API_KEY = ""  # Kullanıcı girecek
CACHE_DIR = Path.home() / ".ymm_audit_cache"
CACHE_DURATION_DAYS = 30


class AIAdvisor:
    """
    AI Denetim Danışmanı
    
    Özellikler:
    - Google Gemini API kullanır
    - Yanıtları önbelleğe alır (tekrar sormaz)
    - Rate limiting ile hata önler
    - Denetim odaklı sorular için optimize edilmiş
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", DEFAULT_API_KEY)
        self.model = None
        self.cache = {}
        self.query_count = 0
        self.max_queries_per_session = 20  # Oturum başına maksimum sorgu
        
        # Önbellek dizinini oluştur
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._load_cache()
    
    def _load_cache(self):
        """Önbelleği dosyadan yükle"""
        cache_file = CACHE_DIR / "ai_cache.json"
        try:
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                    # Eski kayıtları temizle
                    self._cleanup_old_cache()
        except Exception:
            self.cache = {}
    
    def _save_cache(self):
        """Önbelleği dosyaya kaydet"""
        cache_file = CACHE_DIR / "ai_cache.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def _cleanup_old_cache(self):
        """Eski önbellek kayıtlarını temizle"""
        cutoff = (datetime.now() - timedelta(days=CACHE_DURATION_DAYS)).isoformat()
        self.cache = {k: v for k, v in self.cache.items() 
                      if v.get("timestamp", "") > cutoff}
    
    def _get_cache_key(self, question: str, context: str = "") -> str:
        """Soru için benzersiz önbellek anahtarı oluştur"""
        content = f"{question}|{context}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _init_model(self) -> bool:
        """Gemini modelini başlat"""
        if self.model is not None:
            return True
        
        if not self.api_key:
            return False
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            
            # Model listesi - ilk çalışanı kullan
            model_names = ['gemini-2.0-flash-exp', 'gemini-pro', 'models/gemini-pro']
            
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    # Test çağrısı
                    return True
                except Exception:
                    continue
            
            return False
        except Exception as e:
            print(f"Gemini API hatası: {e}")
            return False
    
    def ask(self, question: str, context: str = "", force_fresh: bool = False) -> Dict:
        """
        AI'ya soru sor
        
        Args:
            question: Sorulacak soru
            context: Ek bağlam bilgisi (hesap kodu, tutar vb.)
            force_fresh: True ise önbelleği atla
        
        Returns:
            {"success": bool, "answer": str, "from_cache": bool, "error": str}
        """
        
        # Sorgu limiti kontrolü
        if self.query_count >= self.max_queries_per_session:
            return {
                "success": False,
                "answer": "",
                "from_cache": False,
                "error": f"Oturum sorgu limiti ({self.max_queries_per_session}) aşıldı. Uygulamayı yeniden başlatın."
            }
        
        # Önbellek kontrolü
        cache_key = self._get_cache_key(question, context)
        
        if not force_fresh and cache_key in self.cache:
            cached = self.cache[cache_key]
            return {
                "success": True,
                "answer": cached["answer"],
                "from_cache": True,
                "error": ""
            }
        
        # API çağrısı
        if not self._init_model():
            return {
                "success": False,
                "answer": "",
                "from_cache": False,
                "error": "API anahtarı ayarlanmamış veya geçersiz."
            }
        
        try:
            # Denetim odaklı sistem promptu
            system_prompt = """Sen bir Yeminli Mali Müşavir (YMM) denetim asistanısın.
Türk vergi mevzuatı konusunda uzmansın. Cevaplarını:
- Kısa ve öz tut (maksimum 3-4 cümle)
- İlgili kanun maddesini belirt (GVK, KVK, VUK)
- Net bir sonuç ver (KKEG mi değil mi, risk var mı yok mu)
- Türkçe cevap ver"""
            
            full_prompt = f"{system_prompt}\n\nSoru: {question}"
            if context:
                full_prompt += f"\n\nBağlam: {context}"
            
            response = self.model.generate_content(full_prompt)
            answer = response.text.strip()
            
            # Önbelleğe kaydet
            self.cache[cache_key] = {
                "answer": answer,
                "timestamp": datetime.now().isoformat()
            }
            self._save_cache()
            
            self.query_count += 1
            
            return {
                "success": True,
                "answer": answer,
                "from_cache": False,
                "error": ""
            }
            
        except Exception as e:
            return {
                "success": False,
                "answer": "",
                "from_cache": False,
                "error": str(e)
            }
    
    def check_kkeg(self, expense_desc: str, amount: float, account_code: str) -> Dict:
        """
        Giderin KKEG olup olmadığını kontrol et
        
        Önce yerel kuralları kontrol eder, emin olamazsa API'ye sorar.
        """
        
        # Yerel kurallar (API'ye sormadan)
        local_result = self._check_local_kkeg_rules(expense_desc, amount, account_code)
        if local_result["certain"]:
            return {
                "success": True,
                "is_kkeg": local_result["is_kkeg"],
                "reason": local_result["reason"],
                "kkeg_rate": local_result["kkeg_rate"],
                "from_ai": False
            }
        
        # Yerel kurallar yetersizse AI'ya sor
        context = f"Hesap: {account_code}, Tutar: {amount:,.2f} TL, Açıklama: {expense_desc}"
        question = f"Bu gider KKEG mi? Hangi oranda?"
        
        result = self.ask(question, context)
        
        if result["success"]:
            # AI yanıtını parse et
            answer_lower = result["answer"].lower()
            is_kkeg = "kkeg" in answer_lower or "kabul edilme" in answer_lower
            
            return {
                "success": True,
                "is_kkeg": is_kkeg,
                "reason": result["answer"],
                "kkeg_rate": self._extract_rate(result["answer"]),
                "from_ai": True
            }
        
        return {
            "success": False,
            "is_kkeg": None,
            "reason": result["error"],
            "kkeg_rate": 0,
            "from_ai": False
        }
    
    def _check_local_kkeg_rules(self, desc: str, amount: float, acc_code: str) -> Dict:
        """Yerel KKEG kuralları (API'ye sormadan)"""
        desc_lower = desc.lower()
        
        # Kesin KKEG durumları
        if any(kw in desc_lower for kw in ["ceza", "para cezası", "trafik cezası", "vergi cezası"]):
            return {"certain": True, "is_kkeg": True, "reason": "Cezalar KKEG (KVK 11/1-d)", "kkeg_rate": 1.0}
        
        if any(kw in desc_lower for kw in ["gecikme faizi", "gecikme zammı", "pişmanlık"]):
            return {"certain": True, "is_kkeg": True, "reason": "Gecikme faizi KKEG (KVK 11/1-d)", "kkeg_rate": 1.0}
        
        if any(kw in desc_lower for kw in ["öiv", "özel iletişim vergisi"]):
            return {"certain": True, "is_kkeg": True, "reason": "ÖİV KKEG (6802 sayılı Kanun)", "kkeg_rate": 1.0}
        
        # Kesin KKEG değil durumları
        if acc_code.startswith("62"):  # Satışların maliyeti
            return {"certain": True, "is_kkeg": False, "reason": "Satışların maliyeti gider yazılabilir", "kkeg_rate": 0}
        
        if acc_code.startswith("72"):  # Direkt işçilik
            return {"certain": True, "is_kkeg": False, "reason": "İşçilik giderleri gider yazılabilir", "kkeg_rate": 0}
        
        # Binek araç (kısmi KKEG)
        if any(kw in desc_lower for kw in ["binek", "rent a car", "araç kiralama"]):
            return {"certain": True, "is_kkeg": True, "reason": "Binek araç %30 KKEG (GVK 40/5)", "kkeg_rate": 0.30}
        
        # Belirsiz durumlar - AI'ya sor
        return {"certain": False, "is_kkeg": None, "reason": "", "kkeg_rate": 0}
    
    def _extract_rate(self, answer: str) -> float:
        """AI yanıtından KKEG oranını çıkar"""
        import re
        
        # %XX formatını ara
        match = re.search(r'%\s*(\d+)', answer)
        if match:
            return int(match.group(1)) / 100
        
        # "tamamen" veya "tamamı" varsa %100
        if any(kw in answer.lower() for kw in ["tamamen", "tamamı", "tümü"]):
            return 1.0
        
        return 0.0
    
    def get_query_stats(self) -> Dict:
        """Sorgu istatistikleri"""
        return {
            "session_queries": self.query_count,
            "max_queries": self.max_queries_per_session,
            "remaining": self.max_queries_per_session - self.query_count,
            "cache_size": len(self.cache)
        }
    
    def check_product_match(
        self, 
        satis_urun: str, 
        alis_urun: str,
        satis_miktar: float = None,
        alis_miktar: float = None,
        satis_birim: str = None,
        alis_birim: str = None
    ) -> Dict:
        """
        İki ürün adının aynı ürünü temsil edip etmediğini AI ile kontrol et
        
        Returns:
            {"success": bool, "is_match": bool, "confidence": float, "reason": str, "from_ai": bool}
        """
        
        # Önce yerel kontrol
        local_result = self._check_local_product_match(satis_urun, alis_urun)
        if local_result["certain"]:
            return {
                "success": True,
                "is_match": local_result["is_match"],
                "confidence": local_result["confidence"],
                "reason": local_result["reason"],
                "from_ai": False
            }
        
        # Yerel kontrol yetersizse AI'ya sor
        context = f"Satış Ürünü: {satis_urun}\nAlış Ürünü: {alis_urun}"
        if satis_miktar and alis_miktar:
            context += f"\nSatış: {satis_miktar} {satis_birim or ''}, Alış: {alis_miktar} {alis_birim or ''}"
        
        question = "Bu iki ürün aynı mı? AYNI veya FARKLI ve 0-100 güven oranı ver."
        
        result = self.ask(question, context)
        
        if result["success"]:
            answer = result["answer"]
            answer_lower = answer.lower()
            is_match = "aynı" in answer_lower and "farklı" not in answer_lower
            confidence = self._extract_confidence(answer)
            
            return {
                "success": True,
                "is_match": is_match,
                "confidence": confidence,
                "reason": answer,
                "from_ai": True,
                "from_cache": result.get("from_cache", False)
            }
        
        return {
            "success": False,
            "is_match": None,
            "confidence": 0,
            "reason": result.get("error", "AI yanıt veremedi"),
            "from_ai": False
        }
    
    def _check_local_product_match(self, urun1: str, urun2: str) -> Dict:
        """Yerel ürün eşleştirme kontrolü"""
        u1 = urun1.upper().strip()
        u2 = urun2.upper().strip()
        
        if u1 == u2:
            return {"certain": True, "is_match": True, "confidence": 100, "reason": "Birebir eşleşme"}
        
        if u1 in u2 or u2 in u1:
            return {"certain": True, "is_match": True, "confidence": 90, "reason": "İçerme eşleşmesi"}
        
        words1 = set(u1.split())
        words2 = set(u2.split())
        common = words1 & words2
        
        if len(common) >= 2:
            total = len(words1 | words2)
            overlap = len(common) / total * 100
            if overlap >= 50:
                return {"certain": True, "is_match": True, "confidence": overlap, "reason": f"Ortak: {', '.join(common)}"}
        
        return {"certain": False, "is_match": None, "confidence": 0, "reason": ""}
    
    def _extract_confidence(self, answer: str) -> float:
        """AI yanıtından güven oranını çıkar"""
        import re
        match = re.search(r'[%\(]?\s*(\d+)\s*[%\)]', answer)
        if match:
            return min(int(match.group(1)), 100)
        
        answer_lower = answer.lower()
        if any(kw in answer_lower for kw in ["kesinlikle", "tamamen"]):
            return 95
        if any(kw in answer_lower for kw in ["muhtemelen", "büyük ihtimalle"]):
            return 75
        return 60


# Basit soru-cevap fonksiyonu (API key kontrolü ile)
def quick_ask(question: str, api_key: str = None) -> str:
    """Hızlı soru sorma"""
    advisor = AIAdvisor(api_key)
    result = advisor.ask(question)
    return result["answer"] if result["success"] else f"Hata: {result['error']}"


if __name__ == "__main__":
    print("AI Denetim Danışmanı modülü yüklendi.")
    
    # Test (API key gerekli)
    advisor = AIAdvisor()
    stats = advisor.get_query_stats()
    print(f"Önbellek boyutu: {stats['cache_size']} kayıt")
    print(f"Oturum sorgu limiti: {stats['max_queries']}")
