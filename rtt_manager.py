#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RTT管理器模块
负责与JLink设备通信并管理RTT连接
"""

import os
import time
import logging
import pylink
import re
import threading


def extract_serial_numbers(text):
    """从文本中提取序列号"""
    pattern = r"Serial No\. (\d+)"
    matches = re.findall(pattern, text)
    return matches


def extract_rtt_address_from_map(map_file_path):
    """从map文件中提取RTT控制块地址
    
    Args:
        map_file_path: map文件路径
        
    Returns:
        int: RTT控制块地址，如果未找到则返回0
    """
    try:
        with open(map_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            map_content = f.read()
        
        # 尝试匹配第一种格式: _SEGGER_RTT      0x20000668   Data         168  segger_rtt.o(.bss._SEGGER_RTT)
        pattern1 = r'_SEGGER_RTT\s+0x([0-9a-fA-F]+)\s+\w+\s+\d+'
        match = re.search(pattern1, map_content)
        
        if match:
            addr_hex = match.group(1)
            return int(addr_hex, 16)
        
        # 尝试匹配第二种格式: .bss._SEGGER_RTT       0x2000084c       0x14 ./Code/foc/FOC.o
        pattern2 = r'\.bss\._SEGGER_RTT\s+0x([0-9a-fA-F]+)\s+0x[0-9a-fA-F]+\s+'
        match = re.search(pattern2, map_content)
        
        if match:
            addr_hex = match.group(1)
            return int(addr_hex, 16)
        
        return 0
    except Exception as e:
        logging.getLogger(__name__).error(f"从map文件提取RTT地址失败: {str(e)}")
        return 0


class RTTManager:
    def __init__(self, config):
        self.config = config
        self.jlink = None
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self.rtt_started = False
        self.last_buffer_info = None
        self.last_buffer_check_time = 0
        self.buffer_check_interval = 0.001  # 缓冲区状态检查间隔，单位秒
        
        # 连接状态监控
        self.connection_monitor_thread = None
        self.monitoring = False
        self.connection_check_interval = 1.0  # 连接状态检查间隔，单位秒
        self.on_connection_lost = None  # 连接丢失回调函数
        
    def get_jlink_list(self):
        """获取已连接的JLink设备列表"""
        try:
            if not self.jlink:
                self.jlink = pylink.JLink()
            
            jlink_list = self.jlink.connected_emulators()
            jlink_list_sn = []
            for i in jlink_list:
                jlink_list_sn.append(extract_serial_numbers(str(i))[0])
            return jlink_list_sn
        except Exception as e:
            self.logger.error(f"获取JLink列表失败: {str(e)}")
            return []

    def connect(self, serial_number, on_connection_lost=None):
        """连接到JLink设备
        
        Args:
            serial_number: JLink设备序列号
            on_connection_lost: 连接丢失时的回调函数
        """
        try:
            if self.jlink:
                self.jlink.close()
            
            # 保存连接丢失回调
            self.on_connection_lost = on_connection_lost
            
            # 连接JLink
            self.jlink = pylink.JLink()
            self.jlink.open(serial_no=serial_number)
            self.logger.info(f"已连接到JLink设备 {serial_number}")
            
            # 设置设备类型
            if not self.config.target_device:
                raise ValueError("未选择目标设备")
            
            # 设置调试接口
            if self.config.debug_interface.upper() == "SWD":
                self.jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
                self.logger.info("使用SWD接口连接")
            else:
                self.jlink.set_tif(pylink.enums.JLinkInterfaces.JTAG)
                self.logger.info("使用JTAG接口连接")
            
            # 设置调试速度
            speed = self.config.debug_speed
            if speed in ["auto", "adaptive"]:
                self.logger.info(f"使用{speed}调试速度")
                self.jlink.connect(self.config.target_device, speed)
            else:
                try:
                    speed_khz = int(speed)
                    self.logger.info(f"设置调试速度为 {speed_khz} kHz")
                    # 连接到目标设备
                    self.jlink.connect(self.config.target_device, speed_khz)
                except ValueError:
                    self.logger.warning(f"无效的调试速度值: {speed}，使用auto模式")
                    self.jlink.connect(self.config.target_device, "auto")
            
            self.logger.info(f"已连接到目标设备 {self.config.target_device}")
            
            # 等待设备运行
            self.logger.info("等待目标设备运行...")
            time.sleep(1)
            
            # 启动RTT
            self._setup_rtt()
            
            # 启动连接状态监控
            self.connected = True
            self._start_connection_monitor()
            
            return True
        except Exception as e:
            self.logger.error(f"连接目标设备失败: {str(e)}")
            self.disconnect()
            return False

    def disconnect(self):
        """断开与JLink的连接"""
        if not self.jlink:
            return
        
        try:
            # 停止连接监控
            self._stop_connection_monitor()
            
            # 停止RTT
            if self.rtt_started:
                self.logger.info("停止RTT...")
                try:
                    self.jlink.rtt_stop()
                except Exception as e:
                    self.logger.error(f"停止RTT失败: {str(e)}")
                self.rtt_started = False
            
            # 关闭JLink连接
            self.logger.info("断开JLink连接...")
            try:
                self.jlink.close()
            except Exception as e:
                self.logger.error(f"关闭JLink连接失败: {str(e)}")
            
            # 清理资源
            self.jlink = None
            self.connected = False
            self.last_buffer_info = None
            
            self.logger.info("JLink连接已断开")
        except Exception as e:
            self.logger.error(f"断开JLink连接过程中发生错误: {str(e)}")

    def is_connected(self):
        """检查是否已连接JLink"""
        return self.jlink and self.jlink.connected()

    def target_connected(self):
        """检查是否已连接目标设备"""
        if not self.is_connected():
            return False
        try:
            return self.jlink.target_connected()
        except Exception as e:
            self.logger.error(f"检查目标设备连接状态失败: {str(e)}")
            return False

    def _start_connection_monitor(self):
        """启动连接状态监控线程"""
        if self.connection_monitor_thread and self.connection_monitor_thread.is_alive():
            return
        
        self.monitoring = True
        self.connection_monitor_thread = threading.Thread(target=self._connection_monitor_loop)
        self.connection_monitor_thread.daemon = True
        self.connection_monitor_thread.start()
        self.logger.info("已启动连接状态监控")

    def _stop_connection_monitor(self):
        """停止连接状态监控线程"""
        self.monitoring = False
        if self.connection_monitor_thread and self.connection_monitor_thread.is_alive():
            self.connection_monitor_thread.join(timeout=2.0)
            if self.connection_monitor_thread.is_alive():
                self.logger.warning("连接监控线程未能在超时时间内结束")
        self.connection_monitor_thread = None

    def _connection_monitor_loop(self):
        """连接状态监控循环"""
        last_jlink_status = True
        
        while self.monitoring and self.connected:
            try:
                # 检查JLink连接状态
                current_jlink_status = self.is_connected()
                
                # 如果JLink连接丢失
                if last_jlink_status and not current_jlink_status:
                    self.logger.warning("检测到JLink连接丢失")
                    self.logger.error("JLink连接已断开")
                    
                    # 调用连接丢失回调
                    if self.on_connection_lost:
                        self.logger.info("触发连接丢失回调")
                        self.on_connection_lost()
                    
                    # 停止监控
                    self.monitoring = False
                    break
                
                # 更新状态
                last_jlink_status = current_jlink_status
                
            except Exception as e:
                self.logger.error(f"连接监控过程中发生错误: {str(e)}")
                # 发生异常也视为连接丢失
                if self.on_connection_lost:
                    self.on_connection_lost()
                self.monitoring = False
                break
            
            # 等待下一次检查
            time.sleep(self.connection_check_interval)

    def _setup_rtt(self):
        """设置RTT"""
        try:
            # 根据RTT模式处理
            if self.config.rtt_mode == "map":
                # 如果是Map文件模式，尝试重新加载RTT地址
                if self.config.map_file_path and os.path.exists(self.config.map_file_path):
                    address = extract_rtt_address_from_map(self.config.map_file_path)
                    if address > 0:
                        self.config.rtt_ctrl_block_addr = address
                        self.logger.info(f"已从Map文件重新加载RTT控制块地址: 0x{address:X}")
                    else:
                        self.logger.error("无法从Map文件中提取RTT控制块地址")
                        raise ValueError("无法从Map文件中提取RTT控制块地址")
                else:
                    self.logger.error("Map文件路径无效或文件不存在")
                    raise ValueError("Map文件路径无效或文件不存在")
            
            # 使用指定地址启动RTT
            if self.config.rtt_ctrl_block_addr:
                # 使用指定地址
                self.jlink.rtt_start(self.config.rtt_ctrl_block_addr)
                self.logger.info(f"RTT已启动，控制块地址: 0x{self.config.rtt_ctrl_block_addr:08X}")
            else:
                self.logger.error("未设置RTT控制块地址")
                raise ValueError("未设置RTT控制块地址")
            
            # 设置RTT状态
            self.rtt_started = True
            
            return True
        except Exception as e:
            self.logger.error(f"RTT启动失败: {str(e)}")
            self.rtt_started = False
            return False

    def read_data(self):
        """读取RTT数据，返回bytes"""
        try:
            if not self.jlink:
                return None
            
            current_time = time.time()
            
            # 检查是否需要更新缓冲区状态
            if self.last_buffer_info is None or (current_time - self.last_buffer_check_time) >= self.buffer_check_interval:
                try:
                    # 尝试获取缓冲区状态
                    buffer_info = self.jlink.rtt_get_buf_status(self.config.rtt_buffer_index)
                    self.last_buffer_info = buffer_info
                    self.last_buffer_check_time = current_time
                    
                    if not buffer_info or not hasattr(buffer_info, 'buffersize_used') or buffer_info.buffersize_used <= 0:
                        # 如果无法获取缓冲区状态或没有数据，返回None
                        return None
                    
                    # 获取可读取的数据长度，最大读取128KB
                    buffered = min(buffer_info.buffersize_used, 131072)
                    self.logger.debug(f"RTT缓冲区已使用: {buffer_info.buffersize_used} 字节，读取: {buffered} 字节")
                except Exception as e:
                    self.logger.debug(f"获取RTT缓冲区状态失败: {str(e)}，使用默认读取大小")
                    buffered = 65536
            else:
                # 使用缓存的缓冲区状态
                buffer_info = self.last_buffer_info
                if not buffer_info or not hasattr(buffer_info, 'buffersize_used') or buffer_info.buffersize_used <= 0:
                    return None
                
                # 获取可读取的数据长度，最大读取128KB
                buffered = min(buffer_info.buffersize_used, 131072)
            
            # 如果没有数据需要读取，直接返回
            if buffered <= 0:
                return None
            
            # 读取数据
            data = self.jlink.rtt_read(self.config.rtt_buffer_index, buffered)
            if not data:
                return None
            
            # 转换为bytes
            if isinstance(data, list):
                # 将列表转换为bytes
                return bytes(data)
            elif isinstance(data, bytes):
                return data
            else:
                return None
        except Exception as e:
            self.logger.error(f"读取RTT数据失败: {str(e)}")
            return None

    def write(self, data, buffer_index=None):
        """写入数据到RTT缓冲区"""
        try:
            if buffer_index is None:
                buffer_index = self.config.rtt_buffer_index
            if isinstance(data, str):
                data = list(data.encode("ascii"))
            self.jlink.rtt_write(buffer_index, data)
            return True
        except Exception as e:
            self.logger.error(f"写入RTT数据失败: {str(e)}")
            return False
