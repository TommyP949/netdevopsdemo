#! /bin/bash
sudo -i
apt-get update
apt-get install -y python-pip git python-dev gcc python-apt
pip install ansible; pip install ansible --upgrade
git init
git config --global user.name "jawhnycooke"
git config --global user.email jawhnycooke@github.com
git clone https://github.com/CumulusNetworks/bluejeans

