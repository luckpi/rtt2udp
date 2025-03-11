#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RTT2UDP主程序
集成GUI、RTT和UDP管理器，实现RTT数据到UDP的转发
"""

import tkinter as tk
import logging
import os
from config import Config
from rtt_manager import RTTManager
from udp_manager import UDPManager
from forwarder import RTTUDPForwarder
from gui_manager import GUIManager

class RTT2UDPApplication:
    def __init__(self):
        # 创建配置
        self.config = Config()
        
        # 创建根窗口
        self.root = tk.Tk()
        
        # 初始化日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 创建管理器
        self.rtt_manager = RTTManager(self.config)
        self.udp_manager = UDPManager(self.config)
        self.forwarder = RTTUDPForwarder(self.rtt_manager, self.udp_manager, self.config)
        self.gui_manager = GUIManager(
            self.root,
            self.config,
            on_start=self.start_conversion,
            on_stop=self.stop_conversion
        )
    
    def start_conversion(self):
        """启动转发服务"""
        # 获取JLink序列号
        serial = self.gui_manager.get_selected_jlink_serial()
        if not serial:
            self.logger.error("未选择有效的JLink设备")
            return False
        
        # 连接RTT
        if not self.rtt_manager.connect(serial):
            return False
        
        # 设置UDP
        if not self.udp_manager.setup():
            self.rtt_manager.disconnect()
            return False
        
        # 启动转发
        if not self.forwarder.start():
            self.udp_manager.close()
            self.rtt_manager.disconnect()
            return False
        
        return True
    
    def stop_conversion(self):
        """停止转发服务"""
        self.forwarder.stop()
        self.udp_manager.close()
        self.rtt_manager.disconnect()
        return True
    
    def on_closing(self):
        """窗口关闭处理"""
        # 确保停止所有转发服务
        self.stop_conversion()
        self.gui_manager.on_closing()
        # 手动销毁窗口
        self.root.destroy()
        
    def run(self):
        """运行应用程序"""
        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

def main():
    app = RTT2UDPApplication()
    app.run()

if __name__ == "__main__":
    main()
