import time
import hmac
import hashlib
import base64
from flask import Flask, request, session, redirect, jsonify

app = Flask(__name__)
app.secret_key = 'generate_a_random_secret_key_here'
QR_SECRET = b'my_qr_signature_secret'
TEACHER_PIN = "theopaque2793"

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScFvW8MtbhXeZa9WZai_OXQIgtK1lfj_4qzmONzVDzhfzSlQw/viewform?embedded=true"
ENCODED_URL = base64.b64encode(FORM_URL.encode()).decode()

def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]

# --- UI HELPER FUNCTION FOR BILINGUAL ERROR SCREENS ---
def render_message(title_ar, title_en, msg_ar, msg_en, status_code=403):
    return f'''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title_ar} | {title_en}</title>
        <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@700&family=Tajawal:wght@500&display=swap" rel="stylesheet">
        <style>
            body {{ 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                min-height: 100vh; margin: 0; background-color: #fcfaf5; 
                background-image: url('https://www.transparenttextures.com/patterns/arabesque.png'); 
                font-family: 'Tajawal', sans-serif; text-align: center; padding: 20px; box-sizing: border-box;
            }}
            .card {{
                background: rgba(255, 255, 255, 0.98); padding: 40px 30px; border-radius: 12px;
                border: 2px solid #d4af37; box-shadow: 0 8px 32px rgba(0,0,0,0.15); 
                max-width: 500px; width: 100%; box-sizing: border-box;
            }}
            h1 {{ font-family: 'Amiri', serif; font-size: 2.2em; margin: 0 0 5px 0; color: #8b0000; }}
            h2 {{ font-family: 'Amiri', serif; font-size: 1.6em; margin: 0 0 20px 0; color: #8b0000; }}
            p.ar {{ font-size: 1.2em; color: #333; margin-bottom: 10px; line-height: 1.6; }}
            p.en {{ font-size: 1.1em; color: #555; margin-bottom: 0; line-height: 1.5; font-family: sans-serif; }}
            .divider {{ height: 1px; background: #eedc9a; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>{title_ar}</h1>
            <h2 dir="ltr">{title_en}</h2>
            <div class="divider"></div>
            <p class="ar">{msg_ar}</p>
            <p dir="ltr" class="en">{msg_en}</p>
        </div>
    </body>
    </html>
    ''', status_code

# 1. HIDE THE DEFAULT URL
@app.route('/')
def index():
    return render_message(
        "مرفوض الدخول", "Access Denied",
        "ليس لديك صلاحية للوصول إلى هذه الصفحة.",
        "You do not have permission to access this page."
    )

# 2. THE SECURE PROJECTOR SCREEN
@app.route('/projector')
def projector():
    pin = request.args.get('pin')
    if pin != TEACHER_PIN:
        return render_message(
            "غير مصرح", "Unauthorized",
            "وصول المعلم فقط. رمز المرور غير صحيح.",
            "Teacher access only. Invalid PIN.", 
            401
        )
        
    return f'''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تسجيل الحضور</title>
        <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@700&family=Tajawal:wght@500&display=swap" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            body {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; background-color: #fcfaf5; background-image: url('https://www.transparenttextures.com/patterns/arabesque.png'); font-family: 'Tajawal', sans-serif; color: #16402c; }}
            .card {{ text-align: center; background: rgba(255, 255, 255, 0.98); padding: 50px 70px; border-radius: 12px; border: 2px solid #d4af37; box-shadow: 0 8px 32px rgba(0,0,0,0.15); }}
            h1 {{ font-family: 'Amiri', serif; font-size: 3.2em; margin-top: 0; margin-bottom: 5px; color: #16402c; }}
            p.subtitle {{ font-size: 1.3em; color: #666; margin-bottom: 35px; }}
            #qrcode {{ display: flex; justify-content: center; padding: 25px; background: white; border-radius: 12px; border: 2px dashed #d4af37; }}
            #qrcode img {{ margin: 0 auto; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>امسح الرمز للتسجيل</h1>
            <p class="subtitle">يرجى توجيه كاميرا الهاتف نحو الرمز أعلاه</p>
            <div id="qrcode"></div>
        </div>
        <script>
            const qrContainer = document.getElementById("qrcode");
            let qrcode = new QRCode(qrContainer, {{ width: 380, height: 380, colorDark : "#16402c", colorLight : "#ffffff", correctLevel : QRCode.CorrectLevel.H }});
            
            async function updateQR() {{
                try {{
                    const response = await fetch('/generate?pin={TEACHER_PIN}');
                    if (!response.ok) return;
                    const data = await response.json();
                    const scanUrl = window.location.origin + "/scan?t=" + data.t + "&token=" + data.token;
                    qrcode.makeCode(scanUrl);
                }} catch (error) {{
                    console.error("Connection error");
                }}
            }}
            updateQR();
            setInterval(updateQR, 6000); 
        </script>
    </body>
    </html>
    '''

