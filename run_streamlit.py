#!/usr/bin/env python3
"""
Streamlit 앱 실행 스크립트
"""

import subprocess
import sys
import os

def run_streamlit():
    """Streamlit 앱을 실행합니다."""
    try:
        # 현재 디렉토리에서 streamlit 실행
        cmd = [sys.executable, "-m", "streamlit", "run", "streamlit_app.py"]
        
        print("🚀 Streamlit 앱을 시작합니다...")
        print("📱 브라우저에서 http://localhost:8501 로 접속하세요")
        print("⏹️  종료하려면 Ctrl+C를 누르세요")
        
        subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
        
    except KeyboardInterrupt:
        print("\n👋 Streamlit 앱이 종료되었습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    run_streamlit()