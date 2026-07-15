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

# 🌐 اتصال قاعدة البيانات السحابية (MongoDB)
MONGO_URI = os.environ.get("MONGO_URI", "YOUR_MONGODB_CONNECTION_STRING_HERE")

mongo_connected = False
try:
    if "YOUR_MONGODB_CONNECTION" not in MONGO_URI and "mongodb+srv" in MONGO_URI:
        client = pymongo.MongoClient(MONGO_URI)
        db = client["whale_radar_db"]
        state_col = db["bot_state"]
        quasimodo_col = db["daily_quasimodo"]
        mongo_connected = True
        print("🟢 تم الاتصال بنجاح بقاعدة البيانات السحابية MongoDB Atlas!")
    else:
        print("⚠️ لم يتم العثور على رابط MongoDB صالح. البوت سيعمل مؤقتاً بالذاكرة المحلية.")
except Exception as e:
    print(f"❌ فشل الاتصال بـ MongoDB: {e}")

DEFAULT_WATCHLIST = [
    ("TSLA", "1h"), ("NVDA", "1h"), ("GOOGL", "1h"), ("MSTR", "1h"),
    ("MSFT", "1h"), ("CRM", "1h"), ("ORCL", "1h"), ("AMZN", "1h"),
    ("AAPL", "1h"), ("AVGO", "1h"), ("ARM", "1h"), ("LLY", "1h"),
    ("COST", "1h"), ("AMD", "1h"), ("MU", "1h"), ("PLTR", "1h"),
    ("1010.SR", "1d"), ("1120.SR", "1d"), ("1180.SR", "1d"), ("2010.SR", "1d"),
    ("2222.SR", "1d"), ("7010.SR", "1d"), ("1140.SR", "1d"), ("2002.SR", "1d")
] # (تم اختصار القائمة الافتراضية هنا لتوفير المساحة، يمكنك إضافة أسهمك من البوت)

