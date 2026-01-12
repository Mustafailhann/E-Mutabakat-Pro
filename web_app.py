"""
e-Mutabakat Pro - Web Uygulaması
Flask tabanlı web arayüzü (Login sistemi ile)
"""

import os
import sys
import json
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path
from functools import wraps

# Flask bağımlılıkları
try:
    from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session, Response
    from werkzeug.utils import secure_filename
except ImportError:
    print("Flask yüklü değil. Yükleniyor...")
    os.system("pip install flask")
    from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session
    from werkzeug.utils import secure_filename

# Flask-Login
try:
    from flask_login import LoginManager, login_user, logout_user, login_required, current_user
except ImportError:
    print("Flask-Login yüklü değil. Yükleniyor...")
    os.system("pip install flask-login")
    from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# Auth modülleri
from auth import authenticate_user, load_user
from database import init_db, get_all_users, create_user, delete_user

# Mevcut modülleri import et
import kdv_iade_listesi
import kdv_web_editor
import satis_fatura_listesi
import satis_web_editor
import pdf_invoice_reader
import gib_viewer
import export_gib_excel

# Audit logging
try:
    import audit_logger
except ImportError:
    audit_logger = None

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Konfigürasyon
app.config['SECRET_KEY'] = 'e-mutabakat-pro-secret-key-2024'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.getcwd(), 'output')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

# Upload klasörü oluştur
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Flask-Login ayarları
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def user_loader(user_id):
    return load_user(user_id)

# İzin verilen dosya uzantıları
ALLOWED_EXTENSIONS = {'zip', 'rar', 'xml', 'pdf', 'ZIP', 'RAR', 'XML', 'PDF'}

# Geçici dosya deposu (oturum bazlı)
uploaded_files = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {ext.lower() for ext in ALLOWED_EXTENSIONS}


def clear_uploaded_files():
    """Yüklenen dosyaları temizle (global listeyi ve disk dosyalarını)"""
    global uploaded_files
    
    # Diskteki dosyaları sil
    for f in uploaded_files:
        try:
            if os.path.exists(f['path']):
                os.remove(f['path'])
        except:
            pass
    
    # Listeyi temizle
    uploaded_files = []
    
    # uploads klasöründeki tüm dosyaları temizle (opsiyonel - daha kapsamlı temizlik)
    try:
        upload_folder = app.config.get('UPLOAD_FOLDER', '')
        if upload_folder and os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                filepath = os.path.join(upload_folder, filename)
                if os.path.isfile(filepath):
                    try:
                        os.remove(filepath)
                    except:
                        pass
            # xml_files alt klasörünü de temizle
            xml_folder = os.path.join(upload_folder, 'xml_files')
            if os.path.exists(xml_folder):
                for filename in os.listdir(xml_folder):
                    filepath = os.path.join(xml_folder, filename)
                    if os.path.isfile(filepath):
                        try:
                            os.remove(filepath)
                        except:
                            pass
            # gib_html alt klasörünü de temizle
            gib_folder = os.path.join(upload_folder, 'gib_html')
            if os.path.exists(gib_folder):
                for filename in os.listdir(gib_folder):
                    filepath = os.path.join(gib_folder, filename)
                    if os.path.isfile(filepath):
                        try:
                            os.remove(filepath)
                        except:
                            pass
    except:
        pass


