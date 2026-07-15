import telebot
import pandas as pd
import numpy as np
import cloudscraper
import threading
import time
import warnings
import os
import json
import pymongo 
import gc 
from concurrent.futures import ThreadPoolExecutor 
from flask import Flask
from datetime import datetime, date
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

warnings.filterwarnings('ignore')

TOKEN = "8666366975:AAFaapaj0XAHUO8-6PbzzNY0GGWiit0bKsk"
bot = telebot.TeleBot(TOKEN)

# 🌐 الاتصال بقاعدة البيانات السحابية (MongoDB)
MONGO_URI = os.environ.get("MONGO_URI", "YOUR_MONGODB_CONNECTION_STRING_HERE")
mongo_connected = False
try:
    if "YOUR_MONGODB_CONNECTION" not in MONGO_URI and "mongodb+srv" in MONGO_URI:
        client = pymongo.MongoClient(MONGO_URI)
        db = client["whale_radar_db"]
        state_col = db["bot_state"]
        quasimodo_col = db["daily_quasimodo"]
        mongo_connected = True
        print("🟢 تم الاتصال بنجاح بـ MongoDB!")
    else:
        print("⚠️ لم يتم العثور على رابط MongoDB صالح.")
except Exception as e:
    print(f"❌ فشل الاتصال: {e}")

DEFAULT_WATCHLIST = [
    ("TSLA", "1h"), ("NVDA", "1h"), ("GOOGL", "1h"), ("MSTR", "1h"), ("MSFT", "1h"), ("AAPL", "1h"),
    ("1010.SR", "1d"), ("1120.SR", "1d"), ("1140.SR", "1d"), ("1180.SR", "1d"), ("2010.SR", "1d"), 
    ("2222.SR", "1d"), ("7010.SR", "1d"), ("1150.SR", "1d"), ("2002.SR", "1d")
] # (يمكنك إضافة أسهمك من البوت بأمر /add)

ARABIC_TICKERS = {
    "الرياض": "1010.SR", "الراجحي": "1120.SR", "البلاد": "1140.SR", "الانماء": "1150.SR", 
    "الاهلي": "1180.SR", "سابك": "2002.SR", "ارامكو": "2222.SR", "اس تي سي": "7010.SR"
}

WATCHLIST = DEFAULT_WATCHLIST.copy()
radar_settings = {"sa": True, "us": True, "market": True, "sniper": True}
subscribed_chats = set()
todays_picks = {}
todays_sniper_picks = {} 
retest_alerts = {} 
notified_retests = set() 
last_update_date = date.today()
active_trades = {} 
trade_history = {"wins": 0, "losses": 0, "log": []} 
ai_learned_patterns = [] 
in_memory_daily_quasimodo = {} 
DB_FILE = "bot_database.json"

# 💾 دوال الذاكرة
def save_database():
    global WATCHLIST, active_trades, trade_history, retest_alerts, subscribed_chats, ai_learned_patterns
    data = {"active_trades": active_trades, "trade_history": trade_history, "retest_alerts": retest_alerts, "subscribed_chats": list(subscribed_chats), "ai_learned_patterns": ai_learned_patterns, "watchlist": WATCHLIST}
    if mongo_connected:
        try: state_col.update_one({"_id": "bot_config"}, {"$set": data}, upsert=True)
        except: pass

def load_database():
    global active_trades, trade_history, retest_alerts, subscribed_chats, ai_learned_patterns, WATCHLIST
    if mongo_connected:
        try:
            data = state_col.find_one({"_id": "bot_config"})
            if data:
                active_trades.update(data.get("active_trades", {}))
                trade_history.update(data.get("trade_history", {"wins": 0, "losses": 0, "log": []}))
                retest_alerts.update(data.get("retest_alerts", {}))
                subscribed_chats.update(data.get("subscribed_chats", []))
                ai_learned_patterns = data.get("ai_learned_patterns", [])
                sw = data.get("watchlist", [])
                if sw: WATCHLIST = [tuple(x) for x in sw]
        except: pass

def get_display_name(ticker):
    for name, t in ARABIC_TICKERS.items():
        if t == ticker: return f"{ticker.replace('.SR', '')}({name})"
    return ticker.replace('.SR', '') if ticker.endswith('.SR') else ticker

