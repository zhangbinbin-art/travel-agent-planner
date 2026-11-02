"""高德 Web 服务地理编码封装（地点名称 -> 经纬度）。

只使用标准库 urllib，不引入新依赖；任何失败都以 GeoCodeError 抛出，
由接口层转换成带明确原因的 HTTP 错误，方便后台录入时定位问题。
"""

import json
import urllib.parse
import urllib.request
from typing import Optional

from core.config import settings

GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"


class GeoCodeError(Exception):
    """地理编码失败（携带建议的 HTTP 状态码与人类可读原因）。"""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _plain_text(value) -> Optional[str]:
    """高德对缺失字段返回 []，统一转换成 None。"""
    if isinstance(value, list):
        if not value:
            return None
        value = value[0]
    if value in (None, "", "[]"):
        return None
    return str(value)


def geocode(address: str, city: Optional[str] = None) -> dict:
    """调用高德地理编码接口，返回标准经纬度与结构化地址。

    参数：
        address: 地点名称，如「杭州西湖」。
        city: 可选城市限制，减少重名地点误判。
    返回：
        dict，包含 lng / lat / formatted_address / province / city / district / level。
    """
    address = (address or "").strip()
    if not address:
        raise GeoCodeError("地点名称不能为空", 400)

    key = (settings.AMAP_WEB_KEY or "").strip()
    if not key:
        raise GeoCodeError("后端未配置高德 Web 服务 Key（backend/.env 的 AMAP_WEB_KEY）", 503)

    params = {"key": key, "address": address, "output": "JSON"}
    city = (city or "").strip()
    if city:
        params["city"] = city

    url = GEOCODE_URL + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        raise GeoCodeError("地理编码服务请求失败，请稍后重试", 502)

    if str(data.get("status")) != "1":
        info = _plain_text(data.get("info")) or "UNKNOWN_ERROR"
        raise GeoCodeError(f"高德地理编码失败：{info}", 502)

    geocodes = data.get("geocodes") or []
    if not geocodes:
        raise GeoCodeError(f"未能解析地点：{address}，请换更完整的名称（如加上城市）", 404)

    first = geocodes[0] or {}
    location = _plain_text(first.get("location")) or ""
    try:
        lng_text, lat_text = location.split(",")
        lng = round(float(lng_text), 6)
        lat = round(float(lat_text), 6)
    except Exception:
        raise GeoCodeError("高德返回的坐标格式异常", 502)

    return {
        "location_name": address,
        "lng": lng,
        "lat": lat,
        "formatted_address": _plain_text(first.get("formatted_address")),
        "province": _plain_text(first.get("province")),
        "city": _plain_text(first.get("city")),
        "district": _plain_text(first.get("district")),
        "level": _plain_text(first.get("level")),
    }
