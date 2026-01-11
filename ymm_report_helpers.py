# -*- coding: utf-8 -*-
"""
YMM Report Helper Functions
Yönetici raporu için yardımcı fonksiyonlar
"""

def calculate_financial_ratios(mizan):
    """
    Mizan'dan finansal oranları hesapla
    
    Returns:
        dict: Finansal oranlar
    """
    # Dönen Varlıklar (1xx hesaplar) - Tüm borç bakiyeleri
    current_assets = sum(
        acc.debit for code, acc in mizan.accounts.items() 
        if code.startswith('1')
    )
    
    # Kısa Vadeli Borçlar (3xx hesaplar) - Tüm alacak bakiyeleri
    current_liabilities = sum(
        acc.credit for code, acc in mizan.accounts.items() 
        if code.startswith('3')
    )
    
    # Stoklar (15x hesaplar)
    inventory = sum(
        acc.debit for code, acc in mizan.accounts.items() 
        if code.startswith('15')
    )
    
    # Özkaynak (5xx hesaplar) - Alacak bakiyeli
    equity = sum(
        acc.credit for code, acc in mizan.accounts.items() 
        if code.startswith('5')
    )
    
    # Toplam Borçlar (3xx + 4xx) - Alacak bakiyeli
    total_liabilities = sum(
        acc.credit for code, acc in mizan.accounts.items() 
        if (code.startswith('3') or code.startswith('4'))
    )
    
    # Oranları hesapla
    ratios = {
        'current_ratio': current_assets / current_liabilities if current_liabilities > 0 else 0,
        'quick_ratio': (current_assets - inventory) / current_liabilities if current_liabilities > 0 else 0,
        'debt_to_equity': total_liabilities / equity if equity > 0 else 0,
        'current_assets': current_assets,
        'current_liabilities': current_liabilities,
        'equity': equity,
        'total_liabilities': total_liabilities
    }
    
    return ratios


def generate_tax_breakdown(mizan, kdv_beyanname=None, muhtasar_beyanname=None):
    """
    Vergi dökümünü oluştur
    
    Returns:
        dict: Vergi türlerine göre tutarlar
    """
    taxes = {
        'kdv_payable': 0,
        'kdv_deferred': 0,
        'income_tax_withholding': 0,
        'sgk_premiums': 0,
        'stamp_tax': 0,
        'other_taxes': 0
    }
    
    # KDV Beyanname'den
    if kdv_beyanname:
        taxes['kdv_payable'] = kdv_beyanname.odenecek_kdv or 0
        taxes['kdv_deferred'] = kdv_beyanname.sonraki_doneme_devreden or 0
    
    # Muhtasar'dan (varsa)
    if muhtasar_beyanname:
        taxes['income_tax_withholding'] = getattr(muhtasar_beyanname, 'toplam_stopaj', 0) or 0
        taxes['sgk_premiums'] = getattr(muhtasar_beyanname, 'toplam_sgk', 0) or 0
    
    # Mizan'dan diğer vergiler - BALANCE kullan (360/361 alacak bakiyeli)
    for code, acc in mizan.accounts.items():
        if code.startswith('360'):
            # Damga vergisi hariç
            if 'damga' in acc.name.lower():
                continue
            elif 'kdv' not in acc.name.lower() and 'sgk' not in acc.name.lower():
                # 360 hesapları ALACAK bakiyeli - negatif balance
                taxes['other_taxes'] += abs(acc.balance)
        elif code.startswith('361'):
            if muhtasar_beyanname is None:
                taxes['sgk_premiums'] += abs(acc.balance)
    
    return taxes


def generate_audit_statement_html(company_name, period):
    """
    Denetim beyanı HTML'i oluştur
    """
    return f'''
    <div class="audit-statement">
        <div class="company-info">
            <h2 style="color: #1a365d; margin-bottom: 8px; font-size: 24px;">{company_name}</h2>
            <p style="color: #718096; font-size: 16px; margin-bottom: 16px;">{period} Dönemi</p>
        </div>
        <div class="audit-declaration" style="background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%); 
                                              padding: 20px; border-left: 4px solid #3182ce; border-radius: 8px; 
                                              margin: 20px 0;">
            <p style="font-size: 15px; line-height: 1.6; color: #2d3748; font-weight: 500;">
                <strong>{period}</strong> dönemi <strong>Yeminli Mali Müşavirliğimizce</strong> denetlenmiş olup, 
                bu rapor denetim bulgularını ve mali durumu özetlemektedir.
            </p>
        </div>
    </div>
    '''


