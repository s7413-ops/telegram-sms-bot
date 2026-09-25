import logging
import asyncio
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==================== الإعدادات والمفاتيح ====================
BOT_TOKEN = "8998915706:AAGJhnybWTWxwS9rjDCOzeVyfikXDTuXNRg"
SIM5_API_KEY = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4MjE4ODQxMzgsImlhdCI6MTc5MDM0ODEzOCwicmF5IjoiNDQ3NjcwOWJjZTUyNTk5YWVkNzlkMmQ0MDAxYmU4YWQiLCJzdWIiOjQ1NzA0MjB9.z34sNIVDnk2nG-p7rJG_Vf3PG3aOsa9jjp-Wfdj1r_0i9mAZj4ToCPAjZZH3wpqoy92_eZfbDYBPFXqhOB7GBzTl2nAjcHktw9TMhKzwciIuZQ_-_OdXLVvdK54knRmpI-7UDKc5E_DHcW8-o1RVMSSzTebE7wjS8w_A6sgZRozTS-wXI_si6aoU9YjTnwx6hkmSpnlCAtH-moU1ZrS6BI7thgJXLlZRxG0aLxyT0uKrxEsD1Fix27JTRfnWXIJyrGdB2y2akIgN6WK1rvxTCC7NOe27-_Lccy0AidGI9v_5chuDD6dmXZ1-K8OxiCqxJwmaEpljhvn5udXQaRfRCA"
SUPABASE_URL = "https://bpgerrfvmqoyktdwgftb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJwZ2VycmZ2bXFveWt0ZHdnZnRiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAzNDMxNTMsImV4cCI6MjEwNTkxOTE1M30.-uaHOc3TMSXlC8keT7G4VkmaYnEALPQ_tr4F1bnshes"
ADMIN_ID = 482878621  # ضع هنا معرف التلجرام الخاص بك (Telegram ID)
# ==========================================================

headers_spb = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

headers_5sim = {
    "Authorization": f"Bearer {SIM5_API_KEY}",
    "Accept": "application/json"
}


# قائمة الخدمات والدول للبدء
SERVICES = {
    "wa_russia": {"name": "واتساب - روسيا 🇷🇺", "service": "whatsapp", "country": "russia", "price": 0.50},
    "wa_usa": {"name": "واتساب - أمريكا 🇺🇸", "service": "whatsapp", "country": "usa", "price": 0.40},
    "wa_indonesia": {"name": "واتساب - إندونيسيا 🇮🇩", "service": "whatsapp", "country": "indonesia", "price": 0.35},
    "wa_england": {"name": "واتساب - بريطانيا 🇬🇧", "service": "whatsapp", "country": "england", "price": 0.45},
    "tg_russia": {"name": "تلجرام - روسيا 🇷🇺", "service": "telegram", "country": "russia", "price": 0.60},
}

