#!/usr/bin/env python3
"""双轴矩阵散点图：横轴=补偿目标 × 纵轴=健全性代价

用法:
    python3 scripts/plot_matrix.py [--output matrix.png]
"""

import argparse
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import numpy as np

# 配置 CJK 字体(跨平台:Windows / macOS / Linux 按优先级 fallback)
plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",      # Windows 默认中文(微软雅黑)
    "SimHei",               # Windows fallback(黑体)
    "SimSun",               # Windows fallback(宋体)
    "PingFang SC",          # macOS 默认中文
    "Hiragino Sans GB",     # macOS fallback
    "Noto Sans CJK SC",     # Linux Noto
    "WenQuanYi Zen Hei",    # Linux fallback
    "DejaVu Sans",          # 兜底
]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False  # 防止负号显示为方块

# ── 轴定义 ──────────────────────────────────────────
X_CATEGORIES = [
    "调用图不完整(可达性)",
    "模式不精确(误报)",
    "污点规范缺失(source-sink)",
    "版本与可达性的鸿沟",
    "数据与标注质量",
]

Y_CATEGORIES = [
    "只剪误报(可能引入漏报)",
    "只补漏报",
    "两者兼顾",
    "零漏报保证",
]

# 子方向颜色
DIRECTION_COLORS = {
    "①": "#e41a1c",
    "②": "#377eb8",
    "③": "#4daf4a",
    "④": "#984ea3",
    "⑤": "#ff7f00",
    "⑥": "#a65628",
    "早期": "#999999",
}


def parse_direction(label: str) -> str:
    """从子方向字段提取方向编号."""
    for d in ["①", "②", "③", "④", "⑤", "⑥"]:
        if d in label:
            return d
    return "早期"


def map_x(value: str) -> int | None:
    """将横轴文本映射到索引."""
    value = value.strip()
    for i, cat in enumerate(X_CATEGORIES):
        if cat in value:
            return i
    # 尝试模糊匹配
    mapping = {
        "可达": 0,
        "调用图": 0,
        "误报": 1,
        "模式": 1,
        "污点": 2,
        "source": 2,
        "版本": 3,
        "数据": 4,
        "标注": 4,
    }
    for key, idx in mapping.items():
        if key in value:
            return idx
    return None


def map_y(value: str) -> int | None:
    """将纵轴文本映射到索引."""
    value = value.strip()
    for i, cat in enumerate(Y_CATEGORIES):
        if value and value[:4] == cat[:4]:
            return i
    # 模糊匹配
    mapping = {
        "只剪误报": 0,
        "可能引入漏报": 0,
        "只补漏报": 1,
        "两者兼顾": 2,
        "零漏报": 3,
        "零漏报保证": 3,
    }
    for key, idx in mapping.items():
        if key in value:
            return idx
    return None


