import math
import tkinter as tk
from tkinter import scrolledtext

def calculate_subnet(hosts):
    def ip_to_bin(ip):
        return '.'.join([format(int(octet), '08b') for octet in ip.split('.')])
    def wildcard_mask(mask):
        return '.'.join([str(255-int(o)) for o in mask.split('.')])
    # Minimum number of bits for hosts
    bits = math.ceil(math.log2(hosts + 2))  # +2 for network and broadcast
    subnet_mask = 32 - bits
    max_hosts = (2 ** bits) - 2
    # Subnet mask in dotted decimal
    mask_bin = '1' * subnet_mask + '0' * bits
    mask_octets = [str(int(mask_bin[i:i+8], 2)) for i in range(0, 32, 8)]
    mask_str = '.'.join(mask_octets)
    # Assign IP addresses (using 192.168.1.0 as base)
    base_ip = [192, 168, 1, 0]
    assigned_ips = []
    for i in range(1, hosts+1):
        ip = base_ip.copy()
        ip[3] += i
        # Handle overflow to next octet
        for j in range(3, 0, -1):
            if ip[j] > 255:
                ip[j] -= 256
                ip[j-1] += 1
        assigned_ips.append({'ip': '.'.join(map(str, ip)), 'subnet_mask': mask_str})
    wildcard = wildcard_mask(mask_str)
    return {
        'Required Hosts': hosts,
        'Max Hosts per Subnet': max_hosts,
        'Subnet Mask': mask_str,
        'CIDR Notation': f'/ {subnet_mask}',
        'Subnet Mask (Binary)': ip_to_bin(mask_str),
        'Wildcard Mask': wildcard,
        'Usable Host Range': f'1 - {max_hosts}',
        'Assigned IPs': assigned_ips
    }

if __name__ == '__main__':
    def run_calc():
        try:
            hosts = int(entry.get())
        except ValueError:
            output.config(state='normal')
            output.delete(1.0, tk.END)
            output.insert(tk.END, 'Please enter a valid integer for hosts.')
            output.config(state='disabled')
            return
        result = calculate_subnet(hosts)
        output.config(state='normal')
        output.delete(1.0, tk.END)
        output.insert(tk.END, '\nDHCP Subnet Calculation:\n')
        for k, v in result.items():
            if k == 'Assigned IPs':
                output.insert(tk.END, f'{k}:\n')
                for idx, host in enumerate(v, 1):
                    output.insert(tk.END, f'  Host {idx}: {host["ip"]} (Subnet Mask: {host["subnet_mask"]})\n')
            else:
                output.insert(tk.END, f'{k}: {v}\n')
        output.config(state='disabled')

    root = tk.Tk()
    root.title('DHCP Subnet Calculator')
    root.configure(bg='#222244')
    root.update_idletasks()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.geometry(f"{width}x{height}+0+0")

    header = tk.Label(root, text='DHCP Subnet Calculator', font=('Arial', 24, 'bold'), fg='#ffffff', bg='#222244')
    header.pack(pady=(20,10))
    input_frame = tk.Frame(root, bg='#222244')
    input_frame.pack(pady=(0,10))
    tk.Label(input_frame, text='Enter number of hosts needed:', font=('Arial', 16), fg='#aaffaa', bg='#222244').pack(side='left', padx=10)
    entry = tk.Entry(input_frame, font=('Arial', 16), width=10, bg='#333355', fg='#ffffff', insertbackground='#ffffff')
    entry.pack(side='left', padx=10)
    tk.Button(input_frame, text='Calculate', font=('Arial', 16, 'bold'), bg='#44aa44', fg='#ffffff', command=run_calc, activebackground='#66ff66').pack(side='left', padx=10)

    output = scrolledtext.ScrolledText(root, width=120, height=40, font=('Consolas', 14), bg='#111133', fg='#aaffaa', insertbackground='#ffffff', borderwidth=0)
    output.pack(padx=20, pady=20, fill='both', expand=True)
    output.config(state='disabled')

    root.mainloop()
