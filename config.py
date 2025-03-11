#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RTT2UDP配置文件
"""

import json
import os

class Config:
    def __init__(self):
        # 配置文件路径
        self.config_file = os.path.join(os.path.dirname(__file__), "config.json")
        
        # JLink配置
        self.target_device = ""  # 目标设备类型，根据实际情况修改
        self.debug_interface = "SWD"  # 可选: "SWD" 或 "JTAG"
        self.debug_speed = "auto"  # 调试速度，可选: "auto"、"adaptive" 或具体数值(kHz)
        
        # RTT配置
        self.rtt_ctrl_block_addr = 0  # RTT控制块地址，0表示自动搜索
        self.rtt_buffer_index = 0  # RTT缓冲区索引，通常使用0
        self.rtt_search_start = 0x20000000  # 搜索起始地址
        self.rtt_search_length = 0x1000  # 搜索长度
        self.rtt_search_step = 4  # 搜索步长
        self.polling_interval = 0.001  # 轮询间隔，单位秒
        
        # UDP配置
        self.udp_ip = "127.0.0.1"  # UDP目标IP地址
        self.udp_port = 8888  # UDP目标端口
        self.local_port = 0  # 本地端口，0表示自动分配
        
        # 其他配置
        self.debug = False  # 是否打印调试信息
        self.auto_save = True  # 是否自动保存配置
        
        # 尝试加载配置文件
        self.load()
    
    @property
    def rtt_search_range(self):
        """获取搜索范围"""
        return (self.rtt_search_start, self.rtt_search_start + self.rtt_search_length)
    
    def save(self):
        """保存配置到文件"""
        self.save_config()
        
    def save_config(self):
        """保存配置到文件"""
        try:
            config_data = {
                "target_device": self.target_device,
                "debug_interface": self.debug_interface,
                "debug_speed": self.debug_speed,
                "rtt_ctrl_block_addr": self.rtt_ctrl_block_addr,
                "rtt_buffer_index": self.rtt_buffer_index,
                "rtt_search_start": self.rtt_search_start,
                "rtt_search_length": self.rtt_search_length,
                "rtt_search_step": self.rtt_search_step,
                "polling_interval": self.polling_interval,
                "udp_ip": self.udp_ip,
                "udp_port": self.udp_port,
                "local_port": self.local_port,
                "debug": self.debug,
                "auto_save": self.auto_save
            }
            
            with open(self.config_file, 'w', encoding="utf-8") as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {str(e)}")
    
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
                    self.rtt_search_start = config_data.get("rtt_search_start", self.rtt_search_start)
                    self.rtt_search_length = config_data.get("rtt_search_length", self.rtt_search_length)
                    self.rtt_search_step = config_data.get("rtt_search_step", self.rtt_search_step)
                    self.polling_interval = config_data.get("polling_interval", self.polling_interval)
                    self.udp_ip = config_data.get("udp_ip", self.udp_ip)
                    self.udp_port = config_data.get("udp_port", self.udp_port)
                    self.local_port = config_data.get("local_port", self.local_port)
                    self.debug = config_data.get("debug", self.debug)
                    self.auto_save = config_data.get("auto_save", self.auto_save)
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
