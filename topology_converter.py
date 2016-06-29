#
#
#    Topology Converter
#       converts a given topology.dot file to a Vagrantfile
#           can use the virtualbox Vagrant provider
#Initially written by Eric Pulvino 2015-10-19
#
#   to do:
#       -Use proper dot file parsing library
#       -Add support for libvirt Vagrant file output

import re
import sys
from definitions import *
from collections import defaultdict

#Parse and set args
topology_file=sys.argv[1]
VAGRANTFILE="./Vagrantfile"
script_storage="./helper_scripts"
clean_up=False #Don't use this-- it removes the generated remap_eth files
verbose=True
mac="A00000000000"
switch_mem="512" #in MB
dhcp_mac_file="./dhcp_mac_map"

def change_mac(mac, offset):
    return "{:012X}".format(int(mac, 16) + offset)

def getKey(item):
    base = 10
    if item[0][0:3].lower() == "eth": base = 0
    val = float(item[0][3:].replace("s","."))
    return val + base

def remove_generated_files(hostname_code_mapper):
    import os
    for hostname in hostname_code_mapper:
        if hostname_code_mapper[hostname][0]=="switch":
            os.remove(script_storage+"/"+hostname+"_remap_eth")

def generate_remapping_files(hostname_code_mapper,connection_map):
    for hostname in hostname_code_mapper:
        if hostname_code_mapper[hostname][0]=="switch":
            #We must create a remap file
            filename=script_storage+"/"+hostname+"_remap_eth"
            with open(filename,"wb") as remap_file:
                remap_file.write("""# Which method to use to re-map the NICs
# Options are "simple", which just renumberes ethN->swpN, or "mapped" which
# uses the array below to re-map ethN names.
REMAP_METHOD="mapped"
# Map of ethN names to new names. The new name can be anything you like, as
# long as the kernel accepts it.
MAP="\n""")
                count=1
                for (interface,net_name,line,line_number) in connection_map[hostname]:
                    remap_file.write("     eth"+str(count)+"="+interface+"\n")
                    count+=1
                remap_file.write("\"\n")


def parse_topology_file():
    #Open topology file
    with open(topology_file,"r") as f1:
        file_contents= f1.readlines()
    #Key is hostname, value is [(port,net_number,topo_line,topo_line_number)]
    ##### This could be done with a class
    connection_map=defaultdict(list)
    #Map Hostnames seen in Topology file to Hostnames defined in the Definitions.py File
    #Key is hostname, value is ("switch/server","box_vers_to_run")
    hostname_code_mapper={}

    #Parse Topology_File
    net_number=1
    line_number=0
    print "\nTopology File Contents:"
    for line in file_contents:
        if line_number == 0: line_number +=1; continue
        elif not re.match("^.* -- .*$",line): continue

        new_net=True
        net_name="net" + str(net_number)
        line_pieces=line.split("--")

        left_side=line_pieces[0].replace("\n","").replace(" ","").replace('"','')
        right_side=line_pieces[1].replace("\n","").replace(" ","").replace('"','')

        lhostname,linterface=left_side.split(":")
        rhostname,rinterface=right_side.split(":")

        #check for hostname existance in definitions.py
        if lhostname in switches: hostname_code_mapper[lhostname]=("switch",switch_code)
        elif lhostname in servers: hostname_code_mapper[lhostname]=("server",server_code)
        else:
            print "ERROR: We have found a Hostname (\""+lhostname+"\") in the Topology File that is not specified"
            print "       as a switch or server in the definitions.py file!"
            exit(1)
        if rhostname in switches: hostname_code_mapper[rhostname]=("switch",switch_code)
        elif rhostname in servers: hostname_code_mapper[rhostname]=("server",server_code)
        else:
            print "ERROR: We have found a Hostname (\""+rhostname+"\") in the Topology File that is not specified"
            print "       as a switch or server in the definitions.py file!"
            exit(1)

        #check to see if interface/hostname combo has already been declared elsewhere
        left_exists = -1
        index=0
        if lhostname in connection_map:
            for link in connection_map[lhostname]:
                if link[0] == linterface:
                    left_exists=index
                    new_net=False
                    #leftside interface already exists use his net_name
                    net_name=link[1]
                index+=1

        right_exists = -1
        index=0
        if rhostname in connection_map:
            for link in connection_map[rhostname]:
                if link[0] == rinterface:
                    right_exists=index
                    if not new_net and net_name!=link[1]:
                        print "WARN: Both interfaces have already been used in the following topology file line:"
                        print "    " + line
                        print "   Move this line to the top of the topology file and try again."
                        exit(1)
                    new_net=False
                    #rightside interface already exists use his net_name
                    net_name=link[1]
                index+=1

        #add interfaces to connection map
        if left_exists == -1: connection_map[lhostname].append([linterface,net_name,line,str(line_number)])
        else:
            connection_map[lhostname][left_exists][2] = "Multiple Lines Generated this Line\n"
            connection_map[lhostname][left_exists][3] = "multi"

        if right_exists == -1: connection_map[rhostname].append([rinterface,net_name,line,str(line_number)])
        else:
            connection_map[rhostname][right_exists][2] = "Multiple Lines Generated this Line\n"
            connection_map[rhostname][right_exists][3] = "multi"


        print "   "+net_name + "    " + left_side + " " + right_side
        if new_net: net_number +=1
        line_number +=1

    #Print collected Content from Definitions.py file
    print "\n\nSwitch OS will be: \"" + switch_code + "\""
    print "   On following devices..."
    for device in switches:
        print "    * " + device
    print
    print ""
    print "Server OS will be: \"" + server_code + "\""
    print "   On following devices..."
    for device in servers:
        print "    * " + device

    #Sort the list for proper interface mapping
    for hostname in connection_map:
        connection_map[hostname].sort(key=getKey)
    if verbose:
        for hostname in connection_map:
            print "\nHostname: " + hostname
            for (interface,net_name,line,line_number) in connection_map[hostname]:
                print "    " + interface + " -- " + net_name
    return hostname_code_mapper,connection_map

