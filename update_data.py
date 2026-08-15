import json
import datetime
import pandas as pd
import akshare as ak
import numpy as np

def safe_float(x):
    try:
        return float(x)
    except:
        return 0.0

def get_market_env():
    """大盘环境判断：基于上证指数"""
    try:
        # 获取上证指数日线（最近60个交易日）
        df = ak.stock_zh_index_daily(symbol="sh000001")
        if df is None or df.empty:
            return "正常", 50
        df = df.tail(60)
        close = df['close'].astype(float)
        vol = df['volume'].astype(float)
        ma20 = close.rolling(20).mean()
        ma20_prev = ma20.shift(5)
        # 均线判断
        cond1 = close.iloc[-1] > ma20.iloc[-1] and ma20.iloc[-1] > ma20_prev.iloc[-1]
        # 量能判断
        vol_5 = vol.tail(5).mean()
        vol_20 = vol.tail(20).mean()
        cond2 = vol_5 > vol_20 * 1.1
        # 涨幅判断（近5日）
        ret_5 = (close.iloc[-1] / close.iloc[-6] - 1) * 100
        cond3 = ret_5 > 0.5
        score = sum([cond1, cond2, cond3])
        if score >= 2:
            return "强", 80
        elif score == 1:
            return "正常", 50
        else:
            return "偏弱", 20
    except Exception as e:
        print(f"get_market_env error: {e}")
        return "正常", 50

def get_sectors():
    """获取行业板块行情，返回列表"""
    try:
        df = ak.stock_board_industry_name_em()
        if df is None or df.empty:
            return []
        # 计算5日、20日涨幅近似（实时行情没有历史，这里只取当日涨幅和量比）
        # 实际可用 stock_board_industry_hist_em 获取历史，但为简化，取当日涨跌幅和量比
        df = df.head(20)  # 取前20个板块
        sectors = []
        for _, row in df.iterrows():
            name = row.get('板块名称', '')
            pct = safe_float(row.get('涨跌幅', 0))
            turnover = safe_float(row.get('换手率', 0))
            # 简单评分：涨跌幅排名 + 量比（用换手率代替）
            score = 3
            if pct > 2:
                score = 5
            elif pct > 0:
                score = 4
            elif pct < -2:
                score = 1
            state = "持续强势" if pct > 1 else ("正在加强" if pct > 0 else "观察")
            sectors.append({
                "name": name,
                "score": score,
                "state": state
            })
        return sectors
    except Exception as e:
        print(f"get_sectors error: {e}")
        return []

