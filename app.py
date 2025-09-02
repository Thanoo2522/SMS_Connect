from flask import Flask, request, jsonify
import os
import requests
from dotenv import load_dotenv

# โหลด .env (สำหรับ local dev) 
load_dotenv()

# ------------------- Config -------------------
VONAGE_API_KEY = os.getenv("VONAGE_API_KEY")
VONAGE_API_SECRET = os.getenv("VONAGE_API_SECRET")
VONAGE_SENDER = os.getenv("VONAGE_SENDER", "test1")
FIREBASE_URL = os.getenv("FIREBASE_URL")  # ตัวอย่าง: https://smshubvonage-default-rtdb.asia-southeast1.firebasedatabase.app/token

# Client API Key/Secret สำหรับตรวจสอบ header
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

app = Flask(__name__)


print("Vonage API Key:", VONAGE_API_KEY)
print("Vonage API Secret:", VONAGE_API_SECRET)
print("Vonage Sender:", VONAGE_SENDER)
# ------------------- Helper -------------------

def get_user_from_firebase(token: str):
    """ดึงข้อมูล user จาก Firebase ตาม token"""
    try:
        url = f"{FIREBASE_URL}/{token}.json"
        res = requests.get(url, timeout=5)
        if res.status_code == 200 and res.json() is not None:
            return res.json()
        return None
    except Exception as e:
        print("Firebase error:", e)
        return None

def send_sms_via_vonage(to_number: str, message: str):
    url = "https://rest.nexmo.com/sms/json" 
    payload = {
        "api_key": VONAGE_API_KEY,
        "api_secret": VONAGE_API_SECRET,
        "to": to_number,
        "from": VONAGE_SENDER,
        "text": message
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ------------------- Routes -------------------

@app.route("/send-sms", methods=["POST"])
def send_sms():
    try:
        # ตรวจสอบ API Key/Secret ของ client
        client_key = request.headers.get("X-API-KEY")
        client_secret = request.headers.get("X-API-SECRET")
        if client_key != API_KEY or client_secret != API_SECRET:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        data = request.json
        token = data.get("token")
        to_number = data.get("phone")  # เบอร์โทร
        message = data.get("message")  # ข้อความ

        if not token or not message:
            return jsonify({"status": "error", "message": "Missing 'token' or 'message'"}), 400

        # ตรวจสอบ token กับ Firebase
        user = get_user_from_firebase(token)
        if not user:
            return jsonify({"status": "error", "message": "Invalid token"}), 403

        # ถ้า client ไม่ส่ง phone → ดึงจาก Firebase
        if not to_number:
            to_number = user.get("phone")
        if not to_number:
            return jsonify({"status": "error", "message": "Missing phone number"}), 400

        # ส่ง SMS ผ่าน Vonage
        result = send_sms_via_vonage(to_number, message)

        return jsonify({"status": "success", "vonage_response": result})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "SMS Render Server is running"})

# ------------------- Main -------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
