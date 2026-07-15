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
    ("1010.SR", "1d"), ("1020.SR", "1d"), ("1030.SR", "1d"), ("1050.SR", "1d"),
    ("1060.SR", "1d"), ("1120.SR", "1d"), ("1140.SR", "1d"), ("1150.SR", "1d"),
    ("1180.SR", "1d"), ("1211.SR", "1d"), ("1212.SR", "1d"), ("1301.SR", "1d"),
    ("1302.SR", "1d"), ("1304.SR", "1d"), ("1320.SR", "1d"), ("1810.SR", "1d"), 
    ("1820.SR", "1d"), ("1830.SR", "1d"), ("1832.SR", "1d"), ("1833.SR", "1d"), 
    ("2002.SR", "1d"), ("2010.SR", "1d"), ("2020.SR", "1d"), ("2040.SR", "1d"), 
    ("2060.SR", "1d"), ("2062.SR", "1d"), ("2082.SR", "1d"), ("2110.SR", "1d"), 
    ("2120.SR", "1d"), ("2130.SR", "1d"), ("2140.SR", "1d"), ("2170.SR", "1d"), 
    ("2180.SR", "1d"), ("2190.SR", "1d"), ("2200.SR", "1d"), ("2222.SR", "1d"), 
    ("2223.SR", "1d"), ("2250.SR", "1d"), ("2270.SR", "1d"), ("2280.SR", "1d"), 
    ("2281.SR", "1d"), ("2282.SR", "1d"), ("2290.SR", "1d"), ("2310.SR", "1d"), 
    ("2320.SR", "1d"), ("2330.SR", "1d"), ("2350.SR", "1d"), ("2360.SR", "1d"), 
    ("2370.SR", "1d"), ("2380.SR", "1d"), ("2381.SR", "1d"), ("4002.SR", "1d"), 
    ("4005.SR", "1d"), ("4006.SR", "1d"), ("4015.SR", "1d"), ("4017.SR", "1d"), 
    ("4030.SR", "1d"), ("4050.SR", "1d"), ("4072.SR", "1d"), ("4090.SR", "1d"), 
    ("4100.SR", "1d"), ("4110.SR", "1d"), ("4140.SR", "1d"), ("4161.SR", "1d"), 
    ("4162.SR", "1d"), ("4163.SR", "1d"), ("4164.SR", "1d"), ("4190.SR", "1d"), 
    ("4210.SR", "1d"), ("4250.SR", "1d"), ("4260.SR", "1d"), ("4263.SR", "1d"), 
    ("4300.SR", "1d"), ("4322.SR", "1d"), ("4323.SR", "1d"), ("6004.SR", "1d"), 
    ("6010.SR", "1d"), ("6014.SR", "1d"), ("6060.SR", "1d"), ("7010.SR", "1d"), 
    ("7020.SR", "1d"), ("7030.SR", "1d"), ("7040.SR", "1d"), ("7201.SR", "1d"), 
    ("7202.SR", "1d"), ("8010.SR", "1d"), ("8012.SR", "1d"), ("8030.SR", "1d"), 
    ("8040.SR", "1d"), ("8070.SR", "1d"), ("8230.SR", "1d")
]

