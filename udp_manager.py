#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UDP管理器模块
负责UDP通信
"""

import socket
import logging

class UDPManager:
    def __init__(self, config):
        self.config = config
        self.socket = None
        self.logger = logging.getLogger(__name__)
    
    def setup(self):
        """设置UDP socket"""
        try:
            if self.socket:
                self.close()
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # 设置socket选项以提高性能
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)  # 增大发送缓冲区
            
            # 绑定到指定或随机端口
            local_port = self.config.local_port
            self.socket.bind(('0.0.0.0', local_port))
            local_addr = self.socket.getsockname()
            
            # 预先保存目标地址，避免每次发送时重新创建
            self.target_addr = (self.config.udp_ip, self.config.udp_port)
            
            self.logger.info(f"UDP socket已创建")
            self.logger.info(f"本地地址: {local_addr[0]}:{local_addr[1]}")
            self.logger.info(f"目标地址: {self.config.udp_ip}:{self.config.udp_port}")
            return True
        except Exception as e:
            self.logger.error(f"创建UDP socket失败: {str(e)}")
            return False
    
    def send_data(self, data):
        """发送数据"""
        if not self.socket or not data:
            return False
        
        try:
            self.socket.sendto(data, self.target_addr)
            return True
        except Exception as e:
            self.logger.error(f"发送数据失败: {str(e)}")
            return False
    
    def close(self):
        """关闭UDP socket"""
        try:
            if self.socket:
                self.logger.info("关闭UDP socket...")
                try:
                    self.socket.close()
                except Exception as e:
                    self.logger.error(f"关闭UDP socket失败: {str(e)}")
                finally:
                    self.socket = None
                    self.logger.info("UDP socket已关闭")
        except Exception as e:
            self.logger.error(f"关闭UDP socket过程中发生错误: {str(e)}")
