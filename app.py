from flask import Flask, request, jsonify
import os
import requests
from dotenv import load_dotenv

# โหลด environment variables
load_dotenv()

VONAGE_API_KEY = os.getenv("VONAGE_API_KEY")
VONAGE_API_SECRET = os.getenv("VONAGE_API_SECRET")
FIREBASE_URL = os.getenv("FIREBASE_URL")  # เช่น https://smshubvonage-default-rtdb.asia-southeast1.firebasedatabase.app

app = Flask(__name__)

def get_user_from_firebase(token: str):
    """ดึงข้อมูล user จาก Firebase ตาม token"""
    try:
        url = f"{FIREBASE_URL}/token/{token}.json"
        res = requests.get(url, timeout=5)
        if res.status_code == 200 and res.json() is not None:
            return res.json()
        return None
    except Exception as e:
        print("Firebase error:", e)
        return None

@app.route("/send-sms", methods=["POST"])
def send_sms():
    try:
        # ตรวจสอบ API Key/Secret
        client_key = request.headers.get("X-API-KEY")
        client_secret = request.headers.get("X-API-SECRET")
        if client_key != VONAGE_API_KEY or client_secret != VONAGE_API_SECRET:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        data = request.json
        token = data.get("token")
        phone = data.get("phone")
        message = data.get("message")

        if not token or not message:
            return jsonify({"status": "error", "message": "Missing 'token' or 'message'"}), 400

        # ตรวจสอบ token กับ Firebase
        user = get_user_from_firebase(token)
        if not user:
            return jsonify({"status": "error", "message": "Invalid token"}), 403

        # ตรวจ quota
        quota = user.get("quota", 0)
        used = user.get("used", 0)
        if used >= quota:
            return jsonify({"status": "error", "message": "Quota exceeded"}), 403

        # ถ้า client ไม่ส่ง phone → ดึงจาก Firebase
        if not phone:
            phone = user.get("phone")
        if not phone:
            return jsonify({"status": "error", "message": "Missing phone number"}), 400

        # ส่ง SMS ผ่าน Vonage
        vonage_url = "https://rest.nexmo.com/sms/json" 
        payload = {
            "api_key": VONAGE_API_KEY,
            "api_secret": VONAGE_API_SECRET,
            "to": phone,
            "from": "VonageSMS",
            "text": message
        }

        response = requests.post(vonage_url, data=payload, timeout=10)
        result = response.json()

        # อัปเดต used ใน Firebase
        new_used = used + 1
        requests.patch(f"{FIREBASE_URL}/tokens/{token}.json", json={"used": new_used})

        return jsonify({"status": "success", "vonage_response": result})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "SMS Render Server is running"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
