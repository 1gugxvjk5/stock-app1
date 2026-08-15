import json
import datetime
import akshare as ak
import pandas as pd
import numpy as np

def safe_float(x):
    try:
        return float(x)
    except:
        return 0.0

def get_market_env():
    try:
        df = ak.stock_zh_index_daily(symbol="sh000001")
        if df is None or df.empty:
            return "正常"
        df = df.tail(30)
        close = df['close'].astype(float)
        ma20 = close.rolling(20).mean()
        cond1 = close.iloc[-1] > ma20.iloc[-1]
        cond2 = ma20.iloc[-1] > ma20.iloc[-5]
        if cond1 and cond2:
            return "强"
        elif cond1:
            return "正常"
        else:
            return "偏弱"
    except Exception as e:
        print(f"获取大盘环境失败: {e}")
        return "正常"

def get_news():
    try:
        df = ak.stock_info_global_em()
        if df is None or df.empty:
            return [{"title": "暂无新闻数据", "time": "00:00", "sentiment": "neutral", "sentimentLabel": "中性", "related": ["无"], "source": "无"}]
        news = []
        for _, row in df.head(6).iterrows():
            title = str(row.get('标题', ''))
            if any(k in title for k in ["利好","增长","超预期","中标","突破","上涨"]):
                sent = "positive"
                label = "利好"
            elif any(k in title for k in ["利空","下滑","违规","处罚","亏损","减持"]):
                sent = "negative"
                label = "利空"
            else:
                sent = "neutral"
                label = "中性"
            news.append({
                "title": title,
                "time": datetime.datetime.now().strftime("%H:%M"),
                "sentiment": sent,
                "sentimentLabel": label,
                "related": ["大盘"],
                "source": "东财快讯"
            })
        return news
    except Exception as e:
        print(f"获取新闻失败: {e}")
        return [{"title": f"新闻获取失败: {e}", "time": "00:00", "sentiment": "neutral", "sentimentLabel": "中性", "related": ["无"], "source": "无"}]

def get_stock_indicators(code):
    try:
        end_date = datetime.date.today().strftime("%Y%m%d")
        start_date = (datetime.date.today() - datetime.timedelta(days=60)).strftime("%Y%m%d")
        hist = ak.stock_zh_a_hist(symbol=code, period="daily",
                                  start_date=start_date,
                                  end_date=end_date,
                                  adjust="qfq")
        if hist is None or len(hist) < 25:
            return None

        close = hist['收盘'].astype(float)
        high = hist['最高'].astype(float)
        low = hist['最低'].astype(float)
        vol = hist['成交量'].astype(float)

        ma20 = close.rolling(20).mean().iloc[-1]
        d20 = (close.iloc[-1] / ma20 - 1) * 100 if ma20 > 0 else 0.0

        r5 = (close.iloc[-1] / close.iloc[-6] - 1) * 100 if len(close) >= 6 else 0.0
        r10 = (close.iloc[-1] / close.iloc[-11] - 1) * 100 if len(close) >= 11 else 0.0
        r20 = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) >= 21 else 0.0

        vol_5 = vol.tail(5).mean()
        vol_20 = vol.tail(20).mean()
        vol_ratio = vol_5 / vol_20 if vol_20 > 0 else 1.0

        prev_close = close.shift(1)
        tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        atr_pct = (atr / close.iloc[-1]) * 100 if close.iloc[-1] > 0 else 0.0

        # ATR过滤器
        if atr_pct > 6:
            return {"decision": "不买", "stateClass": "高波动", "metrics": None}

        # 状态分类
        if d20 > 15 or r5 > 15:
            stateClass = "高位观察"
            decision = "不买"
        elif r5 < 0 and r10 > 0 and r20 > 0:
            stateClass = "回调观察"
            decision = "观察"
        elif 0 < r5 <= 8 and r10 <= 8 and r20 <= 10:
            stateClass = "启动观察"
            decision = "买" if r5 > 2 else "观察"
        elif 0 < r5 < 15 and r10 > 0 and r20 > 0:
            stateClass = "趋势观察"
            decision = "买"
        elif r5 > 0 and (r10 <= 0 or r20 <= 0) and -5 <= d20 <= 5 and vol_ratio > 1.2:
            stateClass = "反弹观察"
            decision = "观察" if r5 < 5 else "买"
        else:
            stateClass = "排除"
            decision = "不买"

        # ATR过滤：短期涨幅过大降级
        if abs(r5) > 2.5 * atr_pct:
            if decision == "买":
                decision = "观察"
                stateClass = stateClass + "（涨幅过大）"

        metrics = {
            "r5": f"{r5:+.1f}%",
            "r10": f"{r10:+.1f}%",
            "r20": f"{r20:+.1f}%",
            "d20": f"{d20:+.1f}%",
            "atr": f"{atr_pct:.1f}%",
            "volRatio": f"{vol_ratio:.2f}"
        }

        return {
            "decision": decision,
            "stateClass": stateClass,
            "metrics": metrics
        }
    except Exception as e:
        print(f"获取股票 {code} 指标失败: {e}")
        return None

