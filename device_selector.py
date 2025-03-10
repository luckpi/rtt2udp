#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JLink设备选择对话框
"""

import tkinter as tk
from tkinter import ttk
import pylink
import tkinter.messagebox
import logging

class DeviceSelector(tk.Toplevel):
    def __init__(self, parent, logger=None):
        super().__init__(parent)
        
        self.title("选择目标设备")
        self.geometry("800x600")
        self.minsize(800, 600)
        
        # 设置模态对话框
        self.transient(parent)
        self.grab_set()
        
        # 存储选择的设备
        self.selected_device = None
        self.logger = logger or logging.getLogger(__name__)
        
        # 获取JLink支持的设备列表
        try:
            self.jlink = pylink.JLink()
            self.devices = self.get_supported_devices()
        except Exception as e:
            self.devices = {}
            self.logger.error(f"获取设备列表失败: {str(e)}")
            tkinter.messagebox.showerror("错误", f"获取设备列表失败: {str(e)}")
        
        # 创建界面
        self.create_widgets()
        
        # 填充设备列表
        self.populate_devices()
        
        # 居中显示
        self.center_window()
    
    def get_supported_devices(self):
        """获取JLink支持的设备列表"""
        devices = {}
        core_map = {}  # 用于存储Core值到内核类型的映射
        
        try:
            # 获取支持的设备数量
            num_devices = self.jlink.num_supported_devices()
            self.logger.info(f"JLink支持的设备总数: {num_devices}")
            
            # 第一遍扫描：获取所有内核类型的映射
            for i in range(num_devices):
                device_info = self.jlink.supported_device(i)
                
                # 获取设备名称
                device_name = device_info.sName
                if isinstance(device_name, bytes):
                    device_name = device_name.decode('utf-8', errors='replace')
                elif hasattr(device_name, '_type_'):  # 处理ctypes字符指针
                    import ctypes
                    if device_name:
                        device_name = ctypes.string_at(device_name).decode('utf-8', errors='replace')
                    else:
                        device_name = "-"
                
                # 获取制造商信息
                manufacturer = device_info.sManu
                if isinstance(manufacturer, bytes):
                    manufacturer = manufacturer.decode('utf-8', errors='replace')
                elif hasattr(manufacturer, '_type_'):  # 处理ctypes字符指针
                    import ctypes
                    if manufacturer:
                        manufacturer = ctypes.string_at(manufacturer).decode('utf-8', errors='replace')
                    else:
                        manufacturer = "-"
                
                # 如果制造商是Unspecified，说明这是内核类型
                if manufacturer == "Unspecified":
                    core_map[device_info.Core] = device_name
                    self.logger.debug(f"找到内核类型映射: {device_name} -> Core={device_info.Core}")
            
            self.logger.info(f"找到 {len(core_map)} 个内核类型映射")
            
            # 第二遍扫描：处理所有设备
            for i in range(num_devices):
                device_info = self.jlink.supported_device(i)
                
                # 获取设备名称
                device_name = device_info.sName
                if isinstance(device_name, bytes):
                    device_name = device_name.decode('utf-8', errors='replace')
                elif hasattr(device_name, '_type_'):  # 处理ctypes字符指针
                    import ctypes
                    if device_name:
                        device_name = ctypes.string_at(device_name).decode('utf-8', errors='replace')
                    else:
                        device_name = "-"
                
                # 获取制造商信息
                manufacturer = device_info.sManu
                if isinstance(manufacturer, bytes):
                    manufacturer = manufacturer.decode('utf-8', errors='replace')
                elif hasattr(manufacturer, '_type_'):  # 处理ctypes字符指针
                    import ctypes
                    if manufacturer:
                        manufacturer = ctypes.string_at(manufacturer).decode('utf-8', errors='replace')
                    else:
                        manufacturer = "-"
                
                # 如果是内核类型设备，归类到"内核类型"分类下
                if manufacturer == "Unspecified":
                    manufacturer = "内核类型"
                # 否则，如果制造商为空或未知，尝试从设备名称判断
                elif not manufacturer or manufacturer == "-":
                    if device_name.startswith("STM32"):
                        manufacturer = "STMicroelectronics"
                    elif device_name.startswith("nRF"):
                        manufacturer = "Nordic Semiconductor"
                    elif device_name.startswith("LPC"):
                        manufacturer = "NXP"
                    elif device_name.startswith("ATSAM"):
                        manufacturer = "Microchip"
                    else:
                        manufacturer = "其他"
                
                # 获取内核类型
                core_name = core_map.get(device_info.Core, "-")
                if core_name == "-":
                    self.logger.debug(f"未找到设备 {device_name} 的内核类型映射 (Core={device_info.Core})")
                
                # 获取Flash和RAM大小
                flash_size = device_info.FlashSize
                ram_size = device_info.RAMSize
                
                device_detail = {
                    'name': device_name,
                    'core': core_name if manufacturer != "内核类型" else "-",
                    'flash': flash_size // 1024 if flash_size else 0,  # 转换为KB
                    'ram': ram_size // 1024 if ram_size else 0  # 转换为KB
                }
                
                # 将设备添加到对应的制造商类别中
                if manufacturer not in devices:
                    devices[manufacturer] = []
                devices[manufacturer].append(device_detail)
            
            # 对每个制造商的设备列表进行排序
            for manufacturer in devices:
                devices[manufacturer].sort(key=lambda x: x['name'])
            
            self.logger.info(f"设备列表获取成功，共有 {len(devices)} 个制造商")
            return devices
        except Exception as e:
            self.logger.error(f"获取设备列表失败: {str(e)}")
            tkinter.messagebox.showerror("错误", f"获取设备列表失败: {str(e)}")
            return {}
        finally:
            try:
                self.jlink.close()
            except:
                pass
    
    def create_widgets(self):
        """创建界面组件"""
        # 搜索框
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 设备树形视图
        self.tree = ttk.Treeview(self, selectmode='browse')
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 设置列
        self.tree["columns"] = ("core", "flash", "ram")
        self.tree.column("#0", width=300, minwidth=200)
        self.tree.column("core", width=150, minwidth=100)
        self.tree.column("flash", width=100, minwidth=80)
        self.tree.column("ram", width=100, minwidth=80)
        
        # 设置列标题
        self.tree.heading("#0", text="设备名称")
        self.tree.heading("core", text="内核")
        self.tree.heading("flash", text="Flash (KB)")
        self.tree.heading("ram", text="RAM (KB)")
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 按钮区域
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="确定", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.on_cancel).pack(side=tk.RIGHT)
    
    def populate_devices(self, search_text=""):
        """填充设备列表"""
        # 清空现有项目
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 添加制造商和设备
        for manufacturer, device_list in self.devices.items():
            # 过滤设备列表
            filtered_devices = [dev for dev in device_list 
                              if search_text.lower() in dev['name'].lower()]
            
            if filtered_devices:
                manufacturer_id = self.tree.insert("", "end", text=manufacturer)
                for device in filtered_devices:
                    self.tree.insert(manufacturer_id, "end", text=device['name'],
                                   values=(device['core'],
                                          f"{device['flash']:,}" if device['flash'] else "-",
                                          f"{device['ram']:,}" if device['ram'] else "-"))
        
        # 如果有搜索文本，展开所有节点
        if search_text:
            for item in self.tree.get_children():
                self.tree.item(item, open=True)
    
    def on_search(self, *args):
        """搜索框内容变化时的处理函数"""
        self.populate_devices(self.search_var.get())
    
    def on_ok(self):
        """确定按钮处理函数"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            # 如果选中的是设备而不是制造商
            if self.tree.parent(selection[0]):
                self.selected_device = item["text"]
                self.logger.info(f"已选择设备: {self.selected_device}")
                self.destroy()
    
    def on_cancel(self):
        """取消按钮处理函数"""
        self.selected_device = None
        self.logger.info("取消选择设备")
        self.destroy()
    
    def center_window(self):
        """将窗口居中显示"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    @staticmethod
    def show_dialog(parent, logger=None):
        """显示设备选择对话框"""
        dialog = DeviceSelector(parent, logger)
        dialog.wait_window()
        return dialog.selected_device
