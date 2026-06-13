"""
EuroGoal Predictor — Formation Matchup Matrix
===============================================
Static tactical advantage scores based on well-known football formation relationships.

Positive score = advantage for the HOME team's formation.
Negative score = advantage for the AWAY team's formation.

Scale: -1.0 (strong disadvantage) to +1.0 (strong advantage), 0.0 = neutral.
"""

from __future__ import annotations

COMMON_FORMATIONS = ["4-3-3", "4-4-2", "4-2-3-1", "3-5-2", "3-4-3", "5-3-2"]

# Matrix[home_formation][away_formation] = advantage score for home team
# Symmetric: M[A][B] = -M[B][A]
FORMATION_MATRIX: dict[str, dict[str, float]] = {
    "4-3-3": {
        "4-3-3":   0.0,
        "4-4-2":   0.3,
        "4-2-3-1": 0.0,
        "3-5-2":  -0.3,
        "3-4-3":   0.1,
        "5-3-2":  -0.2,
    },
    "4-4-2": {
        "4-3-3":  -0.3,
        "4-4-2":   0.0,
        "4-2-3-1": -0.2,
        "3-5-2":   0.1,
        "3-4-3":  -0.1,
        "5-3-2":   0.2,
    },
    "4-2-3-1": {
        "4-3-3":   0.0,
        "4-4-2":   0.2,
        "4-2-3-1": 0.0,
        "3-5-2":  -0.1,
        "3-4-3":   0.0,
        "5-3-2":  -0.1,
    },
    "3-5-2": {
        "4-3-3":   0.3,
        "4-4-2":  -0.1,
        "4-2-3-1": 0.1,
        "3-5-2":   0.0,
        "3-4-3":   0.2,
        "5-3-2":   0.0,
    },
    "3-4-3": {
        "4-3-3":  -0.1,
        "4-4-2":   0.1,
        "4-2-3-1": 0.0,
        "3-5-2":  -0.2,
        "3-4-3":   0.0,
        "5-3-2":  -0.1,
    },
    "5-3-2": {
        "4-3-3":   0.2,
        "4-4-2":  -0.2,
        "4-2-3-1": 0.1,
        "3-5-2":   0.0,
        "3-4-3":   0.1,
        "5-3-2":   0.0,
    },
}

# Descriptions for each matchup relationship
_MATCHUP_DESCRIPTIONS: dict[tuple[str, str], dict] = {
    ("4-3-3", "4-4-2"): {
        "description": "4-3-3 的中场三人组对 4-4-2 的双中场形成人数优势，控球和传球线路更占优。",
        "key_factors": ["中场人数优势", "边路进攻空间", "高位逼抢优势"],
    },
    ("4-3-3", "3-5-2"): {
        "description": "3-5-2 的翼卫可以利用 4-3-3 边锋身后的空间，中场人数占优。",
        "key_factors": ["翼卫空间利用", "中场人数劣势", "边路防守压力"],
    },
    ("4-3-3", "5-3-2"): {
        "description": "5-3-2 的五后卫体系能有效吸收 4-3-3 的边路进攻，防守端人数占优。",
        "key_factors": ["防守人数优势", "边路封堵", "反击空间有限"],
    },
    ("4-4-2", "4-2-3-1"): {
        "description": "4-2-3-1 的前腰位置可以在 4-4-2 两线之间找到空间，创造机会。",
        "key_factors": ["前腰自由空间", "中场组织优势", "双后腰保护"],
    },
    ("4-4-2", "3-5-2"): {
        "description": "4-4-2 的边前卫可以压制 3-5-2 的翼卫，但中路人数略处下风。",
        "key_factors": ["边路对抗", "中路人数平衡", "翼卫攻防转换"],
    },
    ("4-4-2", "5-3-2"): {
        "description": "4-4-2 的宽度可以拉开 5-3-2 的防线，边路传中是主要进攻手段。",
        "key_factors": ["宽度优势", "传中机会", "中路密集防守"],
    },
    ("4-2-3-1", "3-5-2"): {
        "description": "3-5-2 的中场人数优势对 4-2-3-1 的双后腰形成压力，但前腰可以利用三后卫之间的缝隙。",
        "key_factors": ["中场争夺", "后卫间缝隙", "攻守平衡"],
    },
    ("4-2-3-1", "5-3-2"): {
        "description": "5-3-2 的防守密度让 4-2-3-1 难以在中路创造机会，但边路空间可以利用。",
        "key_factors": ["中路防守密集", "边路空间", "破密防能力"],
    },
    ("3-5-2", "3-4-3"): {
        "description": "3-5-2 的中场五人对 3-4-3 形成人数优势，翼卫的攻防覆盖更全面。",
        "key_factors": ["中场人数优势", "翼卫覆盖", "前锋对抗"],
    },
    ("3-4-3", "5-3-2"): {
        "description": "3-4-3 的三前锋对 5-3-2 的五后卫，进攻端人数劣势但宽度拉开了防线。",
        "key_factors": ["前锋 vs 后卫人数", "宽度拉扯", "反击效率"],
    },
}


def get_formation_advantage(home_formation: str, away_formation: str) -> float:
    """Return the tactical advantage score for the home team.

    Returns 0.0 if either formation is unknown or not in the matrix.
    """
    home = home_formation.strip()
    away = away_formation.strip()
    if home in FORMATION_MATRIX and away in FORMATION_MATRIX[home]:
        return FORMATION_MATRIX[home][away]
    return 0.0


def get_matchup_analysis(home_formation: str, away_formation: str) -> dict:
    """Return a rich analysis dict with advantage, description, and key factors."""
    score = get_formation_advantage(home_formation, away_formation)

    if score > 0.05:
        label = "主队阵型优势"
    elif score < -0.05:
        label = "客队阵型优势"
    else:
        label = "阵型均衡"

    # Look up description (try both orderings)
    key = (home_formation.strip(), away_formation.strip())
    alt_key = (away_formation.strip(), home_formation.strip())
    info = _MATCHUP_DESCRIPTIONS.get(key) or _MATCHUP_DESCRIPTIONS.get(alt_key)

    description = ""
    key_factors: list[str] = []
    if info:
        description = info["description"]
        key_factors = info["key_factors"]
    elif score == 0.0 and home_formation.strip() == away_formation.strip():
        description = "双方使用相同阵型，比赛结果更多取决于球员个人能力和临场发挥。"
        key_factors = ["阵型相同", "球员能力", "临场发挥"]
    else:
        description = f"{home_formation} 对阵 {away_formation}，阵型之间无明显的战术克制关系。"
        key_factors = ["阵型中性"]

    return {
        "home_formation": home_formation.strip(),
        "away_formation": away_formation.strip(),
        "advantage_score": round(score, 2),
        "advantage_label": label,
        "description": description,
        "key_factors": key_factors,
    }
