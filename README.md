python rtt2udp.py# RTT2UDP 转换器

这个工具用于将JLink的RTT(Real-Time Transfer)数据转发到UDP端口，方便其他应用程序接收和处理RTT数据。

## 功能特点

- 通过PyLink连接JLink设备
- 读取RTT数据并转发到指定的UDP端口
- 可配置的设备类型、RTT缓冲区和UDP目标地址
- 简单易用的命令行界面

## 安装依赖

在使用前，请确保安装了所需的Python依赖：

```bash
pip install pylink-square
```

同时，确保已安装JLink软件包，并且JLink驱动程序已正确安装。

## 配置

在`config.py`文件中可以修改以下配置：

- `target_device`: 目标设备类型（例如"STM32F407VE"）
- `rtt_buffer_index`: RTT缓冲区索引（通常为0）
- `polling_interval`: 轮询间隔（秒）
- `udp_ip`: UDP目标IP地址
- `udp_port`: UDP目标端口
- `debug`: 是否启用调试输出

## 使用方法

1. 连接JLink设备到计算机
2. 根据实际情况修改`config.py`中的配置
3. 运行程序：

```bash
python rtt2udp.py
```

4. 程序将开始将RTT数据转发到指定的UDP端口
5. 按`Ctrl+C`停止程序

## 接收UDP数据

可以使用任何支持UDP的工具或程序接收转发的数据，例如：

```python
import socket

# 创建UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 8888))  # 绑定到与config.py中相同的端口

print("等待接收RTT数据...")
while True:
    data, addr = sock.recvfrom(1024)
    print(f"收到数据: {data.decode('utf-8', errors='replace')}")
```

## 故障排除

- 确保JLink设备已正确连接
- 验证目标设备类型是否正确
- 检查RTT是否已在目标设备上启用
- 确认UDP端口没有被防火墙阻止

## 许可

MIT
