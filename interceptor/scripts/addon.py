import logging
from mitmproxy import websocket

# Setup basic logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("interceptor.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class StockbitInterceptor:
    def websocket_message(self, flow):
        # Get the latest message
        message = flow.messages[-1]
        
        # Determine origin and destination
        direction = "CLIENT -> SERVER" if message.from_client else "SERVER -> CLIENT"
        
        # Get handshake URL
        url = flow.handshake_flow.request.pretty_url
        
        # We target websocket connections to Stockbit streams
        if "stockbit" in url or "pubsub" in url or "stream" in url:
            payload = message.content
            is_text = message.is_text
            
            logging.info(f"[WS-FRAME] {direction} | URL: {url}")
            
            # Coba decode data
            data = None
            if is_text:
                text_content = payload.decode('utf-8', errors='ignore')
                logging.info(f"  Text Payload: {text_content}")
                try:
                    data = json.loads(text_content)
                except Exception:
                    data = text_content
            else:
                hex_data = payload.hex()
                logging.info(f"  Binary Payload (size: {len(payload)} bytes): {hex_data[:200]}")
                data = hex_data

            # Simpan secara terstruktur ke data/raw/websocket_stream.jsonl
            try:
                os.makedirs("data/raw", exist_ok=True)
                filepath = os.path.join("data/raw", "websocket_stream.jsonl")
                log_entry = {
                    "timestamp": time.time(),
                    "direction": direction,
                    "url": url,
                    "is_text": is_text,
                    "payload": data
                }
                with open(filepath, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception as e:
                logging.error(f"Gagal menulis log websocket: {e}")

    def response(self, flow):
        url = flow.request.pretty_url
        
        if "exodus.stockbit.com" in url:
            # Skip noise
            if any(x in url for x in ["/notification/count", "/images/", "/assets/"]):
                return

            try:
                response_text = flow.response.text
                if not response_text:
                    return
                
                # Parse JSON to confirm it is valid
                data = json.loads(response_text)
                
                # Save request headers containing authorization or cookie
                req_headers = dict(flow.request.headers)
                if "authorization" in req_headers or "cookie" in req_headers:
                    os.makedirs("data", exist_ok=True)
                    with open("data/session_headers.json", "w", encoding="utf-8") as h_file:
                        json.dump(req_headers, h_file, indent=2)
                
                # Determine safe filename based on URL path
                from urllib.parse import urlparse
                path_str = urlparse(url).path.strip("/")
                if not path_str:
                    path_str = "root"
                
                # Replace slashes and other characters that might be invalid in Windows filenames
                sanitized_filename = "".join(c if c.isalnum() or c in "-_" else "_" for c in path_str) + ".jsonl"
                
                os.makedirs("data/raw", exist_ok=True)
                filepath = os.path.join("data/raw", sanitized_filename)
                
                logging.info(f"[HTTP-INTERCEPT] URL: {url} -> {filepath}")
                
                with open(filepath, "a", encoding="utf-8") as f:
                    log_entry = {
                        "timestamp": time.time(),
                        "url": url,
                        "payload": data
                    }
                    f.write(json.dumps(log_entry) + "\n")
                    
            except Exception as e:
                # Quietly ignore non-JSON or parsing failures for other endpoints
                pass

# Import necessary modules
import json
import os
import time

addons = [
    StockbitInterceptor()
]

