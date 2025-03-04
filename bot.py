import re
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction, FlexSendMessage, ImageSendMessage
)
import requests

LINE_CHANNEL_ACCESS_TOKEN = "jgtJGulnykjI52MKGg4NckOb8Gr8vo1dkuTEOtpwfVZzrF6N5YtlPUwSACumpuCtqBiW6pUOxwT9knOTAp497Nb41hK6lAccSEBhOmvRqOqn+L85BqayUvg5dVUsGkWCZ+enNPiiEydWtrYVxcG2qQdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "c7bd0640701fa6fca53ded72467a26c4"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

PREDICTION_API_URL = "https://bot-api-clothing.onrender.com/predict"

user_sessions = {}

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Line Chatbot for Penguin Prediction is Running."

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_input = event.message.text.strip().lower()

    if user_input in ["เริ่มต้น"]:
        reply_text = (
            "? คำนวณไซส์เสื้อของคุณง่ายๆ ในไม่กี่ขั้นตอน!\n"
            "✨ เพียงตอบคำถามสั้นๆ แล้วรับคำแนะนำไซส์ที่เหมาะกับคุณ\n"
            "\n"
            "? วิธีใช้งาน:\n"
            "1️⃣ กรอกข้อมูลพื้นฐาน ได้แก่ อายุ, ส่วนสูง และน้ำหนัก\n"
            "2️⃣ รอระบบคำนวณไซส์ที่เหมาะสม\n"
            "3️⃣ รับคำแนะนำไซส์เสื้อที่ตรงกับรูปร่างของคุณ\n"
            "\n"
            "? หากต้องการเริ่มใหม่ พิมพ์ 'ยกเลิก' ได้เลย!\n\n"
            "? เริ่มเลย! กรุณากรอกอายุของคุณ (ปี) เช่น 25"
        )
        user_sessions[user_id] = {"step": 1, "data": {}}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return

    if user_input in ["ถูกต้อง", "ยืนยันข้อมูล"]:
        if user_id not in user_sessions or "data" not in user_sessions[user_id]:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="ไม่พบข้อมูล กรุณาเริ่มใหม่"))
            return

        user_data = user_sessions[user_id]["data"]

        try:
            response = requests.post(PREDICTION_API_URL, json=user_data)
            response.raise_for_status()  # ตรวจสอบสถานะของการตอบกลับ
            result = response.json()
            if "prediction" in result:
                reply_text = f"ผลลัพธ์: {result['prediction']}"
            else:
                reply_text = f"Error: {result.get('error', 'ไม่สามารถคำนวณได้')}"
        except requests.exceptions.HTTPError as http_err:
            reply_text = f"HTTP error occurred: {http_err}"
        except requests.exceptions.RequestException as req_err:
            reply_text = f"Request error occurred: {req_err}"
        except ValueError:
            reply_text = "Invalid response received from server."
        finally:
            del user_sessions[user_id]
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
            return

    if user_input == "ยกเลิก":
        del user_sessions[user_id]
        reply_text = "ข้อมูลถูกยกเลิกแล้ว หากต้องการเริ่มใหม่ให้กดปุ่ม เริ่มต้น ที่เมนู"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return

    if user_id in user_sessions:
        session = user_sessions[user_id]
        step = session["step"]

        try:
            if step in [1, 2, 3]:
                if not re.match(r'^\d+(\.\d+)?$', user_input):
                    reply_text = "กรุณากรอกเฉพาะค่าตัวเลขที่เป็นบวก เช่น 25"
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
                    return

                value = float(user_input)

                if step == 1:
                    session["data"]["age"] = value
                    reply_text = "กรุณากรอกส่วนสูงของคุณ (cm) เช่น 170"
                elif step == 2:
                    session["data"]["height"] = value
                    reply_text = "กรุณากรอกน้ำหนักของคุณ (kg) เช่น 65"
                elif step == 3:
                    session["data"]["weight"] = value
                    summary_flex = create_summary_flex(session["data"])
                    line_bot_api.reply_message(event.reply_token, summary_flex)
                    return

                session["step"] += 1
        
        except ValueError:
            reply_text = "กรุณากรอกค่าตัวเลขที่ถูกต้อง"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
            return

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return


def create_summary_flex(user_data):
    flex_message = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#E1F5FE",
            "cornerRadius": "md",
            "paddingAll": "lg",
            "contents": [
                {
                    "type": "text",
                    "text": "ข้อมูลส่วนตัวของคุณ",
                    "weight": "bold",
                    "size": "xl",
                    "color": "#01579B",
                    "align": "center"
                },
                {
                    "type": "separator",
                    "margin": "sm",
                    "color": "#B3E5FC"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "sm",
                    "spacing": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"? อายุ: {user_data['age']} ปี",
                            "size": "md",
                            "color": "#1E88E5"
                        },
                        {
                            "type": "text",
                            "text": f"? ส่วนสูง: {user_data['height']} ซม.",
                            "size": "md",
                            "color": "#1E88E5"
                        },
                        {
                            "type": "text",
                            "text": f"? น้ำหนัก: {user_data['weight']} กก.",
                            "size": "md",
                            "color": "#1E88E5"
                        },
                    ]
                },
                {
                    "type": "separator",
                    "margin": "sm",
                    "color": "#B3E5FC"
                },
                {
                    "type": "text",
                    "text": "ข้อมูลของคุณถูกต้องหรือไม่?",
                    "margin": "sm",
                    "size": "md",
                    "color": "#01579B",
                    "align": "center",
                    "weight": "bold"
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "backgroundColor": "#B3E5FC",
            "cornerRadius": "md",
            "paddingAll": "md",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#0288D1",
                    "action": {
                        "type": "message",
                        "label": "✅ ถูกต้อง",
                        "text": "ยืนยันข้อมูล"
                    },
                    "height": "sm"
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "color": "#78909C",
                    "action": {
                        "type": "message",
                        "label": "⛔ ยกเลิก",
                        "text": "ยกเลิก"
                    },
                    "height": "sm"
                }
            ]
        }
    }
    return FlexSendMessage(alt_text="สรุปข้อมูลของคุณ", contents=flex_message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
