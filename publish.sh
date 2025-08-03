#!/bin/bash

rm -rf dist/ build/ *.egg-info

python3 setup.py sdist bdist_wheel


echo "🚀 Активация виртуального окружения..."
source venv/bin/activate

echo "🧹 Очистка предыдущих билдов..."
rm -rf dist/ build/ *.egg-info

echo "📦 Сборка пакета..."
python3 setup.py sdist bdist_wheel

echo "🔑 Публикация на PyPI..."
python3 -m twine upload dist/*
pip3 uninstall shadowPaySDK --break-system-packages
pip3 install --upgrade shadowpaySDK --break-system-packages


echo "✅ Готово! Выйти из venv можно командой: deactivate"
