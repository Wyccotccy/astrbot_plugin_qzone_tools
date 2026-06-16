# image_utils.py
"""
图片格式转换工具

所有插件生成的图片（浏览器截图、刻度叠加图、下载图片等）
统一通过此模块转换为目标格式后再返回给 AI。
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image

# 支持的输出格式
SUPPORTED_FORMATS = {"png", "jpg", "webp"}

# Pillow 格式名映射
_FORMAT_MAP = {
    "webp": "WEBP",
    "png": "PNG",
    "jpg": "JPEG",
}

# 扩展名映射
_EXT_MAP = {
    "webp": ".webp",
    "png": ".png",
    "jpg": ".jpg",
}


def convert_image_format(
    input_path: str | Path,
    output_format: str = "png",
    quality: int = 80,
    *,
    overwrite: bool = True,
) -> str:
    """
    将图片转换为目标格式。

    :param input_path:   输入图片路径（任意 Pillow 支持的格式）
    :param output_format: 目标格式 "webp" | "png" | "jpg"
    :param quality:       JPEG/WEBP 质量 (1-100)，PNG 忽略此参数
    :param overwrite:     True=覆盖原文件，False=另存为同名新扩展名文件
    :return:              转换后的文件绝对路径
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"图片文件不存在: {input_path}")

    output_format = output_format.lower().strip()
    if output_format not in SUPPORTED_FORMATS:
        raise ValueError(f"不支持的格式: {output_format}，可选: {SUPPORTED_FORMATS}")

    pillow_format = _FORMAT_MAP[output_format]
    target_ext = _EXT_MAP[output_format]

    img = Image.open(input_path)

    # RGBA → RGB (JPEG 不支持透明通道)
    if pillow_format == "JPEG" and img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
        img = background

    # 确定输出路径
    if overwrite:
        # 如果已经是目标格式，直接覆盖
        if input_path.suffix.lower() == target_ext:
            img.save(str(input_path), format=pillow_format, quality=quality)
            return str(input_path.resolve())
        # 否则覆盖原文件（改扩展名）
        output_path = input_path.with_suffix(target_ext)
        img.save(str(output_path), format=pillow_format, quality=quality)
        # 删除旧格式文件（如果扩展名不同）
        try:
            os.remove(str(input_path))
        except OSError:
            pass
        return str(output_path.resolve())
    else:
        output_path = input_path.with_suffix(target_ext)
        img.save(str(output_path), format=pillow_format, quality=quality)
        return str(output_path.resolve())


def get_format_from_config(config: dict) -> str:
    """从插件配置中读取图片输出格式，带默认值和校验。"""
    fmt = config.get("image_output_format", "png").lower().strip()
    if fmt not in SUPPORTED_FORMATS:
        fmt = "png"
    return fmt


def get_output_ext(fmt: str) -> str:
    """格式名 → 文件扩展名。"""
    return _EXT_MAP.get(fmt, ".png")
