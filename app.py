# -*- coding: utf-8 -*-
"""
温柔治愈风自助塔罗休闲小游戏 - 后端服务
技术栈：Python Flask
定位：纯娱乐小游戏，严禁算命、运势预测、吉凶判断
"""

import os
import random
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import requests

# 加载环境变量
load_dotenv()

app = Flask(__name__)
# 允许跨域，方便本地调试
CORS(app)

# 从环境变量读取大模型配置
API_KEY = os.getenv("LLM_API_KEY", "")
# 智谱 GLM OpenAI 兼容接口
API_BASE_URL = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
# 固定使用用户指定的 glm-4.7-flash 模型
MODEL_NAME = "glm-4.7-flash"

# 是否启用本地兜底文案（默认开启，保证无 API Key 时也能跑通交互）
LOCAL_FALLBACK_ENABLED = os.getenv("LOCAL_FALLBACK_ENABLED", "true").lower() in ("true", "1", "yes")


# 韦特塔罗 78 张卡牌名称，数字 1~78 一一映射
TAROT_CARDS = [
    "愚人", "魔术师", "女祭司", "皇后", "皇帝", "教皇", "恋人", "战车", "力量", "隐者",
    "命运之轮", "正义", "倒吊人", "死神", "节制", "恶魔", "塔", "星星", "月亮", "太阳",
    "审判", "世界",
    # 权杖 suit
    "权杖首牌", "权杖二", "权杖三", "权杖四", "权杖五", "权杖六", "权杖七", "权杖八",
    "权杖九", "权杖十", "权杖侍从", "权杖骑士", "权杖王后", "权杖国王",
    # 圣杯 suit
    "圣杯首牌", "圣杯二", "圣杯三", "圣杯四", "圣杯五", "圣杯六", "圣杯七", "圣杯八",
    "圣杯九", "圣杯十", "圣杯侍从", "圣杯骑士", "圣杯王后", "圣杯国王",
    # 宝剑 suit
    "宝剑首牌", "宝剑二", "宝剑三", "宝剑四", "宝剑五", "宝剑六", "宝剑七", "宝剑八",
    "宝剑九", "宝剑十", "宝剑侍从", "宝剑骑士", "宝剑王后", "宝剑国王",
    # 星币 suit
    "星币首牌", "星币二", "星币三", "星币四", "星币五", "星币六", "星币七", "星币八",
    "星币九", "星币十", "星币侍从", "星币骑士", "星币王后", "星币国王",
]

# 正逆位中文映射
DIRECTION_LABELS = {
    "upright": "正位",
    "reversed": "逆位",
}

# 大阿卡纳治愈向牌意：侧重内心视角，不做吉凶判断
MAJOR_ARCANA_MEANINGS = {
    "愚人": "带着好奇与信任踏上新旅程，允许自己轻松尝试。",
    "魔术师": "你手中已经拥有需要的资源，现在是发挥创造力的时候。",
    "女祭司": "静下心来，倾听内在智慧与直觉的轻声低语。",
    "皇后": "用温柔与滋养对待自己，你值得被好好照顾。",
    "皇帝": "建立稳定的结构，温柔而坚定地掌控自己的生活节奏。",
    "教皇": "向传统与学习寻求启发，找到让自己安心的指引。",
    "恋人": "看见内心的价值选择，在关系与自我之间寻找和谐。",
    "战车": "运用意志力朝着目标前进，你有力量穿越眼前的挑战。",
    "力量": "以温柔而坚定的方式面对自己，真正的勇气来自内心。",
    "隐者": "给自己一段独处的时光，在安静中你会找到答案。",
    "命运之轮": "变化是生命自然的节奏，顺势而为也是一种智慧。",
    "正义": "诚实面对自己，在平衡中承担属于自己的责任。",
    "倒吊人": "偶尔的暂停不是停滞，而是换一个角度看世界。",
    "死神": "放下旧有的篇章，转化才会带来新的空间。",
    "节制": "在看似对立的事物间找到平衡，耐心会带来调和。",
    "恶魔": "看见那些束缚你的模式，觉察本身就是自由的开始。",
    "塔": "突变带来释放，旧的结构瓦解后才有重建的可能。",
    "星星": "怀抱希望与宁静的信心，疗愈正在悄然发生。",
    "月亮": "在不确定中信任直觉，潜意识正悄悄为你点亮路标。",
    "太阳": "带着喜悦与活力活在当下，明朗的能量正围绕着你。",
    "审判": "从过去的经验中觉醒，给自己一个重新出发的机会。",
    "世界": "一个阶段趋于完整，整合后的你正站在新的起点。",
}


