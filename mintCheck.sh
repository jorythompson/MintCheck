#!/bin/sh
export PATH=$PATH:/usr/lib/chromium-browser
export PYTHONPATH=/home/jordan/pythonDevelopment/github
export PYTHONPATH=/mnt/usbdrive/python/github
#python /mnt/usbdrive/python/MintCheck/mintCheck.py --config /mnt/usbdrive/python/MintCheck/home.ini --live
#python /mnt/usbdrive/python/MintCheck/mintCheck.py --config /mnt/usbdrive/python/MintCheck/home.ini --prompt_for_text
python /mnt/usbdrive/python/MintCheck/mintCheck.py --config /mnt/usbdrive/python/MintCheck/home.ini
exit
