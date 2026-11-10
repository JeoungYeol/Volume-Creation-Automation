"""
build.py - AutoMediaFormatter 빌드 스크립트

이 스크립트를 실행하면 dist 폴더에 AutoMediaFormatter.exe가 생성됩니다.

사전 준비:
    pip install pyinstaller PySide6

사용법:
    python build.py

결과:
    dist/AutoMediaFormatter.exe
"""

import subprocess
import sys
import os


def check_requirements():
    """필수 패키지 설치 여부 확인"""
    import importlib.util

    # (pip 패키지명, import 모듈명)
    required = [
        ("pyinstaller", "PyInstaller"),
        ("PySide6", "PySide6"),
        ("Pillow", "PIL"),  # create_icon.py에서 사용
    ]
    missing = [pip_name for pip_name, module in required
               if importlib.util.find_spec(module) is None]

    if missing:
        print(f"[오류] 다음 패키지가 필요합니다: {', '.join(missing)}")
        print(f"설치: pip install {' '.join(missing)}")
        return False
    return True


def build():
    """PyInstaller로 exe를 빌드합니다."""
    print("=" * 50)
    print("  AutoMediaFormatter 빌드 시작")
    print("=" * 50)

    # 아이콘이 없으면 생성
    icon_path = os.path.join("resources", "icon.ico")
    if not os.path.exists(icon_path):
        print("\n[1/3] 아이콘 생성 중...")
        subprocess.run([sys.executable, "create_icon.py"], check=True)
    else:
        print("\n[1/3] 아이콘 확인 완료")

    # 빌드
    print("\n[2/3] exe 빌드 중... (1~2분 소요)")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "build.spec", "--clean"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"\n[오류] 빌드 실패:")
        print(result.stderr)
        return False

    # 결과 확인
    exe_path = os.path.join("dist", "AutoMediaFormatter.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n[3/3] 빌드 성공!")
        print(f"  파일: {os.path.abspath(exe_path)}")
        print(f"  크기: {size_mb:.1f} MB")
        print(f"\n  ※ 실행 시 관리자 권한(UAC)이 자동으로 요청됩니다.")
    else:
        print("\n[오류] exe 파일이 생성되지 않았습니다.")
        return False

    print("\n" + "=" * 50)
    print("  빌드 완료!")
    print("=" * 50)
    return True


if __name__ == "__main__":
    if not check_requirements():
        sys.exit(1)
    if not build():
        sys.exit(1)