def generate_tax_breakdown_html(taxes):
    """
    Vergi dökümü tablo HTML'i - Sadeleştirilmiş (KDV + SGK)
    """
    
    return f'''
    <div class="section-card">
        <h3 style="color: #1a365d; margin-bottom: 20px; font-size: 20px; 
                   border-bottom: 3px solid #3182ce; padding-bottom: 10px;">
            📊 Vergi Dökümü
        </h3>
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background: #f7fafc; border-bottom: 2px solid #e2e8f0;">
                    <th style="padding: 12px; text-align: left; color: #2d3748;">Vergi Türü</th>
                    <th style="padding: 12px; text-align: right; color: #2d3748;">Tutar</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid #e2e8f0; background: #fafafa;">
                    <td style="padding: 12px;">KDV (Sonraki Döneme Devreden)</td>
                    <td style="padding: 12px; text-align: right; font-family: 'Consolas', monospace; color: #38a169; font-weight: 600;">
                        {taxes['kdv_deferred']:,.2f} TL
                    </td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 12px;">SGK Primleri</td>
                    <td style="padding: 12px; text-align: right; font-family: 'Consolas', monospace; font-weight: 600;">
                        {taxes['sgk_premiums']:,.2f} TL
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    '''


def generate_financial_ratios_html(ratios):
    """
    Finansal oranlar kartları HTML'i
    """
    # Cari oran değerlendirmesi
    current_ratio_status = "✅ İyi" if ratios['current_ratio'] >= 1.5 else ("⚠️ Orta" if ratios['current_ratio'] >= 1.0 else "🔴 Düşük")
    current_ratio_color = "#38a169" if ratios['current_ratio'] >= 1.5 else ("#d69e2e" if ratios['current_ratio'] >= 1.0 else "#e53e3e")
    
    # Likidite değerlendirmesi
    quick_ratio_status = "✅ İyi" if ratios['quick_ratio'] >= 1.0 else ("⚠️ Düşük" if ratios['quick_ratio'] >= 0.5 else "🔴 Kritik")
    quick_ratio_color = "#38a169" if ratios['quick_ratio'] >= 1.0 else ("#d69e2e" if ratios['quick_ratio'] >= 0.5 else "#e53e3e")
    
    # Borç/Özkaynak değerlendirmesi
    debt_eq_status = "✅ Düşük" if ratios['debt_to_equity'] <= 1.0 else ("⚠️ Orta" if ratios['debt_to_equity'] <= 2.0 else "🔴 Yüksek")
    debt_eq_color = "#38a169" if ratios['debt_to_equity'] <= 1.0 else ("#d69e2e" if ratios['debt_to_equity'] <= 2.0 else "#e53e3e")
    
    return f'''
    <div class="section-card">
        <h3 style="color: #1a365d; margin-bottom: 20px; font-size: 20px; 
                   border-bottom: 3px solid #3182ce; padding-bottom: 10px;">
            📈 Finansal Oranlar
        </h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
            <!-- Cari Oran -->
            <div style="background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%); 
                        padding: 20px; border-radius: 12px; border-left: 4px solid {current_ratio_color};">
                <div style="color: #718096; font-size: 13px; margin-bottom: 8px;">Cari Oran</div>
                <div style="font-size: 28px; font-weight: 700; color: {current_ratio_color}; margin-bottom: 8px;">
                    {ratios['current_ratio']:.2f}
                </div>
                <div style="font-size: 12px; color: #4a5568;">{current_ratio_status}</div>
                <div style="font-size: 11px; color: #a0aec0; margin-top: 8px;">
                    Dönen Varlıklar / KV Borçlar
                </div>
            </div>
            
            <!-- Likidite Oranı -->
            <div style="background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%); 
                        padding: 20px; border-radius: 12px; border-left: 4px solid {quick_ratio_color};">
                <div style="color: #718096; font-size: 13px; margin-bottom: 8px;">Likidite Oranı</div>
                <div style="font-size: 28px; font-weight: 700; color: {quick_ratio_color}; margin-bottom: 8px;">
                    {ratios['quick_ratio']:.2f}
                </div>
                <div style="font-size: 12px; color: #4a5568;">{quick_ratio_status}</div>
                <div style="font-size: 11px; color: #a0aec0; margin-top: 8px;">
                    (Dönen Varl. - Stoklar) / KV Borçlar
                </div>
            </div>
            
            <!-- Borç/Özkaynak -->
            <div style="background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%); 
                        padding: 20px; border-radius: 12px; border-left: 4px solid {debt_eq_color};">
                <div style="color: #718096; font-size: 13px; margin-bottom: 8px;">Borç / Özkaynak</div>
                <div style="font-size: 28px; font-weight: 700; color: {debt_eq_color}; margin-bottom: 8px;">
                    {ratios['debt_to_equity']:.2f}
                </div>
                <div style="font-size: 12px; color: #4a5568;">{debt_eq_status}</div>
                <div style="font-size: 11px; color: #a0aec0; margin-top: 8px;">
                    Toplam Borçlar / Özkaynak
                </div>
            </div>
        </div>
    </div>
    '''