def generate_vagrantfile(hostname_code_mapper,connection_map):
    #Build Vagrant_file for VirtualBox
    global mac
    mac_file = open(dhcp_mac_file,"w")
    with open(VAGRANTFILE,"w") as vfile:
        vfile.write("# Created by Topology-Converter\n#    using topology data from: "+topology_file+"\n")
        vfile.write("""Vagrant.configure(\"2\") do |config|
  ##### GLOBAL OPTIONS #####
  config.vm.provider \"virtualbox\" do |v|
    v.gui=false
  end""")

        vfile.write("\n  ##### DEFINE VMs #####\n")
        for hostname in connection_map:
            filtered_hostname=hostname.replace("-","_")
            vfile.write("  ##### DEFINE VM for "+hostname+" #####\n")
            vfile.write("  config.vm.define \"" + hostname + "\" do |" + filtered_hostname + "|\n")
            vfile.write("      "+filtered_hostname+".vm.provider \"virtualbox\" do |v|\n")
            vfile.write("        v.name = \""+hostname+"\"\n")
            if hostname_code_mapper[hostname][0] == "switch":
                vfile.write("        v.memory = "+switch_mem+"\n")
            vfile.write("      end\n")
            vfile.write("      "+filtered_hostname+".vm.hostname = \""+hostname+"\"\n")
            vfile.write("      "+filtered_hostname+".vm.box = \""+hostname_code_mapper[hostname][1]+"\"\n")



            vfile.write("\n")
            for (interface,net_name,line,line_number) in connection_map[hostname]:
                vfile.write("          # Local_Interface: "+interface+" Topology_File_Line("+line_number+"):"+line)
                if interface == "eth1":
                    vfile.write("          "+filtered_hostname+".vm.network \"private_network\", virtualbox__intnet: '"+net_name+"', auto_config: false, :mac => \""+mac+"\"\n\n")
                    mac_file.write(hostname+", "+mac+"\n")

                    mac = change_mac(mac, 1)
                    continue
                elif hostname_code_mapper[hostname][0] == "server":
                    vfile.write("          "+filtered_hostname+".vm.network \"private_network\", virtualbox__intnet: '"+net_name+"', auto_config: false\n\n")
                else:
                    vfile.write("          "+filtered_hostname+".vm.network \"private_network\", virtualbox__intnet: '"+net_name+"', cumulus__intname: '"+interface+"', auto_config: true\n\n")


            vfile.write("      #Apply MGMT interface Config to ETH1 (only works for Debian based networking)\n")
            vfile.write("      "+filtered_hostname+".vm.provision \"file\", source: \""+script_storage+"/mgmt_interface\", destination: \"/home/vagrant/mgmt_interface\"\n")
            vfile.write("      "+filtered_hostname+".vm.provision \"shell\", inline: \"chmod 777 /home/vagrant/mgmt_interface\"\n")
            vfile.write("      "+filtered_hostname+".vm.provision \"shell\", inline: \"/home/vagrant/mgmt_interface\"\n\n")



            if hostname_code_mapper[hostname][0] == "switch":
                vfile.write("      #Apply the interface re-map\n")
                vfile.write("      "+filtered_hostname+".vm.provision \"file\", source: \""+script_storage+"/rename_eth_swp\", destination: \"/home/vagrant/rename_eth_swp\"\n")
                vfile.write("      "+filtered_hostname+".vm.provision \"file\", source: \""+script_storage+"/"+hostname+"_remap_eth\", destination: \"/home/vagrant/remap_eth\"\n")
                vfile.write("      "+filtered_hostname+".vm.provision \"file\", source: \""+script_storage+"/apply_interface_remap\", destination: \"/home/vagrant/apply_interface_remap\"\n")
                vfile.write("      "+filtered_hostname+".vm.provision \"shell\", inline: \"chmod 777 /home/vagrant/apply_interface_remap\"\n")
                vfile.write("      "+filtered_hostname+".vm.provision \"shell\", inline: \"/home/vagrant/apply_interface_remap\"\n\n")

            vfile.write("      "+filtered_hostname+".vm.provider \"virtualbox\" do |vbox|\n")
            count=1
            for (interface,net_name,line,line_number) in connection_map[hostname]:
                vfile.write("        vbox.customize ['modifyvm', :id, '--nicpromisc"+str(count+1)+"', 'allow-vms']\n")
                count +=1
            vfile.write("      end\n")

            vfile.write("  end\n\n")
        vfile.write("end\n")
    mac_file.close()

def main():
    hostname_code_mapper,connection_map = parse_topology_file()

    generate_remapping_files(hostname_code_mapper,connection_map)

    generate_vagrantfile(hostname_code_mapper,connection_map)

    if clean_up: remove_generated_files(hostname_code_mapper)


if __name__ == "__main__":
    main()
    print "\nVagrantfile has been generated!\n\nDONE!\n"
exit(0)
