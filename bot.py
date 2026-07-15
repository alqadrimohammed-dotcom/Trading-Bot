# [نفس الإعدادات السابقة، أضفت لك دوال الإدارة أدناه]

@bot.message_handler(commands=['add'])
def add_stock(m):
    try:
        parts = m.text.split()
        if len(parts) < 3:
            bot.reply_to(m, "⚠️ صيغة خاطئة! استخدم: `/add [الرمز] [الفريم]`\nمثال: `/add AAPL 1h`")
            return
        symbol, interval = parts[1].upper(), parts[2]
        WATCHLIST.append((symbol, interval))
        save_database()
        bot.reply_to(m, f"✅ تم إضافة {symbol} بنجاح إلى قائمة الرادار ({interval})!")
    except Exception as e: bot.reply_to(m, f"❌ حدث خطأ: {e}")

@bot.message_handler(commands=['remove'])
def remove_stock(m):
    try:
        symbol = m.text.split()[1].upper()
        global WATCHLIST
        WATCHLIST = [x for x in WATCHLIST if x[0] != symbol]
        save_database()
        bot.reply_to(m, f"🗑️ تم حذف {symbol} من قائمة المراقبة.")
    except: bot.reply_to(m, "⚠️ استخدم: `/remove [الرمز]`")

@bot.message_handler(commands=['list'])
def list_stocks(m):
    msg = "📋 **قائمة المراقبة الحالية:**\n" + "\n".join([f"▪️ {x[0]} ({x[1]})" for x in WATCHLIST])
    bot.reply_to(m, msg, parse_mode="Markdown")

# [باقي الكود يوضع هنا كما في النسخة السابقة...]
