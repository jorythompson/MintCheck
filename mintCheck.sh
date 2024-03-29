#!/bin/bash
# Open a shell like this for testing:
# bash --noprofile --norc
if [ -f "mintCheck.py" ];
then
  export MINT_FOLDER=./
else
  export MINT_FOLDER=/mnt/usbdrive/python/mintCheck
fi
export API_FOLDER=$MINT_FOLDER/../github/mintapi
cd $MINT_FOLDER
export PYTHONPATH=$API_FOLDER
python $MINT_FOLDER/mintCheck.py --config $MINT_FOLDER/home.ini
exit