def get_stocks_from_active_list(limit=150, output_max=10):
    """扫描活跃股，返回 (信号股票列表, 全部扫描股票列表)"""
    stocks = []
    all_scanned = []

    try:
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return stocks, all_scanned

        df = df[~df['名称'].str.contains('ST|退', na=False)]
        df = df.sort_values('成交额', ascending=False).head(limit)

        print(f"获取到 {len(df)} 只活跃股，开始计算指标...")

        for _, row in df.iterrows():
            code = str(row['代码'])
            name = str(row['名称'])
            result = get_stock_indicators(code)

            if result is None:
                all_scanned.append({
                    "name": name,
                    "code": code,
                    "decision": "未知",
                    "stateClass": "数据不足"
                })
                continue

            decision = result['decision']
            stateClass = result['stateClass']
            metrics = result['metrics']

            all_scanned.append({
                "name": name,
                "code": code,
                "decision": decision,
                "stateClass": stateClass
            })

            if decision in ["买", "观察"] and metrics:
                if stateClass in ["趋势观察", "回调观察"]:
                    holding_period = "长期（1-3个月）"
                elif stateClass == "启动观察":
                    holding_period = "短期（1-2周）"
                else:
                    holding_period = "仅观察"

                if decision == "买":
                    prob_up = 70 if stateClass == "趋势观察" else 60
                else:
                    prob_up = 50

                stocks.append({
                    "name": name,
                    "code": code,
                    "decision": decision,
                    "holdingPeriod": holding_period,
                    "probUp": prob_up,
                    **metrics,
                    "stateClass": stateClass,
                    "newsSentiment": "中性"
                })

                if len(stocks) >= output_max:
                    break

        print(f"扫描完成，共处理 {len(all_scanned)} 只股票，其中 {len(stocks)} 只进入信号列表")
        return stocks, all_scanned

    except Exception as e:
        print(f"获取活跃股列表失败: {e}")
        return stocks, all_scanned

def generate_data():
    print("开始获取大盘环境...")
    env = get_market_env()
    print(f"大盘环境: {env}")

    print("开始获取新闻...")
    news = get_news()
    print(f"新闻条数: {len(news)}")

    print("开始扫描全市场活跃股...")
    stocks, scanned = get_stocks_from_active_list(limit=150, output_max=10)
    print(f"最终信号股票数: {len(stocks)}，扫描总数: {len(scanned)}")

    # 板块数据（固定）
    sectors = [
        {"name": "半导体", "score": 4, "state": "持续强势"},
        {"name": "人工智能", "score": 4, "state": "持续强势"},
        {"name": "新能源车", "score": 3, "state": "正在加强"},
        {"name": "军工", "score": 3, "state": "正在加强"}
    ]

    data = {
        "updateTime": datetime.datetime.now().strftime("%H:%M"),
        "marketEnv": env,
        "news": news,
        "sectors": sectors,
        "stocks": stocks,
        "scannedStocks": scanned
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("data.json 已生成")

if __name__ == "__main__":
    generate_data()
