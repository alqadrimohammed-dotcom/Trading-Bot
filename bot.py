import telebot
import pandas as pd
import numpy as np
import cloudscraper
import threading
import time
import warnings
import os
from flask import Flask
from datetime import datetime, date
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

warnings.filterwarnings('ignore')

# التوكن الخاص بك
TOKEN = "8666366975:AAFaapaj0XAHUO8-6PbzzNY0GGWiit0bKsk"
bot = telebot.TeleBot(TOKEN)

WATCHLIST = [
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

# إعدادات غرفة العمليات المستقلة
radar_settings = {
    "sa": True,      # السوق السعودي
    "us": True,      # السوق الأمريكي
    "market": True,  # رادار استكشاف النماذج الجديدة
    "sniper": True   # رادار القناص (إعادة الاختبار)
}

subscribed_chats = set()
todays_picks = {}
todays_sniper_picks = {} # قائمة الأسهم التي تم قنصها بنجاح اليوم
retest_alerts = {} # ذاكرة التنبيهات لأي سهم يشكل نموذج صحيح
notified_retests = set() 
last_update_date = date.today()

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
            res = scraper.get(url, timeout=5)
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
    
    if len(df) >= 30:
        x_20 = np.arange(20)
        slope_high, _ = np.polyfit(x_20, df['High'].iloc[-20:].values, 1)
        slope_low, _ = np.polyfit(x_20, df['Low'].iloc[-20:].values, 1)
        converging = (df['High'].iloc[-20:].values[0] - df['Low'].iloc[-20:].values[0]) > (df['High'].iloc[-20:].values[-1] - df['Low'].iloc[-20:].values[-1])
        if (slope_high < 0) and (slope_low < 0) and (slope_high < slope_low) and converging: models.append("📐 وتد هابط")
        elif (slope_high > 0) and (slope_low > 0) and (slope_low > slope_high) and converging: models.append("📐 وتد صاعد")
        elif (slope_high < 0) and (slope_low > 0) and converging: models.append("🔺 مثلث متماثل")
        
    return {"trend": trend, "models": models, "label": label}

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
            if t_1wk['trend'] == "صاعد": bull.append("🌟 إجماع شامل: الفريم الأسبوعي يوافق الاتجاه ويدعم الصعود (خير وبركة)")
            if t_1wk['trend'] == "هابط": bear.append("🌟 إجماع شامل: الفريم الأسبوعي يوافق الاتجاه ويدعم الهبوط (خير وبركة)")
        elif interval == "1d": 
            mtf_buy_ok = t_1wk['trend'] == "صاعد"
            mtf_sell_ok = t_1wk['trend'] == "هابط"
            h_tf_name = "الفريم الأسبوعي"
        else: 
            mtf_buy_ok, mtf_sell_ok, h_tf_name = True, True, "الفريم الأكبر"

        # قرار الدخول يتطلب نموذج صريح وتوافق تام
        if len(bull) >= 2 or is_qm_bull: 
            if is_qm_bull and "SMC: كوازمودو شرائي" not in bull: bull.insert(0, "👑 SMC: كوازمودو شرائي")
            if not mtf_buy_ok:
                action, reason = "مراقبة 🟡 (إلغاء شراء)", "\n➕ ".join([""] + bull).strip() + f"\n\n⚠️ **الدخول ملغى لأن {h_tf_name} هابط!** 🚫"
            else:
                action, reason = "شراء فوري 🟢", "\n➕ ".join([""] + bull).strip()
                signal_price = float(df['Close'].iloc[-2]) if df['Engulf_Bull'].iloc[-1] else current_price
                entry = str(round(signal_price, 2))
                sl = f"{round(float(df['Low'].tail(15).min()), 2)} (كسر الأدنى)"
                targets = f"🎯 هدف أول: {round(n_res_val, 2)}"
                
        elif len(bear) >= 2 or is_qm_bear:
            if is_qm_bear and "SMC: كوازمودو بيعي" not in bear: bear.insert(0, "👑 SMC: كوازمودو بيعي")
            if not mtf_sell_ok:
                action, reason = "مراقبة 🟡 (إلغاء بيع)", "\n➖ ".join([""] + bear).strip() + f"\n\n⚠️ **الدخول ملغى لأن {h_tf_name} صاعد!** 🚫"
            else:
                action, reason = "بيع فوري 🔴", "\n➖ ".join([""] + bear).strip()
                signal_price = float(df['Close'].iloc[-2]) if df['Engulf_Bear'].iloc[-1] else current_price
                entry = str(round(signal_price, 2))
                sl = f"{round(float(df['High'].tail(15).max()), 2)} (اختراق الأعلى)"
                targets = f"🎯 هدف أول: {round(n_sup_val, 2)}"
        else:
            reason = "تحليل السهم يظهر عدم اكتمال الإجماع الفني.\n"
            if len(bull) >= 1: reason += "\n➕ " + "\n➕ ".join(bull)
            if len(bear) >= 1: reason += "\n➖ " + "\n➖ ".join(bear)

        # 🧠 إضافة السهم لذاكرة القناص إذا تم تأكيد نموذج صحيح وإجماع
        if record_alert and ("فوري" in action):
            try:
                exact_entry = float(entry.split()[0])
                model_name = reason.split('\n')[0].replace('➕ ', '').replace('➖ ', '')
                retest_alerts[ticker] = {"price": exact_entry, "action": action, "model": model_name}
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
        if subscribed_chats:
            for ticker, interval in WATCHLIST:
                try:
                    # فلترة الأسواق حسب إعدادات اللوحة
                    market_type = "sa" if ticker.endswith(".SR") else "us"
                    if market_type == "sa" and not radar_settings["sa"]: continue
                    if market_type == "us" and not radar_settings["us"]: continue

                    # 1. نظام القناص (مراقبة الأسهم المحفوظة في الذاكرة)
                    if radar_settings["sniper"] and ticker in retest_alerts and (ticker, date.today()) not in notified_retests:
                        df_current = fetch_yahoo_data(ticker, interval)
                        current_p = float(df_current['Close'].iloc[-1])
                        target_info = retest_alerts[ticker]
                        target_price = target_info["price"]
                        
                        # إذا تراجع السعر ولمس نقطة الدخول أو اقترب منها
                        if abs(current_p - target_price) <= (target_price * 0.005):
                            alert_msg = f"🚨 **قناص التداول (إشارة تنفذت الآن)** 🚨\n\n📊 السهم: {get_display_name(ticker)}\n🎯 **السعر وصل لنقطة الدخول:** {current_p}\n🛒 **نقطة النموذج:** {target_price}\n💡 **بناءً على:** {target_info['model']}"
                            for chat_id in subscribed_chats:
                                try: bot.send_message(chat_id, alert_msg, parse_mode="Markdown")
                                except: pass
                            
                            # تسجيل السهم في قائمة القناص لليوم ومنع إرسال تنبيه متكرر
                            notified_retests.add((ticker, date.today())) 
                            todays_sniper_picks[ticker] = {"price": target_price, "model": target_info['model']}
                            del retest_alerts[ticker]

                    # 2. رادار النماذج (اكتشاف نماذج جديدة 100%)
                    if radar_settings["market"]:
                        res = get_immediate_signal(ticker, interval, record_alert=True)
                        if res and "error" not in res and ("فوري" in res['action']):
                            for chat_id in subscribed_chats:
                                try: bot.send_message(chat_id, f"🚨 **رادار النماذج (اكتشاف جديد)** 🚨\n*(تم حفظ نقطة الدخول في القناص لمعاودة الاختبار)*\n\n{format_msg(res)}", parse_mode="Markdown")
                                except: pass
                except: pass
        time.sleep(600)

def check_new_day():
    global todays_picks, todays_sniper_picks, last_update_date, notified_retests
    if date.today() > last_update_date:
        todays_picks.clear()
        todays_sniper_picks.clear()
        notified_retests.clear()
        last_update_date = date.today()

# دالة لتوليد لوحة تحكم الرادار
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
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🇸🇦 تصفية شاملة (سعودي)"), KeyboardButton("🇺🇸 تصفية شاملة (أمريكي)"))
    markup.add(KeyboardButton("👑 بحث الكوازمودو (QM)"), KeyboardButton("💎 بحث الماسة (Diamond)"))
    markup.add(KeyboardButton("📐 بحث الأوتاد (Wedges)"), KeyboardButton("🔺 بحث المثلثات (Triangles)"))
    markup.add(KeyboardButton("⚙️ لوحة تحكم الرادار"), KeyboardButton("🎯 أسهم القناص (اليوم)"))
    markup.add(KeyboardButton("📋 أسهم قائمة التصفيات"))
    bot.reply_to(m, "مرحباً بك في رادار الحيتان المُحسن!\n🚀 تم تحويل البوت إلى (غرفة عمليات متكاملة) لخدمتك.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.strip() == "⚙️ لوحة تحكم الرادار")
def radar_panel(m):
    bot.reply_to(m, "⚙️ **غرفة التحكم المستقلة:**\nاضغط على أي زر لتشغيل أو إيقاف الخدمة التي تريدها:", reply_markup=get_radar_markup(), parse_mode="Markdown")

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

@bot.message_handler(func=lambda m: m.text.strip() in ["👑 بحث الكوازمودو (QM)", "💎 بحث الماسة (Diamond)", "📐 بحث الأوتاد (Wedges)", "🔺 بحث المثلثات (Triangles)"])
def pattern_menu(m):
    markup = InlineKeyboardMarkup()
    if "الكوازمودو" in m.text: p_code, p_name = "qm", "الكوازمودو 👑"
    elif "الماسة" in m.text: p_code, p_name = "diamond", "الماسة 💎"
    elif "الأوتاد" in m.text: p_code, p_name = "wedge", "الأوتاد 📐"
    elif "المثلثات" in m.text: p_code, p_name = "triangle", "المثلثات 🔺"
        
    btn_sa = InlineKeyboardButton("السوق السعودي 🇸🇦", callback_data=f"search_{p_code}_sa")
    btn_us = InlineKeyboardButton("السوق الأمريكي 🇺🇸", callback_data=f"search_{p_code}_us")
    markup.row(btn_sa, btn_us) 
    
    bot.reply_to(m, f"يرجى تحديد السوق للبحث عن نموذج **{p_name}**:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("search_"))
def process_pattern_search(call):
    check_new_day()
    parts = call.data.split('_')
    p_code, market = parts[1], parts[2]
    
    if p_code == "qm": pat_name, pat_icon, kw = "الكوازمودو (QM)", "👑", "كوازمودو"
    elif p_code == "diamond": pat_name, pat_icon, kw = "الماسة (Diamond)", "💎", "ماسة"
    elif p_code == "wedge": pat_name, pat_icon, kw = "الأوتاد (Wedges)", "📐", "وتد"
    elif p_code == "triangle": pat_name, pat_icon, kw = "المثلثات (Triangles)", "🔺", "مثلث"
    
    m_name = "السعودي 🇸🇦 (يومي)" if market == "sa" else "الأمريكي 🇺🇸 (خيارات 1H)"
    
    msg = bot.edit_message_text(f"{pat_icon} **جاري بدء المسح لنموذج {pat_name} في السوق {m_name}...**\n⏳ يرجى الانتظار...", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
    
    target_wl = [item for item in WATCHLIST if (market == "sa" and item[0].endswith(".SR")) or (market == "us" and not item[0].endswith(".SR"))]
    total = len(target_wl)
    found, error_count = [], 0
    
    for i, (t, interval) in enumerate(target_wl, 1):
        try:
            res = get_immediate_signal(t, interval, record_alert=True)
            if res and "error" not in res:
                if kw in res['reason'] and ("شراء" in res['action'] or "بيع" in res['action']):
                    found.append(res)
                    todays_picks[res['ticker']] = f"{pat_icon} {res['action']}"
            else:
                error_count += 1
        except:
            error_count += 1
            
        if i % 10 == 0:
            try: bot.edit_message_text(f"{pat_icon} **جاري الفحص لنموذج {pat_name} ({m_name})...**\n⏳ **التقدم:** تم مسح {i} من أصل {total} سهم...\n*(محرك التيربو الذكي مفعل 🚀)*", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
            except: pass
            
    reply = f"{pat_icon} **نتائج البحث عن {pat_name} - السوق {m_name}** {pat_icon}\n\n"
    if not found:
        reply += "لم يُرصد هذا النموذج جاهزاً للاختراق في هذا السوق حالياً.\n"
    else:
        for idx, res in enumerate(found, 1):
            reply += f"#{idx}\n{format_msg(res)}\n"
            
    if error_count > 0: reply += f"\n⚠️ *(تنويه: تم تخطي بعض الأسهم لضمان سرعة الاتصال)*"
    
    try: bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=reply, parse_mode="Markdown")
    except: bot.send_message(call.message.chat.id, reply, parse_mode="Markdown")

@bot.message_handler(func=lambda m: "تصفية شاملة" in m.text.strip())
def find_best_confluence(m):
    check_new_day()
    market = "sa" if "سعودي" in m.text else "us"
    m_name = "السعودي 🇸🇦" if market == "sa" else "الأمريكي 🇺🇸 (خيارات 1H)"
    msg = bot.reply_to(m, f"🔍 **جاري بدء المسح الشامل للسوق {m_name}...**\n⏳ يرجى الانتظار، المسح الآمن قيد العمل...")

    buys, sells = [], []
    error_count = 0
    target_watchlist = [item for item in WATCHLIST if (market == "sa" and item[0].endswith(".SR")) or (market == "us" and not item[0].endswith(".SR"))]
    total = len(target_watchlist)

    for i, (t, interval) in enumerate(target_watchlist, 1):
        try:
            res = get_immediate_signal(t, interval, record_alert=True)
            if res and "error" not in res:
                if "شراء فوري" in res['action']: buys.append((res['reason'].count('➕'), res))
                elif "بيع فوري" in res['action']: sells.append((res['reason'].count('➖'), res))
            else:
                error_count += 1
        except:
            error_count += 1

        if i % 10 == 0:
            try: bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"🔍 **جاري المسح الشامل للسوق {m_name}...**\n⏳ **التقدم:** تم فحص {i} من أصل {total} سهم...\n*(محرك التيربو الذكي مفعل 🚀)*", parse_mode="Markdown")
            except: pass

    buys.sort(key=lambda x: x[0], reverse=True)
    sells.sort(key=lambda x: x[0], reverse=True)

    if not buys and not sells:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"لا توجد فرص قوية تتوافق مع الإجماع الفني الصارم حالياً.", parse_mode="Markdown")
        return

    reply = "🏆 **أقوى الفرص بناءً على الإجماع الفني** 🏆\n\n"
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

    if error_count > 0: reply += f"\n⚠️ *(تنويه: تم تخطي بعض الأسهم لضمان سرعة الاتصال)*"
    
    try: bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=reply, parse_mode="Markdown")
    except: bot.send_message(m.chat.id, reply, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def analyze_manual_stock(m):
    text = m.text.strip().upper()
    ignore = ["🇸🇦 تصفية شاملة (سعودي)", "🇺🇸 تصفية شاملة (أمريكي)", "👑 بحث الكوازمودو (QM)", "💎 بحث الماسة (Diamond)", "📐 بحث الأوتاد (Wedges)", "🔺 بحث المثلثات (Triangles)", "⚙️ لوحة تحكم الرادار", "🎯 أسهم القناص (اليوم)", "📋 أسهم قائمة التصفيات"]
    if text in ignore or text.startswith("/"): return
    t = ARABIC_TICKERS.get(text.replace("أ", "ا").replace("إ", "ا").replace("ة", "ه"), text)
    if t.isdigit() and len(t) == 4: t += ".SR"

    msg = bot.reply_to(m, f"⏳ جاري الفحص المعمق لـ {text}...")
    res = get_immediate_signal(t, "1d" if t.endswith(".SR") else "1h", record_alert=True)
    if res and "error" not in res:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=format_msg(res), parse_mode="Markdown")
    else:
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"⚠️ تعذر تحليل السهم.\n**السبب:** {res.get('error', 'السهم غير مدرج أو بيانات غير كافية.')}")

# --- خادم الويب الوهمي لضمان عمل البوت مجاناً 24/7 ---
app = Flask(__name__)
@app.route('/')
def home():
    return "🚀 البوت يعمل بنجاح على السيرفر!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_server, daemon=True).start()
# -----------------------------------------------------

print("=== تم التشغيل بنجاح ===")
threading.Thread(target=auto_scanner, daemon=True).start()
bot.polling(none_stop=True)