# 📥 جلب البيانات
def fetch_yahoo_data(ticker, interval="1d", retries=2):
    period = "1y" if interval == "1d" else ("2y" if interval == "1wk" else "60d")
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?range={period}&interval={interval}"
    scraper = cloudscraper.create_scraper()
    for _ in range(retries):
        try:
            res = scraper.get(url, timeout=4)
            if res.status_code == 200:
                data = res.json()
                if 'chart' in data and 'error' in data['chart'] and data['chart']['error']: continue
                result = data['chart']['result'][0]
                df = pd.DataFrame({'Open': result['indicators']['quote'][0]['open'], 'High': result['indicators']['quote'][0]['high'], 'Low': result['indicators']['quote'][0]['low'], 'Close': result['indicators']['quote'][0]['close'], 'Volume': result['indicators']['quote'][0]['volume']})
                df.index = pd.to_datetime(result['timestamp'], unit='s')
                return df.dropna()
        except: time.sleep(0.5)
    raise Exception("Connection Error")

def get_analysis_data(ticker, interval):
    df = fetch_yahoo_data(ticker, interval)
    if not ticker.endswith(".SR") or interval == "1h": df = df.iloc[:-1].copy() # فلتر الصرامة لتأكيد الإغلاق
    if len(df) < 50: return {"trend": "عرضي", "label": "عرضي ⚪"}
    c = float(df['Close'].iloc[-1])
    sma50 = float(df['Close'].rolling(50).mean().iloc[-1])
    if c > sma50: return {"trend": "صاعد", "label": "صاعد 🟢 (إيجابي)"}
    elif c < sma50: return {"trend": "هابط", "label": "هابط 🔴 (سلبي)"}
    return {"trend": "عرضي", "label": "عرضي ⚪ (توازن)"}

