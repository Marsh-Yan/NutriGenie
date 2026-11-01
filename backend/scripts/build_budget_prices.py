"""Build the explicitly estimated remainder; values are not retailer live quotes."""
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app/db/seed_data"

# id | planning package price CNY | amount | g/ml | specification | anchor
# These amounts describe a budgeting basis, never an invented retailer SKU.
ROWS = """
3|19.90|500|g|生鸡胸肉，去皮去骨，未调味|manual
5|22.00|500|g|鲜猪里脊肉，非普通后腿肉|manual
6|3.99|360|g|原味盒装嫩豆腐，参考祖名绢豆腐规格|wujiang
7|47.99|500|g|生鲜去骨牛肉，参考牛腿肉档位|wuhan
9|115.00|908|g|去头去壳去虾线冷冻大虾仁，按标签净重|sam-history
12|4.00|250|g|鲜小葱，按购买重量，不假定每把重量|manual
14|8.00|500|g|干鸡蛋挂面，不是鲜湿面|manual
16|22.00|500|g|鲜活整条鲈鱼，含头骨内脏的购买重|manual
23|18.00|500|g|去骨鸡腿肉，非整鸡腿|manual
25|89.00|500|g|生三文鱼肉，去骨分切，非熟制或鱼骨|manual
26|15.00|250|g|鲜芦笋，按购买重量|manual
27|8.00|500|g|普通鲜柠檬，带皮购买重|manual
28|16.80|1500|ml|普通鲜牛奶，参考光明纯鲜牛奶规格|wujiang
29|14.40|980|g|原味酸牛奶，参考光明原味酸牛奶规格|wujiang
30|15.00|1000|g|原味纯燕麦片，干品，无果干奶粉混合|manual
31|12.00|400|g|普通全麦切片面包，按净重|manual
32|12.00|500|g|原味干意大利面|manual
33|25.00|200|g|原味动物黄油，非人造黄油|manual
34|18.00|200|g|原味芝士片，按整包净重而非每片假定克重|manual
35|79.00|750|ml|日常烹饪橄榄油，按体积，不假定密度|manual
36|18.85|1280|ml|生抽酱油，参考海天金标生抽规格|wujiang
37|7.80|500|ml|食用陈醋，参考恒顺陈醋规格|wujiang
38|14.49|1900|ml|烹饪料酒，参考老恒和原酿料酒规格|wujiang
39|3.23|500|g|普通食盐，参考区域零售均价取整|wuhan
40|5.00|500|g|普通白砂糖，参考食糖区域零售均价取整|wuhan
41|12.00|30|g|纯黑胡椒粉，非黑椒汁或复合椒盐|manual
42|26.00|1900|ml|老抽酱油，参考海天草菇老抽规格|wujiang
43|9.90|1000|g|蚝油，参考海天上等蚝油，按克不是毫升|wujiang
44|5.34|500|g|鲜辣椒，按购买重量，参考区域辣椒零售价取整|wuhan
45|8.00|300|g|番茄酱，非番茄沙司混用体积|manual
46|129.00|1000|g|大西洋真鳕鱼肉，冷冻去骨分切，非银鳕鱼或油鱼|sam-history
47|18.00|500|g|鲜牛油果，含皮核购买重|manual
49|15.00|185|g|金枪鱼罐头，按罐装净含量含汁液，非沥干鱼肉重|manual
50|59.00|200|g|原切生牛排，非拼接调理牛排|manual
51|20.00|500|g|鲜猪瘦肉切丝，含切配溢价估算|manual
52|10.00|500|g|生花生仁，去壳，非带壳花生|manual
53|6.90|50|g|干辣椒段，参考禾煜辣椒段规格|wujiang
54|18.00|250|ml|纯芝麻香油，按体积|manual
55|8.00|50|g|干紫菜，非调味即食海苔|manual
56|2.27|1000|ml|零售瓶装饮用水，非居民自来水水费|wuhan
57|8.00|1000|g|生糙米，干品|manual
58|20.00|500|g|原味生藜麦，干品，非藜麦混合饭|manual
59|8.00|1000|g|普通生小米，干品|manual
60|5.00|500|g|鲜甜玉米棒，含玉米芯购买重，非净玉米粒|manual
61|4.00|500|g|鲜红薯，带皮购买重|manual
62|12.00|500|g|干荞麦面，非即食调味面|manual
63|7.00|500|g|干米粉，不是泡发后重量|manual
64|6.00|400|g|原味熟馒头，按净重，非每个固定克重|manual
65|5.67|500|g|鲜山药，带皮购买重，参考区域零售价|wuhan
66|1.72|500|g|普通鲜南瓜，参考区域零售价取整，带皮籽|wuhan
70|2.00|500|g|鲜大白菜，非小白菜，参考上海大白菜行情取整|shanghai
74|2.90|500|g|鲜莴笋，含皮叶购买重，参考区域零售价|wuhan
76|10.00|500|g|鲜秋葵，按购买重|manual
77|3.87|500|g|鲜豆角，按购买重，参考区域零售价取整|wuhan
78|12.00|500|g|鲜去壳豌豆仁，非带荚豌豆|manual
79|8.00|500|g|原味去芯玉米粒，鲜或冷冻，非玉米棒|manual
80|5.91|500|g|鲜莲藕，购买重，参考区域零售价|wuhan
81|24.90|150|g|干黑木耳，参考禾煜黑木耳规格，非泡发木耳|wujiang
82|6.00|500|g|鲜海带或水发海带，非干海带|manual
83|1.61|500|g|鲜豆芽，购买重，参考区域零售价取整|wuhan
84|4.00|500|g|鲜紫甘蓝，购买重|manual
85|10.00|500|g|鲜红黄彩椒，非普通青椒|manual
86|21.80|400|g|冷鲜鸡翅中，带骨，参考大成规格|wujiang
87|20.00|500|g|生鸡小胸/鸡里脊，去骨未调味|manual
90|50.00|500|g|鲜去骨羊肉，非带骨羊排|manual
91|22.00|500|g|生鸭胸肉，带皮去骨未调味，非烟熏鸭胸|manual
92|45.00|500|g|生去骨火鸡胸肉，小包装零售预算，非普通鸡胸肉|manual
94|49.00|500|g|真龙利鱼鱼柳，非低价巴沙鱼冒充|manual
95|28.00|500|g|整条鲜鲳鱼，含头骨购买重|manual
96|25.00|500|g|生鱿鱼，按购买重量，非干鱿鱼|manual
97|18.00|500|g|鲜带壳扇贝，非扇贝肉，重量计价不假定个数|manual
98|8.00|500|g|鲜带壳蛤蜊，非净蛤蜊肉|manual
99|8.00|1000|ml|无糖原味豆浆成品，非干豆粉|manual
100|12.00|500|g|干鹰嘴豆，未煮未泡发|manual
101|8.00|500|g|干黑豆，非熟制罐头|manual
102|8.00|500|g|干红豆|manual
103|7.00|500|g|干绿豆|manual
104|5.00|500|g|干黄豆|manual
105|10.00|500|g|去壳鲜毛豆仁，非带荚毛豆|manual
109|18.00|125|g|鲜蓝莓，按盒装净含量预算，不是整盒当500克|manual
110|30.00|500|g|鲜草莓，非冷冻果酱，季节波动大|manual
111|12.00|500|g|鲜猕猴桃，含皮购买重|manual
115|35.00|500|g|原味杏仁果仁，非带壳果，品种差异大|manual
116|30.00|500|g|原味核桃仁，非带壳核桃|manual
117|40.00|500|g|原味腰果仁，非带壳果|manual
118|12.00|500|g|生芝麻，干品，非芝麻酱|manual
119|18.61|1000|ml|普通菜籽油，区域零售参考，不将升当千克|wuhan
120|28.35|1000|ml|普通花生油，区域零售参考，不将升当千克|wuhan
122|5.00|400|g|食用玉米淀粉，干品|manual
123|35.00|500|g|普通蜂蜜，按净重，非蜂蜜饮料|manual
124|6.00|250|g|鲜香菜，按购买重，非每把固定克重|manual
125|6.00|35|g|纯孜然粉，非复合烧烤撒料|manual
126|6.00|50|g|纯辣椒粉，非复合蘸料|manual
127|3.00|10|g|咖喱粉，参考味好美小袋规格，非咖喱块|wujiang
128|10.00|43|g|日常调味芥末酱，非芥末油或纯山葵|manual
129|3.00|400|g|低钠盐，参考淮牌加碘低钠盐规格|wujiang
130|5.00|50|g|食用泡打粉，非酵母粉|manual
131|10.00|30|g|纯白胡椒粉，非复合椒盐|manual
132|12.00|15|g|干迷迭香碎，非鲜迷迭香|manual
"""