def admin_required(f):
    """Admin yetkisi gerektiren sayfalar için decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# ================== AUTH ROUTES ==================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Giriş sayfası"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        ip_address = request.remote_addr
        
        # Rate limit kontrolü
        if audit_logger:
            allowed, remaining = audit_logger.check_rate_limit(ip_address, username)
            if not allowed:
                error = f'Çok fazla başarısız deneme. {remaining} saniye bekleyin.'
                audit_logger.log_rate_limit_exceeded(ip_address, username)
                return render_template('login.html', error=error)
        
        user = authenticate_user(username, password)
        if user:
            # Giriş başarılı - önceki kullanıcının dosyalarını temizle
            clear_uploaded_files()
            login_user(user, remember=remember)
            
            # Audit log
            if audit_logger:
                audit_logger.log_login_success(username, ip_address, request.user_agent.string)
            
            return redirect(url_for('index'))
        else:
            # Başarısız giriş log
            if audit_logger:
                locked, info = audit_logger.log_login_failure(username, ip_address)
                if locked:
                    error = f'Hesap geçici olarak kilitlendi. {info} saniye bekleyin.'
                else:
                    error = f'Geçersiz kullanıcı adı veya şifre. ({info} deneme kaldı)'
            else:
                error = 'Geçersiz kullanıcı adı veya şifre'
    
    return render_template('login.html', error=error)


@app.route('/register', methods=['POST'])
def register():
    """Kayıt sayfası - sadece çalışanlar için"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    password2 = request.form.get('password2', '')
    
    # Validasyon
    if not username or not password:
        return render_template('login.html', error='Kullanıcı adı ve şifre gerekli')
    
    if len(password) < 4:
        return render_template('login.html', error='Şifre en az 4 karakter olmalı')
    
    if password != password2:
        return render_template('login.html', error='Şifreler eşleşmiyor')
    
    # Kullanıcı oluştur (user rolü ile)
    success, message = create_user(username, password, 'user')
    
    if success:
        return render_template('login.html', success=f'Kayıt başarılı! "{username}" kullanıcısı ile giriş yapabilirsiniz.')
    else:
        return render_template('login.html', error=message)


@app.route('/logout')
@login_required
def logout():
    """Çıkış - dosyaları da temizle"""
    # Audit log
    if audit_logger:
        audit_logger.log_logout(current_user.username, request.remote_addr)
    
    clear_uploaded_files()
    logout_user()
    return redirect(url_for('login'))


# ================== PROFILE ROUTES ==================

@app.route('/profile')
@login_required
def profile():
    """Profil sayfası"""
    from database import get_user_by_id
    
    # Kullanıcı bilgilerini al
    user_data = get_user_by_id(current_user.id)
    created_at = user_data['created_at'] if user_data else 'Bilinmiyor'
    last_login = user_data['last_login'] if user_data and user_data['last_login'] else 'Hiç'
    
    # Aktivite loglarını al
    activities = []
    session_count = 0
    activity_count = 0
    
    if audit_logger:
        # Bu kullanıcıya ait aktiviteleri filtrele
        all_logs = audit_logger.get_recent_logins(limit=100)
        for log in all_logs:
            if log.get('username') == current_user.username:
                # Tarih formatını düzenle
                timestamp = log.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        timestamp = dt.strftime('%d.%m.%Y %H:%M')
                    except:
                        pass
                
                activity_type = 'login' if log.get('event') == 'LOGIN_SUCCESS' else 'logout'
                if 'PASSWORD' in log.get('event', ''):
                    activity_type = 'password'
                
                activities.append({
                    'event': log.get('event'),
                    'timestamp': timestamp,
                    'ip': log.get('ip', 'Bilinmiyor'),
                    'type': activity_type
                })
                
                if log.get('event') == 'LOGIN_SUCCESS':
                    session_count += 1
                activity_count += 1
        
        # Son 10 aktiviteyi göster
        activities = activities[:10]
    
    return render_template('profile.html', 
                          activities=activities,
                          session_count=session_count,
                          activity_count=activity_count,
                          created_at=created_at,
                          last_login=last_login)


@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Şifre değiştirme API'si"""
    from auth import verify_password
    from database import update_user_password, get_user_by_id
    
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    # Validasyon
    if not current_password or not new_password or not confirm_password:
        return render_template('profile.html', error='Tüm alanları doldurun')
    
    if len(new_password) < 4:
        return render_template('profile.html', error='Yeni şifre en az 4 karakter olmalı')
    
    if new_password != confirm_password:
        return render_template('profile.html', error='Yeni şifreler eşleşmiyor')
    
    # Mevcut şifreyi doğrula
    user_data = get_user_by_id(current_user.id)
    if not verify_password(current_password, user_data['password_hash']):
        return render_template('profile.html', error='Mevcut şifre yanlış')
    
    # Şifreyi güncelle
    update_user_password(current_user.id, new_password)
    return render_template('profile.html', success='Şifreniz başarıyla değiştirildi!')


