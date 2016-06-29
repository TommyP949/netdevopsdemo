#!/bin/bash

function error() {
  echo -e "\e[0;33mERROR: The Zero Touch Provisioning script failed while running the command $BASH_COMMAND at line $BASH_LINENO.\e[0m" >&2
}
trap error ERR

export SSH_KEY_URL="http://10.254.254.254/authorized_keys"
export LICENSE_URL="http://10.254.254.254/license.txt"

#Install license
wget -q -O /root/license.txt $LICENSE_URL
/usr/cumulus/bin/cl-license -i /root/license.txt

#Setup SSH key authentication for Ansible
mkdir -p /root/.ssh
wget -O /root/.ssh/authorized_keys $SSH_KEY_URL
mkdir -p /home/cumulus/.ssh
wget -O /home/cumulus/.ssh/authorized_keys $SSH_KEY_URL
chown -R cumulus:cumulus /home/cumulus/.ssh

## Debating if this should be done with Ansible or ZTP
echo "Enable Managment MRF"
apt-get update
apt-get install -yq cl-mgmtvrf
/usr/sbin/cl-mgmtvrf -e

#Reboot the switch
/sbin/shutdown -r -t 10 now "Rebooting switch to finish ZTP install"

exit 0
#CUMULUS-AUTOPROVISIONING
