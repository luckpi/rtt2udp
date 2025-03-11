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
        
        # 转发服务状态
        self.forwarding_active = False
    
    def start_conversion(self):
        """启动转发服务"""
        # 获取JLink序列号
        serial = self.gui_manager.get_selected_jlink_serial()
        if not serial:
            self.logger.error("未选择有效的JLink设备")
            return False
        
        # 连接RTT，传入连接丢失回调
        if not self.rtt_manager.connect(serial, on_connection_lost=self.on_connection_lost):
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
        
        # 更新转发状态
        self.forwarding_active = True
        
        return True
    
    def stop_conversion(self):
        """停止转发服务"""
        self.forwarding_active = False
        self.forwarder.stop()
        self.udp_manager.close()
        self.rtt_manager.disconnect()
        return True
    
    def on_connection_lost(self):
        """连接丢失回调函数"""
        self.logger.warning("检测到JLink连接丢失，自动停止转发服务")
        
        # 如果转发服务正在运行，则停止
        if self.forwarding_active:
            # 使用tkinter的after方法确保在主线程中执行UI更新
            self.root.after(0, self._handle_connection_lost)
    
    def _handle_connection_lost(self):
        """在主线程中处理连接丢失"""
        # 停止转发服务
        self.stop_conversion()
        
        # 更新UI状态
        self.gui_manager.update_ui_on_stop()
        
        # 显示提示信息
        self.gui_manager.show_info("JLink连接已断开，转发服务已自动停止")
    
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