# ================== ADMIN ROUTES ==================

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    """Admin paneli"""
    users = get_all_users()
    
    # Tüm kullanıcı aktivitelerini al
    all_activities = []
    if audit_logger:
        # Giriş/Çıkış logları
        login_logs = audit_logger.get_recent_logins(limit=50)
        for log in login_logs:
            timestamp = log.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime('%d.%m.%Y %H:%M:%S')
                except:
                    pass
            
            all_activities.append({
                'event': log.get('event'),
                'username': log.get('username'),
                'timestamp': timestamp,
                'ip': log.get('ip') or log.get('ip_address', 'Bilinmiyor'),
                'user_agent': log.get('user_agent', '')[:50] if log.get('user_agent') else ''
            })
        
        # Güvenlik logları
        security_logs = audit_logger.get_failed_logins(limit=20)
        for log in security_logs:
            timestamp = log.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime('%d.%m.%Y %H:%M:%S')
                except:
                    pass
            
            all_activities.append({
                'event': log.get('event'),
                'username': log.get('username'),
                'timestamp': timestamp,
                'ip': log.get('ip') or log.get('ip_address', 'Bilinmiyor'),
                'reason': log.get('reason', ''),
                'locked': log.get('locked', False)
            })
        
        # Tarihe göre sırala (en yeni başta)
        all_activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        all_activities = all_activities[:30]  # Son 30 aktivite
    
    return render_template('admin.html', 
                          users=users, 
                          activities=all_activities,
                          message=request.args.get('message'), 
                          error=request.args.get('error'))


@app.route('/admin/add-user', methods=['POST'])
@login_required
@admin_required
def admin_add_user():
    """Yeni kullanıcı ekle"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'user')
    
    if not username or not password:
        return redirect(url_for('admin_panel', error='Kullanıcı adı ve şifre gerekli'))
    
    if len(password) < 4:
        return redirect(url_for('admin_panel', error='Şifre en az 4 karakter olmalı'))
    
    success, message = create_user(username, password, role)
    
    if success:
        return redirect(url_for('admin_panel', message=f'Kullanıcı "{username}" oluşturuldu'))
    else:
        return redirect(url_for('admin_panel', error=message))


@app.route('/admin/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    """Kullanıcı sil"""
    delete_user(user_id)
    return redirect(url_for('admin_panel', message='Kullanıcı silindi'))


# ================== MAIN ROUTES ==================

@app.route('/')
@login_required
def index():
    """Ana sayfa"""
    return render_template('index.html', files=uploaded_files)


@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Dosya yükleme endpoint'i"""
    if 'files[]' not in request.files:
        return jsonify({'success': False, 'error': 'Dosya seçilmedi'})
    
    files = request.files.getlist('files[]')
    uploaded = []
    
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Benzersiz isim oluştur
            unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            file_info = {
                'name': filename,
                'path': filepath,
                'size': os.path.getsize(filepath),
                'uploaded': datetime.now().strftime('%H:%M:%S')
            }
            uploaded_files.append(file_info)
            uploaded.append(file_info)
    
    return jsonify({
        'success': True, 
        'files': uploaded,
        'total': len(uploaded_files)
    })


@app.route('/clear-files', methods=['POST'])
@login_required
def clear_files():
    """Dosya listesini temizle"""
    global uploaded_files
    
    # Dosyaları sil
    for f in uploaded_files:
        try:
            if os.path.exists(f['path']):
                os.remove(f['path'])
        except:
            pass
    
    uploaded_files = []
    return jsonify({'success': True})


@app.route('/get-files')
@login_required
def get_files():
    """Yüklü dosyaları listele"""
    return jsonify({'files': uploaded_files})