ARABIC_TICKERS = {
    "الرياض": "1010.SR", "الجزيرة": "1020.SR", "الاستثمار": "1030.SR", "الفرنسي": "1050.SR",
    "الاول": "1060.SR", "الراجحي": "1120.SR", "البلاد": "1140.SR", "الانماء": "1150.SR", 
    "الاهلي": "1180.SR", "معادن": "1211.SR", "استرا": "1212.SR", "اسلاك": "1301.SR", 
    "بوان": "1302.SR", "اليمامة": "1304.SR", "انابيب الشرق": "1320.SR", "سيرا": "1810.SR", 
    "الحكير": "1820.SR", "لجام": "1830.SR", "صدر": "1832.SR", "مهارة": "1833.SR", 
    "سابك": "2002.SR", "سابك للمغذيات": "2010.SR", "سافكو": "2020.SR", "الخزف": "2040.SR", 
    "التصنيع": "2060.SR", "الكيميائية": "2062.SR", "اكوا باور": "2082.SR", "الكابلات": "2110.SR", 
    "المتطورة": "2120.SR", "صدق": "2130.SR", "ايان": "2140.SR", "اللجين": "2170.SR", 
    "فيبكو": "2180.SR", "سيسكو": "2190.SR", "انابيب السعودية": "2200.SR", "ارامكو": "2222.SR", 
    "لوبريف": "2223.SR", "المجموعة": "2250.SR", "سدافكو": "2270.SR", "المراعي": "2280.SR", 
    "التنمية": "2281.SR", "المطاحن": "2282.SR", "ينساب": "2290.SR", "سبكيم": "2310.SR", 
    "البابطين": "2320.SR", "المتقدمة": "2330.SR", "كيان": "2350.SR", "الفخارية": "2360.SR", 
    "مسك": "2370.SR", "بترو رابغ": "2380.SR", "الحفر": "2381.SR", "دله": "4002.SR", 
    "رعاية": "4005.SR", "المواساة": "4006.SR", "جمجوم": "4015.SR", "فقيه": "4017.SR", 
    "البحري": "4030.SR", "ساسكو": "4050.SR", "ام بي سي": "4072.SR", "طيبة": "4090.SR", 
    "مكة": "4100.SR", "باتك": "4110.SR", "صادرات": "4140.SR", "بن داود": "4161.SR", 
    "المنجم": "4162.SR", "الدواء": "4163.SR", "النهدي": "4164.SR", "جرير": "4190.SR", 
    "بوبا": "4210.SR", "جبل عمر": "4250.SR", "المتحدة": "4260.SR", "سال": "4263.SR", 
    "دار الاركان": "4300.SR", "رتال": "4322.SR", "سمو": "4323.SR", "التموين": "6004.SR",
    "نادك": "6010.SR", "الامار": "6014.SR", "الشرقية للتنمية": "6060.SR", "اس تي سي": "7010.SR", 
    "موبايلي": "7020.SR", "زين": "7030.SR", "عذيب": "7040.SR", "بحر العرب": "7201.SR", 
    "سلوشنز": "7202.SR", "التعاونية": "8010.SR", "اعادة": "8012.SR", "ميدغلف": "8030.SR", 
    "اليانز": "8040.SR", "الدرع العربي": "8070.SR", "تكافل الراجحي": "8230.SR"
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

def log_quasimodo_setup(ticker, name, direction, interval, price, details):
    today_str = date.today().strftime('%Y-%m-%d')
    setup_data = {"ticker": ticker, "name": name, "direction": direction, "interval": interval, "price": price, "details": details, "timestamp": datetime.now().isoformat()}
    if today_str not in in_memory_daily_quasimodo: in_memory_daily_quasimodo[today_str] = []
    if not any(x['ticker'] == ticker and x['interval'] == interval and x['direction'] == direction for x in in_memory_daily_quasimodo[today_str]):
        in_memory_daily_quasimodo[today_str].append(setup_data)
    if mongo_connected:
        try: quasimodo_col.update_one({"date": today_str}, {"$addToSet": {"setups": setup_data}}, upsert=True)
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

def get_immediate_signal(ticker, interval="1d", record_alert=False):
    try:
        df = fetch_yahoo_data(ticker, interval)
        if df.empty or len(df) < 100: return {"error": "بيانات غير كافية."}
        
        # 🔒 تطبيق فلتر التأكيد الصارم للسوق الأمريكي (فريم الساعة 1H)
        if not ticker.endswith(".SR") or interval == "1h":
            df = df.iloc[:-1].copy()
            
        current_price = float(df['Close'].iloc[-1])
        df['Body'] = abs(df['Close'] - df['Open'])
        
        df['Sweep_Bull'] = df['Low'] < df['Low'].rolling(15).min().shift(1)
        df['Sweep_Bear'] = df['High'] > df['High'].rolling(15).max().shift(1)
        df['CHoCH_Bull'] = df['Close'] > df['High'].rolling(8).max().shift(1)
        df['CHoCH_Bear'] = df['Close'] < df['Low'].rolling(8).min().shift(1)
        df['Bullish_FVG'] = df['Low'] > df['High'].shift(2)
        df['Bearish_FVG'] = df['High'] < df['Low'].shift(2)
        
        safe_range = (df['High'] - df['Low']).replace(0, 0.0001)
        wyckoff_acc = (df['Close'] < df['Close'].rolling(50).mean()) & (df['Volume'] > 1.5 * df['Volume'].rolling(20).mean()) & (((df['Close'] - df['Low']) / safe_range) > 0.75)
        wyckoff_dist = (df['Close'] > df['Close'].rolling(50).mean()) & (df['Volume'] > 1.5 * df['Volume'].rolling(20).mean()) & (((df['High'] - df['Close']) / safe_range) > 0.75)
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['BB_Lower'] = df['SMA_20'] - (2 * df['Close'].rolling(20).std())
        df['BB_Upper'] = df['SMA_20'] + (2 * df['Close'].rolling(20).std())
        
        is_qm_bull = (df['Sweep_Bull'].tail(5).any()) and (df['CHoCH_Bull'].iloc[-1])
        is_qm_bear = (df['Sweep_Bear'].tail(5).any()) and (df['CHoCH_Bear'].iloc[-1])
        
        bull, bear = [], []
        if is_qm_bull: 
            bull.append("👑 SMC: كوازمودو شرائي (تصفية + CHoCH)")
            log_quasimodo_setup(ticker, get_display_name(ticker), "شرائي 🟢", interval, current_price, "كوازمودو صاعد")
        if is_qm_bear:
            bear.append("👑 SMC: كوازمودو بيعي (تصفية + CHoCH)")
            log_quasimodo_setup(ticker, get_display_name(ticker), "بيعي 🔴", interval, current_price, "كوازمودو هابط")

        if df['Bullish_FVG'].iloc[-1]: bull.append("SMC: فجوة سيولة شرائية (FVG)")
        if df['Bearish_FVG'].iloc[-1]: bear.append("SMC: فجوة سيولة بيعية (FVG)")
        if wyckoff_acc.iloc[-1]: bull.append("📊 وايكوف: تجميع وسيولة ضخمة بالقاع")
        if wyckoff_dist.iloc[-1]: bear.append("📊 وايكوف: تصريف وسيولة بالقمة")
        if float(df['Low'].iloc[-1]) < float(df['BB_Lower'].iloc[-1]): bull.append("بولنجر: الأدنى خارج البولنجر باند 📉")
        if float(df['High'].iloc[-1]) > float(df['BB_Upper'].iloc[-1]): bear.append("بولنجر: الأعلى خارج البولنجر باند 📈")
        
        t_1h = get_analysis_data(ticker, '1h')
        t_4h = get_analysis_data(ticker, '4h')
        t_1d = get_analysis_data(ticker, '1d')
        
        mtf_dash = [f"1س: {t_1h['label']}", f"4س: {t_4h['label']}", f"يومي: {t_1d['label']}"]
        mtf_buy_ok = (t_4h['trend'] == "صاعد") and (t_1d['trend'] == "صاعد")
        mtf_sell_ok = (t_4h['trend'] == "هابط") and (t_1d['trend'] == "هابط")
        
        is_golden = False
        action, targets, sl, entry, reason = "انتظار 🟡", "", "", "غير محدد", "تذبذب."
        
        if len(bull) >= 2 or is_qm_bull:
            if not mtf_buy_ok:
                action, reason = "مراقبة 🟡 (إلغاء شراء)", "\n➕ ".join([""] + bull).strip() + "\n⚠️ **الاتجاه العام هابط!**"
            else:
                action = "شراء فوري 🟢"
                # 🌟 التحقق من الفرصة الذهبية
                if is_qm_bull and mtf_buy_ok and (wyckoff_acc.iloc[-1] or df['Bullish_FVG'].iloc[-1]): is_golden = True
                reason = "\n➕ ".join([""] + bull).strip()
                entry = str(round(current_price, 2))
                exact_sl = round(float(df['Low'].tail(15).min()), 2)
                sl = f"{exact_sl} (كسر الأدنى)"
                targets = f"🎯 هدف مفتوح (مقاومة تالية)"
                
        elif len(bear) >= 2 or is_qm_bear:
            if not mtf_sell_ok:
                action, reason = "مراقبة 🟡 (إلغاء بيع)", "\n➖ ".join([""] + bear).strip() + "\n⚠️ **الاتجاه العام صاعد!**"
            else:
                action = "بيع فوري 🔴"
                reason = "\n➖ ".join([""] + bear).strip()
                entry = str(round(current_price, 2))
                exact_sl = round(float(df['High'].tail(15).max()), 2)
                sl = f"{exact_sl} (اختراق الأعلى)"
                targets = f"🎯 هدف مفتوح (دعم تالي)"

        if record_alert and ("فوري" in action) and ticker not in active_trades:
            try:
                exact_entry = float(entry.split()[0])
                model_name = reason.split('\n')[0].replace('➕ ', '').replace('➖ ', '')
                trade_type = "buy" if "شراء" in action else "sell"
                retest_alerts[ticker] = {"price": exact_entry, "action": action, "model": model_name, "type": trade_type, "target": current_price * 1.05, "sl": exact_sl}
                save_database()
            except: pass

        return {"ticker": ticker, "price": round(current_price, 2), "action": action, "targets": targets, "sl": sl, "entry": entry, "reason": reason, "mtf_dash": mtf_dash, "is_golden": is_golden}
    except Exception as e: return {"error": str(e), "ticker": ticker}

def format_msg(res):
    if "error" in res: return f"⚠️ تعذر تحليل السهم: {res.get('ticker', '')}"
    if res.get('is_golden'):
        msg = f"🌟💎 **فـرصـة ذهـبـيـة مـكـتـمـلـة** 💎🌟\n🔥 **سيطرة مطلقة رصدها الرادار** 🔥\n━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 **السهم:** {get_display_name(res['ticker'])} | **السعر:** {res['price']}\n🛒 **الدخول:** {res['entry']}\n🛑 **الوقف الصارم:** {res['sl']}\n━━━━━━━━━━━━━━━━━━━━\n💡 **أسباب القوة (Confluence):**\n{res['reason']}\n\n🧭 **إجماع الفريمات:**\n" + "\n".join([f"✅ {line}" for line in res['mtf_dash']])
    else:
        msg = f"🎯 **القرار:** {res['action']}\n📊 **السهم:** {get_display_name(res['ticker'])} | **السعر:** {res['price']}\n━━━━━━━━━━━━\n🧭 **لوحة الفريمات:**\n" + "\n".join([f"▪️ {line}" for line in res['mtf_dash']])
        msg += f"\n━━━━━━━━━━━━\n🛒 **نقطة الدخول:** {res['entry']}\n🛑 **الوقف:** {res['sl']}\n💡 **الأسباب الفنية:**\n{res['reason']}\n"
    return msg

def auto_scanner():
    while True:
        if subscribed_chats and radar_settings["market"]:
            target_watchlist = WATCHLIST.copy()
            def scan_single(item):
                try: return get_immediate_signal(item[0], item[1], record_alert=True)
                except: return None

            with ThreadPoolExecutor(max_workers=3) as executor:
                results = list(executor.map(scan_single, target_watchlist))
            gc.collect()

            for res in results:
                if res and "error" not in res and ("فوري" in res['action']):
                    for chat_id in list(subscribed_chats):
                        try:
                            if res.get('is_golden'): bot.send_message(chat_id, f"🚨🌟 **تنبيه فرصة ذهبية نادرة جداً!** 🌟🚨\n\n{format_msg(res)}", parse_mode="Markdown")
                            else: bot.send_message(chat_id, f"🚨 **رادار النماذج (اكتشاف جديد)** 🚨\n\n{format_msg(res)}", parse_mode="Markdown")
                        except: pass
        time.sleep(600)

def check_new_day():
    global todays_picks, todays_sniper_picks, last_update_date, notified_retests, in_memory_daily_quasimodo
    if date.today() > last_update_date:
        todays_picks.clear()
        todays_sniper_picks.clear()
        notified_retests.clear()
        in_memory_daily_quasimodo = {date.today().strftime('%Y-%m-%d'): []} 
        last_update_date = date.today()

def get_radar_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🇸🇦 تصفية شاملة (سعودي)"), KeyboardButton("🇺🇸 تصفية شاملة (أمريكي)"))
    markup.add(KeyboardButton("🔍 كوازمودو سعودي 🇸🇦"), KeyboardButton("🔍 كوازمودو أمريكي 🇺🇸"))
    markup.add(KeyboardButton("🦇 كاشف الهارمونيك والكلاسيكي"), KeyboardButton("📊 التقرير اليومي للـ AI"))
    markup.add(KeyboardButton("📋 أسهم قائمة التصفيات"), KeyboardButton("⚙️ إعدادات الرادار"))
    return markup

def get_inline_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    btn_sa = InlineKeyboardButton(f"{'✅' if radar_settings['sa'] else '❌'} رادار السوق السعودي 🇸🇦", callback_data="toggle_sa")
    btn_us = InlineKeyboardButton(f"{'✅' if radar_settings['us'] else '❌'} رادار السوق الأمريكي 🇺🇸", callback_data="toggle_us")
    btn_market = InlineKeyboardButton(f"{'✅' if radar_settings['market'] else '❌'} رادار استكشاف النماذج 📡", callback_data="toggle_market")
    btn_sniper = InlineKeyboardButton(f"{'✅' if radar_settings['sniper'] else '❌'} رادار القناص (الدخول) 🎯", callback_data="toggle_sniper")
    markup.add(btn_sa, btn_us, btn_market, btn_sniper)
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    subscribed_chats.add(m.chat.id)
    save_database()
    bot.reply_to(m, "مرحباً بك في رادار الحيتان المُحسن 🐋!\n🚀 تم تفعيل كاشف (الفرص الذهبية 🌟) وكاشف الهارمونيك المنفصل وجميع أدوات الذكاء الاصطناعي.", reply_markup=get_radar_markup())

# --- دوال الأزرار (التي كانت محذوفة بالخطأ وتم إرجاعها) ---

@bot.message_handler(func=lambda m: m.text.strip() == "🦇 كاشف الهارمونيك والكلاسيكي")
def scan_harmonics_classical(m):
    msg = bot.reply_to(m, "🦇 **جاري تشغيل محرك الهارمونيك والكلاسيكي بشكل منعزل...**\n*(يبحث عن قيعان مزدوجة W، واختراقات هندسية)*\n⏳ يرجى الانتظار...")
    found_patterns = []
    def check_harmonic(item):
        ticker, interval = item
        try:
            df = fetch_yahoo_data(ticker, interval)
            if not ticker.endswith(".SR") or interval == "1h": df = df.iloc[:-1].copy()
            if len(df) < 50: return None
            recent_lows = df['Low'].iloc[-20:-5]
            current_lows = df['Low'].iloc[-5:]
            min1, min2 = recent_lows.min(), current_lows.min()
            if abs(min1 - min2) / min1 < 0.015: 
                peak_between = df['High'].iloc[-20:].max()
                current_price = df['Close'].iloc[-1]
                if current_price > peak_between * 0.98:
                    return {"ticker": ticker, "pattern": "قاع مزدوج (Double Bottom - W) اختراق إيجابي 📈", "price": current_price}
        except: pass
        return None

    with ThreadPoolExecutor(max_workers=3) as executor: results = list(executor.map(check_harmonic, WATCHLIST))
    gc.collect() 
    for r in results:
        if r: found_patterns.append(r)
    if not found_patterns:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text="📭 لم يتم رصد أي نماذج هارمونيك أو كلاسيكية مكتملة حالياً.")
        return
    reply = "🦇 **نتائج محرك الهارمونيك والكلاسيكي المستقل:**\n\n"
    for p in found_patterns: reply += f"▪️ **{get_display_name(p['ticker'])}**\n   📐 النموذج: {p['pattern']}\n   💲 السعر: {round(p['price'], 2)}\n\n"
    bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=reply, parse_mode="Markdown")

