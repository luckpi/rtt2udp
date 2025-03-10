#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JLink RTT to UDP转换器
将JLink RTT数据转发到UDP端口
"""

import socket
import sys
import time
import threading
import logging
import pylink
from config import Config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RTT2UDP")

class RTT2UDP:
    def __init__(self, config):
        """
        初始化RTT2UDP转换器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.jlink = None
        self.udp_socket = None
        self.running = False
        self.connected = False
        self.thread = None
    
    def connect_jlink(self):
        """连接到JLink设备"""
        try:
            logger.info(f"正在连接JLink设备...")
            self.jlink = pylink.JLink()
            self.jlink.open()
            
            # 设置设备类型
            self.jlink.connect(self.config.target_device)
            
            # 设置RTT
            self.jlink.rtt_start()
            
            # 等待RTT启动
            timeout = 10  # 10秒超时
            start_time = time.time()
            while not self.jlink.rtt_get_num_up_buffers() and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if not self.jlink.rtt_get_num_up_buffers():
                logger.error("RTT启动失败，未找到上行缓冲区")
                return False
            
            logger.info(f"JLink连接成功，找到 {self.jlink.rtt_get_num_up_buffers()} 个上行缓冲区")
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"连接JLink设备失败: {str(e)}")
            if self.jlink:
                try:
                    self.jlink.close()
                except:
                    pass
                self.jlink = None
            return False
    
    def setup_udp(self):
        """设置UDP socket"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info(f"UDP socket已创建，目标地址: {self.config.udp_ip}:{self.config.udp_port}")
            return True
        except Exception as e:
            logger.error(f"创建UDP socket失败: {str(e)}")
            return False
    
    def start(self):
        """启动RTT到UDP的转发"""
        if self.running:
            logger.warning("转发服务已经在运行")
            return False
        
        if not self.connected and not self.connect_jlink():
            return False
        
        if not self.udp_socket and not self.setup_udp():
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._forward_data)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("RTT到UDP转发服务已启动")
        return True
    
    def stop(self):
        """停止转发服务"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        
        if self.jlink:
            try:
                self.jlink.rtt_stop()
                self.jlink.close()
            except:
                pass
            self.jlink = None
            self.connected = False
        
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
            self.udp_socket = None
        
        logger.info("RTT到UDP转发服务已停止")
    
    def _forward_data(self):
        """转发RTT数据到UDP的主循环"""
        buffer_index = self.config.rtt_buffer_index
        
        try:
            while self.running:
                # 读取RTT数据
                data = self.jlink.rtt_read(buffer_index, 1024)
                
                if data:
                    # 发送数据到UDP
                    self.udp_socket.sendto(data, (self.config.udp_ip, self.config.udp_port))
                    
                    if self.config.debug:
                        try:
                            logger.debug(f"转发数据: {data.decode('utf-8', errors='replace')}")
                        except:
                            logger.debug(f"转发二进制数据: {len(data)} 字节")
                
                # 短暂休眠以避免CPU占用过高
                time.sleep(self.config.polling_interval)
        except Exception as e:
            logger.error(f"数据转发过程中发生错误: {str(e)}")
            self.running = False

def main():
    """主函数"""
    config = Config()
    converter = RTT2UDP(config)
    
    try:
        if converter.start():
            logger.info("按Ctrl+C停止服务...")
            # 保持主线程运行
            while converter.running:
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("接收到停止信号")
    finally:
        converter.stop()

if __name__ == "__main__":
    main()