# --- 1. أمر /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}", headers=headers_spb) as resp:
            data = await resp.json()
            if not data or (isinstance(data, list) and len(data) == 0):
                payload = {"telegram_id": user_id, "balance": 0.0}
                await session.post(f"{SUPABASE_URL}/rest/v1/users", json=payload, headers=headers_spb)

    keyboard = [
        [InlineKeyboardButton("🛒 قائمة شراء الأرقام", callback_data="show_services")],
        [InlineKeyboardButton("💰 عرض رصيدي", callback_data="check_balance"), InlineKeyboardButton("💳 شحن رصيد", callback_data="deposit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 أهلاً بك في بوت الأرقام الافتراضية!\nاختر من القائمة أدناه:", reply_markup=reply_markup)

# --- 2. عرض قائمة الخدمات ---
async def show_services_menu(query):
    keyboard = []
    for key, item in SERVICES.items():
        keyboard.append([InlineKeyboardButton(f"{item['name']} (${item['price']:.2f})", callback_data=f"buy_{key}")])
    keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("اختر الخدمة والدولة التي تريد شراء رقم لها:", reply_markup=reply_markup)

# --- 3. فحص ومتابعة وصول كود الـ SMS تلقائياً ---
async def check_sms_loop(context: ContextTypes.DEFAULT_TYPE, order_id: int, user_id: int, phone: str, price: float, msg_id: int):
    check_url = f"https://5sim.net/v1/user/check/{order_id}"
    
    # محاولة فحص الرسالة لمدة 120 ثانية (كل 5 ثوانٍ محاولة)
    for _ in range(24):
        await asyncio.sleep(5)
        async with aiohttp.ClientSession() as session:
            async with session.get(check_url, headers=headers_5sim) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    sms_list = res.get("sms", [])
                    if sms_list and len(sms_list) > 0:
                        sms_code = sms_list[0].get("code", "لا يوجد كود")
                        sms_text = sms_list[0].get("text", "")
                        
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"🎉 **وصل كود التفعيل بنجاح!**\n\n📱 الرقم: `{phone}`\n🔑 الكود: `{sms_code}`\n\n💬 نص الرسالة:\n`{sms_text}`",
                            parse_mode="Markdown"
                        )
                        return

    # في حال انقضاء الوقت ولم يصل الكود (إلغاء واسترجاع الرصيد)
    cancel_url = f"https://5sim.net/v1/user/cancel/{order_id}"
    async with aiohttp.ClientSession() as session:
        await session.get(cancel_url, headers=headers_5sim)
        
        # إرجاع المبلغ لحساب المستخدم في Supabase
        async with session.get(f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}", headers=headers_spb) as resp:
            u_data = await resp.json()
            curr_bal = float(u_data[0]["balance"]) if (isinstance(u_data, list) and len(u_data) > 0) else 0.0
            refunded_bal = curr_bal + price
            await session.patch(f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}", json={"balance": refunded_bal}, headers=headers_spb)

    await context.bot.send_message(
        chat_id=user_id,
        text=f"❌ **لم يصل كود التفعيل للرقم `{phone}` خلال الوقت المحدد.**\n\n🔄 تم إلغاء الطلب وإرجاع المبلغ (${price:.2f}) إلى رصيدك بنجاح.",
        parse_mode="Markdown"
    )

# --- 4. معالجة ضغطات الأزرار ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("🛒 قائمة شراء الأرقام", callback_data="show_services")],
            [InlineKeyboardButton("💰 عرض رصيدي", callback_data="check_balance"), InlineKeyboardButton("💳 شحن رصيد", callback_data="deposit")]
        ]
        await query.message.edit_text("👋 أهلاً بك في بوت الأرقام الافتراضية!\nاختر من القائمة أدناه:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "show_services":
        await show_services_menu(query)

    elif query.data == "check_balance":
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}", headers=headers_spb) as resp:
                data = await resp.json()
                balance = float(data[0]["balance"]) if (isinstance(data, list) and len(data) > 0) else 0.0
                await query.message.reply_text(f"💳 رصيدك الحالي: **${balance:.2f}**", parse_mode="Markdown")

    elif query.data == "deposit":
        await query.message.reply_text("🔑 لإعادة شحن رصيدك، أرسل كارت الشحن (الكود) في الرسالة التالية مباشرة:")

    # شراء رقم
    elif query.data.startswith("buy_"):
        service_key = query.data.replace("buy_", "")
        if service_key not in SERVICES:
            return

        srv_info = SERVICES[service_key]
        price = srv_info["price"]

        # فحص رصيد المستخدم
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}", headers=headers_spb) as resp:
                data = await resp.json()
                balance = float(data[0]["balance"]) if (isinstance(data, list) and len(data) > 0) else 0.0

        if balance < price:
            await query.message.reply_text(f"❌ رصيدك غير كافٍ لشراء هذا الرقم!\n(سعر الخدمة: ${price:.2f} - رصيدك: ${balance:.2f})")
            return

        await query.message.reply_text("⏳ جاري طلب الرقم من المزود...")

        url = f"https://5sim.net/v1/user/buy/activation/{srv_info['country']}/any/{srv_info['service']}"
        res = None
        
        async with aiohttp.ClientSession() as session:
            # محاولة طلب الرقم 3 مرات لتفادي الضغط المؤقت على السيرفر (502)
            for _ in range(3):
                async with session.get(url, headers=headers_5sim) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        break
                await asyncio.sleep(2)

            if not res or "id" not in res:
                await query.message.reply_text("❌ المزود (5SIM) يواجه ضغطاً أو شحاً في الأرقام حالياً. يرجى إعادة المحاولة لاحقاً.")
                return

            order_id = res["id"]
            phone = res["phone"]

            # خصم الرصيد في Supabase
            new_bal = balance - price
            await session.patch(f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}", json={"balance": new_bal}, headers=headers_spb)

        msg = await query.message.reply_text(
            f"✅ **تم شراء الرقم بنجاح!**\n\n📱 الرقم: `{phone}`\n💵 المبلغ المخصوم: ${price:.2f}\n\n⏳ جاري انتظار وصول كود التفعيل تلقائياً...",
            parse_mode="Markdown"
        )

        # تشغيل الفحص الدوري للـ SMS في الخلفية
        asyncio.create_task(check_sms_loop(context, order_id, user_id, phone, price, msg.message_id))