@bot.message_handler(func=lambda m: "كوازمودو" in m.text.strip())
def find_quasimodo_only(m):
    market = "sa" if "سعودي" in m.text else "us"
    m_name = "السعودي 🇸🇦" if market == "sa" else "الأمريكي 🇺🇸"
    msg = bot.reply_to(m, f"🔍 **جاري تشغيل كاشف كوازمودو في السوق {m_name}...**\n⚡ تم تفعيل فحص الشموع المغلقة الصارم لمنع التراجع الفني...")
    target_watchlist = [item for item in WATCHLIST if (market == "sa" and item[0].endswith(".SR")) or (market == "us" and not item[0].endswith(".SR"))]
    def scan_for_qm(item):
        ticker, interval = item
        try:
            df = fetch_yahoo_data(ticker, interval)
            if not ticker.endswith(".SR") or interval == "1h": df = df.iloc[:-1].copy()
            if len(df) < 50: return None
            df['Sweep_Bull'] = df['Low'] < df['Low'].rolling(15).min().shift(1)
            df['Sweep_Bear'] = df['High'] > df['High'].rolling(15).max().shift(1)
            df['CHoCH_Bull'] = df['Close'] > df['High'].rolling(8).max().shift(1)
            df['CHoCH_Bear'] = df['Close'] < df['Low'].rolling(8).min().shift(1)
            is_qm_bull = (df['Sweep_Bull'].tail(5).any()) and (df['CHoCH_Bull'].iloc[-1])
            is_qm_bear = (df['Sweep_Bear'].tail(5).any()) and (df['CHoCH_Bear'].iloc[-1])
            current_p = round(float(df['Close'].iloc[-1]), 2)
            if is_qm_bull: return {"ticker": ticker, "type": "👑 كوازمودو شرائي (صعود)", "price": current_p, "interval": interval}
            elif is_qm_bear: return {"ticker": ticker, "type": "🩸 كوازمودو بيعي (هبوط)", "price": current_p, "interval": interval}
        except: pass
        return None
    with ThreadPoolExecutor(max_workers=3) as executor: results = list(executor.map(scan_for_qm, target_watchlist))
    gc.collect() 
    qm_found = [r for r in results if r is not None]
    if not qm_found:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"📭 لم يتم رصد أي نموذج كوازمودو مكتمل حالياً في السوق {m_name}.", parse_mode="Markdown")
        return
    reply = f"🎯 **نتائج رادار كوازمودو النشط في السوق {m_name}:**\n\n"
    for idx, item in enumerate(qm_found, 1): reply += f"{idx}. **{get_display_name(item['ticker'])}** ({item['interval']})\n   🔹 النموذج: {item['type']}\n   💲 سعر الرصد: {item['price']}\n\n"
    bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=reply, parse_mode="Markdown")

