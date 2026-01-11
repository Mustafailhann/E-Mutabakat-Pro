# -*- coding: utf-8 -*-
"""
Denetçi Ekranı (Auditor View) - Detaylı Denetim Raporu
Denetçinin kontrol ettiği tüm bulgular, hesap detayları ve aksiyonlar
"""

from datetime import datetime
from typing import List, Dict
from ymm_audit import AuditFinding, ExecutiveReportData, RiskLevel, FindingType, MizanData


def evaluate_check_status(findings: List[AuditFinding], mizan: MizanData) -> Dict[str, dict]:
    """
    Her kontrol kalemi için durum değerlendir
    Returns: {'check_name': {'status': '✅', 'finding_count': 0, 'class': 'pass'}}
    """
    checks = {}
    
    # Ters bakiye kontrolü
    ters_bakiye = [f for f in findings if f.finding_type == FindingType.TERS_BAKIYE]
    checks['ters_bakiye'] = {
        'name': 'Ters Bakiye Kontrolleri',
        'status': '⚠️' if ters_bakiye else '✅',
        'count': len(ters_bakiye),
        'class': 'warning' if ters_bakiye else 'pass'
    }
    
    # Kasa adat kontrolü (100 hesabı yüksek bakiye)
    adat = [f for f in findings if f.finding_type == FindingType.ADAT and f.account_code == '100']
    checks['kasa_adat'] = {
        'name': 'Kasa Adat Kontrolü',
        'status': '⚠️' if adat else '✅',
        'count': len(adat),
        'class': 'warning' if adat else 'pass'
    }
    
    # 131 Ortaklardan Alacak kontrolü
    ortaklardan = [f for f in findings if f.account_code == '131']
    checks['ortaklardan_alacak'] = {
        'name': '131 Ortaklardan Alacak Faiz Kontrolü',
        'status': '⚠️' if ortaklardan else '✅',
        'count': len(ortaklardan),
        'class': 'warning' if ortaklardan else 'pass'
    }
    
    # 331 Örtülü sermaye kontrolü
    ortulu = [f for f in findings if f.finding_type == FindingType.ORTULU_SERMAYE]
    checks['ortulu_sermaye'] = {
        'name': '331 Örtülü Sermaye Kontrolü',
        'status': '🔴' if ortulu else '✅',
        'count': len(ortulu),
        'class': 'danger' if ortulu else 'pass'
    }
    
    # 360/361 Vergi/SGK kontrolü
    vergi_hesaplari = [f for f in findings if f.account_code in ['360', '361']]
    checks['vergi_sgk'] = {
        'name': '360/361 Vergi ve SGK Kontrolü',
        'status': '⚠️' if vergi_hesaplari else '✅',
        'count': len(vergi_hesaplari),
        'class': 'warning' if vergi_hesaplari else 'pass'
    }
    
    # 30.000 TL Nakit Sınır Kontrolü (VUK 320/323)
    nakit_sinir = [f for f in findings if f.finding_type == FindingType.NAKIT_SINIR]
    checks['nakit_sinir_30k'] = {
        'name': '30.000 TL Nakit Sınır Kontrolü (VUK 320)',
        'status': '🔴' if nakit_sinir else '✅',
        'count': len(nakit_sinir),
        'class': 'danger' if nakit_sinir else 'pass'
    }
    
    # Binek araç kontrolleri
    binek = [f for f in findings if f.finding_type == FindingType.BINEK_KISIT]
    checks['binek_arac'] = {
        'name': 'Binek Araç Gider Kısıtlaması',
        'status': '⚠️' if binek else '✅',
        'count': len(binek),
        'class': 'warning' if binek else 'pass'
    }
    
    # KDV kontrolü
    kdv = [f for f in findings if f.finding_type == FindingType.KDV_UYUMSUZLUK]
    checks['kdv_beyanname'] = {
        'name': 'KDV Beyanname - Mizan Mutabakatı',
        'status': '⚠️' if kdv else '✅',
        'count': len(kdv),
        'class': 'warning' if kdv else 'pass'
    }
    
    # Muhtasar kontrolü
    muhtasar = [f for f in findings if f.finding_type == FindingType.STOPAJ_FARK]
    checks['muhtasar'] = {
        'name': 'Muhtasar Beyanname Kontrolü',
        'status': '⚠️' if muhtasar else '✅',
        'count': len(muhtasar),
        'class': 'warning' if muhtasar else 'pass'
    }
    
    # Fatura-Defter karşılaştırması
    fatura = [f for f in findings if f.finding_type == FindingType.FATURA_EKSIK]
    checks['fatura_defter'] = {
        'name': 'Fatura - Defter Karşılaştırması',
        'status': '⚠️' if fatura else '✅',
        'count': len(fatura),
        'class': 'warning' if fatura else 'pass'
    }
    
    return checks


