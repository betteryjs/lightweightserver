#!/usr/bin/bash

git pull origin master
systemctl stop LightTGBot.service
echo  "" > LightTGBot.log

cp  LightTGBot.service  /lib/systemd/system/
chmod 644 /lib/systemd/system/LightTGBot.service
systemctl daemon-reload
systemctl start LightTGBot.service
systemctl enable LightTGBot.service
systemctl status LightTGBot.service
tail -f LightTGBot.log
