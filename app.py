import time
import hmac
import hashlib
from flask import Flask, request, session, redirect

app = Flask(__name__)
app.secret_key = 'generate_a_random_secret_key_here'
QR_SECRET = b'my_qr_signature_secret'

@app.route('/scan')
def scan():
    token = request.args.get('token')
    timestamp = request.args.get('t')
    
    # 1. Check if the QR code is older than 10 seconds
    current_time = int(time.time())
    if current_time - int(timestamp) > 10:
        return "QR Code Expired. Please scan the newest one on the board.", 403
        
    # 2. Validate the cryptographic signature (prevents students from faking timestamps)
    expected_token = hmac.new(QR_SECRET, timestamp.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_token, token):
        return "Invalid QR Code.", 403
        
    # 3. Create a secure session cookie restricted to this specific phone
    session['authorized'] = True
    session['expires'] = current_time + 120 # Give them 2 minutes to submit the form
    
    return redirect('/form')

@app.route('/form')
def form():
    # Verify the user scanned a valid QR code in the last 2 minutes
    if not session.get('authorized') or time.time() > session.get('expires', 0):
        return "Session expired or unauthorized. Please scan the board again.", 403
        
    # Serve the Google Form inside a fullscreen iframe to hide the real Google URL
    return '''
    <html>
      <body style="margin:0;padding:0;">
        <iframe src="https://docs.google.com/forms/YOUR_FORM_LINK/viewform?embedded=true" 
                width="100%" height="100%" frameborder="0" marginheight="0" marginwidth="0">
            Loading…
        </iframe>
      </body>
    </html>
    '''