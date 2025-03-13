#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UDP管理器模块
负责UDP通信
"""

import socket
import logging
import select

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
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)  # 增大接收缓冲区
            
            # 设置非阻塞模式
            self.socket.setblocking(False)
            
            # 绑定到指定或随机端口
            local_port = self.config.local_port
            self.socket.bind(('0.0.0.0', local_port))
            local_addr = self.socket.getsockname()
            
            # 预先保存目标地址，避免每次发送时重新创建
            self.target_addr = (self.config.udp_ip, self.config.udp_port)
            
            # 记录最后一个发送数据的地址，用于回复
            self.last_sender_addr = None
            
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
    
    def receive_data(self, timeout=0.1, max_size=8192):
        """接收UDP数据
        
        Args:
            timeout: 接收超时时间，单位秒
            max_size: 最大接收数据大小
            
        Returns:
            bytes: 接收到的数据，如果没有数据则返回None
        """
        if not self.socket:
            return None
        
        try:
            # 使用select等待数据
            readable, _, _ = select.select([self.socket], [], [], timeout)
            
            if not readable:
                return None
            
            # 接收数据
            data, addr = self.socket.recvfrom(max_size)
            
            # 记录发送方地址，用于后续回复
            self.last_sender_addr = addr
            
            return data
        except socket.error as e:
            # if e.errno != socket.errno.EAGAIN and e.errno != socket.errno.EWOULDBLOCK:
            #     self.logger.warning(f"接收数据失败: {str(e)}")
            return None
        except Exception as e:
            # self.logger.warning(f"接收数据失败: {str(e)}")
            return None
    
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
