# RTT2UDP 转换器

这个工具用于将JLink的RTT(Real-Time Transfer)数据转发到UDP端口，方便其他应用程序接收和处理RTT数据。

## 功能特点

- 通过PyLink连接JLink设备
- 读取RTT数据并转发到指定的UDP端口
- 可配置的设备类型、RTT缓冲区和UDP目标地址
- 图形用户界面(GUI)和命令行界面
- 支持多种调试接口(SWD/JTAG)和速度设置

## 系统要求

- Python 3.6+
- JLink软件包和驱动程序
- Windows/Linux/macOS

## 安装依赖

在使用前，请确保安装了所需的Python依赖：

```bash
# 使用requirements.txt安装所有依赖
pip install -r requirements.txt

# 或者单独安装
pip install pylink-square>=0.14.2
```

同时，确保已安装JLink软件包，并且JLink驱动程序已正确安装。

## 配置

在 `config.json`文件中可以修改以下配置，或通过GUI界面进行配置：

- `target_device`: 目标设备类型（例如"STM32F407VE"）
- `debug_interface`: 调试接口，可选"SWD"或"JTAG"
- `debug_speed`: 调试速度，可选"auto"、"adaptive"或具体数值(kHz)
- `rtt_ctrl_block_addr`: RTT控制块地址，0表示自动搜索
- `rtt_buffer_index`: RTT缓冲区索引（通常为0）
- `rtt_search_start`: 搜索起始地址
- `rtt_search_length`: 搜索长度
- `rtt_search_step`: 搜索步长
- `polling_interval`: 轮询间隔（秒）
- `udp_ip`: UDP目标IP地址
- `udp_port`: UDP目标端口
- `local_port`: 本地端口，0表示自动分配
- `debug`: 是否启用调试输出

## 使用方法

1. 连接JLink设备到计算机
2. 运行程序：

```bash
python main.py
```

3. 在GUI界面中选择JLink设备、配置参数并启动转发
4. 点击"停止"按钮停止转发

## 项目结构

- `main.py`: 主程序入口(GUI模式)
- `config.py`: 配置管理
- `rtt_manager.py`: RTT通信管理
- `udp_manager.py`: UDP通信管理
- `forwarder.py`: 数据转发逻辑
- `gui_manager.py`: GUI界面管理
- `device_selector.py`: JLink设备选择器

## 接收UDP数据

可以使用任何支持UDP的工具或程序接收转发的数据，例如：

```python
import socket

# 创建UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 8888))  # 绑定到与config.json中相同的端口

print("等待接收RTT数据...")
while True:
    data, addr = sock.recvfrom(65535)
    print(f"收到数据: {data.decode('utf-8', errors='replace')}")
```

## 故障排除

- **如果使用过程中，MCU进行调试，工具则会异常，需要点击停止后重新启用，即可正常使用**
- 确保JLink设备已正确连接
- 验证目标设备类型是否正确
- 检查RTT是否已在目标设备上启用
- 确认UDP端口没有被防火墙阻止
- 如果无法自动找到RTT控制块，尝试手动指定RTT控制块地址
- 检查日志输出以获取更详细的错误信息

## 许可

MIT