@bot.message_handler(func=lambda m: "تصفية شاملة" in m.text.strip())
def find_best_confluence(m):
    check_new_day()
    market = "sa" if "سعودي" in m.text else "us"
    m_name = "السعودي 🇸🇦" if market == "sa" else "الأمريكي 🇺🇸"
    msg = bot.reply_to(m, f"🔍 **جاري بدء المسح الشامل للسوق {m_name}...**\n⚡ جاري البحث عن الفرص الذهبية...")
    buys, sells = [], []
    target_watchlist = [item for item in WATCHLIST if (market == "sa" and item[0].endswith(".SR")) or (market == "us" and not item[0].endswith(".SR"))]
    def scan_single(item):
        try: return get_immediate_signal(item[0], item[1])
        except: return None
    with ThreadPoolExecutor(max_workers=3) as executor: results = list(executor.map(scan_single, target_watchlist))
    gc.collect() 
    for res in results:
        if res and "error" not in res:
            if "شراء فوري" in res['action']:
                score = 100 if res.get('is_golden') else res['reason'].count('➕')
                buys.append((score, res))
            elif "بيع فوري" in res['action']:
                score = 100 if res.get('is_golden') else res['reason'].count('➖')
                sells.append((score, res))
    buys.sort(key=lambda x: x[0], reverse=True)
    sells.sort(key=lambda x: x[0], reverse=True)
    if not buys and not sells:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"لا توجد فرص قوية تتوافق مع الإجماع الفني الصارم حالياً.", parse_mode="Markdown")
        return
    reply = f"🏆 **أقوى الفرص بناءً على الإجماع الفني {m_name}** 🏆\n\n"
    if buys[:2]:
        reply += "🟢 **أقوى فرص الشراء (Call):**\n\n"
        for score, res in buys[:2]: reply += f"{format_msg(res)}\n"
    if sells[:2]:
        reply += "🔴 **أقوى فرص البيع (Put):**\n\n"
        for score, res in sells[:2]: reply += f"{format_msg(res)}\n"
    bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=reply, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text.strip() == "📊 التقرير اليومي للـ AI")
