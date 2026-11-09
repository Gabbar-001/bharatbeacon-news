import os
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent))

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import config
from src.youtube_publisher import SECRETS_FILE, TOKEN_FILE, SCOPES, verify_channel, upload_video
from google_auth_oauthlib.flow import InstalledAppFlow

auth_code_received = None

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code_received
        query = parse_qs(urlparse(self.path).query)
        code = query.get("code")
        error = query.get("error")

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        if code:
            auth_code_received = code[0]
            html = """
            <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #0f172a; color: white;">
                <h1 style="color: #22c55e;">&#10004; Authorization Successful!</h1>
                <p style="font-size: 18px;">BharatBeacon is now connected to your YouTube channel.</p>
                <p style="color: #94a3b8;">You can close this tab and return to the application.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
        else:
            err_msg = error[0] if error else "Unknown error"
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #0f172a; color: white;">
                <h1 style="color: #ef4444;">&#10008; Authorization Failed</h1>
                <p style="font-size: 18px;">Error: {err_msg}</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        pass  # Suppress default server access logs

def run_oauth():
    print("\n" + "=" * 65)
    print("   BHARATBEACON — YOUTUBE ONE-CLICK AUTHENTICATION")
    print("=" * 65)

    if not SECRETS_FILE.exists():
        print(f"[X] Credentials file not found: {SECRETS_FILE}")
        return False

    port = 8080
    redirect_uri = f"http://localhost:{port}/"

    flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS_FILE), SCOPES)
    flow.redirect_uri = redirect_uri
    flow.oauth2session._state = None  # Prevent CSRF mismatch errors

    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

    print(f"\n[*] Starting local listener on {redirect_uri} ...")
    server = HTTPServer(("localhost", port), OAuthCallbackHandler)

    print("\n[AUTH URL] Open this link in your browser to sign in:")
    print(auth_url)
    print("\n[*] Opening default browser automatically...")
    sys.stdout.flush()

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    print("[*] Waiting for authorization in browser...")
    sys.stdout.flush()

    while auth_code_received is None:
        server.handle_request()

    server.server_close()
    print("\n[✓] Received authorization code from Google!")
    print("[*] Exchanging code for refresh token...")

    try:
        flow.fetch_token(code=auth_code_received)
        creds = flow.credentials
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        print(f"[✓] Token saved to: {TOKEN_FILE.name}")
    except Exception as e:
        print(f"[X] Failed to exchange token: {e}")
        return False

    # Verify channel details
    print("\n[*] Verifying channel connection...")
    info = verify_channel()
    if info:
        print("-" * 55)
        print(f"  Channel Title:   {info['title']}")
        print(f"  Channel ID:      {info['id']}")
        if info.get('customUrl'):
            print(f"  Channel Handle:  {info['customUrl']}")
        print(f"  Subscribers:     {info['subscribers']}")
        print(f"  Total Videos:    {info['videoCount']}")
        print("-" * 55)
        print(f"\n[✓] CONNECTED SUCCESSFULLY TO '{info['title']}'!")

    # Proceed to upload latest Shorts
    print("\n" + "=" * 65)
    print("   UPLOADING LATEST SHORTS TO YOUTUBE")
    print("=" * 65)
    import json
    shorts_files = list(config.SHORTS_OUTPUT_DIR.glob("SHORTS_*.mp4"))
    if shorts_files:
        latest = max(shorts_files, key=lambda f: f.stat().st_mtime)
        ts = latest.stem.replace("SHORTS_", "")
        meta_file = config.METADATA_DIR / f"METADATA_shorts_{ts}.json"
        if meta_file.exists():
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        else:
            meta = {
                "format": "shorts",
                "video_path": str(latest),
                "title": f"BharatBeacon Top 10 in 60s | India's Window to the World #Shorts",
                "description": f"BharatBeacon — India's Window to the World\n\n#Shorts #BharatBeacon",
                "tags": ["Shorts", "BharatBeacon", "India News"]
            }

        print(f"[*] Video:       {latest.name}")
        print(f"[*] Title:       {meta.get('title')}")
        print(f"[*] Visibility:  {config.YOUTUBE_PRIVACY.upper()}")
        print("\n[*] Uploading bytes to YouTube Data API...")
        sys.stdout.flush()

        vid = upload_video(meta, privacy_status=config.YOUTUBE_PRIVACY)
        if vid and vid != "staged_locally":
            print(f"\n[✓] PUBLISHED SUCCESSFULLY!")
            print(f"👉 Watch on YouTube: https://youtube.com/shorts/{vid}")
            return True
        else:
            print("[!] Upload returned without video ID.")
            return False

    return True

if __name__ == "__main__":
    run_oauth()
