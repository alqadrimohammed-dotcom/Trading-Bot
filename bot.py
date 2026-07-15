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
import gc # 🧹 أداة تنظيف الذاكرة العشوائية
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

WATCHLIST = []
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
    data = {
        "active_trades": active_trades,
        "trade_history": trade_history,
        "retest_alerts": retest_alerts,
        "subscribed_chats": list(subscribed_chats),
        "ai_learned_patterns": ai_learned_patterns,
        "watchlist": WATCHLIST
    }
    if mongo_connected:
        try:
            state_col.update_one({"_id": "bot_config"}, {"$set": data}, upsert=True)
        except Exception as e:
            print(f"Error saving to MongoDB: {e}")
    else:
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving DB: {e}")

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
                if saved_watchlist:
                    WATCHLIST = [tuple(x) for x in saved_watchlist]
                else:
                    WATCHLIST = DEFAULT_WATCHLIST.copy()
                return
        except Exception as e:
            print(f"Error loading from MongoDB: {e}")
            
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
                if saved_watchlist:
                    WATCHLIST = [tuple(x) for x in saved_watchlist]
                else:
                    WATCHLIST = DEFAULT_WATCHLIST.copy()
        else:
            WATCHLIST = DEFAULT_WATCHLIST.copy()
    except Exception as e:
        WATCHLIST = DEFAULT_WATCHLIST.copy()
        print(f"Error loading local DB: {e}")

