import time
import hmac
import hashlib
from flask import Flask, request, session, redirect, jsonify

app = Flask(__name__)
app.secret_key = 'generate_a_random_secret_key_here'
QR_SECRET = b'my_qr_signature_secret'

# 1. THE PROJECTOR SCREEN (This fixes the 404 error)
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>QR Attendance</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            body { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: sans-serif; background-color: #f4f4f9;}
            #qrcode { margin-top: 20px; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            #timer { color: #e74c3c; }
        </style>
    </head>
    <body>
        <h1>Scan for Attendance</h1>
        <h2>New code in: <span id="timer">10</span>s</h2>
        <div id="qrcode"></div>
        
        <script>
            const qrContainer = document.getElementById("qrcode");
            let qrcode = new QRCode(qrContainer, { width: 300, height: 300 });
            let countdownInterval;
            
            async function updateQR() {
                // Fetch new secure token from the server
                const response = await fetch('/generate');
                const data = await response.json();
                
                // Build the URL the student will scan
                const scanUrl = window.location.origin + "/scan?t=" + data.t + "&token=" + data.token;
                qrcode.makeCode(scanUrl);
                
                // Reset timer
                let timeLeft = 10;
                document.getElementById("timer").innerText = timeLeft;
                
                if (countdownInterval) clearInterval(countdownInterval);
                countdownInterval = setInterval(() => {
                    timeLeft -= 1;
                    document.getElementById("timer").innerText = timeLeft;
                }, 1000);
            }

            updateQR();
            setInterval(updateQR, 10000); // Fetch a new QR code every 10 seconds
        </script>
    </body>
    </html>
    '''

# 2. GENERATE NEW TOKENS (Used by the projector screen)
@app.route('/generate')
def generate():
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