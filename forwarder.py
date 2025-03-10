#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据转发器模块
负责RTT数据到UDP的转发
"""

import time
import logging
import threading

class RTTUDPForwarder:
    def __init__(self, rtt_manager, udp_manager, config):
        self.rtt_manager = rtt_manager
        self.udp_manager = udp_manager
        self.config = config
        self.running = False
        self.thread = None
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """启动转发"""
        if self.running:
            self.logger.warning("转发服务已经在运行")
            return False
        
        # 启动转发线程
        self.running = True
        self.thread = threading.Thread(target=self._forward_loop)
        self.thread.daemon = True
        self.thread.start()
        
        self.logger.info("RTT到UDP转发服务已启动")
        return True
    
    def stop(self):
        """停止转发"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        
        self.logger.info("RTT到UDP转发服务已停止")
    
    def _forward_loop(self):
        """转发数据的主循环"""
        buffer_index = self.config.rtt_buffer_index
        
        try:
            while self.running:
                # 读取RTT数据
                data = self.rtt_manager.read_data(buffer_index)
                
                if data:
                    # 发送数据到UDP
                    self.udp_manager.send_data(data)
                    
                    if self.config.debug:
                        try:
                            self.logger.debug(f"转发数据: {data.decode('utf-8', errors='replace')}")
                        except:
                            self.logger.debug(f"转发二进制数据: {len(data)} 字节")
                
                # 短暂休眠以避免CPU占用过高
                time.sleep(self.config.polling_interval)
        except Exception as e:
            self.logger.error(f"数据转发过程中发生错误: {str(e)}")
            self.running = False
