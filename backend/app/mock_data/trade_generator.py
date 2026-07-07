"""Realistic trade data generator for China-ASEAN bilateral trade."""
import numpy as np
from typing import Dict, List

# Fix random seed for reproducibility
np.random.seed(42)


# ── Country data ──
COUNTRIES = [
    {"code": "VNM", "name_cn": "越南", "name_en": "Vietnam",
     "asean_member": 1, "rcep_member": 1, "gdp_billion_usd": 430.0, "population_million": 100.3,
     "latitude": 21.0, "longitude": 105.8, "base_trade": 150.0,
     "key_chapters": [85, 84, 50, 61, 62, 72, 39]},  # electronics, machinery, textiles, steel, plastics
    {"code": "THA", "name_cn": "泰国", "name_en": "Thailand",
     "asean_member": 1, "rcep_member": 1, "gdp_billion_usd": 495.0, "population_million": 71.7,
     "latitude": 13.7, "longitude": 100.5, "base_trade": 100.0,
     "key_chapters": [84, 85, 87, 40, 73, 71]},
    {"code": "MYS", "name_cn": "马来西亚", "name_en": "Malaysia",
     "asean_member": 1, "rcep_member": 1, "gdp_billion_usd": 400.0, "population_million": 33.7,
     "latitude": 3.1, "longitude": 101.7, "base_trade": 90.0,
     "key_chapters": [85, 84, 27, 15, 39, 71]},
    {"code": "IDN", "name_cn": "印度尼西亚", "name_en": "Indonesia",
     "asean_member": 1, "rcep_member": 1, "gdp_billion_usd": 1370.0, "population_million": 277.5,
     "latitude": -6.2, "longitude": 106.8, "base_trade": 80.0,
     "key_chapters": [84, 85, 72, 39, 15, 38]},
    {"code": "PHL", "name_cn": "菲律宾", "name_en": "Philippines",
     "asean_member": 1, "rcep_member": 1, "gdp_billion_usd": 395.0, "population_million": 117.3,
     "latitude": 14.6, "longitude": 120.9, "base_trade": 50.0,
     "key_chapters": [85, 84, 87, 61, 27, 10]},
    {"code": "SGP", "name_cn": "新加坡", "name_en": "Singapore",
     "asean_member": 1, "rcep_member": 1, "gdp_billion_usd": 510.0, "population_million": 5.9,
     "latitude": 1.3, "longitude": 103.8, "base_trade": 70.0,
     "key_chapters": [85, 84, 71, 27, 90, 88]},
    {"code": "MMR", "name_cn": "缅甸", "name_en": "Myanmar",
     "asean_member": 1, "rcep_member": 1, "gdp_billion_usd": 65.0, "population_million": 54.4,
     "latitude": 16.8, "longitude": 96.1, "base_trade": 15.0,
     "key_chapters": [84, 85, 87, 27, 52, 71]},
    {"code": "KHM", "name_cn": "柬埔寨", "name_en": "Cambodia",
     "asean_member": 1, "rcep_member": 1, "gdp_billion_usd": 32.0, "population_million": 16.7,
     "latitude": 11.5, "longitude": 104.9, "base_trade": 10.0,
     "key_chapters": [61, 62, 85, 64, 84, 52]},
    {"code": "LAO", "name_cn": "老挝", "name_en": "Laos",
     "asean_member": 1, "rcep_member": 1, "gdp_billion_usd": 18.0, "population_million": 7.5,
     "latitude": 17.9, "longitude": 102.6, "base_trade": 5.0,
     "key_chapters": [85, 84, 87, 71, 44]},
    {"code": "BRN", "name_cn": "文莱", "name_en": "Brunei",
     "asean_member": 1, "rcep_member": 1, "gdp_billion_usd": 17.0, "population_million": 0.45,
     "latitude": 4.9, "longitude": 114.9, "base_trade": 1.5,
     "key_chapters": [84, 85, 87, 73]},
]