def show_daily_ai_report(m):
    today_str = date.today().strftime('%Y-%m-%d')
    reply = f"🧠 **التقرير اليومي المفصل لأداء الذكاء الاصطناعي ({today_str}):**\n━━━━━━━━━━━━━━━━━━━━\n"
    reply += f"💾 **سجل كوازمودو المكتشف لليوم:**\n"
    setups_today = []
    if mongo_connected:
        try:
            today_log = quasimodo_col.find_one({"date": today_str})
            if today_log and "setups" in today_log: setups_today = today_log["setups"]
        except: pass
    if not setups_today: setups_today = in_memory_daily_quasimodo.get(today_str, [])
    if not setups_today: reply += "📭 لم يتم رصد أو تسجيل أي نماذج كوازمودو حتى الآن اليوم.\n"
    else:
        reply += f"🔥 تم رصد **{len(setups_today)}** نموذج كوازمودو اليوم:\n\n"
        for idx, item in enumerate(setups_today, 1): reply += f"{idx}. **{item['name']}** ({item['interval']})\n   🏷️ الاتجاه: **{item['direction']}**\n   💲 السعر: {item['price']}\n   💡 التفاصيل: {item['details']}\n\n"
    bot.reply_to(m, reply, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text.strip() == "⚙️ إعدادات الرادار")
