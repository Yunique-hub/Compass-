"""Academic taxonomy labels kept separate from exact major and runtime family."""
from __future__ import annotations


ACADEMIC_TAXONOMY = (
    "computer_information", "electronic_electrical_engineering", "mechanical_industrial_engineering",
    "civil_built_environment", "chemical_materials_engineering", "mathematics_statistics", "physics",
    "chemistry", "earth_geography", "life_sciences", "agriculture_environment", "veterinary_animal_science",
    "medicine", "nursing", "pharmacy", "public_health", "psychology", "economics", "finance", "accounting",
    "business_management", "public_administration", "law", "international_relations", "education",
    "languages_linguistics", "literature", "history_philosophy", "journalism_communication", "visual_design",
    "performing_arts", "architecture", "sports_physical_education", "hospitality_tourism", "interdisciplinary",
    "undecided", "other_emerging",
)


def classify_taxonomy_domain(major: str, discipline_family: str) -> str:
    text = major.casefold()
    rules = (
        ("nursing", ("护理",)), ("pharmacy", ("药学", "制药")), ("public_health", ("公共卫生", "预防医学")),
        ("veterinary_animal_science", ("兽医", "动物医学", "动物科学")), ("medicine", ("临床医学", "口腔医学", "医学")),
        ("electronic_electrical_engineering", ("电子", "电气", "通信")),
        ("mechanical_industrial_engineering", ("机械", "自动化", "机器人工程", "工业工程")),
        ("civil_built_environment", ("土木", "工程管理")), ("chemical_materials_engineering", ("化工", "材料")),
        ("physics", ("物理",)), ("chemistry", ("化学",)), ("earth_geography", ("地理", "地质", "海洋")),
        ("agriculture_environment", ("农学", "农业", "环境", "生态", "葡萄")),
        ("accounting", ("会计", "审计", "财务管理")), ("finance", ("金融", "投资")),
        ("business_management", ("工商管理", "市场营销", "人力资源")),
        ("public_administration", ("公共管理", "行政管理")), ("international_relations", ("国际关系", "外交")),
        ("languages_linguistics", ("英语", "外语", "翻译", "语言学")),
        ("literature", ("文学", "汉语言")), ("history_philosophy", ("历史", "哲学", "文物")),
        ("visual_design", ("设计", "美术", "视觉传达")), ("performing_arts", ("音乐", "舞蹈", "表演")),
        ("sports_physical_education", ("体育", "运动训练")), ("hospitality_tourism", ("旅游", "酒店")),
        ("architecture", ("建筑", "城乡规划")),
    )
    for domain, signals in rules:
        if any(signal in text for signal in signals):
            return domain
    family_defaults = {
        "computer_information": "computer_information", "engineering": "mechanical_industrial_engineering",
        "mathematics_statistics": "mathematics_statistics", "life_sciences": "life_sciences",
        "medicine_health": "medicine", "economics": "economics", "finance_accounting": "finance",
        "business_management": "business_management", "law": "law", "psychology": "psychology",
        "education": "education", "languages_linguistics": "languages_linguistics",
        "journalism_communication": "journalism_communication", "art_design": "visual_design",
        "architecture_built_environment": "architecture", "social_humanities": "history_philosophy",
        "agriculture_environment": "agriculture_environment", "undecided": "undecided",
    }
    return family_defaults.get(discipline_family, "other_emerging")