def log_quasimodo_setup(ticker, name, direction, interval, price, details):
    today_str = date.today().strftime('%Y-%m-%d')
    setup_data = {
        "ticker": ticker,
        "name": name,
        "direction": direction,
        "interval": interval,
        "price": price,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    
    if today_str not in in_memory_daily_quasimodo:
        in_memory_daily_quasimodo[today_str] = []
    if not any(x['ticker'] == ticker and x['interval'] == interval and x['direction'] == direction for x in in_memory_daily_quasimodo[today_str]):
        in_memory_daily_quasimodo[today_str].append(setup_data)
        
    if mongo_connected:
        try:
            quasimodo_col.update_one(
                {"date": today_str},
                {"$addToSet": {"setups": setup_data}},
                upsert=True
            )
        except Exception as e:
            print(f"Error logging Quasimodo to MongoDB: {e}")

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
    if len(df) < 50: return {"trend": "عرضي", "models": [], "label": "عرضي ⚪ | توازن"}
    
    c = float(df['Close'].iloc[-1])
    sma50 = float(df['Close'].rolling(50).mean().iloc[-1])
    prev_high = float(df['High'].iloc[-20:-10].max())
    
    if c > prev_high and c > sma50: 
        trend = "صاعد"
        label = "صاعد قوي 🟢 | سيطرة مشترين"
    elif c > sma50: 
        trend = "صاعد"
        label = "صاعد 🟡 | مسار إيجابي"
    elif c < sma50 and c < df['Low'].iloc[-20:-10].min(): 
        trend = "هابط"
        label = "هابط قوي 🔴 | سيطرة بائعين"
    elif c < sma50: 
        trend = "هابط"
        label = "هابط 🟠 | مسار سلبي"
    else: 
        trend = "عرضي"
        label = "عرضي ⚪ | توازن"

    models = []
    df['Body'] = abs(df['Close'] - df['Open'])
    df['Sweep_Bull'] = df['Low'] < df['Low'].rolling(15).min().shift(1)
    df['Sweep_Bear'] = df['High'] > df['High'].rolling(15).max().shift(1)
    df['CHoCH_Bull'] = df['Close'] > df['High'].rolling(8).max().shift(1)
    df['CHoCH_Bear'] = df['Close'] < df['Low'].rolling(8).min().shift(1)
    
    if (df['Sweep_Bull'].tail(5).any()) and (df['CHoCH_Bull'].iloc[-1]): models.append("👑 كوازمودو")
    if (df['Sweep_Bear'].tail(5).any()) and (df['CHoCH_Bear'].iloc[-1]): models.append("🩸 كوازمودو بيعي")
    
    if df['Low'].iloc[-1] > df['High'].shift(2).iloc[-1]: models.append("FVG شرائي")
    if df['High'].iloc[-1] < df['Low'].shift(2).iloc[-1]: models.append("FVG بيعي")
    
    safe_range = (df['High'] - df['Low']).replace(0, 0.0001)
    wyckoff_acc = (df['Close'] < df['Close'].rolling(50).mean()) & (df['Volume'] > 1.5 * df['Volume'].rolling(20).mean()) & (((df['Close'] - df['Low']) / safe_range) > 0.75)
    wyckoff_dist = (df['Close'] > df['Close'].rolling(50).mean()) & (df['Volume'] > 1.5 * df['Volume'].rolling(20).mean()) & (((df['High'] - df['Close']) / safe_range) > 0.75)
    if wyckoff_acc.iloc[-1] or wyckoff_acc.tail(3).any(): models.append("📊 تجميع")
    if wyckoff_dist.iloc[-1] or wyckoff_dist.tail(3).any(): models.append("📉 تصريف")
    
    return {"trend": trend, "models": models, "label": label}

def check_4h_breakout(ticker):
    try:
        df_4h = fetch_yahoo_data(ticker, "4h")
        if len(df_4h) < 50: return None
        res = df_4h['High'].rolling(50).max().shift(2).iloc[-1]
        sup = df_4h['Low'].rolling(50).min().shift(2).iloc[-1]
        
        c1, c2 = df_4h['Close'].iloc[-1], df_4h['Close'].iloc[-2]
        
        if c1 > res and c2 > res:
            return {"type": "اختراق مقاومة رئيسية وإغلاق شمعتين 4س 🚀", "level": round(res, 2), "signal": "buy"}
        elif c1 < sup and c2 < sup:
            return {"type": "كسر دعم رئيسي وإغلاق شمعتين 4س 🩸", "level": round(sup, 2), "signal": "sell"}
    except: return None
    return None

def ai_market_study():
    global ai_learned_patterns
    for ticker, interval in WATCHLIST:
        try:
            df = fetch_yahoo_data(ticker, interval)
            if df.empty or len(df) < 50: continue
            if (df['Close'].iloc[-1] / df['Close'].iloc[-2] - 1) > 0.04:
                pattern_fingerprint = f"Pattern_{datetime.now().strftime('%m%d')}_{ticker}"
                if pattern_fingerprint not in ai_learned_patterns:
                    ai_learned_patterns.append(pattern_fingerprint)
                    save_database()
        except: pass

def get_immediate_signal(ticker, interval="1d", record_alert=False):
    try:
        df = fetch_yahoo_data(ticker, interval)
        if df.empty or len(df) < 100: return {"error": "بيانات غير كافية."}
        current_price = float(df['Close'].iloc[-1])
        
        df['Body'] = abs(df['Close'] - df['Open'])
        df['Lower_Wick'], df['Upper_Wick'] = df[['Open', 'Close']].min(axis=1) - df['Low'], df['High'] - df[['Open', 'Close']].max(axis=1)
        df['Pin_Bull'], df['Pin_Bear'] = (df['Lower_Wick'] > 2 * df['Body']) & (df['Upper_Wick'] < df['Body']), (df['Upper_Wick'] > 2 * df['Body']) & (df['Lower_Wick'] < df['Body'])
        df['Engulf_Bull'] = (df['Close'].shift(1) < df['Open'].shift(1)) & (df['Close'] > df['Open']) & (df['Close'] > df['Open'].shift(1))
        df['Engulf_Bear'] = (df['Close'].shift(1) > df['Open'].shift(1)) & (df['Close'] < df['Open']) & (df['Close'] < df['Open'].shift(1))
        df['Sweep_Bull'], df['Sweep_Bear'] = df['Low'] < df['Low'].rolling(15).min().shift(1), df['High'] > df['High'].rolling(15).max().shift(1)
        df['CHoCH_Bull'], df['CHoCH_Bear'] = df['Close'] > df['High'].rolling(8).max().shift(1), df['Close'] < df['Low'].rolling(8).min().shift(1)
        df['Bullish_FVG'], df['Bearish_FVG'] = df['Low'] > df['High'].shift(2), df['High'] < df['Low'].shift(2)
        
        df['Strong_Move'] = df['Body'] > (2.0 * df['Body'].rolling(10).mean().shift(1))
        df['OB_Demand'] = (df['Close'].shift(1) < df['Open'].shift(1)) & (df['Close'] > df['Open']) & df['Strong_Move']
        df['OB_Supply'] = (df['Close'].shift(1) > df['Open'].shift(1)) & (df['Close'] < df['Open']) & df['Strong_Move']
        at_demand = (not df[df['OB_Demand']].empty) and (float(df[df['OB_Demand']]['Low'].iloc[-1]) * 0.99 <= current_price <= float(df[df['OB_Demand']]['High'].iloc[-1]) * 1.01)
        at_supply = (not df[df['OB_Supply']].empty) and (float(df[df['OB_Supply']]['Low'].iloc[-1]) * 0.99 <= current_price <= float(df[df['OB_Supply']]['High'].iloc[-1]) * 1.01)
        safe_range = (df['High'] - df['Low']).replace(0, 0.0001)
        wyckoff_acc = (df['Close'] < df['Close'].rolling(50).mean()) & (df['Volume'] > 1.5 * df['Volume'].rolling(20).mean()) & (((df['Close'] - df['Low']) / safe_range) > 0.75)
        wyckoff_dist = (df['Close'] > df['Close'].rolling(50).mean()) & (df['Volume'] > 1.5 * df['Volume'].rolling(20).mean()) & (((df['High'] - df['Close']) / safe_range) > 0.75)

        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['BB_Lower'], df['BB_Upper'] = df['SMA_20'] - (2 * df['Close'].rolling(20).std()), df['SMA_20'] + (2 * df['Close'].rolling(20).std())
        df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = (df['Volume'] * df['Typical_Price']).rolling(window=20).sum() / df['Volume'].rolling(window=20).sum()
        
        daily = df.resample('D').agg({'High':'max', 'Low':'min'}).dropna()
        n_res_val = float(daily['High'].iloc[-2]) if (len(daily)>1 and float(daily['High'].iloc[-2])>current_price) else round(current_price * 1.03, 2)
        n_sup_val = float(daily['Low'].iloc[-2]) if (len(daily)>1 and float(daily['Low'].iloc[-2])<current_price) else round(current_price * 0.97, 2)

        bull, bear = [], []
        
        is_qm_bull = (df['Sweep_Bull'].tail(5).any()) and (df['CHoCH_Bull'].iloc[-1])
        is_qm_bear = (df['Sweep_Bear'].tail(5).any()) and (df['CHoCH_Bear'].iloc[-1])
        
        if is_qm_bull:
            bull.append("👑 SMC: كوازمودو شرائي")
            log_quasimodo_setup(ticker, get_display_name(ticker), "شرائي 🟢", interval, current_price, "كوازمودو صاعد (تصفية سيولة القاع مع اختراق CHoCH)")
        elif is_qm_bear:
            bear.append("👑 SMC: كوازمودو بيعي")
            log_quasimodo_setup(ticker, get_display_name(ticker), "بيعي 🔴", interval, current_price, "كوازمودو هابط (تصفية سيولة القمة مع كسر CHoCH)")

        breakout_4h = check_4h_breakout(ticker)
        retest_level = None
        if breakout_4h:
            if breakout_4h["signal"] == "buy": 
                bull.append(f"برايس أكشن: {breakout_4h['type']}")
                retest_level = breakout_4h['level']
            elif breakout_4h["signal"] == "sell": 
                bear.append(f"برايس أكشن: {breakout_4h['type']}")
                retest_level = breakout_4h['level']
        
        if any(ticker in p for p in ai_learned_patterns): 
            bull.append("🧠 الذكاء الاصطناعي: السهم يطابق بصمة نموذج مكتشف ذاتياً")

        if df['Bullish_FVG'].iloc[-1]: bull.append("SMC: فجوة سيولة شرائية (FVG)")
        if at_demand: bull.append("🎯 طلب: ارتداد من منطقة طلب")
        if wyckoff_acc.iloc[-1] or wyckoff_acc.tail(3).any(): bull.append("📊 وايكوف: تجميع وسيولة ضخمة بالقاع")
        if df['Pin_Bull'].iloc[-1] or df['Pin_Bull'].iloc[-2]: bull.append("برايس أكشن: بن بار انعكاسية 🔨")
        if df['Engulf_Bull'].iloc[-1] or df['Engulf_Bull'].iloc[-2]: bull.append("برايس أكشن: ابتلاعية شرائية 🚀")
        if float(df['Low'].iloc[-1]) < float(df['BB_Lower'].iloc[-1]): bull.append("بولنجر: الأدنى خارج البولنجر باند 📉")
        if current_price > float(df['VWAP'].iloc[-1]): bull.append("VWAP: السعر فوق متوسط الحيتان 🐳")

        if df['Bearish_FVG'].iloc[-1]: bear.append("SMC: فجوة سيولة بيعية (FVG)")
        if at_supply: bear.append("🎯 عرض: ارتداد من منطقة عرض")
        if wyckoff_dist.iloc[-1] or wyckoff_dist.tail(3).any(): bear.append("📊 وايكوف: تصريف وسيولة بالقمة")
        if df['Pin_Bear'].iloc[-1] or df['Pin_Bear'].iloc[-2]: bear.append("برايس أكشن: بن بار سلبية 🪫")
        if df['Engulf_Bear'].iloc[-1] or df['Engulf_Bear'].iloc[-2]: bear.append("برايس أكشن: ابتلاعية بيعية 🩸")
        if float(df['High'].iloc[-1]) > float(df['BB_Upper'].iloc[-1]): bear.append("بولنجر: الأعلى خارج البولنجر باند 📈")
        if current_price < float(df['VWAP'].iloc[-1]): bear.append("VWAP: السعر تحت متوسط الحيتان 🐳")

        action, targets, sl, entry, reason, mtf_dash = "انتظار 🟡", "", "", "لم تتحقق شروط", "تذبذب عرضي.", []
        exact_target, exact_sl = 0, 0
        
        t_1h = get_analysis_data(ticker, '1h')
        t_4h = get_analysis_data(ticker, '4h')
        t_1d = get_analysis_data(ticker, '1d')
        t_1wk = get_analysis_data(ticker, '1wk')
        
        mtf_dash.append(f"1س: {t_1h['label']}" + (f" ⟵ ({' | '.join(t_1h['models'])})" if t_1h['models'] else ""))
        mtf_dash.append(f"4س: {t_4h['label']}" + (f" ⟵ ({' | '.join(t_4h['models'])})" if t_4h['models'] else ""))
        mtf_dash.append(f"يومي: {t_1d['label']}" + (f" ⟵ ({' | '.join(t_1d['models'])})" if t_1d['models'] else ""))
        mtf_dash.append(f"أسبوعي: {t_1wk['label']}" + (f" ⟵ ({' | '.join(t_1wk['models'])})" if t_1wk['models'] else ""))
        
        if interval == "1h": 
            mtf_buy_ok = (t_4h['trend'] == "صاعد") and (t_1d['trend'] == "صاعد")
            mtf_sell_ok = (t_4h['trend'] == "هابط") and (t_1d['trend'] == "هابط")
            h_tf_name = "الفريمات الكبرى (4س واليومي)"
            if t_1wk['trend'] == "صاعد": bull.append("🌟 إجماع شامل: الفريم الأسبوعي يوافق الاتجاه ويدعم الصعود")
            if t_1wk['trend'] == "هابط": bear.append("🌟 إجماع شامل: الفريم الأسبوعي يوافق الاتجاه ويدعم الهبوط")
        elif interval == "1d": 
            mtf_buy_ok = t_1wk['trend'] == "صاعد"
            mtf_sell_ok = t_1wk['trend'] == "هابط"
            h_tf_name = "الفريم الأسبوعي"
        else: 
            mtf_buy_ok, mtf_sell_ok, h_tf_name = True, True, "الفريم الأكبر"

        if len(bull) >= 2 or is_qm_bull: 
            if is_qm_bull and "SMC: كوازمودو شرائي" not in bull: bull.insert(0, "👑 SMC: كوازمودو شرائي")
            if not mtf_buy_ok:
                action, reason = "مراقبة 🟡 (إلغاء شراء)", "\n➕ ".join([""] + bull).strip() + f"\n\n⚠️ **الدخول ملغى لأن {h_tf_name} هابط!** 🚫"
            else:
                action, reason = "شراء فوري 🟢", "\n➕ ".join([""] + bull).strip()
                exact_entry = retest_level if retest_level else (float(df['Close'].iloc[-2]) if df['Engulf_Bull'].iloc[-1] else current_price)
                entry = str(round(exact_entry, 2))
                exact_sl = round(float(df['Low'].tail(15).min()), 2)
                sl = f"{exact_sl} (كسر الأدنى)"
                exact_target = round(n_res_val, 2)
                targets = f"🎯 هدف أول: {exact_target}"
                
        elif len(bear) >= 2 or is_qm_bear:
            if is_qm_bear and "SMC: كوازمودو بيعي" not in bear: bear.insert(0, "👑 SMC: كوازمودو بيعي")
            if not mtf_sell_ok:
                action, reason = "مراقبة 🟡 (إلغاء بيع)", "\n➖ ".join([""] + bear).strip() + f"\n\n⚠️ **الدخول ملغى لأن {h_tf_name} صاعد!** 🚫"
            else:
                action, reason = "بيع فوري 🔴", "\n➖ ".join([""] + bear).strip()
                exact_entry = retest_level if retest_level else (float(df['Close'].iloc[-2]) if df['Engulf_Bear'].iloc[-1] else current_price)
                entry = str(round(exact_entry, 2))
                exact_sl = round(float(df['High'].tail(15).max()), 2)
                sl = f"{exact_sl} (اختراق الأعلى)"
                exact_target = round(n_sup_val, 2)
                targets = f"🎯 هدف أول: {exact_target}"
        else:
            reason = "تحليل السهم يظهر عدم اكتمال الإجماع الفني.\n"
            if len(bull) >= 1: reason += "\n➕ " + "\n➕ ".join(bull)
            if len(bear) >= 1: reason += "\n➖ " + "\n➖ ".join(bear)

        if record_alert and ("فوري" in action):
            try:
                exact_entry = float(entry.split()[0])
                model_name = reason.split('\n')[0].replace('➕ ', '').replace('➖ ', '')
                trade_type = "buy" if "شراء" in action else "sell"
                retest_alerts[ticker] = {"price": exact_entry, "action": action, "model": model_name, "type": trade_type, "target": exact_target, "sl": exact_sl}
                save_database()
            except: pass

        return {"ticker": ticker, "price": round(current_price, 2), "action": action, "targets": targets, "sl": sl, "entry": entry, "reason": reason, "mtf_dash": mtf_dash}
    except Exception as e: return {"error": str(e), "ticker": ticker}

def format_msg(res):
    if "error" in res: return f"⚠️ تعذر تحليل السهم: {res.get('ticker', '')}"
    msg = f"🎯 **القرار:** {res['action']}\n"
    msg += f"📊 **السهم:** {get_display_name(res['ticker'])} | **السعر:** {res['price']}\n"
    msg += f"━━━━━━━━━━━━\n🧭 **لوحة الفريمات (MTF):**\n" + "\n".join([f"▪️ {line}" for line in res['mtf_dash']])
    msg += f"\n━━━━━━━━━━━━\n🛒 **نقطة الدخول (النموذج):** {res['entry']}\n🚩 **الأهداف:** \n{res['targets']}\n🛑 **الوقف:** {res['sl']}\n💡 **الأسباب الفنية:**\n{res['reason']}\n"
    return msg

def auto_scanner():
    while True:
        ai_market_study()
        if subscribed_chats:
            for ticker, interval in WATCHLIST:
                try:
                    market_type = "sa" if ticker.endswith(".SR") else "us"
                    if market_type == "sa" and not radar_settings["sa"]: continue
                    if market_type == "us" and not radar_settings["us"]: continue

                    df_current = fetch_yahoo_data(ticker, interval)
                    current_p = float(df_current['Close'].iloc[-1])

                    if radar_settings["sniper"] and ticker in retest_alerts and (ticker, date.today()) not in notified_retests:
                        target_info = retest_alerts[ticker]
                        target_price = target_info["price"]
                        
                        if abs(current_p - target_price) <= (target_price * 0.005):
                            alert_msg = f"🚨 **قناص التداول (إشارة تنفذت الآن)** 🚨\n\n📊 السهم: {get_display_name(ticker)}\n🎯 **السعر وصل لنقطة الدخول:** {current_p}\n🛒 **نقطة النموذج:** {target_price}\n💡 **بناءً على:** {target_info['model']}"
                            for chat_id in list(subscribed_chats):
                                try: bot.send_message(chat_id, alert_msg, parse_mode="Markdown")
                                except: pass
                            
                            notified_retests.add((ticker, date.today())) 
                            todays_sniper_picks[ticker] = {"price": target_price, "model": target_info['model']}
                            
                            active_trades[ticker] = target_info
                            del retest_alerts[ticker]
                            save_database() 

                    if ticker in active_trades:
                        trade = active_trades[ticker]
                        trade_closed = False
                        if trade["type"] == "buy":
                            if current_p >= trade["target"]:
                                trade_history["wins"] += 1
                                trade_history["log"].append(f"✅ ربح: {get_display_name(ticker)} | {trade['model']}")
                                trade_closed = True
                                for chat_id in list(subscribed_chats): bot.send_message(chat_id, f"🧠 **تحديث الذكاء الاصطناعي:**\n✅ صفقة {get_display_name(ticker)} حققت الهدف بنجاح!", parse_mode="Markdown")
                            elif current_p <= trade["sl"]:
                                trade_history["losses"] += 1
                                trade_history["log"].append(f"❌ خسارة: {get_display_name(ticker)} | {trade['model']}")
                                trade_closed = True
                                for chat_id in list(subscribed_chats): bot.send_message(chat_id, f"🧠 **تحديث الذكاء الاصطناعي:**\n❌ صفقة {get_display_name(ticker)} ضربت الوقف.", parse_mode="Markdown")
                        elif trade["type"] == "sell":
                            if current_p <= trade["target"]:
                                trade_history["wins"] += 1
                                trade_history["log"].append(f"✅ ربح: {get_display_name(ticker)} | {trade['model']}")
                                trade_closed = True
                                for chat_id in list(subscribed_chats): bot.send_message(chat_id, f"🧠 **تحديث الذكاء الاصطناعي:**\n✅ صفقة {get_display_name(ticker)} حققت الهدف بنجاح!", parse_mode="Markdown")
                            elif current_p >= trade["sl"]:
                                trade_history["losses"] += 1
                                trade_history["log"].append(f"❌ خسارة: {get_display_name(ticker)} | {trade['model']}")
                                trade_closed = True
                                for chat_id in list(subscribed_chats): bot.send_message(chat_id, f"🧠 **تحديث الذكاء الاصطناعي:**\n❌ صفقة {get_display_name(ticker)} ضربت الوقف.", parse_mode="Markdown")
                        
                        if trade_closed:
                            del active_trades[ticker]
                            save_database()

                    if radar_settings["market"]:
                        res = get_immediate_signal(ticker, interval, record_alert=True)
                        if res and "error" not in res and ("فوري" in res['action']):
                            for chat_id in list(subscribed_chats):
                                try: bot.send_message(chat_id, f"🚨 **رادار النماذج (اكتشاف جديد)** 🚨\n*(تم حفظ السهم للقناص والتقييم)*\n\n{format_msg(res)}", parse_mode="Markdown")
                                except: pass
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
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🇸🇦 تصفية شاملة (سعودي)"), KeyboardButton("🇺🇸 تصفية شاملة (أمريكي)"))
    markup.add(KeyboardButton("🔍 كوازمودو سعودي 🇸🇦"), KeyboardButton("🔍 كوازمودو أمريكي 🇺🇸"))
    markup.add(KeyboardButton("🎯 أسهم القناص (اليوم)"), KeyboardButton("📊 التقرير اليومي للـ AI"))
    markup.add(KeyboardButton("📋 أسهم قائمة التصفيات"), KeyboardButton("⚙️ لوحة تحكم الرادار"))
    bot.reply_to(m, "مرحباً بك في رادار الحيتان المُحسن 🐋!\n🚀 تم تفعيل الذاكرة السحابية، كاشف كوازمودو المخفف لتناسب السيرفرات، ونظام الإدارة السريعة للفرص.", reply_markup=markup)

@bot.message_handler(func=lambda m: "كوازمودو" in m.text.strip())
def find_quasimodo_only(m):
    market = "sa" if "سعودي" in m.text else "us"
    m_name = "السعودي 🇸🇦" if market == "sa" else "الأمريكي 🇺🇸"
    msg = bot.reply_to(m, f"🔍 **جاري تشغيل كاشف كوازمودو في السوق {m_name}...**\n⚡ تم تفعيل محرك الفحص المتوازي (المخفف لمنع التجمد)...")
    
    target_watchlist = [item for item in WATCHLIST if (market == "sa" and item[0].endswith(".SR")) or (market == "us" and not item[0].endswith(".SR"))]
    
    def scan_for_qm(item):
        ticker, interval = item
        try:
            df = fetch_yahoo_data(ticker, interval)
            if len(df) < 50: return None
            df['Body'] = abs(df['Close'] - df['Open'])
            df['Sweep_Bull'] = df['Low'] < df['Low'].rolling(15).min().shift(1)
            df['Sweep_Bear'] = df['High'] > df['High'].rolling(15).max().shift(1)
            df['CHoCH_Bull'] = df['Close'] > df['High'].rolling(8).max().shift(1)
            df['CHoCH_Bear'] = df['Close'] < df['Low'].rolling(8).min().shift(1)
            
            is_qm_bull = (df['Sweep_Bull'].tail(5).any()) and (df['CHoCH_Bull'].iloc[-1])
            is_qm_bear = (df['Sweep_Bear'].tail(5).any()) and (df['CHoCH_Bear'].iloc[-1])
            current_p = round(float(df['Close'].iloc[-1]), 2)
            
            if is_qm_bull:
                log_quasimodo_setup(ticker, get_display_name(ticker), "شرائي 🟢", interval, current_p, "كوازمودو صاعد (تصفية سيولة القاع مع CHoCH صاعد)")
                return {"ticker": ticker, "type": "👑 كوازمودو شرائي (صعود)", "price": current_p, "interval": interval}
            elif is_qm_bear:
                log_quasimodo_setup(ticker, get_display_name(ticker), "بيعي 🔴", interval, current_p, "كوازمودو هابط (تصفية سيولة القمة مع CHoCH هابط)")
                return {"ticker": ticker, "type": "🩸 كوازمودو بيعي (هبوط)", "price": current_p, "interval": interval}
        except: pass
        return None

    # مسح متوازي هادئ يناسب 512 ميجا رام
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(scan_for_qm, target_watchlist))
        
    gc.collect() # 🧹 أمر تنظيف الرام فوراً بعد انتهاء الفحص
    
    qm_found = [r for r in results if r is not None]
    
    if not qm_found:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"📭 لم يتم رصد أي نموذج كوازمودو مكتمل حالياً في السوق {m_name}.", parse_mode="Markdown")
        return
        
    reply = f"🎯 **نتائج رادار كوازمودو النشط في السوق {m_name}:**\n*(تم تدوين جميع هذه الأسهم في سجل التقرير اليومي)*\n\n"
    for idx, item in enumerate(qm_found, 1):
        reply += f"{idx}. **{get_display_name(item['ticker'])}** ({item['interval']})\n"
        reply += f"   🔹 النموذج: {item['type']}\n"
        reply += f"   💲 سعر الرصد: {item['price']}\n\n"
        
    try: bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=reply, parse_mode="Markdown")
    except: bot.send_message(m.chat.id, reply, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text.strip() == "📊 التقرير اليومي للـ AI")