def get_stock_list(limit=10):
    """获取个股列表，尽量选取强势板块中的活跃股"""
    try:
        # 获取全A实时行情，按成交额排序取前 limit 只
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return []
        df = df[df['代码'].str.match(r'^(60|00|30|68)')]  # 过滤主板、创业板、科创板
        df = df.sort_values('成交额', ascending=False).head(limit)
        stocks = []
        for _, row in df.iterrows():
            code = str(row['代码'])
            name = str(row['名称'])
            pct = safe_float(row['涨跌幅'])
            # 获取历史日线计算均线、ATR等
            try:
                hist = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=(datetime.date.today() - datetime.timedelta(days=60)).strftime("%Y%m%d"), end_date=datetime.date.today().strftime("%Y%m%d"), adjust="qfq")
                if hist is not None and len(hist) >= 25:
                    close = hist['收盘'].astype(float)
                    vol = hist['成交量'].astype(float)
                    ma20 = close.rolling(20).mean().iloc[-1]
                    d20 = (close.iloc[-1] / ma20 - 1) * 100
                    r5 = (close.iloc[-1] / close.iloc[-6] - 1) * 100
                    r10 = (close.iloc[-1] / close.iloc[-11] - 1) * 100
                    r20 = (close.iloc[-1] / close.iloc[-21] - 1) * 100
                    vol_ratio = vol.tail(5).mean() / vol.tail(20).mean() if vol.tail(20).mean() > 0 else 1
                    # 计算 ATR
                    tr = pd.concat([(hist['最高'] - hist['最低']), (hist['最高'] - hist['收盘'].shift()).abs(), (hist['最低'] - hist['收盘'].shift()).abs()], axis=1).max(axis=1)
                    atr = tr.rolling(14).mean().iloc[-1]
                    atr_pct = (atr / close.iloc[-1]) * 100
                    # 简单分类
                    if d20 > 15 or r5 > 15:
                        stateClass = "高位观察"
                        decision = "不买"
                    elif r5 < 0 and r10 > 0 and r20 > 0:
                        stateClass = "回调观察"
                        decision = "观察"
                    elif 0 < r5 <= 8 and r10 <= 5 and r20 <= 10:
                        stateClass = "启动观察"
                        decision = "观察" if r5 > 5 else "买"
                    elif 0 < r5 < 15 and r10 > 0 and r20 > 0:
                        stateClass = "趋势观察"
                        decision = "买"
                    else:
                        stateClass = "排除"
                        decision = "不买"
                    holding_period = "长期（1-3个月）" if stateClass in ["趋势观察","回调观察"] else ("短期（1-2周）" if stateClass == "启动观察" else "仅观察")
                    prob_up = 60 + int(d20) if decision == "买" else (40 if decision == "观察" else 20)
                    stocks.append({
                        "name": name,
                        "code": code,
                        "decision": decision,
                        "holdingPeriod": holding_period,
                        "probUp": prob_up,
                        "r5": f"{r5:+.1f}%",
                        "r10": f"{r10:+.1f}%",
                        "r20": f"{r20:+.1f}%",
                        "d20": f"{d20:+.1f}%",
                        "atr": f"{atr_pct:.1f}%",
                        "volRatio": f"{vol_ratio:.2f}",
                        "stateClass": stateClass,
                        "newsSentiment": "中性"
                    })
                else:
                    continue
            except Exception as e:
                print(f"get stock hist error {code}: {e}")
                continue
        return stocks
    except Exception as e:
        print(f"get_stock_list error: {e}")
        return []

def get_news():
    """获取实时财经新闻，返回列表"""
    try:
        df = ak.stock_info_global_em()
        if df is None or df.empty:
            return []
        news = []
        for _, row in df.head(6).iterrows():
            title = str(row.get('标题', ''))
            # 简单情感判断
            keywords_pos = ["利好","增长","超预期","中标","突破","上涨","回购"]
            keywords_neg = ["利空","下滑","违规","处罚","亏损","减持","问询"]
            sentiment = "positive" if any(k in title for k in keywords_pos) else ("negative" if any(k in title for k in keywords_neg) else "neutral")
            sentimentLabel = "利好" if sentiment == "positive" else ("利空" if sentiment == "negative" else "中性")
            news.append({
                "title": title,
                "time": datetime.datetime.now().strftime("%H:%M"),
                "sentiment": sentiment,
                "sentimentLabel": sentimentLabel,
                "related": ["大盘"] if sentiment == "neutral" else ["相关板块"],
                "source": "东财快讯"
            })
        return news
    except Exception as e:
        print(f"get_news error: {e}")
        return [{"title": "新闻获取失败，请稍后", "time": "00:00", "sentiment": "neutral", "sentimentLabel": "中性", "related": ["无"], "source": "无"}]

def generate_data():
    print("开始获取大盘环境...")
    env, position = get_market_env()
    print(f"大盘环境: {env}")
    print("开始获取板块...")
    sectors = get_sectors()
    print(f"板块数量: {len(sectors)}")
    print("开始获取个股...")
    stocks = get_stock_list(8)
    print(f"个股数量: {len(stocks)}")
    print("开始获取新闻...")
    news = get_news()
    print(f"新闻数量: {len(news)}")
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
