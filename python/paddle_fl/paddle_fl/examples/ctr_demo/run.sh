#!/bin/bash
unset http_proxy
unset https_proxy
python fl_master.py
sleep 2
python -u fl_scheduler.py > scheduler.log &
sleep 5
python -u fl_server.py >server0.log &
sleep 2
for ((i=0;i<2;i++))
do 
    python -u fl_trainer.py $i >trainer$i.log &
    sleep 2
done
	
