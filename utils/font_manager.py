"""한글 폰트 설정 유틸리티"""

import platform
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt


def setup_korean_font():
    """시스템에 맞는 한글 폰트를 설정합니다."""
    try:
        system = platform.system()
        
        if system == "Darwin":  # macOS
            font_candidates = ["AppleGothic", "Apple SD Gothic Neo", "Noto Sans CJK KR"]
        elif system == "Windows":
            font_candidates = ["Malgun Gothic", "Microsoft YaHei", "Noto Sans CJK KR"]
        else:  # Linux
            font_candidates = ["NanumGothic", "Noto Sans CJK KR", "DejaVu Sans"]

        available_fonts = [f.name for f in fm.fontManager.ttflist]

        for font in font_candidates:
            if font in available_fonts:
                plt.rcParams["font.family"] = font
                plt.rcParams["axes.unicode_minus"] = False
                return font

        # 기본 폰트 설정
        plt.rcParams["font.family"] = "DejaVu Sans"
        plt.rcParams["axes.unicode_minus"] = False
        return "DejaVu Sans"

    except Exception:
        plt.rcParams["font.family"] = "DejaVu Sans"
        plt.rcParams["axes.unicode_minus"] = False
        return "DejaVu Sans"