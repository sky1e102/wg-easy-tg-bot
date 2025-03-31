import os
import subprocess
import sys

def create_venv():
    """Создает виртуальное окружение."""
    if not os.path.exists("venv"):
        subprocess.check_call([sys.executable, "-m", "venv", "venv"])
        print("Виртуальное окружение создано.")
    else:
        print("Виртуальное окружение уже существует.")

def install_requirements():
    """Устанавливает зависимости из requirements.txt."""
    pip_executable = os.path.join("venv", "Scripts", "pip") if os.name == "nt" else os.path.join("venv", "bin", "pip")
    subprocess.check_call([pip_executable, "install", "-r", "requirements.txt"])
    print("Зависимости установлены.")

def main():
    create_venv()
    install_requirements()
    print("Установка завершена. Активируйте виртуальное окружение и запустите приложение.")

if __name__ == "__main__":
    main()