def radar_panel(m):
    bot.reply_to(m, "⚙️ **غرفة التحكم المستقلة:**\nاضغط على أي زر لتشغيل أو إيقاف الخدمة:", reply_markup=get_inline_markup(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_"))
def toggle_radar_setting(call):
    key = call.data.split("_")[1]
    radar_settings[key] = not radar_settings[key]
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_inline_markup())

@bot.message_handler(func=lambda m: m.text.strip() == "📋 أسهم قائمة التصفيات")
def show_todays_picks(m):
    check_new_day()
    if not todays_picks: bot.reply_to(m, "📭 القائمة فارغة اليوم.")
    else:
        reply = f"📋 **قائمة التصفيات لتاريخ ({date.today().strftime('%d-%m-%Y')}):**\n\n"
        for idx, (t, act) in enumerate(todays_picks.items(), 1): reply += f"{idx}. {get_display_name(t)} ⬅️ **{act}**\n"
        bot.reply_to(m, reply, parse_mode="Markdown")

@bot.message_handler(commands=['add'])
def add_stock(m):
    try:
        parts = m.text.split()
        symbol, interval = parts[1].upper(), parts[2]
        WATCHLIST.append((symbol, interval))
        save_database()
        bot.reply_to(m, f"✅ تم إضافة {symbol} بنجاح!")
    except: bot.reply_to(m, "⚠️ استخدم: `/add AAPL 1h`")

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
    msg = "📋 **قائمة المراقبة الحالية:**\n" + "\n".join([f"▪| {x[0]} ({x[1]})" for x in WATCHLIST])
    bot.reply_to(m, msg, parse_mode="Markdown")

# --- دالة التحليل اليدوي (لأي نص يتم كتابته مثل TSLA) يجب أن تكون دائماً في الأسفل ---
@bot.message_handler(func=lambda m: True)
def analyze_manual_stock(m):
    text = m.text.strip().upper()
    ignore = ["🇸🇦 تصفية شاملة (سعودي)", "🇺🇸 تصفية شاملة (أمريكي)", "⚙️ إعدادات الرادار", "🎯 أسهم القناص (اليوم)", "📋 أسهم قائمة التصفيات", "📊 التقرير اليومي للـ AI", "🔍 كوازمودو سعودي 🇸🇦", "🔍 كوازمودو أمريكي 🇺🇸", "🦇 كاشف الهارمونيك والكلاسيكي"]
    if text in ignore or text.startswith("/"): return
    
    t = ARABIC_TICKERS.get(text.replace("أ", "ا").replace("إ", "ا").replace("ة", "ه"), text)
    if t.isdigit() and len(t) == 4: t += ".SR"

    msg = bot.reply_to(m, f"⏳ جاري الفحص المعمق لـ {text}...")
    interval = "1d" if t.endswith(".SR") else "1h"
    res = get_immediate_signal(t, interval, record_alert=True)
    
    if res and "error" not in res:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=format_msg(res), parse_mode="Markdown")
        if not any(item[0] == t for item in WATCHLIST):
            WATCHLIST.append((t, interval))
            save_database()
            bot.send_message(m.chat.id, f"✅ **تم تحديث الذاكرة:**\nتم إدراج السهم ({t}) تلقائياً للمراقبة المستمرة!", parse_mode="Markdown")
    else:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"⚠️ تعذر تحليل السهم.\n**السبب:** {res.get('error', 'السهم غير مدرج أو البيانات غير كافية.')}")

app = Flask(__name__)
@app.route('/')
def home(): return "🚀 البوت يعمل بجميع ميزاته ودواله بنجاح!"
def run_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

threading.Thread(target=run_server, daemon=True).start()
load_database()
threading.Thread(target=auto_scanner, daemon=True).start()

bot.remove_webhook()
bot.polling(none_stop=True)