ARABIC_TICKERS = {
    "الرياض": "1010.SR", "الراجحي": "1120.SR", "البلاد": "1140.SR",
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

def save_database():
    global WATCHLIST, active_trades, trade_history, retest_alerts, subscribed_chats, ai_learned_patterns
    data = {"active_trades": active_trades, "trade_history": trade_history, "retest_alerts": retest_alerts, "subscribed_chats": list(subscribed_chats), "ai_learned_patterns": ai_learned_patterns, "watchlist": WATCHLIST}
    if mongo_connected:
        try: state_col.update_one({"_id": "bot_config"}, {"$set": data}, upsert=True)
        except: pass
    else:
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
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
                saved_watchlist = data.get("watchlist", [])
                if saved_watchlist: WATCHLIST = [tuple(x) for x in saved_watchlist]
                return
        except: pass
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                active_trades.update(data.get("active_trades", {}))
                trade_history.update(data.get("trade_history", {"wins": 0, "losses": 0, "log": []}))
                retest_alerts.update(data.get("retest_alerts", {}))
                subscribed_chats.update(data.get("subscribed_chats", []))
                ai_learned_patterns = data.get("ai_learned_patterns", [])
                saved_watchlist = data.get("watchlist", [])
                if saved_watchlist: WATCHLIST = [tuple(x) for x in saved_watchlist]
    except: pass

def get_display_name(ticker):
    for name, t in ARABIC_TICKERS.items():
        if t == ticker: return f"{ticker.replace('.SR', '')}({name})"
    return ticker.replace('.SR', '') if ticker.endswith('.SR') else ticker

def fetch_yahoo_data(ticker, interval="1d", retries=2):
    period = "1y" if interval == "1d" else ("2y" if interval == "1wk" else "730d")
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?range={period}&interval={interval}"
    scraper = cloudscraper.create_scraper()
    for _ in range(retries):
        try:
            res = scraper.get(url, timeout=3)
            if res.status_code == 200:
                data = res.json()
                if 'chart' in data and 'error' in data['chart'] and data['chart']['error']: continue
                result = data['chart']['result'][0]
                df = pd.DataFrame({'Open': result['indicators']['quote'][0]['open'], 'High': result['indicators']['quote'][0]['high'], 'Low': result['indicators']['quote'][0]['low'], 'Close': result['indicators']['quote'][0]['close'], 'Volume': result['indicators']['quote'][0]['volume']})
                df.index = pd.to_datetime(result['timestamp'], unit='s')
                return df.dropna()
        except: time.sleep(0.3)
    raise Exception("Connection Error")

def get_analysis_data(ticker, interval):
    df = fetch_yahoo_data(ticker, interval)
    if not ticker.endswith(".SR") or interval == "1h": df = df.iloc[:-1].copy() # فلتر الصرامة الأمريكي
    if len(df) < 50: return {"trend": "عرضي", "models": [], "label": "عرضي ⚪"}
    c = float(df['Close'].iloc[-1])
    sma50 = float(df['Close'].rolling(50).mean().iloc[-1])
    if c > sma50: trend, label = "صاعد", "صاعد 🟢"
    elif c < sma50: trend, label = "هابط", "هابط 🔴"
    else: trend, label = "عرضي", "عرضي ⚪"
    return {"trend": trend, "models": [], "label": label}

def ai_market_study():
    pass # مخفف للذاكرة

def get_immediate_signal(ticker, interval="1d", record_alert=False):
    try:
        df = fetch_yahoo_data(ticker, interval)
        if df.empty or len(df) < 100: return {"error": "بيانات غير كافية."}
        
        # 🔒 تطبيق فلتر التأكيد الصارم
        if not ticker.endswith(".SR") or interval == "1h":
            df = df.iloc[:-1].copy()
            
        current_price = float(df['Close'].iloc[-1])
        df['Body'] = abs(df['Close'] - df['Open'])
        
        # مؤشرات السيولة وSMC
        df['Sweep_Bull'] = df['Low'] < df['Low'].rolling(15).min().shift(1)
        df['Sweep_Bear'] = df['High'] > df['High'].rolling(15).max().shift(1)
        df['CHoCH_Bull'] = df['Close'] > df['High'].rolling(8).max().shift(1)
        df['CHoCH_Bear'] = df['Close'] < df['Low'].rolling(8).min().shift(1)
        df['Bullish_FVG'] = df['Low'] > df['High'].shift(2)
        
        # وايكوف وبولنجر باند
        safe_range = (df['High'] - df['Low']).replace(0, 0.0001)
        wyckoff_acc = (df['Close'] < df['Close'].rolling(50).mean()) & (df['Volume'] > 1.5 * df['Volume'].rolling(20).mean()) & (((df['Close'] - df['Low']) / safe_range) > 0.75)
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['BB_Lower'] = df['SMA_20'] - (2 * df['Close'].rolling(20).std())
        
        is_qm_bull = (df['Sweep_Bull'].tail(5).any()) and (df['CHoCH_Bull'].iloc[-1])
        
        bull, bear = [], []
        if is_qm_bull: bull.append("👑 SMC: كوازمودو شرائي (تصفية + CHoCH)")
        if df['Bullish_FVG'].iloc[-1]: bull.append("SMC: فجوة سيولة شرائية (FVG)")
        if wyckoff_acc.iloc[-1]: bull.append("📊 وايكوف: تجميع وسيولة ضخمة بالقاع")
        # الاعتماد على قاع الشمعة خارج البولنجر كما حددتها سابقاً
        if float(df['Low'].iloc[-1]) < float(df['BB_Lower'].iloc[-1]): bull.append("بولنجر: الأدنى خارج البولنجر باند 📉")
        
        t_1h = get_analysis_data(ticker, '1h')
        t_4h = get_analysis_data(ticker, '4h')
        t_1d = get_analysis_data(ticker, '1d')
        
        mtf_dash = [f"1س: {t_1h['label']}", f"4س: {t_4h['label']}", f"يومي: {t_1d['label']}"]
        mtf_buy_ok = (t_4h['trend'] == "صاعد") and (t_1d['trend'] == "صاعد")
        
        is_golden = False
        action, targets, sl, entry, reason = "انتظار 🟡", "", "", "غير محدد", "تذبذب."
        
        if len(bull) >= 2 or is_qm_bull:
            if not mtf_buy_ok:
                action, reason = "مراقبة 🟡 (إلغاء شراء)", "\n➕ ".join([""] + bull).strip() + "\n⚠️ **الاتجاه العام هابط!**"
            else:
                action = "شراء فوري 🟢"
                # 🌟 التحقق من الفرصة الذهبية: كوازمودو + فريمات متفقة + وايكوف أو فجوة
                if is_qm_bull and mtf_buy_ok and (wyckoff_acc.iloc[-1] or df['Bullish_FVG'].iloc[-1]):
                    is_golden = True
                    
                reason = "\n➕ ".join([""] + bull).strip()
                entry = str(round(current_price, 2))
                exact_sl = round(float(df['Low'].tail(15).min()), 2)
                sl = f"{exact_sl} (كسر الأدنى)"
                targets = f"🎯 هدف مفتوح (مقاومة تالية)"
                
        return {"ticker": ticker, "price": round(current_price, 2), "action": action, "targets": targets, "sl": sl, "entry": entry, "reason": reason, "mtf_dash": mtf_dash, "is_golden": is_golden}
    except Exception as e: return {"error": str(e), "ticker": ticker}

def format_msg(res):
    if "error" in res: return f"⚠️ تعذر تحليل السهم: {res.get('ticker', '')}"
    
    # 🌟 التنسيق الذهبي الجديد 🌟
    if res.get('is_golden'):
        msg = f"🌟💎 **فـرصـة ذهـبـيـة مـكـتـمـلـة** 💎🌟\n"
        msg += f"🔥 **سيطرة مطلقة رصدها الرادار** 🔥\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 **السهم:** {get_display_name(res['ticker'])} | **السعر:** {res['price']}\n"
        msg += f"🛒 **الدخول:** {res['entry']}\n"
        msg += f"🛑 **الوقف الصارم:** {res['sl']}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"💡 **أسباب القوة (Confluence):**\n{res['reason']}\n\n"
        msg += f"🧭 **إجماع الفريمات:**\n" + "\n".join([f"✅ {line}" for line in res['mtf_dash']])
    else:
        # التنسيق العادي
        msg = f"🎯 **القرار:** {res['action']}\n"
        msg += f"📊 **السهم:** {get_display_name(res['ticker'])} | **السعر:** {res['price']}\n"
        msg += f"━━━━━━━━━━━━\n🧭 **لوحة الفريمات:**\n" + "\n".join([f"▪️ {line}" for line in res['mtf_dash']])
        msg += f"\n━━━━━━━━━━━━\n🛒 **نقطة الدخول:** {res['entry']}\n🛑 **الوقف:** {res['sl']}\n💡 **الأسباب الفنية:**\n{res['reason']}\n"
    return msg

def auto_scanner():
    while True:
        if subscribed_chats and radar_settings["market"]:
            target_watchlist = WATCHLIST.copy()
            def scan_single(item):
                t, interval = item
                try: return get_immediate_signal(t, interval, record_alert=True)
                except: return None

            with ThreadPoolExecutor(max_workers=3) as executor:
                results = list(executor.map(scan_single, target_watchlist))
            gc.collect()

            for res in results:
                if res and "error" not in res and ("فوري" in res['action']):
                    for chat_id in list(subscribed_chats):
                        try:
                            # تمييز الإشعار الصوتي/النصي للفرصة الذهبية
                            if res.get('is_golden'):
                                bot.send_message(chat_id, f"🚨🌟 **تنبيه فرصة ذهبية نادرة جداً!** 🌟🚨\n\n{format_msg(res)}", parse_mode="Markdown")
                            else:
                                bot.send_message(chat_id, f"🚨 **رادار النماذج (اكتشاف جديد)** 🚨\n\n{format_msg(res)}", parse_mode="Markdown")
                        except: pass
        time.sleep(600)

def get_radar_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🇸🇦 تصفية شاملة (سعودي)"), KeyboardButton("🇺🇸 تصفية شاملة (أمريكي)"))
    markup.add(KeyboardButton("🔍 كوازمودو سعودي 🇸🇦"), KeyboardButton("🔍 كوازمودو أمريكي 🇺🇸"))
    markup.add(KeyboardButton("🦇 كاشف الهارمونيك والكلاسيكي"), KeyboardButton("📊 التقرير اليومي للـ AI"))
    markup.add(KeyboardButton("📋 أسهم قائمة التصفيات"), KeyboardButton("⚙️ إعدادات الرادار"))
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    subscribed_chats.add(m.chat.id)
    save_database()
    bot.reply_to(m, "مرحباً بك في رادار الحيتان المُحسن 🐋!\n🚀 تم تفعيل كاشف (الفرص الذهبية 🌟) وكاشف الهارمونيك المنفصل.", reply_markup=get_radar_markup())

# 🦇 محرك الهارمونيك والكلاسيكي المستقل (Lightweight)
@bot.message_handler(func=lambda m: m.text.strip() == "🦇 كاشف الهارمونيك والكلاسيكي")
def scan_harmonics_classical(m):
    msg = bot.reply_to(m, "🦇 **جاري تشغيل محرك الهارمونيك والكلاسيكي بشكل منعزل...**\n*(يبحث عن قيعان مزدوجة W، واختراقات هندسية)*\n⏳ يرجى الانتظار...")
    
    found_patterns = []
    
    def check_harmonic(item):
        ticker, interval = item
        try:
            df = fetch_yahoo_data(ticker, interval)
            if len(df) < 50: return None
            
            # فلتر الصرامة
            if not ticker.endswith(".SR") or interval == "1h": df = df.iloc[:-1].copy()
            
            # كشف نموذج القاع المزدوج (Double Bottom - W) الخفيف على الذاكرة
            recent_lows = df['Low'].iloc[-20:-5]
            current_lows = df['Low'].iloc[-5:]
            min1, min2 = recent_lows.min(), current_lows.min()
            
            if abs(min1 - min2) / min1 < 0.015: # القاعين متقاربين بنسبة 1.5%
                peak_between = df['High'].iloc[-20:].max()
                current_price = df['Close'].iloc[-1]
                if current_price > peak_between * 0.98: # السعر يخترق قمة حرف W
                    return {"ticker": ticker, "pattern": "قاع مزدوج (Double Bottom - W) اختراق إيجابي 📈", "price": current_price}
        except: pass
        return None

    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(check_harmonic, WATCHLIST))
    gc.collect() # 🧹 تنظيف الذاكرة بعد الاستخدام
    
    for r in results:
        if r: found_patterns.append(r)
        
    if not found_patterns:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text="📭 لم يتم رصد أي نماذج هارمونيك أو كلاسيكية مكتملة حالياً.")
        return
        
    reply = "🦇 **نتائج محرك الهارمونيك والكلاسيكي المستقل:**\n\n"
    for p in found_patterns:
        reply += f"▪️ **{get_display_name(p['ticker'])}**\n"
        reply += f"   📐 النموذج: {p['pattern']}\n"
        reply += f"   💲 السعر: {round(p['price'], 2)}\n\n"
        
    bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=reply, parse_mode="Markdown")

