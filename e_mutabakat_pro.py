import sys
import os
# Add parent directory to path to allow importing modules from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import webbrowser
import queue
import compare_invoices
import generate_report
import kdv_iade_listesi
import kdv_web_editor
import pdf_invoice_reader
import satis_fatura_listesi
import satis_web_editor
import html_kebir_parser

# YMM Modülleri
try:
    from ymm_audit import YMMAuditEngine
    from ymm_report_generator import generate_ymm_html_report
    from ymm_auditor_report import generate_auditor_report
    from beyanname_parser import parse_kdv_beyanname_pdf, parse_muhtasar_beyanname_pdf
    from mizan_parser import parse_excel_mizan
    YMM_AVAILABLE = True
except ImportError as e:
    print(f"YMM modülleri yüklenemedi: {e}")
    YMM_AVAILABLE = False

class EMutabakatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("e-Mutabakat Pro - Fatura ve Defter Analiz Uzmanı")
        self.root.geometry("800x650")
        self.root.resizable(True, True)
        
        # Style
        style = ttk.Style()
        style.configure("TButton", padding=8, font=("Segoe UI", 10))
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TLabelframe.Label", font=("Segoe UI", 11, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground="#2E74B5")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 12, "bold"), foreground="#555")
        
        # Modern buton stilleri
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"))
        style.map("Accent.TButton", background=[("active", "#2E74B5")])
        
        self.paths = {}
        self.ymm_paths = {}  # YMM sekmesi için ayrı paths
        self.ymm_info = {}   # YMM/Denetçi bilgileri
        self.log_queue = queue.Queue()
        self.check_log_queue()
        
        self.create_widgets()
        
    def create_widgets(self):
        # Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", pady=10, padx=15)
        
        header = ttk.Label(header_frame, text="e-Mutabakat Pro", style="Header.TLabel")
        header.pack(side="left")
        
        subtitle = ttk.Label(header_frame, text="Fatura • Defter • YMM Denetim", style="SubHeader.TLabel")
        subtitle.pack(side="left", padx=20)
        
        # Notebook (Sekmeler)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=5)
        
        # YMM Denetim sekmesi gizlendi
        # self.tab_ymm = ttk.Frame(self.notebook)
        # self.notebook.add(self.tab_ymm, text="  🔍 YMM Denetim  ")
        # self.create_ymm_tab()
        
        # Sekme: KDV İade Modülü
        self.tab_kdv = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_kdv, text="  💰 KDV İade Modülü  ")
        self.create_kdv_iade_tab()
        
        # Footer
        footer = tk.Label(self.root, text="Designed by AI Agent • v3.0", font=("Segoe UI", 8), fg="#999")
        footer.pack(side="bottom", pady=5)

    def create_kdv_iade_tab(self):
        """KDV İade Modülü sekmesi - KDV ve Satış listeleri"""
        tab = self.tab_kdv
        
        # Fatura Dosyaları Bölümü
        frame_inv = ttk.LabelFrame(tab, text="📁 Fatura Dosyaları (Zip/Rar/Xml/PDF)", padding=(10, 10))
        frame_inv.pack(fill="x", padx=10, pady=5)
        
        btn_frame = ttk.Frame(frame_inv)
        btn_frame.pack(fill="x", pady=2)
        
        ttk.Button(btn_frame, text="➕ Dosya Ekle", command=self.add_invoice_file).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🗑️ Listeyi Temizle", command=self.clear_invoice_list).pack(side="left", padx=5)
        
        self.inv_listbox = tk.Listbox(frame_inv, height=5, selectmode="extended", font=("Consolas", 9))
        self.inv_listbox.pack(fill="x", pady=5)
        
        # KDV İade Butonları
        frame_actions = ttk.LabelFrame(tab, text="📤 KDV İade İşlemleri", padding=(10, 10))
        frame_actions.pack(fill="x", padx=10, pady=5)
        
        btn_row1 = ttk.Frame(frame_actions)
        btn_row1.pack(fill="x", pady=5)
        
        ttk.Button(btn_row1, text="📊 KDV İade Listesi (Excel)", command=self.generate_kdv_listesi, width=25).pack(side="left", padx=5)
        ttk.Button(btn_row1, text="🌐 KDV Liste (Web Düzenleyici)", command=self.open_kdv_web_editor, width=25).pack(side="left", padx=5)
        
        btn_row2 = ttk.Frame(frame_actions)
        btn_row2.pack(fill="x", pady=5)
        
        ttk.Button(btn_row2, text="💰 Satış Fatura Listesi (Web)", command=self.open_satis_web_editor, width=25).pack(side="left", padx=5)
        
        # Açıklama
        info_frame = ttk.LabelFrame(tab, text="ℹ️ Bilgi", padding=(10, 10))
        info_frame.pack(fill="x", padx=10, pady=5)
        
        info_text = """
• KDV İade Listesi: GİB formatında İndirilecek KDV listesi Excel dosyası oluşturur
• KDV Liste (Web): Faturaları web tarayıcıda düzenlemenize olanak tanır
• Satış Fatura Listesi: Satış faturalarınızı listeler (VKN ile filtreleme)
        """
        ttk.Label(info_frame, text=info_text.strip(), font=("Segoe UI", 9), justify="left").pack(anchor="w")
        
        # Status Log
        self.log_text = tk.Text(tab, height=6, width=80, font=("Consolas", 9), state="disabled", bg="#1e1e1e", fg="#dcdcdc")
        self.log_text.pack(padx=10, pady=5, fill="x")

    def create_ymm_tab(self):
        """YMM Denetim sekmesi"""
        tab = self.tab_ymm
        
        if not YMM_AVAILABLE:
            ttk.Label(tab, text="⚠️ YMM modülleri yüklenemedi!", font=("Segoe UI", 14, "bold")).pack(pady=50)
            return
        
        # Sol panel - Dosya yükleme (Scrollable)
        paned = ttk.PanedWindow(tab, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Sol panel için scroll container
        left_container = ttk.Frame(paned)
        paned.add(left_container, weight=1)
        
        # Canvas ve Scrollbar
        canvas = tk.Canvas(left_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        
        # Scrollable frame
        left_panel = ttk.Frame(canvas)
        
        # Canvas içine frame ekle
        canvas_frame = canvas.create_window((0, 0), window=left_panel, anchor="nw")
        
        # Scroll konfigürasyonu
        def configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_frame, width=event.width)
        
        left_panel.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", configure_scroll)
        
        # Mouse wheel scroll
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Pack scrollbar ve canvas
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Beyanname Bölümü
        frame_beyan = ttk.LabelFrame(left_panel, text="📋 Beyannameler (PDF)", padding=(10, 8))
        frame_beyan.pack(fill="x", pady=5)
        
        self.add_ymm_file_selector(frame_beyan, "KDV 1 Beyanname", "kdv_beyanname", 
                                   file_types=[("PDF", "*.pdf")])
        self.add_ymm_file_selector(frame_beyan, "KDV 2 Beyanname", "kdv2_beyanname", 
                                   file_types=[("PDF", "*.pdf")])
        self.add_ymm_file_selector(frame_beyan, "Muhtasar Beyanname", "muhtasar_beyanname", 
                                   file_types=[("PDF", "*.pdf")])
        
        # Mizan Bölümü
        frame_mizan = ttk.LabelFrame(left_panel, text="📊 Mizan Dosyaları", padding=(10, 8))
        frame_mizan.pack(fill="x", pady=5)
        
        self.add_ymm_file_selector(frame_mizan, "Aylık Mizan (XLSX)", "aylik_mizan", 
                                   file_types=[("Excel", "*.xlsx *.xls")])
        self.add_ymm_file_selector(frame_mizan, "Kümülatif Mizan (XLSX)", "kumulatif_mizan", 
                                   file_types=[("Excel", "*.xlsx *.xls")])
        
        # Kebir Bölümü
        frame_kebir = ttk.LabelFrame(left_panel, text="📚 Kebir Defteri", padding=(10, 8))
        frame_kebir.pack(fill="x", pady=5)
        
        self.add_ymm_file_selector(frame_kebir, "Kebir (HTM/XML)", "kebir", 
                                   file_types=[("Kebir Dosyaları", "*.htm *.html *.xml"), ("HTML", "*.htm *.html"), ("XML", "*.xml")])
        
        # Fatura Dosyaları Bölümü (Çoklu dosya desteği)
        frame_fatura = ttk.LabelFrame(left_panel, text="📁 Fatura Dosyaları (ZIP/XML)", padding=(10, 8))
        frame_fatura.pack(fill="x", pady=5)
        
        # Alış Faturaları
        ttk.Label(frame_fatura, text="Alış Faturaları:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        alis_btn_frame = ttk.Frame(frame_fatura)
        alis_btn_frame.pack(fill="x", pady=2)
        ttk.Button(alis_btn_frame, text="➕ Dosya Ekle", command=lambda: self.add_ymm_fatura("alis")).pack(side="left", padx=2)
        ttk.Button(alis_btn_frame, text="🗑️ Temizle", command=lambda: self.clear_ymm_fatura("alis")).pack(side="left", padx=2)
        
        self.alis_fatura_listbox = tk.Listbox(frame_fatura, height=3, font=("Consolas", 8), selectmode="extended")
        self.alis_fatura_listbox.pack(fill="x", pady=2)
        
        # Satış Faturaları
        ttk.Label(frame_fatura, text="Satış Faturaları:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(5, 0))
        satis_btn_frame = ttk.Frame(frame_fatura)
        satis_btn_frame.pack(fill="x", pady=2)
        ttk.Button(satis_btn_frame, text="➕ Dosya Ekle", command=lambda: self.add_ymm_fatura("satis")).pack(side="left", padx=2)
        ttk.Button(satis_btn_frame, text="🗑️ Temizle", command=lambda: self.clear_ymm_fatura("satis")).pack(side="left", padx=2)
        
        self.satis_fatura_listbox = tk.Listbox(frame_fatura, height=3, font=("Consolas", 8), selectmode="extended")
        self.satis_fatura_listbox.pack(fill="x", pady=2)
        
        # Denetçi Bilgileri Bölümü
        frame_denetci = ttk.LabelFrame(left_panel, text="👤 Denetçi Bilgileri", padding=(10, 8))
        frame_denetci.pack(fill="x", pady=5)
        
        # YMM Bilgileri
        ymm_row = ttk.Frame(frame_denetci)
        ymm_row.pack(fill="x", pady=2)
        ttk.Label(ymm_row, text="YMM Adı:", width=12).pack(side="left")
        self.ymm_info["ymm_name"] = tk.StringVar(value="YUSUF GÜLER")
        ttk.Entry(ymm_row, textvariable=self.ymm_info["ymm_name"], width=20).pack(side="left", padx=3)
        ttk.Label(ymm_row, text="Unvan:", width=8).pack(side="left")
        self.ymm_info["ymm_title"] = tk.StringVar(value="Yeminli Mali Müşavir")
        ttk.Entry(ymm_row, textvariable=self.ymm_info["ymm_title"], width=18).pack(side="left", padx=3)
        
        # Denetçi Bilgileri
        auditor_row = ttk.Frame(frame_denetci)
        auditor_row.pack(fill="x", pady=2)
        ttk.Label(auditor_row, text="Denetçi Adı:", width=12).pack(side="left")
        self.ymm_info["auditor_name"] = tk.StringVar(value="Mehmet BİLGİN")
        ttk.Entry(auditor_row, textvariable=self.ymm_info["auditor_name"], width=20).pack(side="left", padx=3)
        ttk.Label(auditor_row, text="Unvan:", width=8).pack(side="left")
        self.ymm_info["auditor_title"] = tk.StringVar(value="Uzman Denetçi")
        ttk.Entry(auditor_row, textvariable=self.ymm_info["auditor_title"], width=18).pack(side="left", padx=3)
        
        # Denetim Butonları
        btn_frame = ttk.Frame(left_panel)
        btn_frame.pack(fill="x", pady=10)
        
        self.btn_ymm_run = ttk.Button(btn_frame, text="🔍 DENETİMİ BAŞLAT", 
                                      command=self.run_ymm_audit, style="Accent.TButton")
        self.btn_ymm_run.pack(side="left", padx=5)
        
        self.btn_ymm_report = ttk.Button(btn_frame, text="📄 Yönetici Raporu", 
                                         command=self.open_ymm_report, state="disabled")
        self.btn_ymm_report.pack(side="left", padx=5)
        
        self.btn_ymm_auditor_report = ttk.Button(btn_frame, text="📝 Denetçi Raporu", 
                                                  command=self.open_ymm_auditor_report, state="disabled")
        self.btn_ymm_auditor_report.pack(side="left", padx=5)
        
        self.btn_ymm_clear_all = ttk.Button(btn_frame, text="🗑️ Tümünü Temizle", 
                                            command=self.clear_all_ymm)
        self.btn_ymm_clear_all.pack(side="left", padx=5)
        
        # İkinci buton satırı - Fatura Listeleri ve Mutabakat
        btn_frame2 = ttk.Frame(left_panel)
        btn_frame2.pack(fill="x", pady=5)
        
        self.btn_ymm_mutabakat = ttk.Button(btn_frame2, text="📋 Mutabakat Raporu", 
                                            command=self.run_ymm_mutabakat, state="disabled")
        self.btn_ymm_mutabakat.pack(side="left", padx=5)
        
        ttk.Button(btn_frame2, text="🌐 KDV Liste (Web)", 
                   command=self.open_ymm_kdv_web).pack(side="left", padx=5)
        ttk.Button(btn_frame2, text="💰 Satış Liste (Web)", 
                   command=self.open_ymm_satis_web).pack(side="left", padx=5)
        
        # Üçüncü buton satırı - AI Danışman
        btn_frame3 = ttk.Frame(left_panel)
        btn_frame3.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame3, text="🤖 AI Danışman", 
                   command=self.open_ai_advisor).pack(side="left", padx=5)
        ttk.Button(btn_frame3, text="⚙️ API Ayarları", 
                   command=self.open_api_settings).pack(side="left", padx=5)
        
        # Sağ panel - Sonuçlar
        right_panel = ttk.Frame(paned)
        paned.add(right_panel, weight=1)
        
        # Sonuç özeti
        result_frame = ttk.LabelFrame(right_panel, text="📈 Denetim Sonuçları", padding=(10, 8))
        result_frame.pack(fill="both", expand=True, pady=5)
        
        # Bulgu kartları
        self.ymm_result_text = tk.Text(result_frame, height=20, width=40, font=("Consolas", 9), 
                                       state="disabled", bg="#f8f8f8", wrap="word")
        self.ymm_result_text.pack(fill="both", expand=True)

    def add_ymm_file_selector(self, parent, label, key, file_types):
        """YMM sekmesi için dosya seçici"""
        if key not in self.ymm_paths:
            self.ymm_paths[key] = tk.StringVar()
            
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        
        ttk.Label(row, text=label, width=22).pack(side="left")
        entry = ttk.Entry(row, textvariable=self.ymm_paths[key], width=30)
        entry.pack(side="left", padx=5)
        
        btn = ttk.Button(row, text="📂", width=3, 
                        command=lambda: self.browse_ymm_file(key, file_types))
        btn.pack(side="left")
        
        # Temizle butonu
        clear_btn = ttk.Button(row, text="✕", width=2,
                               command=lambda k=key: self.ymm_paths[k].set(""))
        clear_btn.pack(side="left", padx=2)

    def browse_ymm_file(self, key, file_types):
        """YMM dosya seçme"""
        filename = filedialog.askopenfilename(filetypes=file_types)
        if filename:
            self.ymm_paths[key].set(filename)
    
    def add_ymm_fatura(self, fatura_type):
        """Çoklu fatura dosyası ekleme (ZIP/XML)"""
        filenames = filedialog.askopenfilenames(
            title=f"{'Alış' if fatura_type == 'alis' else 'Satış'} Fatura Dosyalarını Seç",
            filetypes=[("Fatura Dosyaları", "*.zip *.xml *.ZIP *.XML"), ("ZIP", "*.zip"), ("XML", "*.xml"), ("Tüm", "*.*")]
        )
        if filenames:
            listbox = self.alis_fatura_listbox if fatura_type == "alis" else self.satis_fatura_listbox
            for f in filenames:
                listbox.insert(tk.END, f)
    
    def clear_ymm_fatura(self, fatura_type):
        """Fatura listesini temizle"""
        listbox = self.alis_fatura_listbox if fatura_type == "alis" else self.satis_fatura_listbox
        listbox.delete(0, tk.END)
    
    def clear_all_ymm(self):
        """Tüm YMM sekmesindeki dosyaları ve sonuçları temizle"""
        # Beyanname path'lerini temizle
        for key in ["kdv_beyanname", "muhtasar_beyanname", "aylik_mizan", "kumulatif_mizan", "kebir"]:
            if key in self.ymm_paths:
                self.ymm_paths[key].set("")
        
        # Fatura listelerini temizle
        self.alis_fatura_listbox.delete(0, tk.END)
        self.satis_fatura_listbox.delete(0, tk.END)
        
        # Sonuç alanını temizle
        self.ymm_result_text.config(state="normal")
        self.ymm_result_text.delete("1.0", "end")
        self.ymm_result_text.insert("end", "📋 YMM Denetim modülüne hoş geldiniz.\n\nDosyalarınızı yükleyip 'DENETİMİ BAŞLAT' butonuna tıklayın.")
        self.ymm_result_text.config(state="disabled")
        
        # Rapor butonlarını devre dışı bırak
        self.btn_ymm_report.config(state="disabled")
        self.btn_ymm_auditor_report.config(state="disabled")

    def run_ymm_audit(self):
        """YMM Denetimi çalıştır"""
        self.btn_ymm_run.config(state="disabled")
        
        # Sonuç alanını temizle
        self.ymm_result_text.config(state="normal")
        self.ymm_result_text.delete("1.0", "end")
        self.ymm_result_text.insert("end", "🔄 Denetim başlatılıyor...\n\n")
        self.ymm_result_text.config(state="disabled")
        
        # Thread'de çalıştır
        t = threading.Thread(target=self._run_ymm_audit_thread)
        t.start()

    def _run_ymm_audit_thread(self):
        """YMM denetim thread'i"""
        try:
            results = []
            engine = YMMAuditEngine()
            
            # Kebir yükle (HTM veya XML)
            kebir_path = self.ymm_paths.get("kebir", tk.StringVar()).get()
            if kebir_path and os.path.exists(kebir_path):
                if kebir_path.lower().endswith('.xml'):
                    # XML Kebir parser
                    try:
                        from xml_kebir_parser import parse_xml_kebir
                        ledger_map, company = parse_xml_kebir(kebir_path)
                        mizan = engine.load_mizan_from_kebir(ledger_map)
                        results.append(f"✅ Kebir (XML) yüklendi: {len(mizan.accounts)} hesap")
                    except ImportError:
                        results.append("⚠️ XML Kebir parser modülü bulunamadı")
                        ledger_map, company = {}, "Firma Adı"
                else:
                    # HTM Kebir parser
                    ledger_map, company = html_kebir_parser.parse_html_kebir(kebir_path)
                    mizan = engine.load_mizan_from_kebir(ledger_map)
                    results.append(f"✅ Kebir (HTM) yüklendi: {len(mizan.accounts)} hesap")
            else:
                company = "Firma Adı"
                results.append("⚠️ Kebir yüklenmedi")
            
            # Fatura dosyalarını yükle (Listbox'tan)
            alis_files = list(self.alis_fatura_listbox.get(0, tk.END))
            alis_count = 0
            for fpath in alis_files:
                if os.path.exists(fpath):
                    try:
                        if fpath.lower().endswith('.zip'):
                            count = engine.load_invoices_from_zip(fpath, "purchase")
                            alis_count += count
                        elif fpath.lower().endswith('.xml'):
                            count = engine.load_invoices_from_xml(fpath, "purchase")
                            alis_count += count
                    except Exception as e:
                        results.append(f"⚠️ Alış yükleme hatası: {os.path.basename(fpath)} - {e}")
            if alis_count > 0:
                results.append(f"✅ Alış faturaları: {alis_count} ({len(alis_files)} dosya)")
            
            satis_files = list(self.satis_fatura_listbox.get(0, tk.END))
            satis_count = 0
            for fpath in satis_files:
                if os.path.exists(fpath):
                    try:
                        if fpath.lower().endswith('.zip'):
                            count = engine.load_invoices_from_zip(fpath, "sales")
                            satis_count += count
                        elif fpath.lower().endswith('.xml'):
                            count = engine.load_invoices_from_xml(fpath, "sales")
                            satis_count += count
                    except Exception as e:
                        results.append(f"⚠️ Satış yükleme hatası: {os.path.basename(fpath)} - {e}")
            if satis_count > 0:
                results.append(f"✅ Satış faturaları: {satis_count} ({len(satis_files)} dosya)")
            
            # Beyanname yükle
            kdv_pdf = self.ymm_paths.get("kdv_beyanname", tk.StringVar()).get()
            kdv_beyanname = None
            if kdv_pdf and os.path.exists(kdv_pdf):
                kdv_beyanname = parse_kdv_beyanname_pdf(kdv_pdf)
                if kdv_beyanname:
                    results.append(f"✅ KDV 1 Beyanname: {kdv_beyanname.donem}")
                    results.append(f"   Hesaplanan: {kdv_beyanname.hesaplanan_kdv:,.2f} TL")
                    results.append(f"   İndirimler: {kdv_beyanname.indirilecek_kdv_toplami:,.2f} TL")
            
            # KDV 2 Beyanname yükle
            kdv2_pdf = self.ymm_paths.get("kdv2_beyanname", tk.StringVar()).get()
            kdv2_beyanname = None
            if kdv2_pdf and os.path.exists(kdv2_pdf):
                try:
                    from kdv2_beyanname_parser import parse_kdv2_beyanname_pdf
                    kdv2_beyanname = parse_kdv2_beyanname_pdf(kdv2_pdf)
                    if kdv2_beyanname:
                        results.append(f"✅ KDV 2 Beyanname: {kdv2_beyanname.donem}")
                        results.append(f"   Sorumlu Matrah: {kdv2_beyanname.sorumlu_matrah:,.2f} TL")
                except ImportError:
                    results.append("⚠️ KDV 2 parser modülü bulunamadı")
                except Exception as e:
                    results.append(f"⚠️ KDV 2 okuma hatası: {str(e)[:50]}")
            
            muhtasar_pdf = self.ymm_paths.get("muhtasar_beyanname", tk.StringVar()).get()
            muhtasar_beyanname = None
            if muhtasar_pdf and os.path.exists(muhtasar_pdf):
                muhtasar_beyanname = parse_muhtasar_beyanname_pdf(muhtasar_pdf)
                if muhtasar_beyanname:
                    results.append(f"✅ Muhtasar: Toplam {muhtasar_beyanname.toplam_stopaj:,.2f} TL")
            
            # Standart kontrolleri çalıştır
            results.append("\n" + "="*40)
            results.append("DENETİM KONTROL EDİLİYOR...")
            
            engine.run_all_checks()
            results.append(f"✅ Standart kontroller: {len(engine.findings)} bulgu")
            
            # Beyanname kontrolleri
            if kdv_beyanname:
                kdv_findings = engine.check_kdv_beyanname(kdv_beyanname)
                results.append(f"✅ KDV 1 kontrolü: {len(kdv_findings)} bulgu")
            
            # KDV 2 kontrolü
            if kdv2_beyanname:
                try:
                    kdv2_findings = engine.check_kdv2_beyanname(kdv2_beyanname)
                    results.append(f"✅ KDV 2 kontrolü: {len(kdv2_findings)} bulgu")
                except AttributeError:
                    results.append("⚠️ KDV 2 kontrol fonksiyonu bulunamadı")
            
            if muhtasar_beyanname:
                muhtasar_findings = engine.check_muhtasar(muhtasar_beyanname)
                results.append(f"✅ Muhtasar kontrolü: {len(muhtasar_findings)} bulgu")
            
            # Rapor oluştur
            results.append("\n" + "="*40)
            results.append("RAPOR OLUŞTURULUYOR...")
            
            exec_report = engine.generate_executive_report()
            exec_report.company_name = company or "Firma"
            exec_report.period = kdv_beyanname.donem if kdv_beyanname else "Dönem"
            
            output_path = os.path.join(os.getcwd(), "YMM_Denetim_Raporu.html")
            
            # Denetçi bilgilerini al
            ymm_name = self.ymm_info.get("ymm_name", tk.StringVar()).get() or "YUSUF GÜLER"
            ymm_title = self.ymm_info.get("ymm_title", tk.StringVar()).get() or "Yeminli Mali Müşavir"
            auditor_name = self.ymm_info.get("auditor_name", tk.StringVar()).get() or "Mehmet BİLGİN"
            auditor_title = self.ymm_info.get("auditor_title", tk.StringVar()).get() or "Uzman Denetçi"
            
            generate_ymm_html_report(
                engine.findings, exec_report, output_path, kdv_beyanname,
                ymm_name=ymm_name,
                ymm_title=ymm_title,
                auditor_name=auditor_name,
                auditor_title=auditor_title
            )
            results.append(f"✅ Yönetici Raporu oluşturuldu")
            
            # Denetçi Raporu oluştur
            auditor_output_path = os.path.join(os.getcwd(), "YMM_Denetci_Raporu.html")
            
            # Çalışan listesini muhtasardan al
            employee_names = []
            if muhtasar_beyanname and hasattr(muhtasar_beyanname, 'employees'):
                employee_names = muhtasar_beyanname.employees
            
            # Fatura verilerini engine'den al
            all_invoices = engine.purchase_invoices + engine.sales_invoices
            
            generate_auditor_report(
                engine.findings, 
                engine.mizan,  # MizanData objesi
                exec_report.company_name or company or "Firma",
                exec_report.period or "Dönem",
                auditor_output_path,
                kebir_data=engine.kebir_data,  # Kebir verisi (muhasebe kayıtları için)
                invoice_data=all_invoices,  # Fatura verileri (KKEG eşleştirmesi için)
                employee_names=employee_names  # Çalışan isimleri (seyahat kontrolü için)
            )
            results.append(f"✅ Denetçi Raporu oluşturuldu")
            
            # Bulguları listele
            results.append("\n" + "="*40)
            results.append(f"TOPLAM BULGU: {len(engine.findings)}")
            results.append("="*40)
            
            for f in engine.findings[:10]:
                results.append(f"[{f.risk_level.value}] {f.account_code}: {f.description[:50]}...")
            
            if len(engine.findings) > 10:
                results.append(f"... ve {len(engine.findings) - 10} bulgu daha")
            
            # Sonuçları göster
            self.root.after(0, lambda: self._show_ymm_results("\n".join(results)))
            self.root.after(0, lambda: self.btn_ymm_report.config(state="normal"))
            self.root.after(0, lambda: self.btn_ymm_auditor_report.config(state="normal"))
            self.root.after(0, lambda: self.btn_ymm_mutabakat.config(state="normal"))
            
        except Exception as e:
            self.root.after(0, lambda: self._show_ymm_results(f"❌ HATA: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.btn_ymm_run.config(state="normal"))

    def _show_ymm_results(self, text):
        """YMM sonuçlarını göster"""
        self.ymm_result_text.config(state="normal")
        self.ymm_result_text.delete("1.0", "end")
        self.ymm_result_text.insert("end", text)
        self.ymm_result_text.config(state="disabled")

    def open_ymm_report(self):
        """YMM Yönetici Raporunu aç"""
        report_path = os.path.abspath("YMM_Denetim_Raporu.html")
        if os.path.exists(report_path):
            webbrowser.open(f"file:///{report_path}")
        else:
            messagebox.showerror("Hata", "Yönetici Raporu dosyası bulunamadı.")
    
    def open_ymm_auditor_report(self):
        """YMM Denetçi Raporunu aç"""
        report_path = os.path.abspath("YMM_Denetci_Raporu.html")
        if os.path.exists(report_path):
            webbrowser.open(f"file:///{report_path}")
        else:
            messagebox.showerror("Hata", "Denetçi Raporu dosyası bulunamadı.")
    
    def run_ymm_mutabakat(self):
        """YMM sekmesinden Fatura-Defter Mutabakat Raporu oluştur"""
        # Gerekli dosyaları kontrol et
        kebir_path = self.ymm_paths.get("kebir", tk.StringVar()).get()
        alis_files = list(self.alis_fatura_listbox.get(0, tk.END))
        
        if not kebir_path or not os.path.exists(kebir_path):
            messagebox.showwarning("Uyarı", "Lütfen önce Kebir dosyası yükleyin.")
            return
        
        if not alis_files:
            messagebox.showwarning("Uyarı", "Lütfen en az bir Alış Faturası dosyası ekleyin.")
            return
        
        try:
            from compare_invoices import run_analysis
            from generate_report import create_html_report
            
            # Analizi çalıştır
            messagebox.showinfo("Bilgi", "Fatura-Defter Mutabakat analizi başlatılıyor...\nBu işlem biraz sürebilir.")
            
            # Fatura ZIP'leri birleştir
            all_zip_files = [f for f in alis_files if f.lower().endswith('.zip')]
            
            if all_zip_files:
                # Tüm ZIP dosyalarını analiz et
                results = run_analysis(kebir_path, all_zip_files)
                
                # Rapor oluştur
                output_path = os.path.join(os.getcwd(), "Fatura_Defter_Analiz_Raporu.html")
                create_html_report(results, output_path)
                
                # Raporu aç
                webbrowser.open(f"file:///{os.path.abspath(output_path)}")
                messagebox.showinfo("Başarılı", f"Mutabakat Raporu oluşturuldu:\n{output_path}")
            else:
                messagebox.showwarning("Uyarı", "Alış faturaları için ZIP dosyası bulunamadı.\nMutabakat analizi ZIP dosyası gerektirir.")
                
        except ImportError as e:
            messagebox.showerror("Hata", f"Mutabakat modülü yüklenemedi:\n{str(e)}")
        except Exception as e:
            messagebox.showerror("Hata", f"Mutabakat analizi hatası:\n{str(e)}")
    
    def open_ymm_kdv_web(self):
        """YMM sekmesinden KDV Web Düzenleyiciyi aç (Alış faturaları)"""
        # Alış faturalarını al
        alis_files = list(self.alis_fatura_listbox.get(0, tk.END))
        
        if not alis_files:
            messagebox.showwarning("Uyarı", "Lütfen önce Alış Faturaları ekleyin.")
            return
        
        try:
            all_invoices = []
            
            for fpath in alis_files:
                if os.path.exists(fpath):
                    if fpath.lower().endswith('.zip'):
                        invoices = kdv_iade_listesi.load_invoices_from_zip(fpath)
                        all_invoices.extend(invoices)
                    elif fpath.lower().endswith('.xml'):
                        inv_data = kdv_iade_listesi.load_invoice_from_xml(fpath)
                        if inv_data:
                            all_invoices.append(inv_data)
                    elif fpath.lower().endswith('.pdf'):
                        inv_list = pdf_invoice_reader.smart_extract_invoices_from_pdf(fpath)
                        if inv_list:
                            all_invoices.extend(inv_list)
            
            if not all_invoices:
                messagebox.showwarning("Uyarı", "Hiç alış faturası bulunamadı!")
                return
            
            output_file = os.path.join(os.getcwd(), "YMM_KDV_Listesi_Editor.html")
            kdv_web_editor.generate_kdv_web_report(all_invoices, output_file)
            webbrowser.open(f"file:///{output_file}")
            
        except Exception as e:
            messagebox.showerror("Hata", f"KDV listesi oluşturulamadı:\n{str(e)}")
    
    def open_ymm_satis_web(self):
        """YMM sekmesinden Satış Web Düzenleyiciyi aç (Satış faturaları)"""
        # Satış faturalarını al
        satis_files = list(self.satis_fatura_listbox.get(0, tk.END))
        
        if not satis_files:
            messagebox.showwarning("Uyarı", "Lütfen önce Satış Faturaları ekleyin.")
            return
        
        try:
            from tkinter import simpledialog
            own_vkn = simpledialog.askstring(
                "Mükellef VKN",
                "Kendi VKN/TCKN'nizi girin (satış faturalarınızı bulmak için):",
                parent=self.root
            )
            
            if not own_vkn or not own_vkn.strip():
                messagebox.showwarning("Uyarı", "VKN girilmedi!")
                return
            
            own_vkn = own_vkn.strip()
            all_invoices = []
            
            for fpath in satis_files:
                if os.path.exists(fpath):
                    if fpath.lower().endswith('.zip'):
                        invs = satis_fatura_listesi.load_sales_invoices_from_zip(fpath, own_vkn=own_vkn)
                        all_invoices.extend(invs)
            
            if not all_invoices:
                messagebox.showwarning("Uyarı", "Hiç satış faturası bulunamadı!")
                return
            
            output_file = os.path.join(os.getcwd(), "YMM_Satis_Listesi_Editor.html")
            satis_web_editor.generate_satis_web_report(all_invoices, output_file)
            webbrowser.open(f"file:///{output_file}")
            
        except Exception as e:
            messagebox.showerror("Hata", f"Satış listesi oluşturulamadı:\n{str(e)}")
    
    def open_api_settings(self):
        """API Ayarları penceresini aç"""
        from tkinter import simpledialog
        import json
        from pathlib import Path
        
        # Mevcut API key'i oku
        config_file = Path.home() / ".ymm_audit_cache" / "api_config.json"
        current_key = ""
        
        try:
            if config_file.exists():
                with open(config_file, "r") as f:
                    config = json.load(f)
                    current_key = config.get("gemini_api_key", "")
        except:
            pass
        
        # API key sor
        masked = current_key[:8] + "..." if len(current_key) > 8 else current_key
        
        new_key = simpledialog.askstring(
            "API Ayarları",
            f"Google Gemini API Anahtarını girin:\n\n(Mevcut: {masked if masked else 'Ayarlanmamış'})",
            parent=self.root
        )
        
        if new_key and new_key.strip():
            try:
                config_file.parent.mkdir(parents=True, exist_ok=True)
                with open(config_file, "w") as f:
                    json.dump({"gemini_api_key": new_key.strip()}, f)
                
                # Environment variable olarak da ayarla
                os.environ["GEMINI_API_KEY"] = new_key.strip()
                
                messagebox.showinfo("Başarılı", "API anahtarı kaydedildi!")
            except Exception as e:
                messagebox.showerror("Hata", f"API anahtarı kaydedilemedi:\n{str(e)}")
    
    def open_ai_advisor(self):
        """AI Danışman penceresini aç"""
        from tkinter import simpledialog
        import json
        from pathlib import Path
        
        # API key kontrolü
        config_file = Path.home() / ".ymm_audit_cache" / "api_config.json"
        api_key = os.environ.get("GEMINI_API_KEY", "")
        
        if not api_key:
            try:
                if config_file.exists():
                    with open(config_file, "r") as f:
                        config = json.load(f)
                        api_key = config.get("gemini_api_key", "")
            except:
                pass
        
        if not api_key:
            result = messagebox.askyesno(
                "API Gerekli",
                "AI Danışman için Gemini API anahtarı gerekli.\n\nŞimdi API ayarlarını açmak ister misiniz?"
            )
            if result:
                self.open_api_settings()
            return
        
        # Soru sor
        question = simpledialog.askstring(
            "AI Denetim Danışmanı",
            "Denetim sorunuzu yazın:\n\n(Örnek: Bu gider KKEG mi? Temsil ağırlama giderleri nasıl muhasebeleştirilir?)",
            parent=self.root
        )
        
        if not question or not question.strip():
            return
        
        try:
            from ai_advisor import AIAdvisor
            
            advisor = AIAdvisor(api_key=api_key)
            result = advisor.ask(question.strip())
            
            if result["success"]:
                cache_info = " (önbellekten)" if result["from_cache"] else ""
                messagebox.showinfo(
                    f"AI Yanıtı{cache_info}",
                    result["answer"]
                )
            else:
                messagebox.showerror("AI Hatası", result["error"])
                
        except ImportError:
            messagebox.showerror("Hata", "AI modülü yüklenemedi. ai_advisor.py dosyasını kontrol edin.")
        except Exception as e:
            messagebox.showerror("Hata", f"AI sorgusu başarısız:\n{str(e)}")

    # ================== ORİJİNAL FONKSIYONLAR ==================
    
    def add_invoice_file(self):
        filenames = filedialog.askopenfilenames(
            title="Fatura Dosyalarını Seç", 
            filetypes=[("Faturalar", "*.zip *.rar *.xml *.pdf"), ("Tüm Dosyalar", "*.*")]
        )
        if filenames:
            for f in filenames:
                self.inv_listbox.insert(tk.END, f)

    def clear_invoice_list(self):
        self.inv_listbox.delete(0, tk.END)

    def add_file_selector(self, parent, label, key, file_types=[("Faturalar", "*.zip *.rar *.xml"), ("Tüm Dosyalar", "*.*")]):
        if key not in self.paths:
            self.paths[key] = tk.StringVar()
            
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        
        ttk.Label(row, text=label, width=22).pack(side="left")
        entry = ttk.Entry(row, textvariable=self.paths[key], width=40)
        entry.pack(side="left", padx=5)
        
        btn = ttk.Button(row, text="📂 Seç", width=8, command=lambda: self.browse_file(key, file_types))
        btn.pack(side="left")

    def browse_file(self, key, file_types):
        if key == "Defter":
            filenames = filedialog.askopenfilenames(filetypes=file_types)
            if filenames:
                self.paths[key].set(";".join(filenames))
        else:
            filename = filedialog.askopenfilename(filetypes=file_types)
            if filename:
                self.paths[key].set(filename)

    def log(self, message):
        self.log_queue.put(message)

    def check_log_queue(self):
        while not self.log_queue.empty():
            try:
                message = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
            except:
                pass
        self.root.after(100, self.check_log_queue)

    def start_analysis_thread(self):
        files = self.inv_listbox.get(0, tk.END)
        ledger_path = self.paths["Defter"].get()
        
        if not ledger_path:
             messagebox.showerror("Hata", "Defter dosyası seçilmedi!")
             return
             
        self.btn_run.config(state="disabled")
        self.btn_open.config(state="disabled")
        self.log("Analiz başlatılıyor... Lütfen bekleyiniz.")
        
        t = threading.Thread(target=self.run_analysis, args=(files, ledger_path))
        t.start()
        
    def run_analysis(self, files, ledger_path):
        try:
            invoice_paths = {}
            for idx, f in enumerate(files):
                invoice_paths[f"Dosya_{idx+1}"] = f
                
            if not invoice_paths:
                self.log("UYARI: Hiç fatura dosyası eklenmedi.")

            summary, csv_path = compare_invoices.run_analysis(ledger_path, invoice_paths, os.getcwd(), log_callback=self.log)
            
            self.log("-" * 30)
            self.log("ANALİZ TAMAMLANDI")
            self.log(f"Eşleşen: {summary.get('Eşleşti', 0)}")
            self.log(f"Belgesiz: {summary.get('BELGESİZ (Fatura Yok)', 0)}")
            self.log(f"KDV Hatası: {summary.get('KDV Hatası', 0)}")
            
            generate_report.create_html_report(os.getcwd())
            self.log("HTML Rapor oluşturuldu.")
            
            self.root.after(0, self.analysis_complete)
            
        except Exception as e:
            self.log(f"HATA OLUŞTU: {str(e)}")
            self.root.after(0, lambda: self.btn_run.config(state="normal"))

    def analysis_complete(self):
        self.btn_run.config(state="normal")
        self.btn_open.config(state="normal")
        messagebox.showinfo("Başarılı", "Analiz tamamlandı. Raporu açabilirsiniz.")
        
    def open_report(self):
        report_path = os.path.abspath("Fatura_Defter_Analiz_Raporu.html")
        if os.path.exists(report_path):
            webbrowser.open(f"file:///{report_path}")
        else:
            messagebox.showerror("Hata", "Rapor dosyası bulunamadı.")
    
    def generate_kdv_listesi(self):
        """GİB formatında İndirilecek KDV Listesi Excel dosyası oluştur."""
        files = self.inv_listbox.get(0, tk.END)
        zip_files = [f for f in files if f.lower().endswith('.zip')]
        xml_files = [f for f in files if f.lower().endswith('.xml')]
        
        if not zip_files and not xml_files:
            default_zips = [
                os.path.join(os.getcwd(), "Gelen e-Fatura.zip"),
                os.path.join(os.getcwd(), "Giden e-Fatura.zip")
            ]
            for dz in default_zips:
                if os.path.exists(dz):
                    zip_files.append(dz)
        
        if not zip_files and not xml_files:
            messagebox.showerror("Hata", "Dosya bulunamadı!\nLütfen ZIP veya XML fatura dosyalarını ekleyin.")
            return
        
        try:
            self.log("KDV İade Listesi oluşturuluyor...")
            
            all_invoices = []
            
            for zip_path in zip_files:
                self.log(f"Yükleniyor: {os.path.basename(zip_path)}")
                try:
                    invoices = kdv_iade_listesi.load_invoices_from_zip(zip_path)
                    all_invoices.extend(invoices)
                    self.log(f"  -> {len(invoices)} fatura bulundu")
                except Exception as e:
                    self.log(f"  HATA: {e}")
            
            for xml_path in xml_files:
                self.log(f"Yükleniyor: {os.path.basename(xml_path)}")
                try:
                    inv_data = kdv_iade_listesi.load_invoice_from_xml(xml_path)
                    if inv_data:
                        all_invoices.append(inv_data)
                        self.log(f"  -> 1 fatura bulundu")
                except Exception as e:
                    self.log(f"  HATA: {e}")
            
            if not all_invoices:
                messagebox.showwarning("Uyarı", "Hiç fatura bulunamadı!")
                return
            
            output_file = filedialog.asksaveasfilename(
                title="KDV Listesini Kaydet",
                defaultextension=".xlsx",
                initialfile="Indirilecek_KDV_Listesi.xlsx",
                filetypes=[("Excel", "*.xlsx")]
            )
            
            if not output_file:
                return
            
            kdv_iade_listesi.generate_kdv_listesi_excel(all_invoices, output_file)
            
            self.log(f"KDV Listesi oluşturuldu: {len(all_invoices)} fatura")
            messagebox.showinfo("Başarılı", f"İndirilecek KDV Listesi oluşturuldu!\n\n{output_file}")
            
            os.startfile(output_file)
            
        except Exception as e:
            messagebox.showerror("Hata", f"KDV listesi oluşturulamadı:\n{str(e)}")
    
    def open_kdv_web_editor(self):
        """İnteraktif web tabanlı KDV listesi düzenleyicisini aç."""
        files = self.inv_listbox.get(0, tk.END)
        zip_files = [f for f in files if f.lower().endswith('.zip')]
        xml_files = [f for f in files if f.lower().endswith('.xml')]
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        
        if not zip_files and not xml_files and not pdf_files:
            default_zips = [
                os.path.join(os.getcwd(), "Gelen e-Fatura.zip"),
                os.path.join(os.getcwd(), "Giden e-Fatura.zip")
            ]
            for dz in default_zips:
                if os.path.exists(dz):
                    zip_files.append(dz)
        
        if not zip_files and not xml_files and not pdf_files:
            messagebox.showerror("Hata", "Dosya bulunamadı!\nLütfen ZIP, XML veya PDF fatura dosyalarını ekleyin.")
            return
        
        try:
            self.log("KDV Web Düzenleyici yükleniyor...")
            
            all_invoices = []
            
            for zip_path in zip_files:
                self.log(f"Yükleniyor: {os.path.basename(zip_path)}")
                try:
                    invoices = kdv_iade_listesi.load_invoices_from_zip(zip_path)
                    all_invoices.extend(invoices)
                    self.log(f"  -> {len(invoices)} fatura bulundu")
                except Exception as e:
                    self.log(f"  HATA: {e}")
            
            for xml_path in xml_files:
                self.log(f"Yükleniyor: {os.path.basename(xml_path)}")
                try:
                    inv_data = kdv_iade_listesi.load_invoice_from_xml(xml_path)
                    if inv_data:
                        all_invoices.append(inv_data)
                        self.log(f"  -> 1 fatura bulundu")
                except Exception as e:
                    self.log(f"  HATA: {e}")
            
            for pdf_path in pdf_files:
                self.log(f"Yükleniyor (PDF): {os.path.basename(pdf_path)}")
                try:
                    inv_list = pdf_invoice_reader.smart_extract_invoices_from_pdf(pdf_path)
                    if inv_list:
                        all_invoices.extend(inv_list)
                        self.log(f"  -> {len(inv_list)} fatura bulundu")
                except Exception as e:
                    self.log(f"  HATA: {e}")
            
            if not all_invoices:
                messagebox.showwarning("Uyarı", "Hiç fatura bulunamadı!")
                return
            
            from tkinter import simpledialog
            own_vkn = simpledialog.askstring(
                "Mükellef VKN",
                "Kendi VKN/TCKN'nizi girin (satış faturalarını hariç tutmak için):\n(Boş bırakırsanız filtreleme yapılmaz)",
                parent=self.root
            )
            
            if own_vkn and own_vkn.strip():
                own_vkn = own_vkn.strip()
                original_count = len(all_invoices)
                all_invoices = [inv for inv in all_invoices if inv.get('satici_vkn', '') != own_vkn]
                filtered_count = original_count - len(all_invoices)
                if filtered_count > 0:
                    self.log(f"  -> {filtered_count} satış faturası hariç tutuldu")
            
            if not all_invoices:
                messagebox.showwarning("Uyarı", "Filtreleme sonrası hiç alış faturası kalmadı!")
                return
            
            output_file = os.path.join(os.getcwd(), "KDV_Listesi_Editor.html")
            kdv_web_editor.generate_kdv_web_report(all_invoices, output_file)
            
            self.log(f"Web düzenleyici oluşturuldu: {len(all_invoices)} fatura")
            
            webbrowser.open(f"file:///{output_file}")
            
        except Exception as e:
            messagebox.showerror("Hata", f"Web düzenleyici oluşturulamadı:\n{str(e)}")
    
    def open_satis_web_editor(self):
        """İnteraktif web tabanlı Satış Fatura Listesi düzenleyicisini aç."""
        files = self.inv_listbox.get(0, tk.END)
        zip_files = [f for f in files if f.lower().endswith('.zip')]
        xml_files = [f for f in files if f.lower().endswith('.xml')]
        
        if not zip_files and not xml_files:
            default_zips = [
                os.path.join(os.getcwd(), "Giden e-Fatura.zip"),
                os.path.join(os.getcwd(), "Gelen e-Fatura.zip")
            ]
            for dz in default_zips:
                if os.path.exists(dz):
                    zip_files.append(dz)
        
        if not zip_files and not xml_files:
            messagebox.showerror("Hata", "Dosya bulunamadı!\nLütfen ZIP veya XML fatura dosyalarını ekleyin.")
            return
        
        try:
            self.log("Satış Fatura Listesi yükleniyor...")
            
            from tkinter import simpledialog
            own_vkn = simpledialog.askstring(
                "Mükellef VKN",
                "Kendi VKN/TCKN'nizi girin (satış faturalarınızı bulmak için):",
                parent=self.root
            )
            
            if not own_vkn or not own_vkn.strip():
                messagebox.showwarning("Uyarı", "VKN girilmedi! Satış faturalarını filtrelemek için VKN gerekli.")
                return
            
            own_vkn = own_vkn.strip()
            all_invoices = []
            
            for zip_path in zip_files:
                self.log(f"Yükleniyor: {os.path.basename(zip_path)}")
                invs = satis_fatura_listesi.load_sales_invoices_from_zip(zip_path, own_vkn=own_vkn)
                all_invoices.extend(invs)
                self.log(f"  -> {len(invs)} satış faturası bulundu")
            
            if not all_invoices:
                messagebox.showwarning("Uyarı", "Hiç satış faturası bulunamadı!\nVKN'nin doğru olduğundan emin olun.")
                return
            
            output_file = os.path.join(os.getcwd(), "Satis_Listesi_Editor.html")
            satis_web_editor.generate_satis_web_report(all_invoices, output_file)
            
            self.log(f"Satış listesi oluşturuldu: {len(all_invoices)} fatura")
            
            webbrowser.open(f"file:///{output_file}")
            
        except Exception as e:
            messagebox.showerror("Hata", f"Satış listesi oluşturulamadı:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = EMutabakatApp(root)
    root.mainloop()
