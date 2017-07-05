# Monitor the GPU running of multiple servers through WEB  and the project references https://github.com/WarBean/gpu_monitor

## Usage:
1. Switch to Python 3 environment

2. Installation dependency:

```shell
pip install itchat
pip install psutil
pip install requests
```

3. Select a server as master server and run

```shell
python master.py --address <host IP> ,if can't get IP auto,you can write IP use --address
```

4. Run on multiple GPU servers

```shell
python slaver.py --address <master IP>
```

5. Get help:

```python
python master.py -h
```
