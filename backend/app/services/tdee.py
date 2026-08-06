"""TDEE / BMR 计算服务

使用 Mifflin-St Jeor 公式（1990 年修订版）
"""

from typing import Literal


def calculate_bmr(
    gender: Literal["male", "female"],
    weight_kg: float,
    height_cm: float,
    age: int,
) -> float:
    """计算基础代谢率 (BMR)

    Mifflin-St Jeor:
        男性: BMR = 10 × 体重(kg) + 6.25 × 身高(cm) - 5 × 年龄 + 5
        女性: BMR = 10 × 体重(kg) + 6.25 × 身高(cm) - 5 × 年龄 - 161
    """
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if gender == "male":
        bmr += 5
    else:
        bmr -= 161
    return round(bmr, 1)


def calculate_tdee(
    gender: Literal["male", "female"],
    weight_kg: float,
    height_cm: float,
    age: int,
    activity_factor: float = 1.55,
) -> float:
    """计算每日总能量消耗 (TDEE)

    TDEE = BMR × 活动系数
    默认活动系数 1.55 对应"中度活动"（每周运动 3-5 天）

    活动系数参考:
        sedentary    1.2   (久坐)
        light        1.375 (轻度活动 1-2 天/周)
        moderate     1.55  (中度活动 3-5 天/周)
        active       1.725 (活跃活动 6-7 天/周)
        extra        1.9   (高强度活动/体力劳动)
    """
    bmr = calculate_bmr(gender, weight_kg, height_cm, age)
    return round(bmr * activity_factor, 1)


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """计算身体质量指数 (BMI)"""
    height_m = height_cm / 100
    return round(weight_kg / (height_m * height_m), 1)


def get_bmi_category(bmi: float) -> str:
    """获取 BMI 分类"""
    if bmi < 18.5:
        return "偏瘦"
    elif bmi < 24.0:
        return "正常"
    elif bmi < 28.0:
        return "偏胖"
    else:
        return "肥胖"