def show_daily_ai_report(m):
    today_str = date.today().strftime('%Y-%m-%d')
    total_trades = trade_history['wins'] + trade_history['losses']
    win_rate_str = f"{(trade_history['wins']/total_trades)*100:.1f}%" if total_trades > 0 else "0.0%"
    
    reply = f"🧠 **التقرير اليومي المفصل لأداء الذكاء الاصطناعي ({today_str}):**\n"
    reply += f"━━━━━━━━━━━━━━━━━━━━\n"
    reply += f"📈 **مؤشرات الأداء العامة (KPIs):**\n"
    reply += f"▪️ نسبة النجاح الكلية (Win Rate): **{win_rate_str}**\n"
    reply += f"▪️ صفقات رابحة: {trade_history['wins']} | خاسرة: {trade_history['losses']}\n"
    reply += f"▪️ صفقات قيد المراقبة الآن: {len(active_trades)}\n"
    reply += f"▪️ النماذج المبتكرة المكتشفة بالكامل: {len(ai_learned_patterns)}\n"
    reply += f"━━━━━━━━━━━━━━━━━━━━\n"
    reply += f"💾 **سجل كوازمودو المكتشف لليوم:**\n"
    
    setups_today = []
    if mongo_connected:
        try:
            today_log = quasimodo_col.find_one({"date": today_str})
            if today_log and "setups" in today_log:
                setups_today = today_log["setups"]
        except Exception as e:
            print(f"Error fetching daily setups from MongoDB: {e}")
            
    if not setups_today:
        setups_today = in_memory_daily_quasimodo.get(today_str, [])
        
    if not setups_today:
        reply += "📭 لم يتم رصد أو تسجيل أي نماذج كوازمودو حتى الآن اليوم.\n"
    else:
        reply += f"🔥 تم رصد **{len(setups_today)}** نموذج كوازمودو اليوم:\n\n"
        for idx, item in enumerate(setups_today, 1):
            reply += f"{idx}. **{item['name']}** ({item['interval']})\n"
            reply += f"   🏷️ الاتجاه: **{item['direction']}**\n"
            reply += f"   💲 السعر: {item['price']}\n"
            reply += f"   💡 التفاصيل: {item['details']}\n\n"
            
    reply += f"━━━━━━━━━━━━━━━━━━━━\n"
    reply += f"🤖 **أحدث النماذج المبتكرة ذاتياً:**\n"
    if not ai_learned_patterns:
        reply += "▪️ في انتظار تشكيل أول نموذج إحصائي مخصص."
    else:
        for pat in ai_learned_patterns[-3:]:
            reply += f"▪️ {pat}\n"
            
    bot.reply_to(m, reply, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text.strip() == "⚙️ لوحة تحكم الرادار")