@app.route('/generate-kdv-excel', methods=['POST'])
@login_required
def generate_kdv_excel():
    """KDV İade Listesi Excel oluştur"""
    try:
        if not uploaded_files:
            return jsonify({'success': False, 'error': 'Dosya yüklenmedi'})
        
        all_invoices = []
        logs = []
        
        for file_info in uploaded_files:
            filepath = file_info['path']
            filename = file_info['name']
            
            if filepath.lower().endswith('.zip'):
                logs.append(f"📂 Yükleniyor: {filename}")
                try:
                    invoices = kdv_iade_listesi.load_invoices_from_zip(filepath)
                    all_invoices.extend(invoices)
                    logs.append(f"  ✅ {len(invoices)} fatura bulundu")
                except Exception as e:
                    logs.append(f"  ❌ Hata: {str(e)}")
            
            elif filepath.lower().endswith('.xml'):
                logs.append(f"📄 Yükleniyor: {filename}")
                try:
                    inv_data = kdv_iade_listesi.load_invoice_from_xml(filepath)
                    if inv_data:
                        all_invoices.append(inv_data)
                        logs.append(f"  ✅ 1 fatura bulundu")
                except Exception as e:
                    logs.append(f"  ❌ Hata: {str(e)}")
            
            elif filepath.lower().endswith('.pdf'):
                logs.append(f"📑 Yükleniyor (PDF): {filename}")
                try:
                    inv_list = pdf_invoice_reader.smart_extract_invoices_from_pdf(filepath)
                    if inv_list:
                        all_invoices.extend(inv_list)
                        logs.append(f"  ✅ {len(inv_list)} fatura bulundu")
                except Exception as e:
                    logs.append(f"  ❌ Hata: {str(e)}")
        
        if not all_invoices:
            return jsonify({
                'success': False, 
                'error': 'Hiç fatura bulunamadı!',
                'logs': logs
            })
        
        # Excel oluştur
        output_file = os.path.join(app.config['OUTPUT_FOLDER'], 'Indirilecek_KDV_Listesi.xlsx')
        kdv_iade_listesi.generate_kdv_listesi_excel(all_invoices, output_file)
        
        logs.append(f"\n✅ Excel oluşturuldu: {len(all_invoices)} fatura")
        
        return jsonify({
            'success': True,
            'file': '/download/kdv-excel',
            'filename': 'Indirilecek_KDV_Listesi.xlsx',
            'invoice_count': len(all_invoices),
            'logs': logs
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/download/kdv-excel')
@login_required
def download_kdv_excel():
    """KDV Excel dosyasını indir"""
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], 'Indirilecek_KDV_Listesi.xlsx')
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name='Indirilecek_KDV_Listesi.xlsx')
    return "Dosya bulunamadı", 404