# HS chapter sections (simplified)
HS_CHAPTERS = {
    1: "活动物", 2: "肉及肉制品", 3: "鱼", 4: "乳", 5: "其他动物产品",
    6: "活植物", 7: "蔬菜", 8: "水果", 9: "咖啡茶", 10: "谷物",
    11: "制粉", 12: "油籽", 13: "虫胶", 14: "植物材料", 15: "油脂",
    16: "肉制品", 17: "糖", 18: "可可", 19: "谷物制品", 20: "蔬菜制品",
    21: "杂项食品", 22: "饮料", 23: "饲料", 24: "烟草",
    25: "盐", 26: "矿石", 27: "矿物燃料", 28: "无机化学品", 29: "有机化学品",
    30: "药品", 31: "肥料", 32: "染料", 33: "化妆品", 34: "洗涤剂",
    35: "蛋白物质", 36: "炸药", 37: "照相用品", 38: "杂项化工", 39: "塑料",
    40: "橡胶", 41: "生皮", 42: "皮革制品", 43: "毛皮", 44: "木及木制品",
    45: "软木", 46: "稻草制品", 47: "纸浆", 48: "纸及纸板", 49: "书籍",
    50: "蚕丝", 51: "羊毛", 52: "棉花", 53: "植物纤维", 54: "化纤长丝",
    55: "化纤短纤", 56: "絮胎", 57: "地毯", 58: "特种织物", 59: "工业用织物",
    60: "针织物", 61: "针织服装", 62: "非针织服装", 63: "其他纺织制品",
    64: "鞋靴", 65: "帽类", 66: "雨伞", 67: "羽毛制品", 68: "石料",
    69: "陶瓷", 70: "玻璃", 71: "珠宝", 72: "钢铁", 73: "钢铁制品",
    74: "铜", 75: "镍", 76: "铝", 78: "铅", 79: "锌",
    80: "锡", 81: "其他金属", 82: "工具", 83: "杂项金属", 84: "机械及设备",
    85: "电气设备", 86: "铁道车辆", 87: "车辆", 88: "航空器", 89: "船舶",
    90: "光学仪器", 91: "钟表", 92: "乐器", 93: "武器", 94: "家具",
    95: "玩具", 96: "杂项制品", 97: "艺术品", 98: "特殊商品", 99: "特殊交易",
}

# HS chapter to section mapping
def get_section(chapter: int) -> str:
    if 1 <= chapter <= 24: return "农产品"
    if 25 <= chapter <= 27: return "矿产品"
    if 28 <= chapter <= 38: return "化工产品"
    if 39 <= chapter <= 40: return "塑料橡胶"
    if 41 <= chapter <= 43: return "皮革"
    if 44 <= chapter <= 49: return "木材纸张"
    if 50 <= chapter <= 63: return "纺织原料"
    if 64 <= chapter <= 67: return "鞋帽伞"
    if 68 <= chapter <= 70: return "非金属制品"
    if 71 <= chapter <= 83: return "金属制品"
    if 84 <= chapter <= 85: return "机电产品"
    if 86 <= chapter <= 89: return "运输设备"
    if 90 <= chapter <= 92: return "精密仪器"
    if 93 <= chapter <= 99: return "其他制品"
    return "其他"


def _year_growth(year: int) -> float:
    """Annual growth multiplier encoding realistic macro patterns."""
    g = 1.0
    # 2015-2019: steady growth ~5-8%
    if 2015 <= year <= 2019:
        g = 1.05 + 0.02 * np.random.randn()
    # 2020: COVID shock
    elif year == 2020:
        g = 0.92
    # 2021: strong rebound
    elif year == 2021:
        g = 1.20
    # 2022: RCEP effective Jan 2022, boost
    elif year == 2022:
        g = 1.10
    elif year == 2023:
        g = 1.06
    elif year == 2024:
        g = 1.08
    elif year == 2025:
        g = 1.07
    return g


def _month_seasonality(month: int) -> float:
    """Monthly seasonality: Q4 peak for holiday season, summer dip."""
    factors = [1.05, 0.90, 1.10, 1.00, 0.95, 0.95, 0.95, 0.95, 1.00, 1.05, 1.10, 1.05]
    return factors[month - 1]


def generate_countries() -> List[Dict]:
    """Return country dimension records."""
    return [{k: v for k, v in c.items() if k != "base_trade" and k != "key_chapters"}
            for c in COUNTRIES]


