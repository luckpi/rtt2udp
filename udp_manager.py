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
            self.logger.info(f"UDP socket已创建，目标地址: {self.config.udp_ip}:{self.config.udp_port}")
            return True
        except Exception as e:
            self.logger.error(f"创建UDP socket失败: {str(e)}")
            return False
    
    def send_data(self, data):
        """发送数据"""
        if not self.socket or not data:
            return False
        
        try:
            self.socket.sendto(data, (self.config.udp_ip, self.config.udp_port))
            return True
        except Exception as e:
            self.logger.error(f"发送数据失败: {str(e)}")
            return False
    
    def close(self):
        """关闭socket"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            finally:
                self.socket = None