@app.route('/api/export/gib-ozet', methods=['POST'])
@login_required
def export_gib_ozet():
    """GİB Özet Liste Excel dosyası oluştur ve indir"""
    try:
        data = request.get_json()
        invoices = data.get('invoices', []) if data else []
        
        if not invoices:
            return jsonify({'success': False, 'error': 'Fatura verisi bulunamadı'}), 400
        
        # Excel oluştur
        output_stream = export_gib_excel.generate_gib_ozet_excel(invoices)
        
        return send_file(
            output_stream,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='gib_indirilecek_kdv_ozet.xlsx'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/gib-kalemli', methods=['POST'])
@login_required
def export_gib_kalemli():
    """GİB Kalem Bazlı Excel dosyası oluştur ve indir"""
    try:
        data = request.get_json()
        invoices = data.get('invoices', []) if data else []
        
        if not invoices:
            return jsonify({'success': False, 'error': 'Fatura verisi bulunamadı'}), 400
        
        # Excel oluştur
        output_stream = export_gib_excel.generate_gib_kalemli_excel(invoices)
        
        return send_file(
            output_stream,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='gib_indirilecek_kdv_kalemli.xlsx'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/generate-kdv-web', methods=['POST'])
@login_required
def generate_kdv_web():
    """KDV Web Düzenleyici oluştur"""
    try:
        own_vkn = request.json.get('vkn', '').strip() if request.json else ''
        
        if not uploaded_files:
            return jsonify({'success': False, 'error': 'Dosya yüklenmedi'})
        
        all_invoices = []
        logs = []
        
        for file_info in uploaded_files:
            filepath = file_info['path']
            filename = file_info['name']
            
            if filepath.lower().endswith('.zip'):
                logs.append(f"📂 Yükleniyor: {filename}")
                try:
                    invoices = kdv_iade_listesi.load_invoices_from_zip(filepath)
                    all_invoices.extend(invoices)
                    logs.append(f"  ✅ {len(invoices)} fatura bulundu")
                except Exception as e:
                    logs.append(f"  ❌ Hata: {str(e)}")
            
            elif filepath.lower().endswith('.xml'):
                logs.append(f"📄 Yükleniyor: {filename}")
                try:
                    inv_data = kdv_iade_listesi.load_invoice_from_xml(filepath)
                    if inv_data:
                        all_invoices.append(inv_data)
                        logs.append(f"  ✅ 1 fatura bulundu")
                except Exception as e:
                    logs.append(f"  ❌ Hata: {str(e)}")
            
            elif filepath.lower().endswith('.pdf'):
                logs.append(f"📑 Yükleniyor (PDF): {filename}")
                try:
                    inv_list = pdf_invoice_reader.smart_extract_invoices_from_pdf(filepath)
                    if inv_list:
                        all_invoices.extend(inv_list)
                        logs.append(f"  ✅ {len(inv_list)} fatura bulundu")
                except Exception as e:
                    logs.append(f"  ❌ Hata: {str(e)}")
        
        # VKN filtresi
        if own_vkn:
            original_count = len(all_invoices)
            all_invoices = [inv for inv in all_invoices if inv.get('satici_vkn', '') != own_vkn]
            filtered = original_count - len(all_invoices)
            if filtered > 0:
                logs.append(f"🔍 {filtered} satış faturası hariç tutuldu")
        
        if not all_invoices:
            return jsonify({
                'success': False, 
                'error': 'Hiç alış faturası bulunamadı!',
                'logs': logs
            })
        
        # Web editor HTML oluştur
        output_file = os.path.join(app.config['OUTPUT_FOLDER'], 'KDV_Listesi_Editor.html')
        kdv_web_editor.generate_kdv_web_report(all_invoices, output_file)
        
        logs.append(f"\n✅ Web düzenleyici oluşturuldu: {len(all_invoices)} fatura")
        
        return jsonify({
            'success': True,
            'url': '/view/kdv-editor',
            'invoice_count': len(all_invoices),
            'logs': logs
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/view/kdv-editor')
@login_required
def view_kdv_editor():
    """KDV Editor HTML'i görüntüle"""
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], 'KDV_Listesi_Editor.html')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return "Dosya bulunamadı", 404


@app.route('/generate-satis-web', methods=['POST'])
@login_required
def generate_satis_web():
    """Satış Fatura Listesi Web oluştur"""
    try:
        own_vkn = request.json.get('vkn', '').strip() if request.json else ''
        
        if not own_vkn:
            return jsonify({'success': False, 'error': 'VKN gerekli!'})
        
        if not uploaded_files:
            return jsonify({'success': False, 'error': 'Dosya yüklenmedi'})
        
        all_invoices = []
        logs = []
        
        for file_info in uploaded_files:
            filepath = file_info['path']
            filename = file_info['name']
            
            if filepath.lower().endswith('.zip'):
                logs.append(f"📂 Yükleniyor: {filename}")
                try:
                    invs = satis_fatura_listesi.load_sales_invoices_from_zip(filepath, own_vkn=own_vkn)
                    all_invoices.extend(invs)
                    logs.append(f"  ✅ {len(invs)} satış faturası bulundu")
                except Exception as e:
                    logs.append(f"  ❌ Hata: {str(e)}")
        
        if not all_invoices:
            return jsonify({
                'success': False, 
                'error': 'Hiç satış faturası bulunamadı! VKN doğru mu?',
                'logs': logs
            })
        
        # Web editor HTML oluştur
        output_file = os.path.join(app.config['OUTPUT_FOLDER'], 'Satis_Listesi_Editor.html')
        satis_web_editor.generate_satis_web_report(all_invoices, output_file)
        
        logs.append(f"\n✅ Satış listesi oluşturuldu: {len(all_invoices)} fatura")
        
        return jsonify({
            'success': True,
            'url': '/view/satis-editor',
            'invoice_count': len(all_invoices),
            'logs': logs
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/view/satis-editor')
@login_required
def view_satis_editor():
    """Satış Editor HTML'i görüntüle"""
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], 'Satis_Listesi_Editor.html')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return "Dosya bulunamadı", 404


@app.route('/gib_viewer_extracted/<path:filename>')
def serve_xslt_file(filename):
    """XSLT dosyalarını servis et"""
    xslt_dir = os.path.join(os.getcwd(), 'gib_viewer_extracted')
    filepath = os.path.join(xslt_dir, filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='text/xml')
    return "XSLT dosyası bulunamadı", 404


@app.route('/uploads/<path:filename>')
@login_required
def serve_uploaded_file(filename):
    """Yüklenen dosyaları görüntüle (PDF, XML, vb.)"""
    print(f"[DEBUG] serve_uploaded_file çağrıldı - filename: {filename}")
    try:
        # Önce uploads klasöründe ara
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f"[DEBUG] İlk deneme path: {filepath}, exists: {os.path.exists(filepath)}")
        
        # Eğer uploads'ta yoksa xml_files klasöründe ara
        if not os.path.exists(filepath):
            xml_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'xml_files')
            filepath = os.path.join(xml_dir, filename)
            print(f"[DEBUG] İkinci deneme path: {filepath}, exists: {os.path.exists(filepath)}")
        
        # Eğer hala yoksa gib_html klasöründe ara
        if not os.path.exists(filepath):
            gib_html_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'gib_html')
            filepath = os.path.join(gib_html_dir, filename)
        
        # Path traversal saldırılarını önle
        base_folders = [
            os.path.abspath(app.config['UPLOAD_FOLDER']),
            os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], 'xml_files')),
            os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], 'gib_html'))
        ]
        
        abs_filepath = os.path.abspath(filepath)
        if not any(abs_filepath.startswith(base) for base in base_folders):
            return "Yetkisiz erişim", 403
        
        if os.path.exists(filepath):
            # PDF dosyaları için inline görüntüle, diğerleri için indir
            if filepath.lower().endswith('.pdf'):
                return send_file(filepath, mimetype='application/pdf')
            elif filepath.lower().endswith('.xml'):
                # XML dosyalarını GIB formatında görüntüle
                print(f"[DEBUG] XML dosyası işleniyor: {filepath}")
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        xml_content = f.read()
                    print(f"[DEBUG] XML içeriği okundu, boyut: {len(xml_content)} karakter")
                    
                    # Enhanced gib_viewer kullan (HTML + metadata döndürür)
                    html_output, metadata = gib_viewer.transform_invoice_to_html(xml_content)
                    print(f"[DEBUG] HTML'e dönüştürüldü, boyut: {len(html_output)} karakter") 
                    
                    # Metadata'yı log'la
                    if metadata:
                        print(f"[DEBUG] Fatura metadata: ETTN={metadata.get('ettn')}, "
                              f"No={metadata.get('invoice_no')}, "
                              f"Tutar={metadata.get('payable_amount')} {metadata.get('currency')}")
                    
                    response = Response(html_output, mimetype='text/html; charset=utf-8')
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                    return response
                except Exception as xml_error:
                    # Hata durumunda ham XML göster
                    import traceback
                    print(f"[ERROR] XSLT dönüşüm hatası: {xml_error}")
                    print(traceback.format_exc())
                    return send_file(filepath, mimetype='application/xml')
            elif filepath.lower().endswith('.html'):
                return send_file(filepath, mimetype='text/html')
            else:
                return send_file(filepath, as_attachment=True)
        
        return "Dosya bulunamadı", 404
    except Exception as e:
        return f"Hata: {str(e)}", 500