def radar_panel(m):
    bot.reply_to(m, "⚙️ **غرفة التحكم المستقلة:**\nاضغط على أي زر لتشغيل أو إيقاف الخدمة:", reply_markup=get_radar_markup(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_"))
def toggle_radar_setting(call):
    key = call.data.split("_")[1]
    radar_settings[key] = not radar_settings[key]
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_radar_markup())

@bot.message_handler(func=lambda m: m.text.strip() == "🎯 أسهم القناص (اليوم)")
def show_sniper_picks(m):
    check_new_day()
    if not todays_sniper_picks:
        bot.reply_to(m, "📭 لم يقم القناص باصطياد أي سهم حتى الآن اليوم.\n*(يجب أن يضرب السعر نقطة الدخول المحفوظة ليظهر هنا)*", parse_mode="Markdown")
    else:
        current_date_str = date.today().strftime('%d-%m-%Y')
        reply = f"🎯 **قائمة صيد القناص الناجحة لتاريخ ({current_date_str}):**\n\n"
        for idx, (t, details) in enumerate(todays_sniper_picks.items(), 1):
            reply += f"{idx}. **{get_display_name(t)}** ⬅️ تم الدخول عند: {details['price']}\n💡 النموذج: {details['model']}\n\n"
        bot.reply_to(m, reply, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text.strip() == "📋 أسهم قائمة التصفيات")
def show_todays_picks(m):
    check_new_day()
    if not todays_picks: bot.reply_to(m, "📭 القائمة فارغة اليوم.")
    else:
        current_date_str = date.today().strftime('%d-%m-%Y')
        reply = f"📋 **قائمة التصفيات لتاريخ ({current_date_str}):**\n\n"
        for idx, (t, act) in enumerate(todays_picks.items(), 1): reply += f"{idx}. {get_display_name(t)} ⬅️ **{act}**\n"
        bot.reply_to(m, reply, parse_mode="Markdown")

@bot.message_handler(func=lambda m: "تصفية شاملة" in m.text.strip())
def find_best_confluence(m):
    check_new_day()
    market = "sa" if "سعودي" in m.text else "us"
    m_name = "السعودي 🇸🇦" if market == "sa" else "الأمريكي 🇺🇸 (خيارات 1H)"
    msg = bot.reply_to(m, f"🔍 **جاري بدء المسح الشامل للسوق {m_name}...**\n⚡ تم تفعيل وضع المسح الموزون (متوافق مع السيرفرات)...")

    buys, sells = [], []
    error_count = 0
    target_watchlist = [item for item in WATCHLIST if (market == "sa" and item[0].endswith(".SR")) or (market == "us" and not item[0].endswith(".SR"))]

    def scan_single(item):
        t, interval = item
        try:
            return get_immediate_signal(t, interval, record_alert=True)
        except:
            return {"error": "timeout", "ticker": t}

    # فحص متوازي لـ 3 أسهم دفعة واحدة
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(scan_single, target_watchlist))
        
    gc.collect() # 🧹 تنظيف الذاكرة

    for res in results:
        if res and "error" not in res:
            if "شراء فوري" in res['action']: buys.append((res['reason'].count('➕'), res))
            elif "بيع فوري" in res['action']: sells.append((res['reason'].count('➖'), res))
        else:
            error_count += 1

    buys.sort(key=lambda x: x[0], reverse=True)
    sells.sort(key=lambda x: x[0], reverse=True)

    if not buys and not sells:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"لا توجد فرص قوية تتوافق مع الإجماع الفني الصارم حالياً.", parse_mode="Markdown")
        return

    reply = f"🏆 **أقوى الفرص بناءً على الإجماع الفني {m_name}** 🏆\n\n"
    if buys[:2]:
        reply += "🟢 **أقوى فرص الشراء (Call):**\n\n"
        for score, res in buys[:2]:
            todays_picks[res['ticker']] = "شراء 🟢"
            reply += f"#{buys.index((score,res))+1}\n{format_msg(res)}\n"
    if sells[:2]:
        reply += "🔴 **أقوى فرص البيع (Put):**\n\n"
        for score, res in sells[:2]:
            todays_picks[res['ticker']] = "بيع 🔴"
            reply += f"#{sells.index((score,res))+1}\n{format_msg(res)}\n"

    if error_count > 0: reply += f"\n⚠️ *(تنويه: تم تخطي {error_count} أسهم بطيئة لضمان استقرار الاتصال)*"
    
    try: bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=reply, parse_mode="Markdown")
    except: bot.send_message(m.chat.id, reply, parse_mode="Markdown")

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
    msg = "📋 **قائمة المراقبة الحالية:**\n" + "\n".join([f"▪| {x[0]} ({x[1]})" for x in WATCHLIST])
    bot.reply_to(m, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def analyze_manual_stock(m):
    text = m.text.strip().upper()
    ignore = ["🇸🇦 تصفية شاملة (سعودي)", "🇺🇸 تصفية شاملة (أمريكي)", "⚙️ لوحة تحكم الرادار", "🎯 أسهم القناص (اليوم)", "📋 أسهم قائمة التصفيات", "📊 التقرير اليومي للـ AI", "🔍 كوازمودو سعودي 🇸🇦", "🔍 كوازمودو أمريكي 🇺🇸"]
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
            bot.send_message(m.chat.id, f"✅ **تم تحديث الذاكرة:**\nتم إدراج السهم ({t}) تلقائياً في رادار القناص والذكاء الاصطناعي للمراقبة المستمرة!", parse_mode="Markdown")
    else:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"⚠️ تعذر تحليل السهم.\n**السبب:** {res.get('error', 'السهم غير مدرج أو البيانات غير كافية.')}")

app = Flask(__name__)
@app.route('/')
def home(): return "🚀 البوت السحابي الموزون يعمل بنجاح ومحمي من الانهيار!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_server, daemon=True).start()

print("=== جاري استرجاع الذاكرة السحابية الدائمة ===")
load_database()
print(f"تم استرجاع قائمة أسهم بحجم: {len(WATCHLIST)} سهم.")

print("=== تم التشغيل بنجاح ===")
threading.Thread(target=auto_scanner, daemon=True).start()

bot.remove_webhook()
bot.polling(none_stop=True)
