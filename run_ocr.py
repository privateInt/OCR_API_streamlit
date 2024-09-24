import subprocess

subprocess.run([
    'streamlit', 'run', '/home/lexcode/바탕화면/workspace/SeunghoonShin/ocrAPI/ssh_ocr.py', '--server.address', '0.0.0.0', '--server.port', '12210', '--theme.base', 'dark'
])