@app.route('/api/xml-metadata/<path:filename>')
@login_required
def get_xml_metadata(filename):
    """XML faturasından metadata bilgilerini JSON olarak döndür"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            xml_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'xml_files')
            filepath = os.path.join(xml_dir, filename)
        
        if not os.path.exists(filepath) or not filepath.lower().endswith('.xml'):
            return jsonify({'error': 'XML dosyası bulunamadı'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Enhanced gib_viewer ile metadata çıkar
        _, metadata = gib_viewer.transform_invoice_to_html(xml_content)
        
        return jsonify({'success': True, 'metadata': metadata})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



# ================== MAIN ==================

def open_browser():
    """Tarayıcıda aç"""
    webbrowser.open('http://127.0.0.1:5000')


if __name__ == '__main__':
    # Veritabanını başlat
    init_db()
    
    print("\n" + "="*50)
    print("  e-Mutabakat Pro - Web Uygulaması")
    print("  http://127.0.0.1:5000")
    print("  Giriş için IT yöneticinize başvurun")
    print("="*50 + "\n")
    
    # Tarayıcıyı otomatik aç (1 saniye gecikmeyle)
    import threading
    threading.Timer(1.5, open_browser).start()
    
    # 0.0.0.0 ile tüm network interface'lerden erişim
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