def generate_auditor_report(
    findings: List[AuditFinding],
    mizan: MizanData,
    company_name: str,
    period: str,
    output_path: str = "YMM_Denetci_Raporu.html",
    kebir_data: dict = None,
    invoice_data: list = None,
    employee_names: list = None
) -> str:
    """
    Denetçi için detaylı denetim raporu oluştur
    """
    
    # Bulgu istatistikleri
    critical = sum(1 for f in findings if f.risk_level == RiskLevel.CRITICAL)
    high = sum(1 for f in findings if f.risk_level == RiskLevel.HIGH)
    medium = sum(1 for f in findings if f.risk_level == RiskLevel.MEDIUM)
    low = sum(1 for f in findings if f.risk_level == RiskLevel.LOW)
    
    # Otomatik kontrol durumları
    checks = evaluate_check_status(findings, mizan)
    
    # Bulgu türlerine göre grupla
    findings_by_type: Dict[str, List[AuditFinding]] = {}
    for f in findings:
        key = f.finding_type.value
        if key not in findings_by_type:
            findings_by_type[key] = []
        findings_by_type[key].append(f)
    
    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Denetçi Raporu - {company_name}</title>
    <style>
        :root {{
            --primary: #1e3a5f;
            --secondary: #3d5a80;
            --accent: #ee6c4d;
            --success: #4caf50;
            --warning: #ff9800;
            --danger: #f44336;
            --bg: #f5f7fa;
            --card: #ffffff;
            --text: #333;
            --border: #ddd;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* Header */
        .header {{
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
        }}
        
        .header h1 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        
        .header-meta {{
            display: flex;
            gap: 30px;
            font-size: 14px;
            opacity: 0.9;
        }}
        
        /* Stats Bar */
        .stats-bar {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .stat {{
            background: var(--card);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border-left: 4px solid;
        }}
        
        .stat.critical {{ border-color: var(--danger); }}
        .stat.high {{ border-color: var(--warning); }}
        .stat.medium {{ border-color: #2196f3; }}
        .stat.low {{ border-color: var(--success); }}
        
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
        }}
        
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        
        /* Sections */
        .section {{
            background: var(--card);
            border-radius: 12px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        
        .section-header {{
            background: var(--primary);
            color: white;
            padding: 15px 20px;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .section-body {{
            padding: 20px;
        }}
        
        /* Findings Table */
        .findings-detail {{
            border-collapse: collapse;
            width: 100%;
        }}
        
        .findings-detail th,
        .findings-detail td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        
        .findings-detail th {{
            background: #f0f0f0;
            font-weight: 600;
        }}
        
        .findings-detail tr:hover {{
            background: #fafafa;
        }}
        
        .risk-tag {{
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .risk-tag.critical {{ background: #ffebee; color: var(--danger); }}
        .risk-tag.high {{ background: #fff3e0; color: #e65100; }}
        .risk-tag.medium {{ background: #e3f2fd; color: #1565c0; }}
        .risk-tag.low {{ background: #e8f5e9; color: #2e7d32; }}
        
        .action-box {{
            background: #fffde7;
            border-left: 3px solid var(--accent);
            padding: 10px 15px;
            margin-top: 10px;
            font-size: 13px;
        }}
        
        .acc-code {{
            font-family: monospace;
            background: #eee;
            padding: 2px 8px;
            border-radius: 3px;
        }}
        
        /* Collapsible */
        .collapse-toggle {{
            cursor: pointer;
            user-select: none;
        }}
        
        .collapse-toggle::before {{
            content: '▼ ';
            font-size: 10px;
        }}
        
        /* Checklist */
        .checklist {{
            list-style: none;
        }}
        
        .checklist li {{
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .checklist input[type="checkbox"] {{
            width: 18px;
            height: 18px;
        }}
        
        /* Print */
        @media print {{
            body {{ background: white; }}
            .section {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>📋 YMM Denetim Çalışma Kağıdı</h1>
            <div class="header-meta">
                <span>🏢 Firma: <strong>{company_name}</strong></span>
                <span>📅 Dönem: <strong>{period}</strong></span>
                <span>👤 Denetçi: ________________</span>
                <span>📆 Tarih: {datetime.now().strftime("%d.%m.%Y")}</span>
            </div>
        </div>
        
        <!-- Stats Bar -->
        <div class="stats-bar">
            <div class="stat critical">
                <div class="stat-value">{critical}</div>
                <div class="stat-label">Kritik Bulgu</div>
            </div>
            <div class="stat high">
                <div class="stat-value">{high}</div>
                <div class="stat-label">Yüksek Risk</div>
            </div>
            <div class="stat medium">
                <div class="stat-value">{medium}</div>
                <div class="stat-label">Orta Risk</div>
            </div>
            <div class="stat low">
                <div class="stat-value">{low}</div>
                <div class="stat-label">Düşük Risk</div>
            </div>
        </div>
        
        <!-- Denetim Kontrol Listesi (OTOMATİK) -->
        <div class="section">
            <div class="section-header">
                <span>📋 Denetim Kontrol Listesi</span>
                <span style="font-size: 12px;">✅ Sorun Yok | ⚠️ Bulgu Var | ⏳ Bekliyor</span>
            </div>
            <div class="section-body">
                {generate_checklist_html(checks)}
            </div>
        </div>
        
        <!-- Bulgular Detay -->
        {generate_findings_by_type(findings_by_type)}
        
        <!-- Mizan Özeti -->
        <div class="section">
            <div class="section-header">
                <span>📊 Mizan Özeti (Seçili Hesaplar)</span>
            </div>
            <div class="section-body">
                {generate_mizan_summary(mizan)}
            </div>
        </div>
        
        <!-- Hesap Grubu Değişim Analizi -->
        <div class="section">
            <div class="section-header">
                <span>📈 Hesap Grubu Değişim Analizi (2'li Gruplar)</span>
            </div>
            <div class="section-body">
                {generate_account_group_analysis(mizan, kebir_data)}
            </div>
        </div>
        
        <!-- Ortaklar ile İşlemler -->
        <div class="section">
            <div class="section-header">
                <span>👥 Ortaklar ile İşlemler (131 / 331)</span>
            </div>
            <div class="section-body">
                {generate_related_party_analysis(mizan, kebir_data)}
            </div>
        </div>
        
        <!-- KKEG Analizi -->
        <div class="section">
            <div class="section-header">
                <span>⚠️ KKEG Analizi (Kanunen Kabul Edilmeyen Giderler)</span>
            </div>
            <div class="section-body">
                {generate_kkeg_section(kebir_data, invoice_data, employee_names)}
            </div>
        </div>
        
        <!-- Denetçi Risk Tespitleri (Mutabakat Raporundan Aktarılan) -->
        {generate_denetci_risk_section(output_path)}
        
        <!-- Denetçi Notları -->
        <div class="section">
            <div class="section-header">
                <span>📝 Denetçi Notları</span>
            </div>
            <div class="section-body">
                <textarea style="width: 100%; height: 150px; border: 1px solid #ddd; padding: 10px; border-radius: 6px;" placeholder="Denetim sırasında alınan notlar..."></textarea>
            </div>
        </div>
        
        <!-- İmza -->
        <div class="section" style="margin-top: 40px;">
            <div class="section-body" style="display: flex; justify-content: space-around; text-align: center;">
                <div>
                    <p>Hazırlayan</p>
                    <div style="border-bottom: 1px solid #333; width: 200px; margin: 40px auto 10px;"></div>
                    <p><small>Denetim Personeli</small></p>
                </div>
                <div>
                    <p>Onaylayan</p>
                    <div style="border-bottom: 1px solid #333; width: 200px; margin: 40px auto 10px;"></div>
                    <p><small>YMM</small></p>
                </div>
            </div>
        </div>
    </div>
    
    <!-- localStorage'dan Denetçi Risklerini Oku -->
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            try {{
                var risks = JSON.parse(localStorage.getItem('denetciRiskleri') || '[]');
                if (risks.length > 0) {{
                    // Risk bölümünü oluştur
                    var container = document.querySelector('.container');
                    var riskSection = document.createElement('div');
                    riskSection.className = 'section';
                    riskSection.style.cssText = 'border-left: 4px solid #ff9800; margin-top: 30px;';
                    
                    var totalAmount = 0;
                    var rowsHtml = '';
                    risks.forEach(function(r) {{
                        rowsHtml += '<tr>';
                        rowsHtml += '<td style="padding: 10px; border: 1px solid #ddd;">' + r.invoiceNo + '</td>';
                        rowsHtml += '<td style="padding: 10px; border: 1px solid #ddd; background: #fff8e1;">' + r.riskType + '</td>';
                        rowsHtml += '<td style="padding: 10px; border: 1px solid #ddd; text-align: right;">' + r.amount.toLocaleString('tr-TR', {{minimumFractionDigits:2}}) + ' TL</td>';
                        rowsHtml += '<td style="padding: 10px; border: 1px solid #ddd;">' + (r.note || '-') + '</td>';
                        rowsHtml += '</tr>';
                        totalAmount += r.amount;
                    }});
                    
                    riskSection.innerHTML = `
                        <div class="section-header" style="background: linear-gradient(135deg, #ff9800 0%, #e65100 100%);">
                            <span>⚠️ Denetçi Risk Tespitleri (` + risks.length + ` adet)</span>
                        </div>
                        <div class="section-body">
                            <p>Aşağıdaki riskler denetçi tarafından Fatura-Defter Mutabakat analizi sırasında tespit edilmiştir.</p>
                            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                                <thead>
                                    <tr style="background: #ff9800; color: white;">
                                        <th style="padding: 12px; border: 1px solid #e65100;">Fatura No</th>
                                        <th style="padding: 12px; border: 1px solid #e65100;">Risk Türü</th>
                                        <th style="padding: 12px; border: 1px solid #e65100;">Tutar</th>
                                        <th style="padding: 12px; border: 1px solid #e65100;">Denetçi Notu</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ` + rowsHtml + `
                                    <tr style="background: #ffe0b2; font-weight: bold;">
                                        <td colspan="2" style="padding: 12px; border: 1px solid #e65100;">TOPLAM RİSK TUTARI</td>
                                        <td style="padding: 12px; border: 1px solid #e65100; text-align: right;">` + totalAmount.toLocaleString('tr-TR', {{minimumFractionDigits:2}}) + ` TL</td>
                                        <td style="padding: 12px; border: 1px solid #e65100;">` + risks.length + ` adet tespit</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    `;
                    
                    // KKEG bölümünden sonra ekle
                    var kkegSection = Array.from(document.querySelectorAll('.section-header')).find(h => h.innerText.includes('KKEG'));
                    if (kkegSection) {{
                        kkegSection.closest('.section').after(riskSection);
                    }} else {{
                        container.appendChild(riskSection);
                    }}
                }}
            }} catch(e) {{
                console.log('Risk okuma hatası:', e);
            }}
        }});
    </script>
</body>
</html>'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path


def generate_checklist_html(checks: Dict[str, dict]) -> str:
    """Kontrol listesi HTML'i oluştur"""
    rows = []
    for key, check in checks.items():
        status_class = check['class']
        badge_style = {
            'pass': 'background: #c6f6d5; color: #276749;',
            'warning': 'background: #feebc8; color: #c05621;',
            'danger': 'background: #fed7d7; color: #c53030;',
            'pending': 'background: #e2e8f0; color: #718096;'
        }.get(status_class, '')
        
        count_text = f" ({check['count']} bulgu)" if check['count'] > 0 else ""
        
        rows.append(f'''
            <tr>
                <td style="width: 60px; text-align: center;">
                    <span style="font-size: 20px;">{check['status']}</span>
                </td>
                <td style="font-weight: 500;">{check['name']}</td>
                <td style="width: 120px;">
                    <span style="padding: 4px 10px; border-radius: 4px; font-size: 11px; {badge_style}">
                        {'SORUN YOK' if status_class == 'pass' else 'BULGU VAR' if status_class in ['warning', 'danger'] else 'BEKLİYOR'}
                        {count_text}
                    </span>
                </td>
            </tr>
        ''')
    
    return f'''
        <table style="width: 100%; border-collapse: collapse;">
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
    '''


def generate_findings_by_type(findings_by_type: Dict[str, List[AuditFinding]]) -> str:
    """Bulgu türlerine göre bölümler oluştur"""
    if not findings_by_type:
        return '''<div class="section">
            <div class="section-header"><span>🔍 Denetim Bulguları</span></div>
            <div class="section-body"><p style="text-align:center; color:#666;">✅ Herhangi bir bulgu tespit edilmedi.</p></div>
        </div>'''
    
    html_parts = []
    for finding_type, findings in findings_by_type.items():
        rows = []
        for f in findings:
            risk_class = f.risk_level.name.lower()
            rows.append(f'''
                <tr>
                    <td><span class="risk-tag {risk_class}">{f.risk_level.value}</span></td>
                    <td><span class="acc-code">{f.account_code}</span></td>
                    <td>
                        {f.description}
                        <div class="action-box">💡 <strong>Öneri:</strong> {f.recommended_action}</div>
                    </td>
                    <td style="text-align: right; font-family: monospace;">{f.amount:,.2f} TL</td>
                </tr>
            ''')
        
        html_parts.append(f'''
            <div class="section">
                <div class="section-header">
                    <span class="collapse-toggle">🔍 {finding_type}</span>
                    <span>{len(findings)} bulgu</span>
                </div>
                <div class="section-body">
                    <table class="findings-detail">
                        <thead>
                            <tr>
                                <th width="100">Risk</th>
                                <th width="120">Hesap</th>
                                <th>Açıklama & Öneri</th>
                                <th width="130">Tutar</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(rows)}
                        </tbody>
                    </table>
                </div>
            </div>
        ''')
    
    return ''.join(html_parts)


def generate_mizan_summary(mizan: MizanData) -> str:
    """Önemli hesapların mizan özeti"""
    if not mizan or not mizan.accounts:
        return '<p>Mizan verisi yüklenmedi.</p>'
    
    important_accounts = ['100', '102', '120', '131', '150', '320', '331', '360', '361', '391', '191', '600', '601']
    
    rows = []
    for prefix in important_accounts:
        for code, acc in mizan.accounts.items():
            if code.startswith(prefix) and len(code) == 3:
                rows.append(f'''
                    <tr>
                        <td><span class="acc-code">{code}</span></td>
                        <td>{acc.name[:30]}</td>
                        <td style="text-align:right; font-family:monospace;">{acc.debit:,.2f}</td>
                        <td style="text-align:right; font-family:monospace;">{acc.credit:,.2f}</td>
                        <td style="text-align:right; font-family:monospace; font-weight:bold;">{acc.balance:,.2f}</td>
                    </tr>
                ''')
    
    return f'''
        <table class="findings-detail">
            <thead>
                <tr>
                    <th width="80">Hesap</th>
                    <th>Hesap Adı</th>
                    <th width="130" style="text-align:right;">Borç</th>
                    <th width="130" style="text-align:right;">Alacak</th>
                    <th width="130" style="text-align:right;">Bakiye</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows) if rows else '<tr><td colspan="5" style="text-align:center;">Hesap bulunamadı</td></tr>'}
            </tbody>
        </table>
    '''


def generate_account_group_analysis(mizan: MizanData, kebir_data: dict = None) -> str:
    """
    2'li hesap gruplarının (10, 11, 12... 77) değişim analizi
    Her grup için toplam Borç/Alacak ve net hareket yönü gösterilir
    """
    if not mizan or not mizan.accounts:
        return '<p>Mizan verisi yüklenmedi.</p>'
    
    # THP 2'li hesap grupları ve açıklamaları
    account_groups = {
        '10': 'Hazır Değerler',
        '11': 'Menkul Kıymetler',
        '12': 'Ticari Alacaklar',
        '13': 'Diğer Alacaklar',
        '15': 'Stoklar',
        '18': 'Gelecek Aylara Ait Giderler',
        '19': 'Diğer Dönen Varlıklar',
        '22': 'Ticari Alacaklar (Uzun)',
        '24': 'Mali Duran Varlıklar',
        '25': 'Maddi Duran Varlıklar',
        '26': 'Maddi Olmayan Duran Varlıklar',
        '30': 'Mali Borçlar',
        '32': 'Ticari Borçlar',
        '33': 'Diğer Borçlar',
        '34': 'Alınan Avanslar',
        '36': 'Ödenecek Vergiler',
        '37': 'Borç ve Gider Karşılıkları',
        '38': 'Gelecek Aylara Ait Gelirler',
        '39': 'Diğer Kısa Vadeli Yabancı Kaynaklar',
        '50': 'Ödenmiş Sermaye',
        '52': 'Sermaye Yedekleri',
        '54': 'Kar Yedekleri',
        '57': 'Geçmiş Yıl Karları',
        '58': 'Geçmiş Yıl Zararları',
        '59': 'Dönem Net Karı/Zararı',
        '60': 'Brüt Satışlar',
        '61': 'Satış İndirimleri',
        '62': 'Satışların Maliyeti',
        '63': 'Faaliyet Giderleri',
        '64': 'Diğer Gelirler',
        '65': 'Diğer Giderler',
        '66': 'Finansman Giderleri',
        '67': 'Olağandışı Gelirler',
        '68': 'Olağandışı Giderler',
        '69': 'Dönem Karı/Zararı',
        '71': 'Direkt İlk Madde Malzeme',
        '72': 'Direkt İşçilik',
        '73': 'Genel Üretim Giderleri',
        '74': 'Hizmet Üretim Maliyeti',
        '76': 'Pazarlama Giderleri',
        '77': 'Genel Yönetim Giderleri',
        '78': 'Finansman Giderleri (Maliyet)',
    }
    
    # Her grup için toplam hesapla
    group_totals = {}
    for code, acc in mizan.accounts.items():
        if len(code) >= 2:
            prefix = code[:2]
            if prefix not in group_totals:
                group_totals[prefix] = {'debit': 0, 'credit': 0, 'balance': 0}
            group_totals[prefix]['debit'] += acc.debit
            group_totals[prefix]['credit'] += acc.credit
            group_totals[prefix]['balance'] += acc.balance
    
    # Sadece hareket olan grupları göster
    rows = []
    for prefix in sorted(group_totals.keys()):
        data = group_totals[prefix]
        if data['debit'] > 0 or data['credit'] > 0:
            name = account_groups.get(prefix, f'{prefix} Hesap Grubu')
            net_change = data['debit'] - data['credit']
            
            # Artış/Azalış yönü
            if net_change > 0:
                direction = '↑'
                dir_color = '#27ae60'  # Yeşil
                dir_text = 'Artış'
            elif net_change < 0:
                direction = '↓'
                dir_color = '#e74c3c'  # Kırmızı
                dir_text = 'Azalış'
            else:
                direction = '—'
                dir_color = '#7f8c8d'
                dir_text = 'Değişim Yok'
            
            rows.append(f'''
                <tr>
                    <td><span class="acc-code">{prefix}</span></td>
                    <td>{name}</td>
                    <td style="text-align:right; font-family:monospace;">{data['debit']:,.2f}</td>
                    <td style="text-align:right; font-family:monospace;">{data['credit']:,.2f}</td>
                    <td style="text-align:right; font-family:monospace; font-weight:bold; color:{dir_color};">
                        {direction} {abs(net_change):,.2f}
                    </td>
                    <td style="text-align:center;">
                        <span style="background:{dir_color}22; color:{dir_color}; padding:2px 8px; border-radius:4px; font-size:11px;">
                            {dir_text}
                        </span>
                    </td>
                </tr>
            ''')
    
    return f'''
        <table class="findings-detail">
            <thead>
                <tr>
                    <th width="60">Grup</th>
                    <th>Hesap Grubu Adı</th>
                    <th width="130" style="text-align:right;">Borç Toplamı</th>
                    <th width="130" style="text-align:right;">Alacak Toplamı</th>
                    <th width="130" style="text-align:right;">Net Değişim</th>
                    <th width="100" style="text-align:center;">Yön</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows) if rows else '<tr><td colspan="6" style="text-align:center;">Hesap grubu bulunamadı</td></tr>'}
            </tbody>
        </table>
    '''


def generate_related_party_analysis(mizan: MizanData, kebir_data: dict = None) -> str:
    """
    131 Ortaklardan Alacaklar ve 331 Ortaklara Borçlar detaylı analizi
    Hem dönem hareketleri hem de bakiye gösterimi
    """
    if not mizan or not mizan.accounts:
        return '<p>Mizan verisi yüklenmedi.</p>'
    
    # 131 ve 331 hesaplarını bul
    ortaklardan_alacak = None
    ortaklara_borc = None
    
    for code, acc in mizan.accounts.items():
        if code.startswith('131'):
            if ortaklardan_alacak is None:
                ortaklardan_alacak = {'debit': 0, 'credit': 0, 'balance': 0, 'name': acc.name}
            ortaklardan_alacak['debit'] += acc.debit
            ortaklardan_alacak['credit'] += acc.credit
            ortaklardan_alacak['balance'] += acc.balance
        elif code.startswith('331'):
            if ortaklara_borc is None:
                ortaklara_borc = {'debit': 0, 'credit': 0, 'balance': 0, 'name': acc.name}
            ortaklara_borc['debit'] += acc.debit
            ortaklara_borc['credit'] += acc.credit
            ortaklara_borc['balance'] += acc.balance
    
    # Kayıt detayları (Kebir'den)
    entries_131 = []
    entries_331 = []
    
    if kebir_data:
        for doc_no, doc_data in kebir_data.items():
            lines = doc_data.get('Lines', [])
            doc_desc = doc_data.get('Desc', doc_no)[:40]
            
            for line in lines:
                acc = line.get('Acc', '')
                if acc.startswith('131'):
                    entries_131.append({
                        'doc': doc_no[:20],
                        'desc': line.get('Desc', doc_desc)[:35],
                        'dc': line.get('DC', 'D'),
                        'amt': float(line.get('Amt', 0) or 0)
                    })
                elif acc.startswith('331'):
                    entries_331.append({
                        'doc': doc_no[:20],
                        'desc': line.get('Desc', doc_desc)[:35],
                        'dc': line.get('DC', 'D'),
                        'amt': float(line.get('Amt', 0) or 0)
                    })
    
    # 131 Tablosu
    html_131 = '<h4 style="color:#1e3a5f; margin:15px 0 10px;">📥 131 - Ortaklardan Alacaklar</h4>'
    if ortaklardan_alacak:
        html_131 += f'''
        <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:15px;">
            <div style="background:#e3f2fd; padding:15px; border-radius:8px; text-align:center;">
                <div style="font-size:11px; color:#666;">Dönem Borç</div>
                <div style="font-size:18px; font-weight:bold; color:#1565c0;">{ortaklardan_alacak['debit']:,.2f} TL</div>
            </div>
            <div style="background:#fce4ec; padding:15px; border-radius:8px; text-align:center;">
                <div style="font-size:11px; color:#666;">Dönem Alacak</div>
                <div style="font-size:18px; font-weight:bold; color:#c62828;">{ortaklardan_alacak['credit']:,.2f} TL</div>
            </div>
            <div style="background:#e8f5e9; padding:15px; border-radius:8px; text-align:center;">
                <div style="font-size:11px; color:#666;">Kümülatif Bakiye</div>
                <div style="font-size:18px; font-weight:bold; color:#2e7d32;">{ortaklardan_alacak['balance']:,.2f} TL</div>
            </div>
            <div style="background:#fff3e0; padding:15px; border-radius:8px; text-align:center;">
                <div style="font-size:11px; color:#666;">Aylık Net Hareket</div>
                <div style="font-size:18px; font-weight:bold; color:#e65100;">{ortaklardan_alacak['debit'] - ortaklardan_alacak['credit']:,.2f} TL</div>
            </div>
        </div>
        '''
        
        if entries_131:
            entry_rows = ''.join([f'''
                <tr>
                    <td>{e['doc']}</td>
                    <td>{e['desc']}</td>
                    <td style="text-align:center;">{"Borç" if e['dc'] in ['D','B'] else "Alacak"}</td>
                    <td style="text-align:right; font-family:monospace;">{e['amt']:,.2f}</td>
                </tr>
            ''' for e in entries_131[:15]])  # İlk 15 kayıt
            
            html_131 += f'''
            <details style="margin-top:10px;">
                <summary style="cursor:pointer; font-weight:600; color:#1e3a5f;">📋 Muhasebe Kayıtları ({len(entries_131)} işlem)</summary>
                <table class="findings-detail" style="margin-top:10px;">
                    <thead><tr>
                        <th width="120">Belge No</th><th>Açıklama</th>
                        <th width="80">B/A</th><th width="120">Tutar</th>
                    </tr></thead>
                    <tbody>{entry_rows}</tbody>
                </table>
                {f'<p style="color:#666; font-size:12px;">... ve {len(entries_131)-15} kayıt daha</p>' if len(entries_131) > 15 else ''}
            </details>
            '''
    else:
        html_131 += '<p style="color:#27ae60;">✅ 131 hesabında hareket bulunmamaktadır.</p>'
    
    # 331 Tablosu
    html_331 = '<h4 style="color:#1e3a5f; margin:25px 0 10px;">📤 331 - Ortaklara Borçlar</h4>'
    if ortaklara_borc:
        html_331 += f'''
        <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:15px;">
            <div style="background:#e3f2fd; padding:15px; border-radius:8px; text-align:center;">
                <div style="font-size:11px; color:#666;">Dönem Borç</div>
                <div style="font-size:18px; font-weight:bold; color:#1565c0;">{ortaklara_borc['debit']:,.2f} TL</div>
            </div>
            <div style="background:#fce4ec; padding:15px; border-radius:8px; text-align:center;">
                <div style="font-size:11px; color:#666;">Dönem Alacak</div>
                <div style="font-size:18px; font-weight:bold; color:#c62828;">{ortaklara_borc['credit']:,.2f} TL</div>
            </div>
            <div style="background:#e8f5e9; padding:15px; border-radius:8px; text-align:center;">
                <div style="font-size:11px; color:#666;">Kümülatif Bakiye</div>
                <div style="font-size:18px; font-weight:bold; color:#2e7d32;">{abs(ortaklara_borc['balance']):,.2f} TL</div>
            </div>
            <div style="background:#fff3e0; padding:15px; border-radius:8px; text-align:center;">
                <div style="font-size:11px; color:#666;">Aylık Net Hareket</div>
                <div style="font-size:18px; font-weight:bold; color:#e65100;">{ortaklara_borc['credit'] - ortaklara_borc['debit']:,.2f} TL</div>
            </div>
        </div>
        '''
        
        if entries_331:
            entry_rows = ''.join([f'''
                <tr>
                    <td>{e['doc']}</td>
                    <td>{e['desc']}</td>
                    <td style="text-align:center;">{"Borç" if e['dc'] in ['D','B'] else "Alacak"}</td>
                    <td style="text-align:right; font-family:monospace;">{e['amt']:,.2f}</td>
                </tr>
            ''' for e in entries_331[:15]])
            
            html_331 += f'''
            <details style="margin-top:10px;">
                <summary style="cursor:pointer; font-weight:600; color:#1e3a5f;">📋 Muhasebe Kayıtları ({len(entries_331)} işlem)</summary>
                <table class="findings-detail" style="margin-top:10px;">
                    <thead><tr>
                        <th width="120">Belge No</th><th>Açıklama</th>
                        <th width="80">B/A</th><th width="120">Tutar</th>
                    </tr></thead>
                    <tbody>{entry_rows}</tbody>
                </table>
                {f'<p style="color:#666; font-size:12px;">... ve {len(entries_331)-15} kayıt daha</p>' if len(entries_331) > 15 else ''}
            </details>
            '''
    else:
        html_331 += '<p style="color:#27ae60;">✅ 331 hesabında hareket bulunmamaktadır.</p>'
    
    return html_131 + html_331


def generate_kkeg_section(kebir_data: dict = None, invoice_data: list = None, employee_names: list = None) -> str:
    """KKEG bulgularını HTML olarak oluştur"""
    if not kebir_data:
        return '<p style="color:#666;">Kebir verisi yüklenmedi, KKEG analizi yapılamadı.</p>'
    
    try:
        from kkeg_detector import KKEGDetector, generate_kkeg_report_html
        
        detector = KKEGDetector(year=2024)
        findings = detector.detect_from_kebir(kebir_data, invoice_data, employee_names)
        
        if not findings:
            return '<p style="color:#27ae60;">✅ KKEG riski tespit edilmedi.</p>'
        
        return generate_kkeg_report_html(findings, kebir_data)
        
    except ImportError:
        return '''<p style="color:#ff9800;">
            ⚠️ KKEG modülü yüklü değil. <code>kkeg_detector.py</code> dosyasını kontrol edin.
        </p>'''
    except Exception as e:
        return f'<p style="color:#e74c3c;">KKEG analizi hatası: {str(e)}</p>'


def generate_denetci_risk_section(output_path: str) -> str:
    """
    Mutabakat raporundan aktarılan denetçi risklerini göster.
    denetci_riskleri.json dosyasını okur.
    """
    import os
    import json
    
    # JSON dosyasının yolu
    base_dir = os.path.dirname(os.path.abspath(output_path))
    json_path = os.path.join(base_dir, "denetci_riskleri.json")
    
    # Downloads klasörünü de kontrol et
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads", "denetci_riskleri.json")
    
    risks = []
    
    # Önce çalışma dizininde ara
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                risks = json.load(f)
        except:
            pass
    # Sonra downloads klasöründe ara
    elif os.path.exists(downloads_path):
        try:
            with open(downloads_path, 'r', encoding='utf-8') as f:
                risks = json.load(f)
        except:
            pass
    
    if not risks:
        return '''
        <div class="section" style="border-left: 4px solid #9e9e9e;">
            <div class="section-header" style="background: linear-gradient(135deg, #9e9e9e 0%, #757575 100%);">
                <span>📋 Denetçi Risk Tespitleri</span>
            </div>
            <div class="section-body">
                <p style="color:#757575; font-style:italic;">
                    Henüz risk aktarılmamış. Mutabakat Raporunda riskleri işaretleyip "📥 Rapora Aktar" butonuna tıklayın.
                </p>
            </div>
        </div>
        '''
    
    # Toplam tutar
    total_amount = sum(r.get('amount', 0) for r in risks)
    
    # Risk tablosu
    rows_html = ""
    for r in risks:
        rows_html += f'''
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;">{r.get('invoiceNo', '-')}</td>
            <td style="padding: 10px; border: 1px solid #ddd; background: #fff8e1;">{r.get('riskType', '-')}</td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">{r.get('amount', 0):,.2f} TL</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{r.get('note', '-') or '-'}</td>
        </tr>
        '''
    
    return f'''
    <div class="section" style="border-left: 4px solid #ff9800;">
        <div class="section-header" style="background: linear-gradient(135deg, #ff9800 0%, #e65100 100%);">
            <span>⚠️ Denetçi Risk Tespitleri ({len(risks)} adet)</span>
        </div>
        <div class="section-body">
            <p>Aşağıdaki riskler denetçi tarafından Fatura-Defter Mutabakat analizi sırasında tespit edilmiştir.</p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <thead>
                    <tr style="background: #ff9800; color: white;">
                        <th style="padding: 12px; border: 1px solid #e65100;">Fatura No</th>
                        <th style="padding: 12px; border: 1px solid #e65100;">Risk Türü</th>
                        <th style="padding: 12px; border: 1px solid #e65100;">Tutar</th>
                        <th style="padding: 12px; border: 1px solid #e65100;">Denetçi Notu</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                    <tr style="background: #ffe0b2; font-weight: bold;">
                        <td colspan="2" style="padding: 12px; border: 1px solid #e65100;">TOPLAM RİSK TUTARI</td>
                        <td style="padding: 12px; border: 1px solid #e65100; text-align: right;">{total_amount:,.2f} TL</td>
                        <td style="padding: 12px; border: 1px solid #e65100;">{len(risks)} adet tespit</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    '''

if __name__ == "__main__":
    # Test
    from ymm_audit import YMMAuditEngine
    import html_kebir_parser
    
    kebir_path = r"c:\Users\Asus\Desktop\RAD EYLÜL EKİM\Yeni klasör\10 2025 Dönem Kebir.HTM"
    ledger_map, company = html_kebir_parser.parse_html_kebir(kebir_path)
    
    engine = YMMAuditEngine()
    mizan = engine.load_mizan_from_kebir(ledger_map)
    findings = engine.run_all_checks()
    
    output = generate_auditor_report(findings, mizan, company or "RAD TEKSTİL", "Ekim 2025")
    print(f"Denetçi raporu oluşturuldu: {output}")
    
    import webbrowser
    webbrowser.open(output)