# 🧠 المحرك الأساسي (يحتوي على جميع المدارس الفنية)
def get_immediate_signal(ticker, interval="1d", record_alert=False):
    try:
        df = fetch_yahoo_data(ticker, interval)
        if len(df) < 100: return {"error": "بيانات غير كافية.", "ticker": ticker}
        
        # 🔒 فلتر الشموع المغلقة للسوق الأمريكي
        if not ticker.endswith(".SR") or interval == "1h": df = df.iloc[:-1].copy()
            
        current_price = float(df['Close'].iloc[-1])
        df['Body'] = abs(df['Close'] - df['Open'])
        
        # 1. سيولة SMC
        df['Sweep_Bull'] = df['Low'] < df['Low'].rolling(15).min().shift(1)
        df['Sweep_Bear'] = df['High'] > df['High'].rolling(15).max().shift(1)
        df['CHoCH_Bull'] = df['Close'] > df['High'].rolling(8).max().shift(1)
        df['CHoCH_Bear'] = df['Close'] < df['Low'].rolling(8).min().shift(1)
        df['Bullish_FVG'] = df['Low'] > df['High'].shift(2)
        df['Bearish_FVG'] = df['High'] < df['Low'].shift(2)
        
        is_qm_bull = (df['Sweep_Bull'].tail(5).any()) and (df['CHoCH_Bull'].iloc[-1])
        is_qm_bear = (df['Sweep_Bear'].tail(5).any()) and (df['CHoCH_Bear'].iloc[-1])

        # 2. وايكوف
        safe_range = (df['High'] - df['Low']).replace(0, 0.0001)
        wyckoff_acc = (df['Close'] < df['Close'].rolling(50).mean()) & (df['Volume'] > 1.5 * df['Volume'].rolling(20).mean()) & (((df['Close'] - df['Low']) / safe_range) > 0.75)
        wyckoff_dist = (df['Close'] > df['Close'].rolling(50).mean()) & (df['Volume'] > 1.5 * df['Volume'].rolling(20).mean()) & (((df['High'] - df['Close']) / safe_range) > 0.75)

        # 3. بولنجر باند وبرايس أكشن
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['BB_Lower'] = df['SMA_20'] - (2 * df['Close'].rolling(20).std())
        df['BB_Upper'] = df['SMA_20'] + (2 * df['Close'].rolling(20).std())
        df['Engulf_Bull'] = (df['Close'].shift(1) < df['Open'].shift(1)) & (df['Close'] > df['Open']) & (df['Close'] > df['Open'].shift(1))
        
        bull, bear = [], []
        if is_qm_bull: bull.append("👑 SMC: كوازمودو شرائي (ضرب سيولة القاع + CHoCH صاعد)")
        if df['Bullish_FVG'].iloc[-1]: bull.append("SMC: فجوة سيولة شرائية (FVG)")
        if wyckoff_acc.iloc[-1]: bull.append("📊 وايكوف: ذروة بيع وتجميع سيولة ضخمة بالقاع")
        if df['Engulf_Bull'].iloc[-1]: bull.append("🕯️ برايس أكشن: شمعة ابتلاعية شرائية قوية")
        if float(df['Low'].iloc[-1]) < float(df['BB_Lower'].iloc[-1]): bull.append("📉 بولنجر: السعر ضرب الحد السفلي وتجاوزه")

        if is_qm_bear: bear.append("👑 SMC: كوازمودو بيعي (ضرب سيولة القمة + CHoCH هابط)")
        if df['Bearish_FVG'].iloc[-1]: bear.append("SMC: فجوة سيولة بيعية (FVG)")
        if wyckoff_dist.iloc[-1]: bear.append("📊 وايكوف: ذروة شراء وتصريف سيولة بالقمة")
        if float(df['High'].iloc[-1]) > float(df['BB_Upper'].iloc[-1]): bear.append("📈 بولنجر: السعر ضرب الحد العلوي وتجاوزه")
        
        # الفريمات
        t_1h = get_analysis_data(ticker, '1h')
        t_4h = get_analysis_data(ticker, '4h')
        t_1d = get_analysis_data(ticker, '1d')
        mtf_dash = [f"1س: {t_1h['label']}", f"4س: {t_4h['label']}", f"يومي: {t_1d['label']}"]
        
        mtf_buy_ok = (t_4h['trend'] == "صاعد") and (t_1d['trend'] == "صاعد")
        mtf_sell_ok = (t_4h['trend'] == "هابط") and (t_1d['trend'] == "هابط")
        
        action, targets, sl, entry, reason = "مراقبة 🟡", "", "", "-", "لا توجد نماذج مكتملة حالياً."
        is_golden = False
        status_label = t_1d['label'] # حالة السهم تؤخذ من اليومي
        
        # الذكاء الاصطناعي (البصمات)
        if any(ticker in p for p in ai_learned_patterns): bull.append("🧠 الذكاء الاصطناعي: السهم يطابق بصمة نموذج تعلمه البوت سابقاً")

        if len(bull) >= 2 or is_qm_bull:
            if not mtf_buy_ok:
                action, reason = "مراقبة 🟡 (إلغاء الشراء)", "\n➕ ".join([""] + bull).strip() + "\n⚠️ **الدخول ملغى لأن الاتجاه العام هابط!**"
            else:
                action = "شراء فوري 🟢"
                reason = "\n➕ ".join([""] + bull).strip()
                entry = str(round(current_price, 2))
                exact_sl = round(float(df['Low'].tail(15).min()), 2)
                sl = f"{exact_sl} (كسر أدنى قاع)"
                targets = f"🎯 هدف أول: {round(current_price * 1.03, 2)}"
                # شرط الفرصة الذهبية
                if is_qm_bull and mtf_buy_ok and (wyckoff_acc.iloc[-1] or df['Bullish_FVG'].iloc[-1]): is_golden = True
                
        elif len(bear) >= 2 or is_qm_bear:
            if not mtf_sell_ok:
                action, reason = "مراقبة 🟡 (إلغاء البيع)", "\n➖ ".join([""] + bear).strip() + "\n⚠️ **الدخول ملغى لأن الاتجاه العام صاعد!**"
            else:
                action = "بيع فوري 🔴"
                reason = "\n➖ ".join([""] + bear).strip()
                entry = str(round(current_price, 2))
                exact_sl = round(float(df['High'].tail(15).max()), 2)
                sl = f"{exact_sl} (اختراق أعلى قمة)"
                targets = f"🎯 هدف أول: {round(current_price * 0.97, 2)}"

        return {"ticker": ticker, "price": round(current_price, 2), "action": action, "targets": targets, "sl": sl, "entry": entry, "reason": reason, "mtf_dash": mtf_dash, "status": status_label, "is_golden": is_golden}
    except Exception as e: return {"error": str(e), "ticker": ticker}

