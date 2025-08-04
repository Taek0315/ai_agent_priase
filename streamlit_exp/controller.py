import os
import subprocess
import sys
import webbrowser
import time

def run_streamlit():
    # 현재 controller.py가 위치한 디렉토리
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)  # 실행 경로를 이 폴더로 강제 변경

    # main.py 경로
    main_file = os.path.join(base_dir, "main.py")
    if not os.path.exists(main_file):
        print("⚠ main.py 파일을 찾을 수 없습니다.")
        sys.exit(1)

    # Streamlit 실행 명령
    command = [sys.executable, "-m", "streamlit", "run", main_file]
    print(f"🚀 Streamlit 앱 실행 중: {main_file}")

    # Streamlit 서버 실행 (백그라운드)
    process = subprocess.Popen(command)

    # 브라우저 자동 실행 (약간의 대기 후)
    time.sleep(2)
    webbrowser.open("http://localhost:8501")

    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Streamlit 서버를 종료합니다...")
        process.terminate()

if __name__ == "__main__":
    run_streamlit()
