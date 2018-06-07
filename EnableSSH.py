"""Developed by Jason Hernandez"""

from getpass import getpass
from multiprocessing import Queue, Process
from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException, NetMikoAuthenticationException
from datetime import datetime
import csv
import logging


class Configure_SSH:

    def __init__(self, username, password, ip):
        #add variables you are looking for in the class here.
        self.user = username
        self.passw = password
        self.ip = ip

    def config_part(self, device, hostname):
        if hostname == '':
            hostname = self.ip
            # if the hostname is blank use the ip address.
        try:
            telnet = ConnectHandler(**device, timeout=60)
            ssh_v2 = telnet.send_command('show ip ssh | include SSH')
            output = '=' * 20 + f'Begin {hostname}' + '=' * 20 + '\n'
            if 'SSH Enabled - version 2.0' in ssh_v2:
                output += f'Looks like SSH v2 is already enabled for {hostname}.'
                output += '\n' + ssh_v2 + '\n'
                ssh_enable = ('line vty 0 15',
                              'transport input telnet ssh')
                telnet.send_config_set(ssh_enable, delay_factor=2)
            elif 'SSH Enabled - version 1.99' in ssh_v2:
                output += f'\nLooks like a crypto cert has been generated but ssh v2 is not set on {hostname}'
                output += '\n' + ssh_v2 + '\n'
                ssh_enable = ('ip ssh version 2',
                              'line vty 0 15',
                              'transport input telnet ssh')
                telnet.send_config_set(ssh_enable, delay_factor=2)
            else:
                key_gen = 'crypto key generate rsa modulus 2048'
                ssh_enable = ('ip ssh version 2',
                              'line vty 0 15',
                              'transport input telnet ssh')
                telnet.send_config_set(key_gen, delay_factor=4)
                telnet.send_config_set(ssh_enable, delay_factor=2)
            output += telnet.send_command('show run | section include line vty')
            telnet.send_command('wr')
            output +=  '\n' + '=' * 20 + f'End {hostname}' + '=' * 20
            telnet.disconnect()
            print(output)
        except NetMikoTimeoutException:
            print(f"SSH is not working to {hostname}. Ensure device is reachable")
            logging.warning(f"{datetime.now()}: SSH is not working to {hostname}. Ensure device is reachable."
                            "Verify correct IP in [Cisco Devices.csv]")
        except NetMikoAuthenticationException:
            print(f"Check your Username/Password. Make sure you have an account on this device.")
            logging.warning(f"{datetime.now()}: Check your username/password to {hostname}"
                            " Make sure you have an account on this device.")
        except ValueError:
            print('Something else has gone wrong on {hostname}. Insure you have the correct priv level.')
            logging.warning(f"{datetime.now()}: Insure your permissions are correct for {hostname}")

    def cisco_ssh_many(self):
        Queue(maxsize=20)
        process = []
        with open("DeviceDB.csv", mode='r') as devices:
            reader = csv.DictReader(devices)
            for row in reader:
                """ Uses CSV file to find device_type, IP_address, and HostName.
                    Ensure all IP's and device_types are correct.
                    HostName field is not used to log into the device, only for sorting data."""
                device_type = row['device_type']
                ip_add = row['IP_Address']
                hostname = row['HostName']
                device = {
                    'device_type': device_type,
                    'ip': ip_add,
                    'username': self.user,
                    'password': self.passw,
                }
                if device_type == 'cisco_ios_telnet':
                    pass
                else:
                    continue
                my_process = Process(target=self.config_part, args=(device, hostname))
                my_process.start()
                process.append(my_process)

        for a_process in process:
            a_process.join()

    def cisco_ssh_one(self):
        device = {
            'device_type': 'cisco_ios',
            'ip': self.ip,
            'username': self.user,
            'password': self.passw
        }
        self.config_part(device, hostname='')


def cisco_ssh_enable():
    logging.basicConfig(filename='SSHEnableFailure.log', level=logging.WARNING)
        # Turns on logging to a file named SSHEnableFailure.
    print("Welcome to the SSH enable script for Cisco Devices\n")
    print("login creds needed!\n")
    username = input('Username: ')
    password = getpass()
    print('Insure "ip domain-name " is set on all devices.\n'
          'This script will attempt to run these commands:\n'
          'conf t\n'
          'crypto key generate rsa modulus 2048\n'
          '# the above command takes a bit of time so we will wait a bit.\n'
          'ip ssh version 2\n'
          'line vty 0 15\n'
          'transport input telnet ssh\n'
          '# for safety telnet wont be turned off.\n'
          '*** test with one device first! ***\n')
    ip = ''
    one_or_all_q = True
    while one_or_all_q:
        one_or_all = input('Are you changing one device or all devices? (one/all): ')
        if one_or_all.lower() == "one":
            ip = input('Please enter the target IP address: ')
            start_time = datetime.now()
            Configure_SSH(username, password, ip).cisco_ssh_one()
            end_time = datetime.now()
            total_time = end_time - start_time
            one_or_all_q = False
        elif one_or_all.lower() == "all":
            print('All devices will be changed.\n\n')
            start_time = datetime.now()
            Configure_SSH(username, password, ip).cisco_ssh_many()
            end_time = datetime.now()
            total_time = end_time - start_time
            one_or_all_q = False
        else:
            print("Enter a valid response.")
    print("###################################################\n\n"
          "Complete! See SSHEnableFailure log for errors!\n"
          f"Total time for script: {total_time}\n\n"
          "###################################################\n")


if __name__ == '__main__':
    cisco_ssh_enable()
