# action_overlay.py
"""
浏览器操作增强显示：在截图上叠加「AI 操作指示图标」

用途
----
AI 每操作一次浏览器（点击 / 长按 / 输入 / 拖动 / 滚动 / 悬停等），
把对应图标画到操作发生的位置，让用户一眼看出「AI 点的是哪里」。

实现要点
--------
- 图标为包内只读资源（resource/action_icons/*.png），带透明通道，直接 alpha 合成；
- 纯代码实现，不依赖提示词；坐标与视口截图像素一一对应；
- 输出写入 data_dir/overlay_cache（运行时产物），不污染插件包体；
- 全部异常内部消化，失败时返回原图路径，绝不影响主流程。
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from astrbot.api import logger

# 图标文件名（与 resource/action_icons 下保持一致）
ICON_CLICK = "01-点击-click.png"
ICON_LONG_PRESS = "02-长按-long-press.png"
ICON_INPUT = "03-输入-input.png"
ICON_DRAG = "04-拖动-drag.png"

# 动作名 → 图标文件
ACTION_ICONS = {
    "click": ICON_CLICK,
    "double_click": ICON_CLICK,
    "right_click": ICON_CLICK,
    "hover": ICON_CLICK,
    "long_press": ICON_LONG_PRESS,
    "input": ICON_INPUT,
    "input_at": ICON_INPUT,
    "drag": ICON_DRAG,
    "scroll": ICON_DRAG,
}

# 动作名 → 中文标签（画在图标下方的小字）
ACTION_LABELS = {
    "click": "点击",
    "double_click": "双击",
    "right_click": "右键",
    "hover": "悬停",
    "long_press": "长按",
    "input": "输入",
    "input_at": "输入",
    "drag": "拖动",
    "scroll": "滚动",
}

# 图标显示尺寸（像素，正方形）
ICON_SIZE = 88
# 标签字号
LABEL_FONT_SIZE = 22

# 每个图标在自身画布中的「锚点」——即图上代表"操作发生位置"的那个像素。
# 贴图时把锚点对准操作坐标，而不是简单地把图片左上角放过去。
# 坐标为归一化比例（0~1），来源于图标 SVG 的 viewBox 分析：
#   四个图标统一为「鼠标指针 + 动作徽章」设计，指针路径完全一致，
#   因此锚点统一取**指针箭头尖端** (52, 30)（「指针指到的位置」才是操作点），
#   动作徽章（靶心 / 长按 / 输入 / 拖动）画在指针右下方作为动作标识。
ICON_ANCHORS = {
    ICON_CLICK: (52 / 128, 30 / 128),
    ICON_LONG_PRESS: (52 / 128, 30 / 128),
    ICON_INPUT: (52 / 128, 30 / 128),
    ICON_DRAG: (52 / 128, 30 / 128),
}
# 未知图标时的默认锚点（画布中心）
DEFAULT_ANCHOR = (0.5, 0.5)


class ActionOverlay:
    """把操作图标叠加到截图上。"""

    def __init__(self, data_dir: str | Path, resource_dir: str | Path, config: dict | None = None):
        self.data_dir = Path(data_dir)
        self.resource_dir = Path(resource_dir)
        self.config = config or {}
        self.icon_dir = self.resource_dir / "action_icons"
        self.cache_dir = self.data_dir / "overlay_cache"
        self._icon_cache: dict[str, Any] = {}
        self._font_cache: dict[int, Any] = {}
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"[ActionOverlay] 缓存目录创建失败: {e}")

    # ==================== 资源加载 ====================

    def _load_icon(self, action: str) -> Any:
        """加载图标（带缓存）。找不到图标返回 None。"""
        filename = ACTION_ICONS.get(action, ICON_CLICK)
        if filename in self._icon_cache:
            return self._icon_cache[filename]

        path = self.icon_dir / filename
        if not path.exists():
            logger.warning(f"[ActionOverlay] 图标不存在: {path}")
            self._icon_cache[filename] = None
            return None

        try:
            icon = Image.open(path).convert("RGBA")
            self._icon_cache[filename] = icon
            return icon
        except Exception as e:
            logger.warning(f"[ActionOverlay] 图标加载失败 {path}: {e}")
            self._icon_cache[filename] = None
            return None

    def _load_font(self, size: int) -> Any:
        """加载字体（带缓存）。找不到字体返回 None（退化为不画文字）。"""
        if size in self._font_cache:
            return self._font_cache[size]

        candidates = [
            self.data_dir / "fonts" / "NotoSansCJK-Regular.ttc",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ]
        for cand in candidates:
            try:
                if cand.exists():
                    font = ImageFont.truetype(str(cand), size)
                    self._font_cache[size] = font
                    return font
            except Exception:
                continue
        self._font_cache[size] = None
        return None

    # ==================== 坐标计算 ====================

    @staticmethod
    def _clamp_into(value: float, low: int, high: int) -> int:
        if high < low:
            return low
        return int(max(low, min(high, value)))

    def _icon_anchor(self, action: str) -> tuple[float, float]:
        """
        返回图标「锚点」在图标方框内的像素偏移（已按 ICON_SIZE 缩放）。

        锚点是图上代表「操作真正发生在哪」的那个点：
          点击 → 指针箭头尖端；长按 → 手指接触点；输入 → I 光标中心；拖动 → 箭头中心。
        贴图时令锚点对准操作坐标，而非按方框左上角对齐，才能精准落位。
        """
        filename = ACTION_ICONS.get(action, ICON_CLICK)
        ax_r, ay_r = ICON_ANCHORS.get(filename, DEFAULT_ANCHOR)
        return ax_r * ICON_SIZE, ay_r * ICON_SIZE

    def _icon_topleft(self, action: str, cx: int, cy: int,
                      img_w: int, img_h: int) -> tuple[int, int]:
        """由「操作点」反推图标左上角坐标，并保证图标完整落在图内。"""
        ax, ay = self._icon_anchor(action)
        left = self._clamp_into(cx - ax, 0, max(0, img_w - ICON_SIZE))
        top = self._clamp_into(cy - ay, 0, max(0, img_h - ICON_SIZE))
        return left, top

    # ==================== 主入口 ====================

    def annotate(
        self,
        screenshot_path: str,
        action: str,
        points: list[tuple[int, int]] | None = None,
        label: str | None = None,
        *,
        viewport: tuple[int, int] | None = None,
    ) -> str:
        """
        在截图上叠加操作图标，返回新图片路径。

        :param screenshot_path: 原始截图路径
        :param action:          动作名（click / long_press / input / drag / scroll ...）
        :param points:          操作点列表（像素坐标，左上原点）。
                                click/长按/输入/悬停传 1 个点；drag/拖动传 [起点, 终点]。
        :param label:           自定义标签文字，None 时用 ACTION_LABELS
        :param viewport:        截图时的视口尺寸 (w, h)。若截图尺寸与之不符（例如全页截图或
                                缩放截图），会按比例换算坐标。
        :return:                叠加后的图片路径；失败时返回原路径
        """
        if not screenshot_path or not os.path.isfile(screenshot_path):
            return screenshot_path
        if not points:
            return screenshot_path

        try:
            base = Image.open(screenshot_path).convert("RGBA")
            img_w, img_h = base.size

            # 坐标换算：截图尺寸与视口不一致时按比例缩放
            pts = list(points)
            if viewport and viewport[0] > 0 and viewport[1] > 0:
                vw, vh = viewport
                if (vw, vh) != (img_w, img_h):
                    sx = img_w / vw
                    sy = img_h / vh
                    pts = [(int(x * sx), int(y * sy)) for x, y in pts]

            icon = self._load_icon(action)
            text = label if label is not None else ACTION_LABELS.get(action, "操作")
            font = self._load_font(LABEL_FONT_SIZE)

            # 拖动类：起点 + 终点两颗图标，并用连线/箭头串起来
            if action in ("drag", "scroll") and len(pts) >= 2:
                self._draw_drag(base, pts[0], pts[1])
                draw_items = [
                    (pts[0], "起点", -1),   # label_below=-1 表示标签画在图标上方
                    (pts[1], "终点", 1),
                ]
            else:
                draw_items = [(pts[0], text, 1)]

            for (px, py), item_text, below in draw_items:
                if icon is not None:
                    ic = icon.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
                    left, top = self._icon_topleft(action, px, py, img_w, img_h)
                    base.alpha_composite(ic, (left, top))
                    if below >= 0:
                        # 标签放图标方框底部之下，避免与图形主体重叠
                        ly = top + ICON_SIZE + 14
                    else:
                        ly = top - 14
                    self._draw_label(base, item_text, px, ly, font)
                else:
                    # 无图标时退化为绘制准星
                    self._draw_crosshair(base, px, py, item_text, font)

            # 落盘：文件名带上动作与坐标指纹，避免同一张截图的多次标注互相覆盖
            sig = hashlib.md5(
                f"{action}|{pts}|{label}".encode("utf-8")
            ).hexdigest()[:8]
            out_name = f"annotated_{Path(screenshot_path).stem}_{action}_{sig}.png"
            out_path = self.cache_dir / out_name
            base.convert("RGB").save(str(out_path), format="PNG")
            return str(out_path)

        except Exception as e:
            logger.warning(f"[ActionOverlay] 叠加失败，返回原图: {e}")
            return screenshot_path

    # ==================== 绘制辅助 ====================

    def _draw_drag(self, base: Any, start: tuple[int, int], end: tuple[int, int]) -> None:
        """画拖拽轨迹：起点圆点 + 粗线 + 终点箭头，方向一目了然。"""
        try:
            import math
            draw = ImageDraw.Draw(base, "RGBA")
            line_color = (139, 92, 246, 235)

            # 主连线
            draw.line([start, end], fill=line_color, width=5)

            # 终点箭头（在靠近终点处画一个三角，指示拖动方向）
            dx, dy = end[0] - start[0], end[1] - start[1]
            dist = math.hypot(dx, dy)
            if dist > 1:
                ux, uy = dx / dist, dy / dist
                # 箭头尖端稍微内缩，避免与终点图标重叠
                tip_x = end[0] - ux * 14
                tip_y = end[1] - uy * 14
                head_len, head_w = 26, 13
                bx, by = tip_x - ux * head_len, tip_y - uy * head_len
                # 垂直方向
                px, py = -uy, ux
                pts = [
                    (tip_x, tip_y),
                    (bx + px * head_w, by + py * head_w),
                    (bx - px * head_w, by - py * head_w),
                ]
                draw.polygon(pts, fill=line_color)

            # 起点圆点
            r = 9
            draw.ellipse([start[0] - r, start[1] - r, start[0] + r, start[1] + r],
                         fill=(37, 99, 235, 235), outline=(255, 255, 255, 235), width=3)
        except Exception as e:
            logger.debug(f"[ActionOverlay] 拖拽轨迹绘制失败: {e}")

    def _draw_label(self, base: Any, text: str, cx: int, cy: int, font: Any) -> None:
        """在图标下方画一个小标签（带圆角底衬，保证可读）。"""
        if not text or font is None:
            return
        try:
            draw = ImageDraw.Draw(base, "RGBA")
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            pad_x, pad_y = 10, 5
            box_w = tw + pad_x * 2
            box_h = th + pad_y * 2

            x0 = self._clamp_into(cx - box_w / 2, 0, max(0, base.width - box_w))
            y0 = self._clamp_into(cy - box_h / 2, 0, max(0, base.height - box_h))
            x1, y1 = x0 + box_w, y0 + box_h

            draw.rounded_rectangle([x0, y0, x1, y1], radius=8,
                                   fill=(17, 24, 39, 215))
            draw.text((x0 + pad_x - bbox[0], y0 + pad_y - bbox[1]),
                      text, font=font, fill=(255, 255, 255, 255))
        except Exception as e:
            logger.debug(f"[ActionOverlay] 标签绘制失败: {e}")

    def _draw_crosshair(self, base: Any, cx: int, cy: int, text: str, font: Any) -> None:
        """图标缺失时的兜底：画十字准星 + 标签。"""
        try:
            draw = ImageDraw.Draw(base, "RGBA")
            r = 26
            color = (239, 68, 68, 235)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=4)
            draw.line([(cx - r - 10, cy), (cx + r + 10, cy)], fill=color, width=3)
            draw.line([(cx, cy - r - 10), (cx, cy + r + 10)], fill=color, width=3)
            self._draw_label(base, text, cx, cy + r + 18, font)
        except Exception as e:
            logger.debug(f"[ActionOverlay] 准星绘制失败: {e}")

    def clear_cache(self, keep: int = 50) -> None:
        """清理叠加缓存，仅保留最新的 keep 个文件。"""
        try:
            files = sorted(
                self.cache_dir.glob("annotated_*.png"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for p in files[keep:]:
                try:
                    p.unlink()
                except OSError:
                    pass
        except Exception as e:
            logger.debug(f"[ActionOverlay] 缓存清理失败: {e}")