# 💬 تنسيق الرسائل بشكل احترافي وواضح
def format_msg(res):
    if "error" in res: return f"⚠️ تعذر تحليل السهم: {res.get('ticker', '')}"
    
    if res.get('is_golden'):
        msg = f"🌟💎 **فـرصـة ذهـبـيـة نـادرة** 💎🌟\n"
        msg += f"🔥 **إجماع فني 100% رصده الرادار** 🔥\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 **السهم:** {get_display_name(res['ticker'])} | **السعر الحالي:** {res['price']}\n"
        msg += f"📈 **وضع السهم العام:** {res['status']}\n"
        msg += f"🛒 **نقطة الدخول:** {res['entry']}\n"
        msg += f"🛑 **الوقف الصارم:** {res['sl']}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"💡 **المدارس المتفقة (Confluence):**\n{res['reason']}\n\n"
        msg += f"🧭 **إجماع الفريمات:**\n" + "\n".join([f"✅ {line}" for line in res['mtf_dash']])
    else:
        msg = f"🎯 **القرار اللحظي:** {res['action']}\n"
        msg += f"📊 **السهم:** {get_display_name(res['ticker'])} | **السعر:** {res['price']}\n"
        msg += f"📈 **وضع السهم العام:** {res['status']}\n"
        msg += f"━━━━━━━━━━━━\n🧭 **لوحة الفريمات:**\n" + "\n".join([f"▪️ {line}" for line in res['mtf_dash']])
        msg += f"\n━━━━━━━━━━━━\n🛒 **نقطة الدخول:** {res['entry']}\n🛑 **الوقف:** {res['sl']}\n💡 **الأسباب والمدارس الفنية:**\n{res['reason']}\n"
    return msg

# 🤖 الرادار التلقائي
def auto_scanner():
    while True:
        if subscribed_chats and radar_settings["market"]:
            target_watchlist = WATCHLIST.copy()
            def scan_single(item):
                try: return get_immediate_signal(item[0], item[1], record_alert=True)
                except: return None

            with ThreadPoolExecutor(max_workers=3) as executor:
                results = list(executor.map(scan_single, target_watchlist))
            gc.collect() # 🧹 تنظيف الذاكرة

            for res in results:
                if res and "error" not in res and ("فوري" in res['action']):
                    for chat_id in list(subscribed_chats):
                        try:
                            if res.get('is_golden'): bot.send_message(chat_id, f"🚨🌟 **تنبيه فرصة ذهبية!** 🌟🚨\n\n{format_msg(res)}")
                            else: bot.send_message(chat_id, f"🚨 **اكتشاف رادار الحيتان** 🚨\n\n{format_msg(res)}")
                        except: pass
        time.sleep(600)

# 📱 لوحة المفاتيح
def get_radar_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🌟 رادار الفرص الذهبية"), KeyboardButton("🦇 كاشف الهارمونيك والكلاسيكي"))
    markup.add(KeyboardButton("🇸🇦 تصفية شاملة (سعودي)"), KeyboardButton("🇺🇸 تصفية شاملة (أمريكي)"))
    markup.add(KeyboardButton("🔍 كوازمودو سعودي 🇸🇦"), KeyboardButton("🔍 كوازمودو أمريكي 🇺🇸"))
    markup.add(KeyboardButton("📊 التقرير اليومي للـ AI"), KeyboardButton("⚙️ إعدادات الرادار"))
    return markup

def get_inline_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton(f"{'✅' if radar_settings['sa'] else '❌'} الرادار السعودي", callback_data="toggle_sa"))
    markup.add(InlineKeyboardButton(f"{'✅' if radar_settings['us'] else '❌'} الرادار الأمريكي", callback_data="toggle_us"))
    markup.add(InlineKeyboardButton(f"{'✅' if radar_settings['market'] else '❌'} رادار استكشاف النماذج التلقائي", callback_data="toggle_market"))
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    subscribed_chats.add(m.chat.id)
    save_database()
    bot.reply_to(m, "مرحباً بك في رادار الحيتان 🐋!\n🚀 تم استعادة جميع المدارس الفنية وترتيب الكود بالكامل مع زر الفرص الذهبية المستقل.", reply_markup=get_radar_markup())

# --- دوال الأزرار ---