# --- 5. معالجة إدخال كروت الشحن من العميل ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code_input = update.message.text.strip()

    async with aiohttp.ClientSession() as session:
        url = f"{SUPABASE_URL}/rest/v1/vouchers?code=eq.{code_input}&is_used=eq.false"
        async with session.get(url, headers=headers_spb) as resp:
            vouchers = await resp.json()

            if not isinstance(vouchers, list) or len(vouchers) == 0:
                return

            voucher = vouchers[0]
            amount = float(voucher["amount"])

            # جلب رصيد المستخدم الحالي
            get_u_url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}"
            async with session.get(get_u_url, headers=headers_spb) as u_resp:
                u_data = await u_resp.json()
                current_bal = float(u_data[0]["balance"]) if (isinstance(u_data, list) and len(u_data) > 0) else 0.0

            new_bal = current_bal + amount

            # تحديث رصيد المستخدم
            patch_u_url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}"
            async with session.patch(patch_u_url, json={"balance": new_bal}, headers=headers_spb) as p_resp:
                if p_resp.status not in [200, 204]:
                    await update.message.reply_text("❌ حدث خطأ أثناء تحديث الرصيد.")
                    return

            # تعليم الكارت كـ مستخدم (is_used = true)
            patch_v_url = f"{SUPABASE_URL}/rest/v1/vouchers?id=eq.{voucher['id']}"
            await session.patch(patch_v_url, json={"is_used": True, "used_by": user_id}, headers=headers_spb)

            await update.message.reply_text(f"🎉 **تم شحن رصيدك بنجاح!**\n\n💵 القيمة المضافة: ${amount:.2f}\n💳 رصيدك الجديد: ${new_bal:.2f}", parse_mode="Markdown")

# --- 6. أوامر الأدمن ---

# أ) إنشاء كارت شحن
async def make_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    try:
        code = context.args[0]
        amount = float(context.args[1])

        async with aiohttp.ClientSession() as session:
            payload = {"code": code, "amount": amount, "is_used": False}
            async with session.post(f"{SUPABASE_URL}/rest/v1/vouchers", json=payload, headers=headers_spb) as resp:
                if resp.status in [200, 201]:
                    await update.message.reply_text(f"✅ **تم إنشاء كارت الشحن بنجاح!**\n\n🎟️ الكود: `{code}`\n💵 القيمة: ${amount:.2f}", parse_mode="Markdown")
                else:
                    err_text = await resp.text()
                    await update.message.reply_text(f"❌ خطأ:\n`{err_text}`", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("⚠️ الصيغة الصحيحة للأمر:\n`/make_card الكود المبلغ`", parse_mode="Markdown")

# ب) إضافة رصيد مباشر لمستخدم
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{target_id}", headers=headers_spb) as resp:
                u_data = await resp.json()
                if not u_data or len(u_data) == 0:
                    await update.message.reply_text("❌ المستخدم غير مسجل في البوت.")
                    return
                curr_bal = float(u_data[0]["balance"])
                new_bal = curr_bal + amount

            async with session.patch(f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{target_id}", json={"balance": new_bal}, headers=headers_spb) as patch_resp:
                if patch_resp.status in [200, 204]:
                    await update.message.reply_text(f"✅ تم إضافة ${amount:.2f} للمستخدم `{target_id}` بنجاح.\n💳 رصيده الحالي: ${new_bal:.2f}", parse_mode="Markdown")
                    try:
                        await context.bot.send_message(chat_id=target_id, text=f"🎉 تم إضافة ${amount:.2f} إلى حسابك بواسطة الإدارة!\n💳 رصيدك الحالي: ${new_bal:.2f}")
                    except Exception:
                        pass
    except Exception:
        await update.message.reply_text("⚠️ الصيغة الصحيحة للأمر:\n`/add_balance ID_المستخدم المبلغ`", parse_mode="Markdown")

# ج) عرض الإحصائيات للأدمن
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SUPABASE_URL}/rest/v1/users", headers=headers_spb) as u_resp:
            users = await u_resp.json()
            users_count = len(users) if isinstance(users, list) else 0

        async with session.get(f"{SUPABASE_URL}/rest/v1/vouchers", headers=headers_spb) as v_resp:
            vouchers = await v_resp.json()
            v_count = len(vouchers) if isinstance(vouchers, list) else 0
            used_v_count = len([v for v in vouchers if v.get("is_used")]) if isinstance(vouchers, list) else 0

    await update.message.reply_text(
        f"📊 **إحصائيات البوت:**\n\n👥 عدد المستخدمين: `{users_count}`\n🎟️ الكروت الكلية: `{v_count}`\n✅ الكروت المستخدمة: `{used_v_count}`",
        parse_mode="Markdown"
    )

# --- 7. تشغيل البوت ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("make_card", make_card))
    app.add_handler(CommandHandler("add_balance", add_balance))
    app.add_handler(CommandHandler("stats", stats))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🚀 البوت الأصلي المكتمل يعمل الآن...")
    app.run_polling()