def build():
    seed = {row["ingredient_id"]: row for row in json.loads((ROOT / "ingredients.json").read_text(encoding="utf-8"))}
    previous = json.loads((ROOT / "market_prices_20261029.json").read_text(encoding="utf-8"))
    sources = {
        "wujiang": {"title": "吴江区菜篮子价格公示表", "publisher": "吴江区发改委", "url": "https://www.wujiang.gov.cn/zgwj/jggs/202606/d4ed617811c845fca601c2c83df8b0fb.shtml", "observed_on": "2026-05-07", "published_on": "2026-06-01", "region": "江苏苏州吴江", "channel": "大润发吴江店/盛泽店监测报价", "limitation": "历史报价；本次只用作预算锚点，不是2026年11月门店实价。"},
        "wuhan": {"title": "武汉生活必需品市场监测周报", "publisher": "武汉市商务局", "url": "https://sw.wuhan.gov.cn/zfxxgk/fdzdgknr/sjfb/jgjczb/202610/t20261028_2869257.shtml", "observed_on": "2026-10-19", "published_on": "2026-10-28", "region": "湖北武汉", "channel": "零售监测均价", "limitation": "采用零售栏；跨地区和取整后作为预算参考，不冒充上海门店售价。"},
        "sam-history": {"title": "陪我减重18斤的山姆好物", "publisher": "食亿个为什么 / 百度转载", "url": "https://health.baidu.com/m/detail/ar_10300077706285264650", "observed_on": None, "published_on": "2025-03-04", "region": "原文未注明门店地区", "channel": "山姆历史第三方商品介绍", "limitation": "非官方、非实时，只有历史文章日期；虾仁115元/908g、真鳕鱼129元/1kg用作预算锚点，非当前成交价。"},
        "shanghai": {"title": previous["publisher"], "publisher": previous["publisher"], "url": previous["url"], "observed_on": previous["observed_on"], "region": previous["region"], "channel": previous["channel"], "limitation": "对应原始XLS；用于通用品名的估算时仍标记estimated。"},
        "hema-history": {"title": "胖东来自营酱油断货，记者走访盒马", "publisher": "海报新闻 / 华龙网转载", "url": "https://www.cqnews.net/1/detail/1313769890766196736/web/content_1313769890766196736.html", "observed_on": "2024-12-02", "published_on": "2024-12-04", "region": "山东济南", "channel": "盒马济南印象城店", "limitation": "有机酱油9.9元/480ml为历史价格，仅作渠道交叉参考；其他调料未给净含量，不能用于单价换算。本次未套用其价格。"},
    }
    entries = []
    for old in previous["entries"]:
        reference = {"status": "observed", "observed_on": previous["observed_on"], "region": "上海市", "source_ids": ["shanghai"], "basis": "purchase_weight", "specification": old["specification"], "source_name": old["source_name"], "unit": "斤", "unit_price_cny": old["unit_price"], "mapping_note": old["mapping_note"], "source_url": previous["url"]}
        entries.append({"ingredient_id": old["ingredient_id"], "name": old["name"], "unit": "斤", "unit_price": old["unit_price"], "price_reference": reference})
    for line in ROWS.strip().splitlines():
        raw_id, price, amount, measure, specification, anchor = line.split("|")
        ingredient_id = int(raw_id)
        scale = Decimal(500 if measure == "g" else 1000)
        normalized = str((Decimal(price) * scale / Decimal(amount)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP))
        unit = "斤" if measure == "g" else "升"
        reference = {"status": "estimated", "estimated_on": "2026-11-01", "region": "中国大陆城市家庭日常采购预算", "unit": unit, "unit_price_cny": normalized, "basis": "purchase_weight" if measure == "g" else "purchase_volume", "planning_package": {"price_cny": price, "amount": amount, "measure": measure, "specification": specification}, "source_ids": [] if anchor == "manual" else [anchor], "method": "manual_budget_estimate" if anchor == "manual" else "retail_reference_budget_estimate", "rationale": "按用户授权设置的人工预算工作值；未取得该食材精确匹配的近期零售证据，不代表任何商家现售SKU或成交价。" if anchor == "manual" else "参考所列来源的品种及规格制定预算；历史/跨地区数据或取整不冒充当前门店实价。", "quantity_warning": "参考包装量是计价基准，不推定每个/盒/瓶重量；不推定可食率或g与ml的密度转换。"}
        entries.append({"ingredient_id": ingredient_id, "name": seed[ingredient_id]["name"], "unit": unit, "unit_price": normalized, "price_reference": reference})
    for entry in entries:
        entry["price_reference"]["anchors"] = [sources[key] for key in entry["price_reference"]["source_ids"]]
    assert len(entries) == len({entry["ingredient_id"] for entry in entries}) == len(seed) == 132
    entries.sort(key=lambda entry: entry["ingredient_id"])
    bundle = {"format": "budget-catalog-v2", "estimated_on": "2026-11-01", "review_after": "2026-11-28", "disclaimer": "33项原始监测参考+99项经用户授权的预算估算；并非132项实时超市价。所有金额CNY，固体元/斤(500g)、液体元/升(1000ml)。", "sources": sources, "entries": entries}
    (ROOT / "budget_prices_20261101.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
