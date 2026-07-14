# [الجزء الأول: الدوال والتهيئة كما هي في الكود السابق، أضف هذا التحديث للدالة:]

def check_breakout_retest(df, interval):
    if interval != "4h": return None
    # تحديد المقاومة والدعم على الـ 4 ساعات
    res = df['High'].rolling(50).max().iloc[-1]
    sup = df['Low'].rolling(50).min().iloc[-1]
    
    # التحقق من إغلاق شمعتين
    c1, c2 = df['Close'].iloc[-1], df['Close'].iloc[-2]
    
    if c1 > res and c2 > res:
        return {"type": "اختراق مقاومة 🚀", "retest_level": round(res, 2)}
    elif c1 < sup and c2 < sup:
        return {"type": "كسر دعم 🩸", "retest_level": round(sup, 2)}
    return None

# [تعديل دالة get_immediate_signal لدمج المنطق الجديد:]
def get_immediate_signal(ticker, interval="1d"):
    try:
        df = fetch_yahoo_data(ticker, interval)
        if df.empty or len(df) < 100: return {"error": "بيانات غير كافية."}
        current_price = float(df['Close'].iloc[-1])
        
        # ... (باقي منطق النماذج كما هو) ...
        # [أضف هذا الجزء قبل القرار النهائي]
        retest_signal = None
        if interval == "1h": # الفحص يتم على 4H
            df_4h = fetch_yahoo_data(ticker, "4h")
            retest_signal = check_breakout_retest(df_4h, "4h")
        
        # [تعديل رسالة القرار لتشمل نقطة إعادة الاختبار]
        # إذا وجد إشارة اختراق، أضفها للأسباب الفنية
        if retest_signal:
            reason = f"👑 {retest_signal['type']} مؤكد بإغلاق شمعتين 4س.\n🎯 **نقطة الدخول عند إعادة الاختبار (Retest):** {retest_signal['retest_level']}\n" + reason
        
        # [استكمال باقي منطق القرار النهائي كما في الكود السابق]
        # ... (احتفظ بباقي الكود كما هو مع تبديل الدالة أعلاه) ...
        return {"ticker": ticker, "price": round(current_price, 2), "action": action, "targets": targets, "sl": sl, "entry": entry, "reason": reason, "mtf_dash": mtf_dash}
    except Exception as e: return {"error": str(e), "ticker": ticker}

# [ملاحظة: تأكد من نسخ باقي الكود (auto_scanner, handlers, server, polling) كما كانت في الرسالة السابقة لضمان التوافق.]
