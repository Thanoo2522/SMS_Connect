from flask import Flask, request, jsonify
import os
import requests
from dotenv import load_dotenv

# โหลด environment variables
load_dotenv()

# Vonage API key/secret จาก environment
VONAGE_API_KEY = os.getenv("VONAGE_API_KEY")
VONAGE_API_SECRET = os.getenv("VONAGE_API_SECRET")

# Firebase Realtime Database base URL เช่น
# https://your-project-id.firebaseio.com
FIREBASE_URL = os.getenv("FIREBASE_URL")

app = Flask(__name__)


def is_valid_token(token: str) -> bool:
    """
    ตรวจสอบ token จาก Firebase (อยู่ใต้ node /tokens)
    """
    try:
        url = f"{FIREBASE_URL}/tokens/{token}.json"
        res = requests.get(url, timeout=5)
        # token ถูกต้องถ้ามี object ใน Firebase
        if res.status_code == 200 and res.json() is not None:
            return True
        return False
    except Exception as e:
        print("Firebase error:", e)
        return False



def get_phone_from_token(token: str) -> str:
    """
    ดึงหมายเลขโทรศัพท์จาก Firebase ตาม token
    """
    try:
        url = f"{FIREBASE_URL}/tokens/{token}/phone.json"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json()
        return None
    except Exception as e:
        print("Firebase error:", e)
        return None


@app.route("/send-sms", methods=["POST"])
def send_sms():
    try:
        data = request.json
        token = data.get("token")
        to_number = data.get("to")
        message = data.get("message")

        # 1. ตรวจสอบ token จาก Firebase
        if not token or not is_valid_token(token):
            return jsonify({"status": "error", "message": "Invalid token"}), 401

        # 2. ถ้า client ไม่ส่ง to_number → ดึงจาก Firebase
        if not to_number:
            to_number = get_phone_from_token(token)

        # 3. ตรวจสอบข้อมูลเบื้องต้น
        if not to_number or not message:
            return jsonify({"status": "error", "message": "Missing 'to' or 'message'"}), 400

        # 4. ส่ง SMS ผ่าน Vonage
        url = "https://rest.nexmo.com/sms/json"
        payload = {
            "api_key": VONAGE_API_KEY,
            "api_secret": VONAGE_API_SECRET,
            "to": to_number,
            "from": "VonageSMS",
            "text": message,
        }

        response = requests.post(url, data=payload, timeout=10)
        result = response.json()

        return jsonify({
            "status": "success",
            "vonage_response": result
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "SMS Render Server is running"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
