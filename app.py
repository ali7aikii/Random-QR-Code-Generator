import time
import hmac
import hashlib
import base64
from flask import Flask, request, session, redirect, jsonify

app = Flask(__name__)
app.secret_key = 'generate_a_random_secret_key_here'
QR_SECRET = b'my_qr_signature_secret'
TEACHER_PIN = "theopaque2793"

# 1. Base64 encode the form link to hide it from casual HTML inspection
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScFvW8MtbhXeZa9WZai_OXQIgtK1lfj_4qzmONzVDzhfzSlQw/viewform?embedded=true"
ENCODED_URL = base64.b64encode(FORM_URL.encode()).decode()

def get_client_ip():
    # Accurately extract the IP behind Render's reverse proxy
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]

# 2. HIDE THE DEFAULT URL (Blocks students from snooping)
@app.route('/')
def index():
    return "Access Denied.", 403

# 3. THE SECURE PROJECTOR SCREEN (Islamic UI & No Timer)
@app.route('/projector')
def projector():
    pin = request.args.get('pin')
    if pin != TEACHER_PIN:
        return "Unauthorized. Teacher access only.", 401
        
    return f'''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تسجيل الحضور</title>
        <!-- Import Arabic fonts from Google -->
        <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@700&family=Tajawal:wght@500&display=swap" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            body {{ 
                display: flex; 
                flex-direction: column; 
                align-items: center; 
                justify-content: center; 
                height: 100vh; 
                margin: 0;
                background-color: #fcfaf5; /* Warm off-white */
                background-image: url('https://www.transparenttextures.com/patterns/arabesque.png'); /* Subtle Islamic pattern */
                font-family: 'Tajawal', sans-serif; 
                color: #16402c; /* Deep Islamic green */
            }}
            .card {{
                text-align: center;
                background: rgba(255, 255, 255, 0.98);
                padding: 50px 70px;
                border-radius: 12px;
                border: 2px solid #d4af37; /* Metallic Gold */
                box-shadow: 0 8px 32px rgba(0,0,0,0.15);
            }}
            h1 {{ 
                font-family: 'Amiri', serif;
                font-size: 3.2em;
                margin-top: 0;
                margin-bottom: 5px;
                color: #16402c;
            }}
            p.subtitle {{
                font-size: 1.3em;
                color: #666;
                margin-bottom: 35px;
            }}
            #qrcode {{ 
                display: flex;
                justify-content: center;
                padding: 25px; 
                background: white; 
                border-radius: 12px; 
                border: 2px dashed #d4af37;
            }}
            #qrcode img {{
                margin: 0 auto;
            }}
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
            // The QR code itself is styled with the deep green color
            let qrcode = new QRCode(qrContainer, {{ 
                width: 380, 
                height: 380,
                colorDark : "#16402c", 
                colorLight : "#ffffff",
                correctLevel : QRCode.CorrectLevel.H
            }});
            
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
            // Silently updates the QR code every 6 seconds without a visual timer
            setInterval(updateQR, 6000); 
        </script>
    </body>
    </html>
    '''

# 4. SECURE TOKEN GENERATOR (Blocks hackers from making fake tokens)
@app.route('/generate')
def generate():
    pin = request.args.get('pin')
    if pin != TEACHER_PIN:
        return jsonify({{"error": "Unauthorized"}}), 401
        
    current_time = str(int(time.time()))
    token = hmac.new(QR_SECRET, current_time.encode(), hashlib.sha256).hexdigest()
    return jsonify({"t": current_time, "token": token})

@app.route('/scan')
def scan():
    token = request.args.get('token')
    timestamp = request.args.get('t')
    
    if not token or not timestamp:
        return "Invalid Request.", 400
        
    current_time = int(time.time())
    # 2. Strict 7-second TTL to kill WhatsApp photo sharing
    if current_time - int(timestamp) > 7:
        return "QR Code Expired. Please scan the newest code.", 403
        
    expected_token = hmac.new(QR_SECRET, timestamp.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_token, token):
        return "Signature mismatch.", 403
        
    # 3. Bind the session to the specific device fingerprint
    session['authorized'] = True
    session['expires'] = current_time + 120 
    session['ip'] = get_client_ip()
    session['user_agent'] = request.headers.get('User-Agent')
    
    return redirect('/form')

@app.route('/form')
def form():
    if not session.get('authorized') or time.time() > session.get('expires', 0):
        return "Session expired. Scan again.", 403
        
    # 4. Verify the device hasn't changed since the scan
    if session.get('ip') != get_client_ip() or session.get('user_agent') != request.headers.get('User-Agent'):
        return "Security policy violation: Device mismatch.", 403
        
    # 5. Inject the iframe dynamically to bypass simple source inspection
    return f'''
    <html>
      <body style="margin:0;padding:0;background:#fff;">
        <div id="container" style="width:100%; height:100vh;"></div>
        <script>
            // Decode the Base64 URL on the fly
            const secret = atob("{ENCODED_URL}");
            document.getElementById('container').innerHTML = 
                '<iframe src="' + secret + '" width="100%" height="100%" frameborder="0" marginheight="0" marginwidth="0"></iframe>';
        </script>
      </body>
    </html>
    '''