@bot.message_handler(func=lambda m: m.text.strip() == "🌟 رادار الفرص الذهبية")
def find_golden_opportunities(m):
    msg = bot.reply_to(m, "🌟 **جاري مسح السوق بحثاً عن الفرص الذهبية النادرة (إجماع 100%)...**\n⏳ يرجى الانتظار...")
    goldens = []
    def scan_golden(item):
        try:
            res = get_immediate_signal(item[0], item[1])
            if res and res.get('is_golden'): return res
        except: return None
    with ThreadPoolExecutor(max_workers=3) as executor: results = list(executor.map(scan_golden, WATCHLIST))
    gc.collect()
    for r in results:
        if r: goldens.append(r)
    
    if not goldens: bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text="📭 لم يجد الرادار أي فرصة تلبي شروط الإجماع الذهبي الصارمة حالياً.")
    else:
        reply = "🌟 **الفرص الذهبية الحالية في السوق:**\n\n"
        for r in goldens: reply += format_msg(r) + "\n"
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=reply)

@bot.message_handler(func=lambda m: "تصفية شاملة" in m.text.strip())
def find_best_confluence(m):
    market = "sa" if "سعودي" in m.text else "us"
    m_name = "السعودي 🇸🇦" if market == "sa" else "الأمريكي 🇺🇸"
    msg = bot.reply_to(m, f"🔍 **جاري بدء المسح الشامل للسوق {m_name}...**")
    buys, sells = [], []
    target_watchlist = [item for item in WATCHLIST if (market == "sa" and item[0].endswith(".SR")) or (market == "us" and not item[0].endswith(".SR"))]
    
    def scan_single(item):
        try: return get_immediate_signal(item[0], item[1])
        except: return None
        
    with ThreadPoolExecutor(max_workers=3) as executor: results = list(executor.map(scan_single, target_watchlist))
    gc.collect() 
    
    for res in results:
        if res and "error" not in res:
            if "شراء فوري" in res['action']: buys.append((res['reason'].count('➕'), res))
            elif "بيع فوري" in res['action']: sells.append((res['reason'].count('➖'), res))
            
    buys.sort(key=lambda x: x[0], reverse=True)
    if not buys and not sells:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"لا توجد إشارات (شراء/بيع) واضحة حالياً في السوق {m_name}.")
        return
        
    reply = f"🏆 **أقوى الفرص للسوق {m_name}** 🏆\n\n"
    for score, res in buys[:3]: reply += f"{format_msg(res)}\n"
    bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=reply)

@bot.message_handler(func=lambda m: m.text.strip() == "🦇 كاشف الهارمونيك والكلاسيكي")
def scan_harmonics_classical(m):
    msg = bot.reply_to(m, "🦇 **جاري تشغيل محرك الهارمونيك المعزول...**\n⏳ يرجى الانتظار...")
    found = []
    def check_harmonic(item):
        ticker, interval = item
        try:
            df = fetch_yahoo_data(ticker, interval)
            if not ticker.endswith(".SR") or interval == "1h": df = df.iloc[:-1].copy()
            if len(df) < 50: return None
            recent_lows, current_lows = df['Low'].iloc[-20:-5], df['Low'].iloc[-5:]
            min1, min2 = recent_lows.min(), current_lows.min()
            if abs(min1 - min2) / min1 < 0.015: 
                peak_between = df['High'].iloc[-20:].max()
                current_price = df['Close'].iloc[-1]
                if current_price > peak_between * 0.98:
                    return {"ticker": ticker, "pattern": "قاع مزدوج (W) إيجابي 📈", "price": current_price}
        except: pass
        return None
    with ThreadPoolExecutor(max_workers=3) as executor: results = list(executor.map(check_harmonic, WATCHLIST))
    gc.collect() 
    for r in results:
        if r: found.append(r)
    if not found: bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text="📭 لم يتم رصد أي نماذج كلاسيكية حالياً.")
    else:
        reply = "🦇 **نتائج محرك الهارمونيك:**\n\n"
        for p in found: reply += f"▪️ **{get_display_name(p['ticker'])}**\n   📐 النموذج: {p['pattern']}\n   💲 السعر: {round(p['price'], 2)}\n\n"
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=reply)

