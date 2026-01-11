# -*- coding: utf-8 -*-
"""
YMM Denetim Raporu HTML Oluşturucu
Modern ve profesyonel görünümlü rapor
"""

from datetime import datetime
from typing import List  
from ymm_audit import AuditFinding, ExecutiveReportData, RiskLevel, FindingType
from ymm_report_helpers import (
    calculate_financial_ratios,
    generate_tax_breakdown,
    generate_audit_statement_html,
    generate_tax_breakdown_html,
    generate_financial_ratios_html
)


def generate_ymm_html_report(
    findings: List[AuditFinding],
    executive_report: ExecutiveReportData,
    output_path: str = "YMM_Denetim_Raporu.html",
    kdv_beyanname = None,
    mizan = None,
    muhtasar_beyanname = None,
    ymm_name: str = "YUSUF GÜLER",
    ymm_title: str = "Yeminli Mali Müşavir",
    auditor_name: str = "Mehmet BİLGİN",
    auditor_title: str = "Uzman Denetçi"
) -> str:
    """
    YMM Denetim Raporu HTML dosyası oluştur
    
    Args:
        findings: Denetim bulguları listesi
        executive_report: Yönetici raporu verileri
        output_path: Çıktı dosya yolu
        kdv_beyanname: KDV beyanname verisi (opsiyonel)
        mizan: Mizan verisi (opsiyonel)
        muhtasar_beyanname: Muhtasar beyanname (opsiyonel)
        ymm_name: YMM adı (varsayılan: YUSUF GÜLER)
        ymm_title: YMM unvanı (varsayılan: Yeminli Mali Müşavir)
        auditor_name: Denetçi adı (varsayılan: Mehmet BİLGİN)
        auditor_title: Denetçi unvanı (varsayılan: Uzman Denetçi)
    """
    
    # Yeni özellikler için hazırlık
    audit_statement_html = ""
    tax_breakdown_html = ""
    financial_ratios_html = ""
    
    # Denetim beyanı (her zaman ekle)
    company_name = executive_report.company_name or "Firma Adı"
    period = executive_report.period or datetime.now().strftime("%B %Y")
    audit_statement_html = generate_audit_statement_html(company_name, period)
    
    # Vergi dökümü (mizan varsa)
    if mizan:
        taxes = generate_tax_breakdown(mizan, kdv_beyanname, muhtasar_beyanname)
        tax_breakdown_html = generate_tax_breakdown_html(taxes)
    
    # Finansal oranlar (mizan varsa)
    if mizan:
        ratios = calculate_financial_ratios(mizan)
        financial_ratios_html = generate_financial_ratios_html(ratios)
    
    # Risk sayıları
    critical_count = sum(1 for f in findings if f.risk_level == RiskLevel.CRITICAL)
    high_count = sum(1 for f in findings if f.risk_level == RiskLevel.HIGH)
    medium_count = sum(1 for f in findings if f.risk_level == RiskLevel.MEDIUM)
    low_count = sum(1 for f in findings if f.risk_level == RiskLevel.LOW)
    total_findings = len(findings)
    
    # Top 5 chart data preparation
    import json
    top5_sales_list = [{"name": name[:25], "value": float(val)} for name, val in (executive_report.top_customers or [])]
    top5_purchases_list = [{"name": name[:25], "value": float(val)} for name, val in (executive_report.top_suppliers or [])]
    top5_sales_json = json.dumps(top5_sales_list, ensure_ascii=False)
    top5_purchases_json = json.dumps(top5_purchases_list, ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YMM Denetim Raporu - {datetime.now().strftime("%B %Y")}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2"></script>
    <style>
        :root {{
            --primary: #1a365d;
            --primary-light: #2c5282;
            --accent: #ed8936;
            --success: #38a169;
            --warning: #d69e2e;
            --danger: #e53e3e;
            --info: #3182ce;
            --bg: #f7fafc;
            --card-bg: #ffffff;
            --text: #2d3748;
            --text-light: #718096;
            --border: #e2e8f0;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: var(--text);
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        /* Header */
        .header {{
            background: var(--card-bg);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .header-left h1 {{
            font-size: 28px;
            color: var(--primary);
            margin-bottom: 8px;
        }}
        
        .header-left p {{
            color: var(--text-light);
            font-size: 14px;
        }}
        
        .header-right {{
            text-align: right;
        }}
        
        .company-name {{
            font-size: 20px;
            font-weight: 600;
            color: var(--primary-light);
        }}
        
        .period-badge {{
            display: inline-block;
            background: linear-gradient(135deg, var(--accent) 0%, #dd6b20 100%);
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 600;
            margin-top: 8px;
        }}
        
        /* Stats Cards */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .stat-card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }}
        
        .stat-icon {{
            width: 50px;
            height: 50px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 12px;
            font-size: 24px;
        }}
        
        .stat-icon.critical {{ background: linear-gradient(135deg, #fc8181 0%, var(--danger) 100%); color: white; }}
        .stat-icon.high {{ background: linear-gradient(135deg, #fbd38d 0%, var(--warning) 100%); color: white; }}
        .stat-icon.medium {{ background: linear-gradient(135deg, #90cdf4 0%, var(--info) 100%); color: white; }}
        .stat-icon.success {{ background: linear-gradient(135deg, #9ae6b4 0%, var(--success) 100%); color: white; }}
        
        .stat-value {{
            font-size: 32px;
            font-weight: 700;
            color: var(--primary);
        }}
        
        .stat-label {{
            font-size: 13px;
            color: var(--text-light);
            margin-top: 4px;
        }}
        
        /* Cards */
        .card {{
            background: var(--card-bg);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}
        
        .card-header {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 2px solid var(--border);
        }}
        
        .card-header h2 {{
            font-size: 18px;
            color: var(--primary);
            margin: 0;
        }}
        
        .card-header .badge {{
            margin-left: auto;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        /* Executive Summary Grid */
        .exec-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }}
        
        .exec-item {{
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }}
        
        .exec-item:last-child {{
            border-bottom: none;
        }}
        
        .exec-label {{
            color: var(--text-light);
            font-size: 14px;
        }}
        
        .exec-value {{
            font-weight: 600;
            color: var(--primary);
            font-size: 15px;
        }}
        
        .exec-value.positive {{ color: var(--success); }}
        .exec-value.negative {{ color: var(--danger); }}
        
        /* Findings Table */
        .findings-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .findings-table th {{
            background: var(--primary);
            color: white;
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .findings-table th:first-child {{
            border-radius: 8px 0 0 0;
        }}
        
        .findings-table th:last-child {{
            border-radius: 0 8px 0 0;
        }}
        
        .findings-table td {{
            padding: 14px 16px;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}
        
        .findings-table tr:hover {{
            background: #f8fafc;
        }}
        
        .risk-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .risk-badge.critical {{
            background: #fed7d7;
            color: #c53030;
        }}
        
        .risk-badge.high {{
            background: #feebc8;
            color: #c05621;
        }}
        
        .risk-badge.medium {{
            background: #bee3f8;
            color: #2b6cb0;
        }}
        
        .risk-badge.low {{
            background: #c6f6d5;
            color: #276749;
        }}
        
        .account-code {{
            font-family: 'Consolas', monospace;
            background: #edf2f7;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 13px;
        }}
        
        .amount {{
            font-family: 'Consolas', monospace;
            font-weight: 600;
        }}
        
        .recommendation {{
            font-size: 12px;
            color: var(--text-light);
            margin-top: 6px;
            padding: 8px;
            background: #f7fafc;
            border-radius: 6px;
            border-left: 3px solid var(--accent);
        }}
        
        /* Top Lists */
        .top-list {{
            list-style: none;
        }}
        
        .top-list li {{
            display: flex;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }}
        
        .top-list li:last-child {{
            border-bottom: none;
        }}
        
        .top-rank {{
            width: 28px;
            height: 28px;
            border-radius: 8px;
            background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary) 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 12px;
            margin-right: 12px;
        }}
        
        .top-name {{
            flex: 1;
            font-weight: 500;
        }}
        
        .top-value {{
            font-family: 'Consolas', monospace;
            font-weight: 600;
            color: var(--primary);
        }}
        
        /* KDV Summary */
        .kdv-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            text-align: center;
        }}
        
        .kdv-item {{
            padding: 20px;
            border-radius: 12px;
            background: #f7fafc;
        }}
        
        .kdv-item.calculated {{ border-left: 4px solid var(--danger); }}
        .kdv-item.deductible {{ border-left: 4px solid var(--success); }}
        .kdv-item.payable {{ border-left: 4px solid var(--accent); }}
        
        .kdv-label {{
            font-size: 13px;
            color: var(--text-light);
            margin-bottom: 8px;
        }}
        
        .kdv-value {{
            font-size: 24px;
            font-weight: 700;
            color: var(--primary);
        }}
        
        /* Financial Ratios */
        .ratio-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
        }}
        
        .ratio-item {{
            background: #f7fafc;
            padding: 16px;
            border-radius: 10px;
            text-align: center;
        }}
        
        .ratio-value {{
            font-size: 28px;
            font-weight: 700;
            color: var(--primary);
        }}
        
        .ratio-label {{
            font-size: 12px;
            color: var(--text-light);
            margin-top: 4px;
        }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 20px;
            color: white;
            font-size: 12px;
            opacity: 0.8;
        }}
        
        /* Editable Styles */
        [contenteditable="true"] {{
            outline: 2px dashed #cbd5e0;
            padding: 4px 8px;
            border-radius: 4px;
            transition: outline-color 0.2s;
        }}
        
        [contenteditable="true"]:hover {{
            outline-color: var(--accent);
        }}
        
        [contenteditable="true"]:focus {{
            outline: 2px solid var(--primary);
            background: #fffbeb;
        }}
        
        .print-btn {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: linear-gradient(135deg, var(--success) 0%, #2f855a 100%);
            color: white;
            border: none;
            padding: 16px 32px;
            border-radius: 50px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 8px 30px rgba(56, 161, 105, 0.4);
            transition: transform 0.2s, box-shadow 0.2s;
            z-index: 1000;
        }}
        
        .print-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(56, 161, 105, 0.5);
        }}
        
        /* Print Styles - Professional PDF Output */
        @media print {{
            @page {{
                size: A4;
                margin: 10mm;
            }}
            
            body {{
                background: white !important;
                padding: 0 !important;
                font-size: 8pt !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            
            .container {{
                max-width: 100% !important;
                padding: 5px !important;
                margin: 0 !important;
            }}
            
            .header {{
                background: linear-gradient(135deg, #1a365d 0%, #2c5282 100%) !important;
                color: white !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            
            .header-left h1, .header-left p {{
                color: white !important;
            }}
            
            .company-name {{
                color: white !important;
            }}
            
            .period-badge {{
                background: var(--accent) !important;
                -webkit-print-color-adjust: exact !important;
            }}
            
            .card, .stat-card {{
                box-shadow: none;
                border: 1px solid #e2e8f0;
                page-break-inside: avoid;
            }}
            
            .stat-icon {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            
            .risk-badge {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            
            .kdv-item {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            
            .top-rank {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            
            .findings-table th {{
                background: #1a365d !important;
                color: white !important;
                -webkit-print-color-adjust: exact !important;
            }}
            
            .print-btn {{
                display: none !important;
            }}
            
            .footer {{
                color: #718096 !important;
                page-break-inside: avoid;
            }}
            
            [contenteditable="true"] {{
                outline: none !important;
            }}
            
            /* Page breaks */
            .card {{
                page-break-inside: avoid;
            }}
            
            .stats-grid {{
                page-break-inside: avoid;
            }}
            
            /* Chart section - scale down for print */
            canvas {{
                max-height: 150px !important;
            }}
            
            /* Scale everything to fit */
            .container {{
                transform: scale(0.85);
                transform-origin: top center;
            }}
            
            /* Section cards - smaller margins */
            .section-card {{
                margin: 10px !important;
                padding: 15px !important;
            }}
            
            /* Charts - hide canvas, show static images */
            .charts-section {{
                transform: none !important;
                margin-bottom: 20px !important;
            }}
            
            .charts-section canvas {{
                display: none !important;
            }}
            
            .chart-image {{
                display: block !important;
                max-width: 100% !important;
                height: auto !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- WRS Imperium Corporate Header -->
        <div style="background: #ffffff; border-radius: 12px; padding: 20px 30px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-bottom: 3px solid #7ba3b8;">
            <div style="display: flex; align-items: center; gap: 5px;">
                <div style="font-family: 'Times New Roman', Georgia, serif; font-size: 42px; font-weight: normal; color: #2d2d2d; letter-spacing: 1px;">WRS</div>
                <div style="font-family: 'Times New Roman', Georgia, serif; font-size: 42px; font-style: italic; font-weight: normal; color: #2d2d2d; letter-spacing: 1px;">imperium</div>
            </div>
            <div style="text-align: right; font-size: 12px; color: #555; line-height: 1.8;">
                <div>📍 Mücahitler Mah. 52092 Sk. Yasem İş Mrk. Şehitkamil/Gaziantep</div>
                <div>📞 +90 (342) 503 27 10 | ✉️ info@wrsimperium.com</div>
                <div>🌐 www.wrsimperium.com</div>
            </div>
        </div>
        
        <!-- YMM Denetçi Bilgileri (Düzenlenebilir) -->
        <div style="background: #ffffff; border-radius: 12px; padding: 15px 30px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 10px rgba(0,0,0,0.08); border-left: 5px solid #c9a227;">
            <div>
                <div contenteditable="true" style="font-size: 18px; font-weight: bold; color: #1e3a5f; min-width: 150px;">{ymm_name}</div>
                <div contenteditable="true" style="font-size: 13px; color: #666; min-width: 150px;">{ymm_title}</div>
            </div>
            <div style="text-align: center; padding: 0 30px;">
                <div style="font-size: 16px; font-weight: 600; color: #1e3a5f;">YMM DENETİM RAPORU</div>
                <div contenteditable="true" style="font-size: 12px; color: #888;">{executive_report.period or datetime.now().strftime("%B %Y")}</div>
            </div>
            <div style="text-align: right;">
                <div contenteditable="true" style="font-size: 16px; font-weight: 600; color: #1e3a5f; min-width: 150px;">{auditor_name}</div>
                <div contenteditable="true" style="font-size: 13px; color: #666; min-width: 150px;">{auditor_title}</div>
            </div>
        </div>
        
        
        <!-- KDV Summary (Beyanname/Mizan) -->
        <div class="card">
            <div class="card-header">
                <h2>📋 KDV Özeti {"(Beyanname)" if kdv_beyanname else "(Mizan)"}</h2>
            </div>
            <div style="display: grid; grid-template-columns: repeat({4 if kdv_beyanname else 3}, 1fr); gap: 15px; text-align: center;">
                <div class="kdv-item calculated">
                    <div class="kdv-label">Hesaplanan KDV (391)</div>
                    <div class="kdv-value">{executive_report.calculated_vat:,.2f} TL</div>
                </div>
                <div class="kdv-item deductible">
                    <div class="kdv-label">İndirilecek KDV (191)</div>
                    <div class="kdv-value">{executive_report.deductible_vat:,.2f} TL</div>
                </div>
                <div class="kdv-item payable">
                    <div class="kdv-label">Ödenecek KDV</div>
                    <div class="kdv-value">{executive_report.payable_vat:,.2f} TL</div>
                </div>
                {"<div class='kdv-item' style='border-left: 4px solid #3182ce;'><div class='kdv-label'>Sonraki Döneme Devreden</div><div class='kdv-value'>" + f"{kdv_beyanname.sonraki_doneme_devreden:,.2f} TL</div></div>" if kdv_beyanname else ""}
            </div>
        </div>
        
        <!-- Top 5 Lists - 2 Column Layout -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <!-- Left Column -->
            <div class="card">
                <div class="card-header">
                    <h2>🏭 Top 5 Satıcı (Alım)</h2>
                </div>
                <div class="card-body" style="padding: 0;">
                    <table style="width: 100%; border-collapse: collapse;">
                        {generate_top_table(executive_report.top_suppliers)}
                    </table>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h2>👥 Top 5 Müşteri (Satış)</h2>
                </div>
                <div class="card-body" style="padding: 0;">
                    <table style="width: 100%; border-collapse: collapse;">
                        {generate_top_table(executive_report.top_customers)}
                    </table>
                </div>
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div class="card">
                <div class="card-header">
                    <h2>📊 Top 5 KDV (191)</h2>
                </div>
                <div class="card-body" style="padding: 0;">
                    <table style="width: 100%; border-collapse: collapse;">
                        {generate_top_table(executive_report.top_kdv_entries)}
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Charts Section - Top 5 Bar Charts -->
    <div class="charts-section" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px;">
        <div style="background: white; border-radius: 12px; padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); height: 220px; position: relative;">
            <h3 style="color: #1a365d; margin-bottom: 10px; font-size: 14px;">📊 Top 5 Satış Dağılımı</h3>
            <div style="height: 180px; position: relative;">
                <canvas id="salesBarChart"></canvas>
            </div>
        </div>
        <div style="background: white; border-radius: 12px; padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); height: 220px; position: relative;">
            <h3 style="color: #1a365d; margin-bottom: 10px; font-size: 14px;">📊 Top 5 Alış Dağılımı</h3>
            <div style="height: 180px; position: relative;">
                <canvas id="purchaseBarChart"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        // Top 5 Sales Bar Chart
        const top5SalesData = {top5_sales_json};
        const totalSales = {executive_report.total_sales or 1};
        
        new Chart(document.getElementById('salesBarChart'), {{
            type: 'bar',
            data: {{
                labels: top5SalesData.map(d => d.name.substring(0, 15)),
                datasets: [{{
                    label: 'Satış (TL)',
                    data: top5SalesData.map(d => d.value),
                    backgroundColor: ['#38a169', '#3182ce', '#ed8936', '#805ad5', '#d69e2e'],
                    borderRadius: 4
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(ctx) {{
                                const pct = ((ctx.raw / totalSales) * 100).toFixed(1);
                                return ctx.raw.toLocaleString('tr-TR') + ' TL (%' + pct + ')';
                            }}
                        }}
                    }},
                    datalabels: {{
                        anchor: 'end',
                        align: 'end',
                        color: '#1a365d',
                        font: {{ weight: 'bold', size: 10 }},
                        formatter: function(value) {{
                            const pct = ((value / totalSales) * 100).toFixed(1);
                            return '%' + pct;
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        ticks: {{
                            callback: function(value) {{
                                return (value / 1000000).toFixed(1) + 'M';
                            }},
                            font: {{ size: 9 }}
                        }},
                        max: Math.max(...top5SalesData.map(d => d.value)) * 1.15
                    }},
                    y: {{
                        ticks: {{ font: {{ size: 9 }} }}
                    }}
                }}
            }},
            plugins: [ChartDataLabels]
        }});
        
        // Top 5 Purchases Bar Chart
        const top5PurchasesData = {top5_purchases_json};
        const totalPurchases = {executive_report.total_purchases or 1};
        
        new Chart(document.getElementById('purchaseBarChart'), {{
            type: 'bar',
            data: {{
                labels: top5PurchasesData.map(d => d.name.substring(0, 15)),
                datasets: [{{
                    label: 'Alış (TL)',
                    data: top5PurchasesData.map(d => d.value),
                    backgroundColor: ['#e53e3e', '#3182ce', '#ed8936', '#805ad5', '#d69e2e'],
                    borderRadius: 4
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(ctx) {{
                                const pct = ((ctx.raw / totalPurchases) * 100).toFixed(1);
                                return ctx.raw.toLocaleString('tr-TR') + ' TL (%' + pct + ')';
                            }}
                        }}
                    }},
                    datalabels: {{
                        anchor: 'end',
                        align: 'end',
                        color: '#1a365d',
                        font: {{ weight: 'bold', size: 10 }},
                        formatter: function(value) {{
                            const pct = ((value / totalPurchases) * 100).toFixed(1);
                            return '%' + pct;
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        ticks: {{
                            callback: function(value) {{
                                return (value / 1000000).toFixed(1) + 'M';
                            }},
                            font: {{ size: 9 }}
                        }},
                        max: Math.max(...top5PurchasesData.map(d => d.value)) * 1.15
                    }},
                    y: {{
                        ticks: {{ font: {{ size: 9 }} }}
                    }}
                }}
            }},
            plugins: [ChartDataLabels]
        }});
    </script>
    
    <!-- Tax Breakdown -->
    {tax_breakdown_html}
    
    <!-- Period Summary Card -->
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 25px; margin: 20px; color: white; text-align: center;">
        <div style="font-size: 14px; opacity: 0.9; margin-bottom: 10px;">📋 Denetim Özeti</div>
        <div style="font-size: 24px; font-weight: bold; margin-bottom: 15px;">{executive_report.period or datetime.now().strftime("%B %Y")}</div>
        <div style="display: flex; justify-content: center; gap: 40px; flex-wrap: wrap;">
            <div>
                <div style="font-size: 11px; opacity: 0.8;">Toplam Satış</div>
                <div style="font-size: 18px; font-weight: 600;">{executive_report.total_sales:,.0f} TL</div>
            </div>
            <div>
                <div style="font-size: 11px; opacity: 0.8;">Toplam Alış</div>
                <div style="font-size: 18px; font-weight: 600;">{executive_report.total_purchases:,.0f} TL</div>
            </div>
            <div>
                <div style="font-size: 11px; opacity: 0.8;">KDV Devreden</div>
                <div style="font-size: 18px; font-weight: 600;">{kdv_beyanname.sonraki_doneme_devreden:,.0f} TL</div>
            </div>
        </div>
    </div>
    
    <!-- Footer -->
    <div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">
        <p>Bu rapor e-Mutabakat Pro YMM Denetim Modülü tarafından otomatik oluşturulmuştur.</p>
        <p>© {datetime.now().year} WRS Imperium - Tüm hakları saklıdır.</p>
    </div>
    
    <!-- Print Button -->
    <button class="print-btn" onclick="prepareAndPrint()">📄 PDF Kaydet</button>
    
    <script>
        // Chart'ları PNG'ye çevir ve yazdır
        function prepareAndPrint() {{
            const charts = document.querySelectorAll('.charts-section canvas');
            let converted = 0;
            
            charts.forEach(canvas => {{
                // Zaten image varsa atla
                if (canvas.parentNode.querySelector('.chart-image')) {{
                    converted++;
                    if (converted === charts.length) {{
                        setTimeout(() => window.print(), 100);
                    }}
                    return;
                }}
                
                try {{
                    // Canvas'ı PNG'ye çevir
                    const dataUrl = canvas.toDataURL('image/png', 1.0);
                    
                    // Image elementi oluştur
                    const img = document.createElement('img');
                    img.src = dataUrl;
                    img.className = 'chart-image';
                    img.style.cssText = 'display:none; width:100%; max-height:200px; object-fit:contain;';
                    
                    // Canvas'ın yanına ekle
                    canvas.parentNode.appendChild(img);
                    
                    converted++;
                    if (converted === charts.length) {{
                        setTimeout(() => window.print(), 100);
                    }}
                }} catch(e) {{
                    console.error('Chart dönüştürme hatası:', e);
                    converted++;
                    if (converted === charts.length) {{
                        setTimeout(() => window.print(), 100);
                    }}
                }}
            }});
            
            // Chart yoksa direkt yazdır
            if (charts.length === 0) {{
                window.print();
            }}
        }}
    </script>
</body>
</html>'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path

def generate_top_table(items: list) -> str:
    """Top 5 tablo HTML'i oluştur - daha okunabilir format"""
    if not items:
        return '<tr><td colspan="3" style="color: #718096; text-align: center; padding: 30px;">Veri bulunamadı</td></tr>'
    
    rows = []
    for i, (name, value) in enumerate(items[:5], 1):
        # Firma adını kısalt
        display_name = name[:35] + "..." if len(name) > 35 else name
        rows.append(f'''
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 12px 15px; width: 40px; text-align: center;">
                    <span style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; 
                                 border-radius: 50%; width: 28px; height: 28px; display: inline-flex; 
                                 align-items: center; justify-content: center; font-weight: bold; font-size: 14px;">{i}</span>
                </td>
                <td style="padding: 12px 10px; font-weight: 500;">{display_name}</td>
                <td style="padding: 12px 15px; text-align: right; font-family: 'Consolas', monospace; 
                           font-weight: 600; color: #2d3748;">{value:,.2f} TL</td>
            </tr>
        ''')
    
    return ''.join(rows)


def generate_top_list(items: list) -> str:
    
    rows = []
    for i, (name, value) in enumerate(items[:5], 1):
        rows.append(f'''
            <li>
                <span class="top-rank">{i}</span>
                <span class="top-name">{name}</span>
                <span class="top-value">{value:,.2f} TL</span>
            </li>
        ''')
    return ''.join(rows)


def generate_findings_table(findings: List[AuditFinding]) -> str:
    """Bulgular tablosu HTML'i oluştur"""
    if not findings:
        return '<p style="text-align: center; color: #718096; padding: 40px;">✅ Herhangi bir denetim bulgusu tespit edilmedi.</p>'
    
    rows = []
    for finding in sorted(findings, key=lambda f: f.risk_level.value):
        risk_class = finding.risk_level.name.lower()
        rows.append(f'''
            <tr>
                <td><span class="risk-badge {risk_class}">{finding.risk_level.value}</span></td>
                <td><span class="account-code">{finding.account_code}</span></td>
                <td>{finding.finding_type.value}</td>
                <td>
                    {finding.description}
                    <div class="recommendation">💡 {finding.recommended_action}</div>
                </td>
                <td class="amount">{finding.amount:,.2f} TL</td>
            </tr>
        ''')
    
    return f'''
        <table class="findings-table">
            <thead>
                <tr>
                    <th style="width: 100px;">Risk</th>
                    <th style="width: 100px;">Hesap</th>
                    <th style="width: 140px;">Bulgu Türü</th>
                    <th>Açıklama & Öneri</th>
                    <th style="width: 140px; text-align: right;">Tutar</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
    '''


if __name__ == "__main__":
    # Test
    from ymm_audit import AuditFinding, ExecutiveReportData, RiskLevel, FindingType
    
    # Örnek bulgular
    test_findings = [
        AuditFinding(
            finding_type=FindingType.TERS_BAKIYE,
            risk_level=RiskLevel.CRITICAL,
            account_code="100",
            description="Kasa hesabı alacak bakiye veriyor: 50.000 TL",
            amount=50000,
            recommended_action="Kayıt dışı hasılat veya hatalı çıkış kontrol edilmeli"
        ),
        AuditFinding(
            finding_type=FindingType.ADAT,
            risk_level=RiskLevel.HIGH,
            account_code="131",
            description="Ortaklardan alacak: 250.000 TL. Transfer fiyatlandırması riski.",
            amount=250000,
            recommended_action="Aylık emsal faiz + %20 KDV'li fatura kesilmelidir"
        ),
    ]
    
    # Örnek yönetici raporu
    test_report = ExecutiveReportData(
        company_name="RAD TEKSTİL SAN. VE TİC. A.Ş.",
        period="Ekim 2025",
        total_sales=5000000,
        gross_profit=1500000,
        gross_margin=30.0,
        interest_expense=125000,
        cash_end=850000,
        current_ratio=1.85,
        calculated_vat=900000,
        deductible_vat=750000,
        payable_vat=150000
    )
    
    output = generate_ymm_html_report(test_findings, test_report)
    print(f"Rapor oluşturuldu: {output}")