def plot_matrix(csv_path: str, output_path: str):
    """绘制双轴矩阵散点图."""
    # 读取数据
    papers = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            x = map_x(row.get("横轴-补偿目标", ""))
            y = map_y(row.get("纵轴-健全性代价", ""))
            direction = parse_direction(row.get("子方向", ""))
            name = row.get("简称", "?")
            is_key_val = row.get("必引") or ""
            is_key = is_key_val.strip().lower() in ("是", "true", "yes", "1")
            papers.append({
                "name": name,
                "x": x,
                "y": y,
                "direction": direction,
                "key": is_key,
            })

    # 过滤有效数据
    valid = [p for p in papers if p["x"] is not None and p["y"] is not None]
    unknown = [p for p in papers if p["x"] is None or p["y"] is None]
    print(f"有效数据点: {len(valid)}/{len(papers)}")
    if unknown:
        print(f"  缺少坐标: {', '.join(p['name'] for p in unknown)}")

    if not valid:
        print("无有效数据点,无法绘图")
        return

    # ── 绘图 ──────────────────────────────────────
    fig, ax = plt.subplots(figsize=(14, 9))

    # 绘制网格背景
    for xi in range(len(X_CATEGORIES)):
        for yi in range(len(Y_CATEGORIES)):
            color = "#f0f0f0" if (xi + yi) % 2 == 0 else "#ffffff"
            ax.add_patch(plt.Rectangle(
                (xi - 0.5, yi - 0.5), 1, 1,
                facecolor=color, edgecolor="#dddddd", linewidth=0.5, zorder=0
            ))

    # 标记空白区域（无论文覆盖的格子）
    covered = set()
    for p in valid:
        covered.add((p["x"], p["y"]))

    for xi in range(len(X_CATEGORIES)):
        for yi in range(len(Y_CATEGORIES)):
            if (xi, yi) not in covered:
                ax.text(xi, yi, "?", ha="center", va="center",
                        fontsize=28, color="#cccccc", fontweight="bold", zorder=1)

    # 绘制散点（加少量 jitter 避免完全重叠）
    rng = np.random.RandomState(42)
    for direction in sorted(set(p["direction"] for p in valid)):
        pts = [p for p in valid if p["direction"] == direction]
        xs = [p["x"] + rng.uniform(-0.18, 0.18) for p in pts]
        ys = [p["y"] + rng.uniform(-0.15, 0.15) for p in pts]
        sizes = [180 if p["key"] else 100 for p in pts]
        edge_colors = ["#333333" if p["key"] else "none" for p in pts]
        line_widths = [2.0 if p["key"] else 0.5 for p in pts]
        colors = [DIRECTION_COLORS.get(direction, "#333333") for _ in pts]

        ax.scatter(xs, ys, s=sizes, c=colors, edgecolors=edge_colors,
                   linewidths=line_widths, alpha=0.85, zorder=3, label=direction)

        # 标注必引论文
        for p in pts:
            if p["key"]:
                ax.annotate(p["name"], (p["x"] + rng.uniform(-0.18, 0.18),
                           p["y"] + rng.uniform(-0.15, 0.15) + 0.08),
                           fontsize=7, ha="center", alpha=0.9,
                           bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                                    edgecolor="none", alpha=0.7))

    # 轴设置
    ax.set_xlim(-0.7, len(X_CATEGORIES) - 0.3)
    ax.set_ylim(-0.7, len(Y_CATEGORIES) - 0.3)
    ax.set_xticks(range(len(X_CATEGORIES)))
    ax.set_xticklabels(X_CATEGORIES, fontsize=10, rotation=20, ha="right")
    ax.set_yticks(range(len(Y_CATEGORIES)))
    ax.set_yticklabels(Y_CATEGORIES, fontsize=10)
    ax.set_xlabel("横轴：LLM 补偿静态分析的哪个短板 →", fontsize=12, fontweight="bold")
    ax.set_ylabel("纵轴：对健全性(Soundness)的代价 →", fontsize=12, fontweight="bold")
    n_total = len(papers)
    ax.set_title("双轴矩阵：LLM + 代码安全论文定位\n"
                 f"({len(valid)}/{n_total} 技术论文有健全性维度;综述/评测/早期 {n_total - len(valid)} 篇不适用)\n"
                 "★ = 必引锚点, ? = 空白区域",
                 fontsize=13, fontweight="bold")

    # 图例
    legend_patches = [mpatches.Patch(color=c, label=d)
                      for d, c in sorted(DIRECTION_COLORS.items())]
    legend_patches.append(mpatches.Patch(facecolor="white", edgecolor="#333333",
                                          linewidth=2, label="★ 必引锚点"))
    legend_patches.append(mpatches.Patch(facecolor="#dddddd", edgecolor="none",
                                          label="空白区域"))
    ax.legend(handles=legend_patches, fontsize=9, loc="upper left",
              bbox_to_anchor=(1.01, 1.0), framealpha=0.9)

    # 网格
    ax.grid(False)
    ax.tick_params(axis="both", which="both", length=0)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    print(f"矩阵图已保存: {output_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="绘制双轴矩阵散点图")
    parser.add_argument("--csv", default="papers.csv", help="papers.csv 路径")
    parser.add_argument("--output", "-o", default="documents/双轴矩阵图.png",
                        help="输出图片路径")
    args = parser.parse_args()

    plot_matrix(args.csv, args.output)


if __name__ == "__main__":
    main()
