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
    """大盘环境判断：基于上证指数"""
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
    """获取全球财经快讯，取前6条"""
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

def get_strong_sectors(top_n=3):
    """获取涨幅靠前的行业板块，返回板块名称列表"""
    try:
        df = ak.stock_board_industry_name_em()
        if df is None or df.empty:
            return []
        # 按涨跌幅排序，取涨幅最大的 top_n 个板块
        df = df.sort_values('涨跌幅', ascending=False).head(top_n)
        return df['板块名称'].tolist()
    except Exception as e:
        print(f"获取强势板块失败: {e}")
        return []

def get_stock_indicators(code):
    """获取单只股票的指标，返回字典，若失败返回None"""
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

        # 状态分类
        if d20 > 15 or r5 > 15:
            stateClass = "高位观察"
            decision = "不买"
        elif r5 < 0 and r10 > 0 and r20 > 0:
            stateClass = "回调观察"
            decision = "观察"
        elif 0 < r5 <= 8 and r10 <= 5 and r20 <= 10:
            stateClass = "启动观察"
            decision = "买" if r5 > 3 else "观察"
        elif 0 < r5 < 15 and r10 > 0 and r20 > 0:
            stateClass = "趋势观察"
            decision = "买"
        else:
            stateClass = "排除"
            decision = "不买"

        if stateClass == "排除":
            return None

        holding_period = "长期（1-3个月）" if stateClass in ["趋势观察", "回调观察"] else (
            "短期（1-2周）" if stateClass == "启动观察" else "仅观察")
        prob_up = 65 if decision == "买" else (45 if decision == "观察" else 25)

        return {
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
        }
    except Exception as e:
        print(f"获取股票 {code} 指标失败: {e}")
        return None

def get_sector_leader(sector_name):
    """获取某个板块的龙头股（按成交额最大）并计算指标"""
    try:
        # 获取板块成分股
        df = ak.stock_board_industry_cons_em(symbol=sector_name)
        if df is None or df.empty:
            return None
        # 按成交额排序，取第一只作为龙头
        df = df.sort_values('成交额', ascending=False).head(1)
        if df.empty:
            return None
        code = str(df.iloc[0]['代码'])
        name = str(df.iloc[0]['名称'])
        indicators = get_stock_indicators(code)
        if indicators is None:
            return None
        indicators['name'] = name
        return indicators
    except Exception as e:
        print(f"获取板块 {sector_name} 龙头失败: {e}")
        return None

def generate_data():
    print("开始获取大盘环境...")
    env = get_market_env()
    print(f"大盘环境: {env}")

    print("开始获取新闻...")
    news = get_news()
    print(f"新闻条数: {len(news)}")

    print("开始获取强势板块...")
    sectors = get_strong_sectors(3)
    print(f"强势板块: {sectors}")

    stocks = []
    sectors_data = []
    for sector in sectors:
        print(f"处理板块: {sector}")
        leader = get_sector_leader(sector)
        if leader:
            stocks.append(leader)
            # 板块信息
            sectors_data.append({
                "name": sector,
                "score": 4,
                "state": "持续强势" if leader['decision'] == "买" else "正在加强"
            })

    # 如果股票数量不足，补充一些活跃股（可选）
    if len(stocks) < 3:
        print("股票数量不足，尝试补充活跃股...")
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                df = df[~df['名称'].str.contains('ST|退', na=False)]
                df = df.sort_values('成交额', ascending=False).head(5)
                for _, row in df.iterrows():
                    code = str(row['代码'])
                    name = str(row['名称'])
                    indicators = get_stock_indicators(code)
                    if indicators:
                        indicators['name'] = name
                        if indicators not in stocks:
                            stocks.append(indicators)
                        if len(stocks) >= 5:
                            break
        except Exception as e:
            print(f"补充股票失败: {e}")

    # 板块数据若为空，使用默认
    if not sectors_data:
        sectors_data = [
            {"name": "半导体", "score": 4, "state": "持续强势"},
            {"name": "人工智能", "score": 4, "state": "持续强势"},
            {"name": "新能源车", "score": 3, "state": "正在加强"}
        ]

    data = {
        "updateTime": datetime.datetime.now().strftime("%H:%M"),
        "marketEnv": env,
        "news": news,
        "sectors": sectors_data,
        "stocks": stocks
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"data.json 已生成，股票数量: {len(stocks)}")

if __name__ == "__main__":
    generate_data()
