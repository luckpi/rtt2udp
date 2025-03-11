#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RTT2UDP配置文件
"""

import json
import os
import sys
import logging
from pathlib import Path

class Config:
    def __init__(self):
        # 设置应用程序名称
        self.app_name = "RTT2UDP"
        
        # 配置文件路径
        self.config_file = self._get_config_path()
        
        # 确保配置目录存在
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # 创建日志记录器
        self.logger = logging.getLogger(__name__)
        
        # JLink配置
        self.target_device = ""  # 目标设备类型，根据实际情况修改
        self.debug_interface = "SWD"  # 可选: "SWD" 或 "JTAG"
        self.debug_speed = "auto"  # 调试速度，可选: "auto"、"adaptive" 或具体数值(kHz)
        
        # RTT配置
        self.rtt_ctrl_block_addr = 0  # RTT控制块地址
        self.rtt_buffer_index = 0  # RTT缓冲区索引，通常使用0
        self.rtt_mode = "manual"  # RTT控制块模式，可选: "manual" 或 "map"
        
        # Map文件配置
        self.map_file_path = ""  # Map文件路径
        
        # UDP配置
        self.udp_ip = "127.0.0.1"  # UDP目标IP地址
        self.udp_port = 8888  # UDP目标端口
        self.local_port = 0  # 本地端口，0表示自动分配
        
        # 其他配置
        self.polling_interval = 0.001  # 轮询间隔，单位秒
        self.debug = False  # 是否打印调试信息
        self.auto_save = True  # 是否自动保存配置
        
        # 尝试加载配置文件
        self.load()
    
    def _get_config_path(self):
        """获取配置文件路径
        
        根据操作系统返回适当的配置文件路径:
        - Windows: %APPDATA%\RTT2UDP\config.json
        - macOS: ~/Library/Application Support/RTT2UDP/config.json
        - Linux: ~/.config/RTT2UDP/config.json
        """
        home = Path.home()
        
        if sys.platform == "win32":
            # Windows
            config_dir = os.path.join(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")), self.app_name)
        elif sys.platform == "darwin":
            # macOS
            config_dir = str(home / "Library" / "Application Support" / self.app_name)
        else:
            # Linux/Unix
            config_dir = str(home / ".config" / self.app_name)
        
        return os.path.join(config_dir, "config.json")
    
    @property
    def rtt_search_range(self):
        """获取搜索范围"""
        return (0, 0)
    
    def save(self):
        """保存配置到文件"""
        self.save_config()
        
    def save_config(self):
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            config_data = {
                "target_device": self.target_device,
                "debug_interface": self.debug_interface,
                "debug_speed": self.debug_speed,
                "rtt_ctrl_block_addr": self.rtt_ctrl_block_addr,
                "rtt_buffer_index": self.rtt_buffer_index,
                "rtt_mode": self.rtt_mode,
                "map_file_path": self.map_file_path,
                "udp_ip": self.udp_ip,
                "udp_port": self.udp_port,
                "local_port": self.local_port,
                "polling_interval": self.polling_interval,
                "debug": self.debug,
                "auto_save": self.auto_save
            }
            
            with open(self.config_file, 'w', encoding="utf-8") as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
                
            self.logger.info(f"配置已保存到: {self.config_file}")
        except Exception as e:
            self.logger.error(f"保存配置失败: {str(e)}")
    
    def load(self):
        """从文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    
                    self.target_device = config_data.get("target_device", self.target_device)
                    self.debug_interface = config_data.get("debug_interface", self.debug_interface)
                    self.debug_speed = config_data.get("debug_speed", self.debug_speed)
                    self.rtt_ctrl_block_addr = config_data.get("rtt_ctrl_block_addr", self.rtt_ctrl_block_addr)
                    self.rtt_buffer_index = config_data.get("rtt_buffer_index", self.rtt_buffer_index)
                    self.rtt_mode = config_data.get("rtt_mode", self.rtt_mode)
                    self.map_file_path = config_data.get("map_file_path", self.map_file_path)
                    self.udp_ip = config_data.get("udp_ip", self.udp_ip)
                    self.udp_port = config_data.get("udp_port", self.udp_port)
                    self.local_port = config_data.get("local_port", self.local_port)
                    self.polling_interval = config_data.get("polling_interval", self.polling_interval)
                    self.debug = config_data.get("debug", self.debug)
                    self.auto_save = config_data.get("auto_save", self.auto_save)
                
                self.logger.info(f"已从 {self.config_file} 加载配置")
            else:
                self.logger.info(f"配置文件不存在，将使用默认配置")
        except Exception as e:
            self.logger.error(f"加载配置失败: {str(e)}")