def get_card_meaning(name: str) -> str:
    """
    获取单张牌的治愈向内心含义
    大阿卡纳使用精确映射，小阿卡纳根据花色与数字/宫廷规则生成
    """
    if name in MAJOR_ARCANA_MEANINGS:
        return MAJOR_ARCANA_MEANINGS[name]

    # 小阿卡纳规则生成
    if name.startswith("权杖"):
        suit_theme = "行动与热情"
    elif name.startswith("圣杯"):
        suit_theme = "情感与关系"
    elif name.startswith("宝剑"):
        suit_theme = "思考与沟通"
    elif name.startswith("星币"):
        suit_theme = "物质与实际"
    else:
        suit_theme = "生活"

    if "侍从" in name:
        return f"带着新鲜感去学习和体验{suit_theme}相关的课题。"
    if "骑士" in name:
        return f"以积极的行动力去追求{suit_theme}方面的目标。"
    if "王后" in name:
        return f"用滋养与包容的态度对待{suit_theme}相关的人事物。"
    if "国王" in name:
        return f"在{suit_theme}方面展现成熟的掌控与稳定。"
    if "首牌" in name:
        return f"{suit_theme}的新契机正在出现，值得用心感受。"

    # 数字牌（中文数字转阿拉伯数字）
    cn_numbers = {
        "首牌": 1, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    }
    num = 0
    for cn, arabic in cn_numbers.items():
        if cn in name:
            num = arabic
            break
    return f"在{suit_theme}的旅程中处于第{num}个阶段，提醒你看见当下的节奏。"


def build_prompt(question: str, cards: list) -> str:
    """
    构建发给大模型的固定提示词
    严禁吉凶预判、命运预测、给决策建议
    要求输出 JSON，方便前端按牌拆分展示
    """
    card_infos = []
    positions = ["过去", "现在", "未来"]
    for i, card in enumerate(cards):
        direction = DIRECTION_LABELS.get(card.get("direction", "upright"), "正位")
        card_infos.append(f"{positions[i]}：{card['name']}（{direction}）")

    cards_text = "，".join(card_infos)

    prompt = f"""你是休闲塔罗小游戏文案助手，只写治愈向娱乐文字，禁止吉凶预判、命运预测、给决策建议、禁止投资建议、禁止学业/感情/生活决策建议。

用户问题：{question}
牌阵：过去、现在、未来
卡牌信息：{cards_text}

【要求】
1. 解读时必须结合每张牌的具体牌面含义（如权杖国王代表成熟掌控与行动力，魔术师代表创造力与资源整合，星币四代表稳定与安全感等），但只做治愈向娱乐化表达，不做吉凶判断。
2. past / present / future 三段分别对应过去、现在、未来，侧重内心视角，语言温柔，不做结果断言。
3. summary 必须结合用户的问题和三张牌的具体含义，写一段积极向上的总结，只鼓励自我觉察，不给具体决策建议。

【极其重要】你必须只输出一个合法的 JSON 对象，不要输出 markdown 代码块、不要输出解释说明、不要输出任何 JSON 以外的文字。JSON 必须可以直接被 Python json.loads 解析。

JSON 格式如下：
{{
  "past": "对应过去的治愈向娱乐文字。",
  "present": "对应现在的治愈向娱乐文字。",
  "future": "对应未来的治愈向娱乐文字。",
  "summary": "结合用户问题与三张牌具体含义的积极向上总结。"
}}

注意：
- 每个字段都是一段完整的温柔文字。
- 不要在 JSON 里包含【温馨提醒】，前端会自行追加固定提醒。
"""
    return prompt


def generate_fallback_segments(question: str, cards: list) -> dict:
    """
    本地兜底文案生成器
    当大模型不可用时，根据卡牌的具体牌意生成治愈向娱乐文字
    返回结构化字段：past, present, future, summary
    """
    positions = ["过去", "现在", "未来"]
    keys = ["past", "present", "future"]
    segments = {}
    card_meanings = []

    for i, card in enumerate(cards):
        direction = DIRECTION_LABELS.get(card.get("direction", "upright"), "正位")
        meaning = get_card_meaning(card["name"])
        card_meanings.append(meaning)

        # 根据位置把牌意包装成内心视角的解读
        if positions[i] == "过去":
            text = f"过去的牌面带来了{card['name']}（{direction}）的能量，它提醒你：{meaning} 这份经历悄悄塑造了你今天的模样。"
        elif positions[i] == "现在":
            text = f"现在的牌面是{card['name']}（{direction}），它映照出你此刻的状态：{meaning} 允许自己被看见，就是一种温柔。"
        else:
            text = f"未来的牌面出现{card['name']}（{direction}），它带来一份柔软的邀请：{meaning} 未来的画布，正等你轻轻落笔。"
        segments[keys[i]] = text

    # 总结：结合用户问题 + 三张牌的具体含义
    summary = (
        f"关于「{question}」，这三张牌共同讲述了一个温柔的故事："
        f"过去{card_meanings[0]}；"
        f"现在{card_meanings[1]}；"
        f"未来{card_meanings[2]}"
        f"无论牌面怎样，你都在慢慢靠近更真实的自己。愿这份觉察成为你的一点点力量，继续向前走。"
    )
    segments["summary"] = summary
    return segments


