import time
import hmac
import hashlib
from flask import Flask, request, session, redirect, jsonify

app = Flask(__name__)
app.secret_key = 'generate_a_random_secret_key_here'
QR_SECRET = b'my_qr_signature_secret'

# Set your secret Teacher PIN here
TEACHER_PIN = "7788" 

# 1. HIDE THE DEFAULT URL (Blocks students from snooping)
@app.route('/')
def index():
    return "Access Denied.", 403

# 2. THE SECURE PROJECTOR SCREEN (Requires PIN)
@app.route('/projector')
def projector():
    # Check if the URL contains the correct PIN
    pin = request.args.get('pin')
    if pin != TEACHER_PIN:
        return "Unauthorized. Teacher access only.", 401
        
    # Note the f''' here and the doubled {{ }} for CSS/JS
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>QR Attendance</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            body {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: sans-serif; background-color: #f4f4f9;}}
            #qrcode {{ margin-top: 20px; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; }}
            #timer {{ color: #e74c3c; }}
        </style>
    </head>
    <body>
        <h1>Scan for Attendance</h1>
        <h2>New code in: <span id="timer">10</span>s</h2>
        <div id="qrcode"></div>
        
        <script>
            const qrContainer = document.getElementById("qrcode");
            let qrcode = new QRCode(qrContainer, {{ width: 300, height: 300 }});
            let countdownInterval;
            
            async function updateQR() {{
                // Securely pass the PIN to the generator
                const response = await fetch('/generate?pin={TEACHER_PIN}');
                if (!response.ok) return; // Stop if unauthorized
                
                const data = await response.json();
                const scanUrl = window.location.origin + "/scan?t=" + data.t + "&token=" + data.token;
                qrcode.makeCode(scanUrl);
                
                let timeLeft = 10;
                document.getElementById("timer").innerText = timeLeft;
                
                if (countdownInterval) clearInterval(countdownInterval);
                countdownInterval = setInterval(() => {{
                    timeLeft -= 1;
                    document.getElementById("timer").innerText = timeLeft;
                }}, 1000);
            }}

            updateQR();
            setInterval(updateQR, 10000); 
        </script>
    </body>
    </html>
    '''

# 3. SECURE TOKEN GENERATOR (Blocks hackers from making fake tokens)
@app.route('/generate')
def generate():
    pin = request.args.get('pin')
    if pin != TEACHER_PIN:
        return jsonify({{"error": "Unauthorized"}}), 401
        
    current_time = str(int(time.time()))
    token = hmac.new(QR_SECRET, current_time.encode(), hashlib.sha256).hexdigest()
    return jsonify({"t": current_time, "token": token})


# 3. SCAN VALIDATION (When a student scans the QR code)
@app.route('/scan')
def scan():
    token = request.args.get('token')
    timestamp = request.args.get('t')
    
    if not token or not timestamp:
        return "Invalid QR Code.", 400
        
    current_time = int(time.time())
    if current_time - int(timestamp) > 10:
        return "QR Code Expired. Please scan the newest one on the board.", 403
        
    expected_token = hmac.new(QR_SECRET, timestamp.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_token, token):
        return "Invalid QR Code.", 403
        
    session['authorized'] = True
    session['expires'] = current_time + 120 # Give them 2 minutes to submit
    
    return redirect('/form')

# 4. THE SECURE FORM
@app.route('/form')
def form():
    if not session.get('authorized') or time.time() > session.get('expires', 0):
        return "Session expired or unauthorized. Please scan the board again.", 403
        
    return '''
    <html>
      <body style="margin:0;padding:0;">
        <iframe src="https://docs.google.com/forms/d/e/1FAIpQLScFvW8MtbhXeZa9WZai_OXQIgtK1lfj_4qzmONzVDzhfzSlQw/viewform?embedded=true" 
                width="100%" height="100%" frameborder="0" marginheight="0" marginwidth="0">
            Loading…
        </iframe>
      </body>
    </html>
    '''