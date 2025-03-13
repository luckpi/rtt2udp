#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据转发器模块
负责RTT数据到UDP的转发和UDP数据到RTT的转发
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
        self.read_thread = None
        self.send_thread = None
        self.data_buffer = bytearray()
        self.buffer_lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """启动转发"""
        if self.running:
            self.logger.warning("转发服务已经在运行")
            return False
        
        # 启动转发线程
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop)
        self.read_thread.daemon = True
        self.read_thread.start()
        
        self.send_thread = threading.Thread(target=self._send_loop)
        self.send_thread.daemon = True
        self.send_thread.start()
        
        self.logger.info("RTT到UDP转发服务已启动")
        return True
    
    def stop(self):
        """停止转发"""
        if not self.running:
            return
        
        # 设置停止标志
        self.running = False
        
        # 等待线程结束，使用更长的超时时间
        if self.read_thread and self.read_thread.is_alive():
            self.logger.info("等待读取线程结束...")
            self.read_thread.join(timeout=5.0)
            if self.read_thread.is_alive():
                self.logger.warning("读取线程未能在超时时间内结束")
            self.read_thread = None
        
        if self.send_thread and self.send_thread.is_alive():
            self.logger.info("等待发送线程结束...")
            self.send_thread.join(timeout=5.0)
            if self.send_thread.is_alive():
                self.logger.warning("发送线程未能在超时时间内结束")
            self.send_thread = None
        
        # 清空缓冲区
        with self.buffer_lock:
            self.data_buffer = bytearray()
        
        self.logger.info("RTT到UDP转发服务已停止")
    
    def _read_loop(self):
        """读取数据的循环"""
        try:
            while self.running:
                # 读取RTT数据
                data = self.rtt_manager.read_data()
                
                if data:
                    # 将数据添加到缓冲区
                    with self.buffer_lock:
                        self.data_buffer.extend(data)
                    
                    # 如果有数据，立即继续读取，不等待
                    continue
                
                # 短暂休眠以避免CPU占用过高
                time.sleep(self.config.polling_interval)
        except Exception as e:
            self.logger.error(f"数据读取过程中发生错误: {str(e)}")
            self.running = False
    
    def _send_loop(self):
        """发送数据的循环"""
        try:
            last_send_time = time.time()
            
            while self.running:
                current_time = time.time()
                buffer_to_send = None
                
                # 检查是否有数据需要发送
                with self.buffer_lock:
                    if len(self.data_buffer) > 0:
                        # 如果缓冲区超过阈值或距离上次发送超过时间阈值，则发送数据
                        if len(self.data_buffer) >= 8192 or (current_time - last_send_time) >= 0.005:
                            buffer_to_send = bytes(self.data_buffer)
                            self.data_buffer = bytearray()
                
                # 发送数据
                if buffer_to_send:
                    self.udp_manager.send_data(buffer_to_send)
                    last_send_time = time.time()
                
                # 短暂休眠以避免CPU占用过高
                time.sleep(0.001)
        except Exception as e:
            self.logger.error(f"数据发送过程中发生错误: {str(e)}")
            self.running = False


class UDPRTTForwarder:
    def __init__(self, rtt_manager, udp_manager, config):
        self.rtt_manager = rtt_manager
        self.udp_manager = udp_manager
        self.config = config
        self.running = False
        self.receive_thread = None
        self.data_buffer = bytearray()
        self.buffer_lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """启动UDP到RTT转发"""
        if self.running:
            self.logger.warning("UDP到RTT转发服务已经在运行")
            return False
        
        # 启动接收线程
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        self.logger.info("UDP到RTT转发服务已启动")
        return True
    
    def stop(self):
        """停止UDP到RTT转发"""
        if not self.running:
            return
        
        # 设置停止标志
        self.running = False
        
        # 等待线程结束
        if self.receive_thread and self.receive_thread.is_alive():
            self.logger.info("等待UDP接收线程结束...")
            self.receive_thread.join(timeout=5.0)
            if self.receive_thread.is_alive():
                self.logger.warning("UDP接收线程未能在超时时间内结束")
            self.receive_thread = None
        
        # 清空缓冲区
        with self.buffer_lock:
            self.data_buffer = bytearray()
        
        self.logger.info("UDP到RTT转发服务已停止")
    
    def _receive_loop(self):
        """接收UDP数据并转发到RTT的循环"""
        try:
            while self.running:
                # 接收UDP数据
                data = self.udp_manager.receive_data(timeout=0.1)
                
                if data:
                    # 将数据写入RTT
                    success = self.rtt_manager.write(data)
                    if not success:
                        self.logger.warning("写入RTT数据失败")
                
                # 短暂休眠以避免CPU占用过高
                time.sleep(0.001)
        except Exception as e:
            self.logger.error(f"UDP接收过程中发生错误: {str(e)}")
            self.running = False