def parse_llm_json(content: str) -> dict:
    """
    尝试解析模型返回的 JSON
    若解析失败，返回 None 让上层走兜底
    """
    import json
    try:
        # 先尝试直接解析
        data = json.loads(content)
    except json.JSONDecodeError:
        # 如果模型包了 markdown 代码块，尝试提取
        stripped = content.strip()
        if stripped.startswith("```"):
            # 去掉 ```json 或 ``` 开头和 ``` 结尾
            lines = stripped.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            stripped = "\n".join(lines).strip()
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return None

    required = {"past", "present", "future", "summary"}
    if not required.issubset(data.keys()):
        return None
    return {k: str(data.get(k, "")).strip() for k in required}


def build_full_text(segments: dict) -> str:
    """把结构化字段拼接成完整文本，方便前端兼容展示"""
    return (
        f"过去：{segments['past']}\n\n"
        f"现在：{segments['present']}\n\n"
        f"未来：{segments['future']}\n\n"
        f"总结：{segments['summary']}\n\n"
        "【温馨提醒：这只是一场轻松的小游戏，仅供自我觉察和娱乐，"
        "不必作为现实选择的依据，你的人生始终由自己掌控。】"
    )


def call_llm(prompt: str) -> dict:
    """
    调用智谱 GLM 大模型 API（OpenAI 兼容接口）
    固定使用 glm-4.7-flash 模型，返回解析后的结构化 segments
    """
    if not API_KEY:
        raise ValueError("未配置 LLM_API_KEY，请检查 .env 文件")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "你是温柔治愈风的休闲小游戏文案助手，只写娱乐向内心视角文字，禁止吉凶预判和决策建议。你必须只输出合法 JSON，不要 markdown 代码块或任何解释。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 400,
    }

    try:
        response = requests.post(API_BASE_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        segments = parse_llm_json(content)
        if not segments:
            raise RuntimeError(f"模型返回格式不符合预期，无法解析 JSON。原始返回：{content[:300]}")
        return segments
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"调用大模型接口失败：{str(e)}")
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"解析大模型返回失败：{str(e)}")


@app.route("/")
def index():
    """首页重定向到 static/index.html"""
    return send_from_directory("static", "index.html")


@app.route("/api/get_tarot_read", methods=["POST"])
def get_tarot_read():
    """
    获取塔罗解读接口
    入参 JSON：{ "question": "...", "cards": [ {name, position, direction}, ... ] }
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    cards = data.get("cards", [])

    # 基础校验
    if not question:
        return jsonify({"error": "问题不能为空哦"}), 400
    if len(question) > 80:
        return jsonify({"error": "问题长度超过80字啦"}), 400
    if len(cards) != 3:
        return jsonify({"error": "请抽取三张牌"}), 400

    # 校验卡牌数据合法性
    for card in cards:
        name = card.get("name", "")
        if name not in TAROT_CARDS:
            return jsonify({"error": f"不认识的卡牌：{name}"}), 400
        direction = card.get("direction", "")
        if direction not in ("upright", "reversed"):
            return jsonify({"error": "卡牌方向必须是 upright 或 reversed"}), 400

    try:
        prompt = build_prompt(question, cards)
        segments = call_llm(prompt)
        return jsonify({
            "success": True,
            "interpretation": build_full_text(segments),
            "segments": segments,
            "cards": cards,
        })
    except Exception as e:
        # 若启用本地兜底，则返回本地生成的治愈文案，保证交互不中断
        if LOCAL_FALLBACK_ENABLED:
            segments = generate_fallback_segments(question, cards)
            return jsonify({
                "success": True,
                "interpretation": build_full_text(segments),
                "segments": segments,
                "cards": cards,
                "fallback": True,
                "fallback_reason": str(e),
            })
        # 未启用兜底时，返回友好错误
        return jsonify({"error": str(e)}), 500


@app.route("/api/cards", methods=["GET"])
def list_cards():
    """
    返回全部78张卡牌名称列表，供前端校验和展示
    """
    return jsonify({
        "success": True,
        "cards": [{"id": i + 1, "name": name} for i, name in enumerate(TAROT_CARDS)]
    })


if __name__ == "__main__":
    # 本地开发默认运行在 5000 端口，开启调试模式
    app.run(host="0.0.0.0", port=5000, debug=True)