# 3. SECURE TOKEN GENERATOR
@app.route('/generate')
def generate():
    pin = request.args.get('pin')
    if pin != TEACHER_PIN:
        return jsonify({"error": "Unauthorized"}), 401
        
    current_time = str(int(time.time()))
    token = hmac.new(QR_SECRET, current_time.encode(), hashlib.sha256).hexdigest()
    return jsonify({"t": current_time, "token": token})

# 4. SCAN VALIDATION & EXPIRATION LOGIC
@app.route('/scan')
def scan():
    token = request.args.get('token')
    timestamp = request.args.get('t')
    
    if not token or not timestamp:
        return render_message(
            "طلب غير صالح", "Invalid Request",
            "الرابط الذي قمت بمسحه غير مكتمل.",
            "The link you scanned is incomplete.", 400
        )
        
    current_time = int(time.time())
    
    if current_time - int(timestamp) > 7:
        return render_message(
            "انتهت صلاحية الرمز", "QR Code Expired",
            "لقد استغرق المسح وقتاً طويلاً. يرجى مسح الرمز الجديد من الشاشة.",
            "Scanning took too long. Please scan the newest code from the screen."
        )
        
    expected_token = hmac.new(QR_SECRET, timestamp.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_token, token):
        return render_message(
            "رمز غير صالح", "Invalid Code",
            "تم التلاعب بهذا الرمز أو أنه غير صحيح.",
            "This code has been tampered with or is incorrect."
        )
        
    session['authorized'] = True
    session['expires'] = current_time + 120 
    session['ip'] = get_client_ip()
    session['user_agent'] = request.headers.get('User-Agent')
    
    return redirect('/form')

# 5. DEVICE SECURITY CHECK & FORM INJECTION
@app.route('/form')
def form():
    if not session.get('authorized') or time.time() > session.get('expires', 0):
        return render_message(
            "انتهت الجلسة", "Session Expired",
            "انتهت مهلة التسجيل. يرجى مسح الرمز مرة أخرى.",
            "Registration timeout. Please scan the code again."
        )
        
    if session.get('ip') != get_client_ip() or session.get('user_agent') != request.headers.get('User-Agent'):
        return render_message(
            "خطأ أمني", "Security Error",
            "تم رصد تغيير في الجهاز أو الشبكة أثناء التسجيل. يرجى إعادة مسح الرمز.",
            "Device or network change detected during registration. Please rescan."
        )
        
    return f'''
    <html>
      <head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
      <body style="margin:0;padding:0;background:#fff;">
        <div id="container" style="width:100%; height:100vh;"></div>
        <script>
            const secret = atob("{ENCODED_URL}");
            document.getElementById('container').innerHTML = 
                '<iframe src="' + secret + '" width="100%" height="100%" frameborder="0" marginheight="0" marginwidth="0"></iframe>';
        </script>
      </body>
    </html>
    '''