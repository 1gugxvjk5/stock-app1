import json
import datetime
import akshare as ak
import pandas as pd

def safe_float(x):
    try:
        return float(x)
    except:
        return 0.0

def get_market_env():
    """只获取上证指数日线，判断大盘环境"""
    try:
        df = ak.stock_zh_index_daily(symbol="sh000001")
        if df is None or df.empty:
            return "正常"
        df = df.tail(30)
        close = df['close'].astype(float)
        ma20 = close.rolling(20).mean()
        # 简单判断：收盘价在20日线上方且20日线向上
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
    """获取全球财经快讯，取前6条"""
    try:
        df = ak.stock_info_global_em()
        if df is None or df.empty:
            return [{"title": "暂无新闻数据", "time": "00:00", "sentiment": "neutral", "sentimentLabel": "中性", "related": ["无"], "source": "无"}]
        news = []
        for _, row in df.head(6).iterrows():
            title = str(row.get('标题', ''))
            # 简单情感判断
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

def generate_data():
    print("开始获取大盘环境...")
    env = get_market_env()
    print(f"大盘环境: {env}")

    print("开始获取新闻...")
    news = get_news()
    print(f"新闻条数: {len(news)}")

    # 固定板块和个股数据（后续可替换为真实）
    sectors = [
        {"name": "半导体", "score": 4, "state": "持续强势"},
        {"name": "人工智能", "score": 4, "state": "持续强势"},
        {"name": "新能源车", "score": 3, "state": "正在加强"},
        {"name": "军工", "score": 3, "state": "正在加强"}
    ]

    stocks = [
        {
            "name": "示例股票1", "code": "600000", "decision": "买",
            "holdingPeriod": "长期（1-3个月）", "probUp": 68,
            "r5": "+6.2%", "r10": "+11.5%", "r20": "+18.3%", "d20": "+8.1%",
            "atr": "2.4%", "volRatio": "1.35", "stateClass": "趋势观察", "newsSentiment": "正面"
        },
        {
            "name": "示例股票2", "code": "000001", "decision": "观察",
            "holdingPeriod": "短期（1-2周）", "probUp": 55,
            "r5": "+4.8%", "r10": "+9.2%", "r20": "+15.6%", "d20": "+5.2%",
            "atr": "3.1%", "volRatio": "1.22", "stateClass": "启动观察", "newsSentiment": "中性"
        }
    ]

    data = {
        "updateTime": datetime.datetime.now().strftime("%H:%M"),
        "marketEnv": env,
        "news": news,
        "sectors": sectors,
        "stocks": stocks
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("data.json 已生成")

if __name__ == "__main__":
    generate_data()
