#!/bin/sh
export PYTHONPATH=/mnt/usbdrive/python/github
# use this line to prompt mint to send a text message for a passcode.  Note that mint will only send a passcode (this
# will only work) if the previous one has expired.
#python /mnt/usbdrive/python/MintCheck/mintCheck.py --config /mnt/usbdrive/python/MintCheck/home.ini --prompt-for-text
python /mnt/usbdrive/python/MintCheck/mintCheck.py --config /mnt/usbdrive/python/MintCheck/home.ini 
exit