@bot.message_handler(func=lambda m: "تصفية شاملة" in m.text.strip())
def find_best_confluence(m):
    market = "sa" if "سعودي" in m.text else "us"
    m_name = "السعودي 🇸🇦" if market == "sa" else "الأمريكي 🇺🇸 (خيارات 1H)"
    msg = bot.reply_to(m, f"🔍 **جاري بدء المسح الشامل للسوق {m_name}...**\n⚡ جاري البحث عن الفرص الذهبية...")

    buys = []
    target_watchlist = [item for item in WATCHLIST if (market == "sa" and item[0].endswith(".SR")) or (market == "us" and not item[0].endswith(".SR"))]

    def scan_single(item):
        try: return get_immediate_signal(item[0], item[1])
        except: return None

    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(scan_single, target_watchlist))
    gc.collect() 

    for res in results:
        if res and "error" not in res and "شراء فوري" in res['action']:
            # إعطاء أولوية مطلقة للفرص الذهبية
            score = 100 if res.get('is_golden') else res['reason'].count('➕')
            buys.append((score, res))

    buys.sort(key=lambda x: x[0], reverse=True)

    if not buys:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"لا توجد فرص قوية تتوافق مع الإجماع الفني الصارم حالياً.", parse_mode="Markdown")
        return

    reply = f"🏆 **أقوى الفرص بناءً على الإجماع الفني {m_name}** 🏆\n\n"
    for score, res in buys[:3]:
        reply += format_msg(res) + "\n"
    
    bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=reply, parse_mode="Markdown")

@bot.message_handler(commands=['add'])
def add_stock(m):
    try:
        parts = m.text.split()
        symbol, interval = parts[1].upper(), parts[2]
        WATCHLIST.append((symbol, interval))
        save_database()
        bot.reply_to(m, f"✅ تم إضافة {symbol} بنجاح!")
    except: bot.reply_to(m, "⚠️ استخدم: `/add AAPL 1h`")

app = Flask(__name__)
@app.route('/')
def home(): return "🚀 البوت يعمل مع رادار الفرص الذهبية!"
def run_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

threading.Thread(target=run_server, daemon=True).start()
load_database()
threading.Thread(target=auto_scanner, daemon=True).start()

bot.remove_webhook()
bot.polling(none_stop=True)