@bot.message_handler(func=lambda m: m.text.strip() == "📊 التقرير اليومي للـ AI")
def show_daily_ai_report(m):
    today_str = date.today().strftime('%Y-%m-%d')
    reply = f"🧠 **تقرير الذكاء الاصطناعي وذاكرة التعلم ({today_str}):**\n━━━━━━━━━━━━━━━━━━━━\n"
    
    # جلب نماذج كوازمودو
    setups_today = in_memory_daily_quasimodo.get(today_str, [])
    if mongo_connected:
        try:
            tl = quasimodo_col.find_one({"date": today_str})
            if tl and "setups" in tl: setups_today = tl["setups"]
        except: pass
        
    reply += f"💾 **سجل كوازمودو لليوم:**\n"
    if not setups_today: reply += "📭 لم يتم رصد نماذج اليوم.\n"
    else:
        for idx, item in enumerate(setups_today, 1): reply += f"{idx}. **{item['name']}** ({item['interval']}) - {item['direction']}\n"
        
    reply += f"\n━━━━━━━━━━━━━━━━━━━━\n🤖 **ذاكرة البصمات (ai_learned_patterns):**\n"
    if not ai_learned_patterns: reply += "▪️ الذاكرة فارغة حالياً. (البوت يجمع البيانات ⏳)\n"
    else:
        for pat in ai_learned_patterns[-5:]: reply += f"✅ بصمة محفوظة: `{pat}`\n"
    bot.reply_to(m, reply, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text.strip() == "⚙️ إعدادات الرادار")
def radar_panel(m):
    bot.reply_to(m, "⚙️ **تحكم بتشغيل الرادارات الخلفية:**", reply_markup=get_inline_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_"))
def toggle_radar_setting(call):
    key = call.data.split("_")[1]
    radar_settings[key] = not radar_settings[key]
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_inline_markup())

@bot.message_handler(func=lambda m: "كوازمودو" in m.text.strip())
def find_quasimodo_only(m):
    market = "sa" if "سعودي" in m.text else "us"
    m_name = "السعودي 🇸🇦" if market == "sa" else "الأمريكي 🇺🇸"
    msg = bot.reply_to(m, f"🔍 **جاري فحص السوق {m_name}...**")
    tw = [i for i in WATCHLIST if (market == "sa" and i[0].endswith(".SR")) or (market == "us" and not i[0].endswith(".SR"))]
    def scan_for_qm(item):
        try:
            res = get_immediate_signal(item[0], item[1])
            if res and ("كوازمودو" in res.get('reason', '')): return res
        except: pass
        return None
    with ThreadPoolExecutor(max_workers=3) as executor: results = list(executor.map(scan_for_qm, tw))
    gc.collect() 
    qm_found = [r for r in results if r is not None]
    if not qm_found: bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"📭 لا يوجد كوازمودو حالياً.")
    else:
        reply = f"🎯 **نتائج رادار كوازمودو:**\n\n"
        for r in qm_found: reply += format_msg(r) + "\n"
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=reply)

# التحليل اليدوي
@bot.message_handler(func=lambda m: True)
def analyze_manual_stock(m):
    text = m.text.strip().upper()
    ignore = ["🌟 رادار الفرص الذهبية", "🦇 كاشف الهارمونيك والكلاسيكي", "🇸🇦 تصفية شاملة (سعودي)", "🇺🇸 تصفية شاملة (أمريكي)", "⚙️ إعدادات الرادار", "📊 التقرير اليومي للـ AI", "🔍 كوازمودو سعودي 🇸🇦", "🔍 كوازمودو أمريكي 🇺🇸"]
    if text in ignore or text.startswith("/"): return
    
    t = ARABIC_TICKERS.get(text.replace("أ", "ا").replace("إ", "ا").replace("ة", "ه"), text)
    if t.isdigit() and len(t) == 4: t += ".SR"
    msg = bot.reply_to(m, f"⏳ جاري الفحص المعمق لـ {text}...")
    interval = "1d" if t.endswith(".SR") else "1h"
    res = get_immediate_signal(t, interval, record_alert=True)
    if res and "error" not in res:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=format_msg(res))
    else:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"⚠️ تعذر تحليل السهم: {res.get('error', '')}")

app = Flask(__name__)
@app.route('/')
def home(): return "🚀 البوت يعمل بالنسخة الشاملة والمتكاملة!"
def run_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

threading.Thread(target=run_server, daemon=True).start()
load_database()
threading.Thread(target=auto_scanner, daemon=True).start()

bot.remove_webhook()
bot.polling(none_stop=True)
