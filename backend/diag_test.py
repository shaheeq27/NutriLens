import os
import httpx
from dotenv import load_dotenv

def run_test():
    load_dotenv(".env")
    key = os.getenv("GEMINI_API_KEY", "")
    
    print(f"Gemini key present: {'YES' if key else 'NO'}")
    if key:
        print(f"Gemini key prefix: {key[:6]}...")
    else:
        return
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={key}"
    payload = {
      "contents": [
        {
          "parts": [
            {
              "text": "Reply with exactly: GEMINI_OK"
            }
          ]
        }
      ]
    }
    
    try:
        resp = httpx.post(url, json=payload, timeout=20.0)
        print(f"\nHTTP Status: {resp.status_code}")
        print(f"Success: {'YES' if resp.status_code == 200 else 'NO'}")
        
        # Sanitize response
        sanitized_resp = resp.text.replace(key, "REDACTED")
        print(f"Sanitized Response Body: {sanitized_resp}")
    except Exception as e:
        sanitized_err = str(e).replace(key, "REDACTED")
        print(f"Error: {sanitized_err}")

if __name__ == "__main__":
    run_test()
