#encoding: utf-8

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import re
import pwd
import time
import json
import psutil
import argparse
import requests
import subprocess
import socket

def get_owner(pid):
    try:
        for line in open('/proc/%d/status' % pid):
            if line.startswith('Uid:'):
                uid = int(line.split()[1])
                return pwd.getpwuid(uid).pw_name
    except:
        return None

def get_hostname():
    hostname = socket.gethostname()
    return hostname

def get_info():
    info = { 'gpu': [], 'process': [] }
    msg = subprocess.Popen('nvidia-smi', stdout = subprocess.PIPE).stdout.read().decode()
    msg = msg.strip().split('\n')

    lino = 8
    while True:
        status = re.findall('.*\d+%.*\d+C.*\d+W / +\d+W.* +(\d+)MiB / +(\d+)MiB.* +(\d+)%.*', msg[lino])
        if status == []: break
        mem_usage, mem_total, percent = status[0]
        info['gpu'].append({
            'mem_usage': float(mem_usage),
            'mem_total': float(mem_total),
            'percent': float(percent),
        })
        lino += 3

    lino = -1
    while True:
        lino -= 1
        status = re.findall('\| +(\d+) +(\d+) +\w+ +([^ ]*) +(\d+)MiB \|', msg[lino])
        if status == []: break
        gpuid, pid, program, mem_usage = status[0]
        username = get_owner(int(pid))
        if username is None:
            print(u'进程已经不存在')
            continue
        wechatname = name_dict.get(username, username)
        try:
            p = psutil.Process(int(pid))
            p.cpu_percent()
            time.sleep(0.5)
            cpu_percent = p.cpu_percent()
        except psutil.NoSuchProcess:
            print(u'进程已经不存在')
            continue
        info['process'].append({
            'gpuid': int(gpuid),
            'pid': int(pid),
            'program': program,
            'cpu_percent': cpu_percent,
            'mem_usage': float(mem_usage),
            'username': username,
            'wechatname': wechatname,
        })
    info['process'].reverse()

    return info

def running_mean(mean_info, curr_info, decay):
    def merge(a, b): return a * decay + b * (1 - decay)
    new_info = { 'gpu': [], 'process': [] }
    for mean_gi, curr_gi in zip(mean_info['gpu'], curr_info['gpu']):
        new_info['gpu'].append({
            'mem_usage': merge(mean_gi['mem_usage'], curr_gi['mem_usage']),
            'mem_total': merge(mean_gi['mem_total'], curr_gi['mem_total']),
            'percent': merge(mean_gi['percent'], curr_gi['percent']),
        })
    mean_pi_dict = { (pi['gpuid'], pi['pid'], pi['program'], pi['username']): pi for pi in mean_info['process'] }
    curr_pi_dict = { (pi['gpuid'], pi['pid'], pi['program'], pi['username']): pi for pi in curr_info['process'] }
    mean_pi_keys = set(mean_pi_dict.keys())
    curr_pi_keys = set(curr_pi_dict.keys())
    for key in sorted(set.union(mean_pi_keys, curr_pi_keys)):
        if key in mean_pi_keys and key in curr_pi_keys:
            mean_pi = mean_pi_dict[key]
            curr_pi = curr_pi_dict[key]
            mean_pi['mem_usage'] = merge(mean_pi['mem_usage'], curr_pi['mem_usage'])
            mean_pi['cpu_percent'] = merge(mean_pi['cpu_percent'], curr_pi['cpu_percent'])
            new_info['process'].append(mean_pi)
        elif key not in mean_pi_keys:
            curr_pi = curr_pi_dict[key]
            new_info['process'].append(curr_pi)
    return new_info

parser = argparse.ArgumentParser()
parser.add_argument('--address', required = True, help = u'master服务器IP地址')
parser.add_argument('--port', default = '5678', help = u'master服务器端口，默认5678')
opt = parser.parse_args()

url = 'http://%s:%s' % (opt.address, opt.port)
name_dict = dict([
    line.strip().split()
    for line in open('username_to_wechatname.txt')
])
mean_info = None
hostname = get_hostname()
while True:
    curr_info = get_info()
    if mean_info is None:
        mean_info = curr_info
    else:
        mean_info = running_mean(mean_info, curr_info, 0.9)
    mean_info['hostname'] = hostname
    data = json.dumps(mean_info)
    try:
        response = requests.get(url, data = data)
        print(u'HTTP状态码:' + ' ' + str(response.status_code))
    except Exception as e:
        print(e)
    time.sleep(10)
