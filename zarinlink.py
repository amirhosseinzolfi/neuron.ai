import requests
from flask import Flask, request
from telegram import ParseMode

app = Flask(__name__)
MERCHANT_ID = "34a974c9-eb10-461f-a662-f530e2e80087"      # جایگزین با Merchant ID خودتان
BASE_URL = "https://t.me/blue_psychology_test_ai_bot"   # دامنه یا آدرس آی‌پی سرورِ شما

# این آبجکت در main ربات مقداردهی می‌شود تا دسترسی به bot فراهم باشد
telegram_bot = None  

def init_telegram_bot(bot):
    """برای ست کردن شیء bot تلگرام از فایل اصلی."""
    global telegram_bot
    telegram_bot = bot

def create_zarinlink(amount_toman: int, chat_id: int, description: str = "شارژ کیف‌پول") -> str:
    """
    amount_toman: مبلغ به تومان
    chat_id: آی‌دی چت برای callback
    برمی‌گرداند: URL لینک پرداخت زرین‌لینک
    """
    amount_rial = amount_toman * 10
    callback_url = f"{BASE_URL}/payment_callback?chat_id={chat_id}&amount={amount_toman}"
    payload = {
        "merchant_id": MERCHANT_ID,
        "amount": amount_rial,
        "description": description,
        "callback_url": callback_url
    }
    r = requests.post("https://api.zarinpal.com/pg/v4/payment/link",
                      json=payload, headers={"Content-Type": "application/json"})
    data = r.json()
    if data.get("data", {}).get("code") == 100:
        return data["data"]["link"]
    else:
        err = data.get("errors") or data
        raise RuntimeError(f"ZarinLink Error: {err}")

def verify_payment(authority: str) -> str:
    """
    authority: کد دریافت‌شده پس از پرداخت
    در صورت موفقیت ref_id (کد پیگیری) را برمی‌گرداند، در غیر این صورت None
    """
    payload = {"merchant_id": MERCHANT_ID, "authority": authority}
    r = requests.post("https://api.zarinpal.com/pg/v4/payment/verify",
                      json=payload, headers={"Content-Type": "application/json"})
    data = r.json()
    if data.get("data", {}).get("code") == 100:
        return data["data"]["ref_id"]
    return None

@app.route('/payment_callback')
def payment_callback():
    """وب‌هوک که زرین‌پال پس از پرداخت فراخوانی می‌کند."""
    authority = request.args.get('authority')
    status    = request.args.get('status')
    try:
        chat_id = int(request.args.get('chat_id'))
        amount  = int(request.args.get('amount'))
    except (TypeError, ValueError):
        return "Invalid parameters", 400

    if not telegram_bot:
        return "Bot not initialized", 500

    if status == 'OK':
        ref_id = verify_payment(authority)
        if ref_id:
            # آپدیت موجودی در DB
            from db import update_balance
            update_balance(chat_id, amount * 10)
            telegram_bot.send_message(
                chat_id=chat_id,
                text=f"✅ کیف‌پول شما به مبلغ {amount:,} تومان شارژ شد.\nکد پیگیری: `{ref_id}`",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            telegram_bot.send_message(chat_id=chat_id, text="❌ خطا در تأیید پرداخت.")
    else:
        telegram_bot.send_message(chat_id=chat_id, text="❌ پرداخت ناموفق یا لغو شد.")
    return "OK"

def run_flask(host='0.0.0.0', port=5000):
    """برای اجرای سرور Flask در یک Thread جداگانه."""
    app.run(host=host, port=port, debug=False, use_reloader=False)
