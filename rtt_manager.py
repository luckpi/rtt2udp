#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RTT管理器模块
负责与JLink设备通信和RTT控制
"""

import time
import logging
import pylink

class RTTManager:
    def __init__(self, config):
        self.config = config
        self.jlink = None
        self.logger = logging.getLogger(__name__)
    
    def connect(self, serial_number):
        """连接到JLink设备"""
        try:
            if self.jlink:
                self.jlink.close()
            
            # 连接JLink
            self.jlink = pylink.JLink()
            self.jlink.open(serial_no=serial_number)
            
            # 设置设备类型
            if not self.config.target_device:
                raise ValueError("未选择目标设备")
            
            # 连接到目标设备
            self.jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
            self.jlink.connect(self.config.target_device)
            
            # 等待设备运行
            self.logger.info("等待目标设备运行...")
            time.sleep(1)
            
            # 启动RTT
            self._setup_rtt()
            
            return True
        except Exception as e:
            self.logger.error(f"连接目标设备失败: {str(e)}")
            self.disconnect()
            return False
    
    def _setup_rtt(self):
        """设置RTT"""
        for i in range(5):  # 最多重试5次
            try:
                if self.config.rtt_ctrl_block_addr > 0:
                    # 直接设置模式
                    self.logger.info(f"使用指定的控制块地址: 0x{self.config.rtt_ctrl_block_addr:X}")
                    self.jlink.rtt_control_block_address = self.config.rtt_ctrl_block_addr
                    self.jlink.rtt_start()
                else:
                    # 搜索模式
                    search_range = (self.config.rtt_search_start, 
                                  self.config.rtt_search_start + self.config.rtt_search_length)
                    self.logger.info(f"搜索控制块，起始地址: 0x{search_range[0]:X}, "
                                   f"结束地址: 0x{search_range[1]:X}, "
                                   f"步长: {self.config.rtt_search_step}")
                    
                    # 设置搜索参数
                    self.jlink.rtt_region_start = search_range[0]
                    self.jlink.rtt_region_end = search_range[1]
                    self.jlink.rtt_search_step = self.config.rtt_search_step
                    
                    # 启动RTT搜索
                    self.jlink.rtt_start()
                    
                    # 等待控制块被找到
                    if not self._wait_for_control_block():
                        raise Exception("未找到RTT控制块")
                
                # 验证缓冲区
                self._verify_buffers()
                return
            except Exception as e:
                if i == 4:  # 最后一次尝试失败
                    raise e
                self.logger.warning(f"RTT启动失败，正在重试({i+1}/5): {str(e)}")
                time.sleep(0.5)
    
    def _wait_for_control_block(self, timeout=5):
        """等待RTT控制块被找到"""
        self.logger.info("等待RTT控制块被找到...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 尝试获取控制块地址
                addr = self.jlink.rtt_control_block_address
                if addr > 0:
                    self.logger.info(f"找到RTT控制块，地址: 0x{addr:X}")
                    return True
                
                # 检查是否还在搜索
                if not self.jlink.rtt_is_searching():
                    # 搜索已完成但未找到控制块
                    if addr == 0:
                        self.logger.warning("搜索完成，未找到RTT控制块")
                        return False
                    # 搜索完成且找到控制块
                    self.logger.info(f"找到RTT控制块，地址: 0x{addr:X}")
                    return True
            except Exception as e:
                self.logger.debug(f"等待RTT控制块时发生错误: {str(e)}")
            
            # 让出CPU时间，避免界面卡死
            time.sleep(0.1)
        
        self.logger.warning("等待RTT控制块超时")
        return False
    
    def _verify_buffers(self):
        """验证RTT缓冲区"""
        buffer_count = self.jlink.rtt_get_num_up_buffers()
        self.logger.info(f"发现 {buffer_count} 个上行缓冲区")
        if buffer_count == 0:
            raise Exception("未找到RTT缓冲区")
        
        if self.config.rtt_buffer_index >= buffer_count:
            self.logger.warning(f"缓冲区索引 {self.config.rtt_buffer_index} 超出范围，已重置为0")
            self.config.rtt_buffer_index = 0
            return 0
        return self.config.rtt_buffer_index
    
    def read_data(self, buffer_index, size=1024):
        """读取RTT数据"""
        if not self.jlink:
            return None
        try:
            return self.jlink.rtt_read(buffer_index, size)
        except Exception as e:
            self.logger.error(f"读取RTT数据失败: {str(e)}")
            return None
    
    def disconnect(self):
        """断开连接"""
        if self.jlink:
            try:
                self.jlink.rtt_stop()
                self.jlink.close()
            except:
                pass
            finally:
                self.jlink = None
