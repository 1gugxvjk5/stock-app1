import json
import random
from datetime import datetime

def generate_data():
    now = datetime.now()
    time_str = now.strftime("%H:%M")

    # 随机调整涨跌幅，模拟数据变化
    def rnd(base, spread=1.5):
        return round(base + random.uniform(-spread, spread), 1)

    data = {
        "updateTime": time_str,
        "marketEnv": random.choice(["强", "正常"]),
        "news": [
            {"title": f"央行开展MLF操作，流动性充裕（{time_str}更新）", "time": time_str, "sentiment": "positive", "sentimentLabel": "利好", "related": ["大盘", "银行"], "source": "财联社"},
            {"title": f"半导体行业景气度提升，设备订单增加（{time_str}更新）", "time": time_str, "sentiment": "positive", "sentimentLabel": "利好", "related": ["半导体"], "source": "东方财富"},
            {"title": f"新能源汽车销量数据发布，同比高增（{time_str}更新）", "time": time_str, "sentiment": "positive", "sentimentLabel": "利好", "related": ["新能源车"], "source": "同花顺"},
            {"title": f"监管层关注部分个股异常波动（{time_str}更新）", "time": time_str, "sentiment": "negative", "sentimentLabel": "利空", "related": ["监管"], "source": "新浪财经"}
        ],
        "sectors": [
            {"name": "半导体", "score": random.choice([4,5]), "state": "持续强势"},
            {"name": "人工智能", "score": random.choice([3,4]), "state": "持续强势"},
            {"name": "新能源车", "score": random.choice([3,4]), "state": "正在加强"},
            {"name": "军工", "score": random.choice([2,3]), "state": "正在加强"}
        ],
        "stocks": [
            {
                "name": "示例半导体股",
                "code": "688001",
                "decision": random.choice(["买","观察"]),
                "holdingPeriod": "长期（1-3个月）" if random.random() > 0.3 else "短期（1-2周）",
                "probUp": random.randint(55, 75),
                "r5": f"{rnd(6.2, 2):+.1f}%",
                "r10": f"{rnd(11.5, 3):+.1f}%",
                "r20": f"{rnd(18.3, 4):+.1f}%",
                "d20": f"{rnd(8.1, 2):+.1f}%",
                "atr": f"{rnd(2.4, 0.5):.1f}%",
                "volRatio": f"{rnd(1.35, 0.3):.2f}",
                "stateClass": "趋势观察",
                "newsSentiment": "正面"
            },
            {
                "name": "示例AI股",
                "code": "300001",
                "decision": random.choice(["买","观察"]),
                "holdingPeriod": "短期（1-2周）" if random.random() > 0.4 else "仅观察",
                "probUp": random.randint(45, 65),
                "r5": f"{rnd(4.8, 2):+.1f}%",
                "r10": f"{rnd(9.2, 3):+.1f}%",
                "r20": f"{rnd(15.6, 4):+.1f}%",
                "d20": f"{rnd(5.2, 2):+.1f}%",
                "atr": f"{rnd(3.1, 0.5):.1f}%",
                "volRatio": f"{rnd(1.22, 0.3):.2f}",
                "stateClass": "启动观察",
                "newsSentiment": "中性"
            },
            {
                "name": "示例新能源股",
                "code": "002001",
                "decision": "观察",
                "holdingPeriod": "仅观察",
                "probUp": random.randint(30, 50),
                "r5": f"{rnd(-1.2, 1.5):+.1f}%",
                "r10": f"{rnd(6.8, 2):+.1f}%",
                "r20": f"{rnd(12.4, 3):+.1f}%",
                "d20": f"{rnd(2.8, 1.5):+.1f}%",
                "atr": f"{rnd(4.5, 1):.1f}%",
                "volRatio": f"{rnd(0.85, 0.2):.2f}",
                "stateClass": "回调观察",
                "newsSentiment": "正面"
            },
            {
                "name": "示例高位股",
                "code": "600001",
                "decision": "不买",
                "holdingPeriod": "高位风险",
                "probUp": random.randint(20, 35),
                "r5": f"{rnd(18.5, 3):+.1f}%",
                "r10": f"{rnd(28.2, 4):+.1f}%",
                "r20": f"{rnd(35.7, 5):+.1f}%",
                "d20": f"{rnd(17.3, 3):+.1f}%",
                "atr": f"{rnd(5.2, 1):.1f}%",
                "volRatio": f"{rnd(2.10, 0.4):.2f}",
                "stateClass": "高位观察",
                "newsSentiment": "负面"
            }
        ]
    }
    return data

if __name__ == "__main__":
    data = generate_data()
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("data.json generated")
