import logging
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# إعدادات السجل
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- الإعدادات الثابتة ---
ADMIN_GROUP_ID = -1003803368309 
MY_PERSONAL_ID = 8412282122 # حسابك كأدمن

# --- جدول العمال والجروبات ---
WORKERS_CONFIG = {
    5423134568: {"name": "محمد منير", "group": -1003779057465},
    1426253253: {"name": "طه", "group": -1003723842645},
    857492707:  {"name": "صلاح", "group": -1003888913270},
    8270215782: {"name": "جواد", "group": -1003777276939},
    7356581068: {"name": "صفوت", "group": -1003737530468},
    1062337898: {"name": "أحمد الحماطي", "group": -1003221600280},
    # يمكنك إضافة أمين وأحمد ياسين هنا بنفس الطريقة
}

user_accounts = {} 
global_stats = {'total_all': 0.0}

def get_acc(uid, name):
    if uid not in user_accounts:
        user_accounts[uid] = {'name': name, 'total': 0.0, 'discounts': 0.0, 'items': {'u':0, 'w':0, 'h':0}}
    return user_accounts[uid]

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not update.message: return
    if update.effective_chat.id == ADMIN_GROUP_ID: return

    # 1. نظام الخصم (للأدمن فقط)
    if uid == MY_PERSONAL_ID and update.message.text and "خصم" in update.message.text:
        if update.message.reply_to_message:
            target_uid = update.message.reply_to_message.forward_from.id if update.message.reply_to_message.forward_from else None
            amount = re.findall(r'(\d+)', update.message.text)
            if target_uid and amount:
                val = float(amount[0])
                acc = get_acc(target_uid, "عامِل")
                acc['total'] -= val
                acc['discounts'] += val
                await update.message.reply_text(f"✅ تم خصم {val} من حساب {acc['name']}")
        return

    # 2. معالجة إيصالات العمال
    if uid not in WORKERS_CONFIG: return
    worker = WORKERS_CONFIG[uid]
    acc = get_acc(uid, worker['name'])
    text = update.message.caption if update.message.photo else update.message.text
    if not text: return

    u = re.findall(r'(\d+)\s*(يونيفرس|يونفرس)', text)
    w = re.findall(r'(\d+)\s*(وورد|وورد كوب|ورد)', text)
    h = re.findall(r'(\d+)\s*(هولك)', text)
    for m in u: acc['items']['u'] += int(m[0])
    for m in w: acc['items']['w'] += int(m[0])
    for m in h: acc['items']['h'] += int(m[0])

    nums = re.findall(r'(\d+\.?\d*)', text)
    curr_val = 0.0
    item_vals = [m[0] for m in u+w+h]
    for n in nums:
        if n not in item_vals: curr_val = float(n); break

    prev_total = global_stats['total_all']
    acc['total'] += curr_val
    global_stats['total_all'] += curr_val

    if update.message.photo:
        photo = update.message.photo[-1].file_id
        await context.bot.send_photo(chat_id=ADMIN_GROUP_ID, photo=photo, 
                                   caption=f"{curr_val:.2f}\n{curr_val:.2f} + {prev_total:.2f}\nالمجموع: {global_stats['total_all']:.2f}")
        await context.bot.send_photo(chat_id=worker['group'], photo=photo, 
                                   caption=f"👤 {worker['name']}\n💰 المبلغ: {curr_val:.2f}\n📊 المجموع: {acc['total']:.2f}")
        
        keyboard = [[InlineKeyboardButton("💳 تصفية الحساب", callback_data=f"ask_{uid}")]]
        await update.message.reply_text(f"✅ تم الحفظ. مجموعك: {acc['total']:.2f}", 
                                       reply_markup=InlineKeyboardMarkup(keyboard) if uid == MY_PERSONAL_ID else None)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    
    if data.startswith("ask_"):
        uid = int(data.split("_")[1])
        keyboard = [[InlineKeyboardButton("✅ نعم، تصفية", callback_data=f"settle_{uid}")],
                    [InlineKeyboardButton("🔙 تراجع (خلف)", callback_data="cancel")]]
        await query.edit_message_text("⚠️ هل أنت متأكد من تصفية الحساب؟", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("settle_"):
        uid = int(data.split("_")[1])
        acc = user_accounts.get(uid)
        if acc:
            tax_comm = acc['total'] * 0.175 
            final = acc['total'] - tax_comm - (acc['items']['u']*12.5 + acc['items']['h']*20)
            report = f"🏁 تصفية {acc['name']}\n💰 الإجمالي: {acc['total']}\n✅ الصافي: {final:.2f}"
            await query.edit_message_text(report)
            acc['total'] = 0 # تصفير الحساب
    
    elif data == "cancel":
        await query.edit_message_text("🔙 تم إلغاء التصفية، الحساب مستمر.")

if __name__ == '__main__':
    # ملاحظة: تأكد أن اسم المتغير في Render هو BOT_TOKEN
    token = os.environ.get('BOT_TOKEN')
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_msg))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("البوت يعمل الآن...")
    app.run_polling()
