# BlueJeans SV5B Deployment

This is collaboration between Cumulus and BlueJeans to automate a Datacenter network.

The goal is to deploy a clos network utilizing ONIE to install system
images on the network switches, ZTP to setup a baseline config (deploy ssh keys),
and finally Ansible to push the actual network configurations (PTM, IP, BGP, etc)

#Files:
- role/config-isc-dhcp-server/files/dhcpd.conf: dhcp file used on the RMP managment switch
- role/mgmt-switch-networking/templates/hosts.j2: host file for OOBM Management switch
- role/apache2/files/ztp-deploy.sh: Zero touch provisioning script which opies license
file, and authorized public key for Ansible.
- Vagrant/Vagrantfile: Vagrant definition to stand up virtual network


#Physical Components:

#Diagrams:

#Automated install instructions:
###Become root and install ansible and git
```
sudo -i
apt-get update
apt-get install -y python-pip git python-dev gcc python-apt
pip install ansible; pip install ansible --upgrade
```

###Clone the git repo locally and cd into the dc1 directory:
```
git clone https://github.com/CumulusNetworks/bluejeans
cd bluejeans/dc1/
```

###Run management.yml ansible playbook
`ansible-playbook management.yml`

###Deploy ssh keys
```
ansible-playbook deploy-ssh-keys.yml -kK
```

###Run the full playbooks
Make sure to use the --extra-vars flag to set vagrant=yes. Leave off the statement if vagrant isn't being used (i.e. running ansible on production). Currently the flag removes  switch/ports.conf and doesn't restart switch (switchd does't exist in VX), and it adds in the eth1 interface that allows for dhcp using the "RMP like" VX switch.
`ansible-playbook main.yml -e vagrant=yes`


#Manual install instructions
###Connect to the management VM
`vagrant ssh management`

###Change to root
vagrant@management:~$ sudo -i

root@management:~#
- echo -e "deb http://ftp.us.debian.org/debian/ wheezy main contrib non-free\ndeb-src http://ftp.us.debian.org/debian/ wheezy main contrib non-free" >> /etc/apt/sources.list
- apt-get update
- apt-get install -y isc-dhcp-server dnsmasq apache2
- apt-get install -y python-pip shedskin libyaml-dev sshpass git python-netaddr
- pip install ansible
- pip install ansible --upgrade

###Setup git and download the repo

root@management:~#
- git init
- git config --global user.name "Your Name"
- git config --global user.email your_email@domain.com
- git clone https://github.com/CumulusNetworks/bluejeans

###Validate OOB connection on the management switch
root@management:~#

- cp ~/bluejeans/dc1/management/etc/network/interfaces /etc/network/interfaces
- service networking restart

###Setup DNS
- cat ~/bluejeans/dc1/management/etc/hosts >> /etc/hosts
- service dnsmasq restart

###Setup DHCP
- cp ~/bluejeans/dc1/management/etc/dhcp/dhcpd.conf /etc/dhcp/dhcpd.conf
- cp ~/bluejeans/dc1/management/etc/dhcp/dhcpd.hosts /etc/dhcp/dhcpd.hosts
- cp ~/bluejeans/dc1/management/etc/dhcp/dhcpd.pools /etc/dhcp/dhcpd.pools
- service isc-dhcp-server restart

###Validate connectivity
Change into the ~/bluejeans/dc1 directory to run the Ansible playbooks

root@management:~# cd bluejeans/dc1
- root@management:~/bluejeans/dc1#
- ansible all -m ping -u cumulus -k
  - (pwd: CumulusLinux!)

###Setup SSH keys and deploy to the network
- ssh-keygen -t rsa
- cp /root/.ssh/id_rsa.pub /var/www/authorized_keys
- cp ~/bluejeans/dc1/var/www/ztp_deploy.sh /var/www/
- ansible-playbook deploy_ssh_keys.yml --ask-become-pass -k
  - (pwd: CumulusLinux!)

###Run the full playbooks
Make sure to use the --extra-vars flag to set vagrant=yes. Leave off the statement if vagrant isn't being used (i.e. running ansible on production). Currently the flag removes  switch/ports.conf and doesn't restart switch (switchd does't exist in VX), and it adds in the eth1 interface that allows for dhcp using the "RMP like" VX switch.
- ansible-playbook main.yml -e vagrant=yes
