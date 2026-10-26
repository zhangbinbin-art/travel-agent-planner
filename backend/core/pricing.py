"""门票价格配置。

本模块保存各景点的预设门票单价，供路线预算估算使用。
价格是项目内置的演示数据，不依赖任何外部票务接口。
"""

from typing import Optional

# 各景点的预设门票价格（单位：元）。未收录的景点回退到 DEFAULT_TICKET_PRICE。
TICKET_PRICES = {"西湖景区": 0.0, "故宫博物院": 60.0, "外滩": 0.0}

# 未知景点使用的默认门票价格（单位：元）。
DEFAULT_TICKET_PRICE = 50.0


def get_ticket_price(name: Optional[str]) -> float:
    """按景点名称返回预设门票价格。

    名称不存在或为 None 时返回默认价格，保证预算估算永远有值。
    """
    if not name:
        return DEFAULT_TICKET_PRICE
    return TICKET_PRICES.get(name, DEFAULT_TICKET_PRICE)
