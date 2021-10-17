#!/bin/bash
homedir=/home/ubuntu
echo "Installing the requirements ... "

echo "Updating source lists"
sudo apt update 

echo "Installing python "
sudo apt install -y python3-pip
sudo apt-get install -y libcairo2-dev libgirepository1.0-dev

echo "Installing application requirements"
pip3 install -r requirements.txt
pip3 install psutil
npm install -g electron@1.8.4 orca