def generate_products() -> List[Dict]:
    """Generate product dimension records (top ~200 HS6 codes)."""
    products = []
    seen = set()
    for country in COUNTRIES:
        for chapter in country["key_chapters"]:
            for _ in range(np.random.randint(3, 6)):
                # Generate a 6-digit HS code
                subheading = np.random.randint(10, 100)
                hs_code = f"{chapter:02d}{subheading:02d}"
                if hs_code in seen:
                    continue
                seen.add(hs_code)
                section = get_section(chapter)
                products.append({
                    "hs_code": hs_code,
                    "hs_name_cn": f"{HS_CHAPTERS.get(chapter, '其他')}-{hs_code}",
                    "hs_name_en": f"{section}-{hs_code}",
                    "hs_chapter": chapter,
                    "hs_section": section,
                    "is_agricultural": 1 if chapter <= 24 else 0,
                    "is_industrial": 1 if 84 <= chapter <= 85 else 0,
                    "is_consumer_goods": 1 if chapter in [61, 62, 64, 95, 94] else 0,
                })
    return products


def generate_trade_records() -> List[Dict]:
    """Generate monthly trade records 2015-2025, China → ASEAN."""
    records = []
    years = list(range(2015, 2026))

    for year in years:
        growth = _year_growth(year)
        for month in range(1, 13):
            season = _month_seasonality(month)
            for country in COUNTRIES:
                base = country["base_trade"]
                country_growth = growth * (1 + 0.1 * np.random.randn())
                monthly_value = (base * country_growth * season) / 12  # billion USD

                # Distribute across key HS chapters for this country
                num_chapters = len(country["key_chapters"])
                for i, chapter in enumerate(country["key_chapters"]):
                    # Chapter weight: earlier chapters in key list have higher weight
                    weight = (num_chapters - i) / sum(range(1, num_chapters + 1))
                    subheading = np.random.randint(10, 100)
                    hs_code = f"{chapter:02d}{subheading:02d}"
                    chapter_value = monthly_value * weight * 1e9 * np.random.uniform(0.8, 1.2)
                    records.append({
                        "year": year,
                        "month": month,
                        "reporter": "CHN",
                        "partner": country["code"],
                        "hs_code": hs_code,
                        "hs_chapter": chapter,
                        "hs_section": get_section(chapter),
                        "trade_value_usd": round(chapter_value, 2),
                        "quantity": round(chapter_value / np.random.uniform(50, 500), 2),
                        "unit": "kg",
                        "trade_flow": "export",
                    })
    return records


def generate_tariff_rules() -> List[Dict]:
    """Generate RCEP tariff rules for common HS codes."""
    rules = []
    seen = set()
    for country in COUNTRIES:
        for chapter in country["key_chapters"]:
            for subheading in range(10, 30):
                hs_code = f"{chapter:02d}{subheading:02d}"
                if hs_code in seen:
                    continue
                seen.add(hs_code)
                mfn = round(np.random.uniform(2.5, 12.0), 1)
                # RCEP rate typically 50-80% of MFN
                rcep = round(mfn * np.random.uniform(0.2, 0.7), 1)
                # Many products will be 0 under RCEP after phase-in
                if np.random.random() > 0.4:
                    rcep = 0.0
                rules.append({
                    "hs_code": hs_code,
                    "partner_country": country["code"],
                    "mfn_rate": mfn,
                    "rcep_rate": rcep,
                    "fta_rate": round(mfn * 0.5, 1) if np.random.random() > 0.5 else None,
                    "rule_of_origin": "区域价值成分40%以上" if chapter <= 27 else "税则归类改变(CTC)",
                    "valid_from": "2022-01-01",
                    "valid_to": "2032-12-31",
                })
    return rules


def generate_all() -> Dict:
    """Generate all mock data."""
    return {
        "countries": generate_countries(),
        "products": generate_products(),
        "trade_records": generate_trade_records(),
        "tariff_rules": generate_tariff_rules(),
    }


if __name__ == "__main__":
    data = generate_all()
    print(f"Countries: {len(data['countries'])}")
    print(f"Products: {len(data['products'])}")
    print(f"Trade records: {len(data['trade_records'])}")
    print(f"Tariff rules: {len(data['tariff_rules'])}")
    sample = data["trade_records"][0]
    print(f"\nSample record: {sample}")