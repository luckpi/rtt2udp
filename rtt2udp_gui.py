#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JLink RTT to UDP转换器 - GUI版本
提供图形界面，可以选择JLink设备、目标设备，并配置UDP端口
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import logging
import queue
import time
import pylink
import socket
from config import Config
from device_selector import DeviceSelector
from rtt_manager import extract_rtt_address_from_map

# 配置日志
class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)

class RTT2UDPApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RTT2UDP 转换器")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        self.config = Config()
        self.jlink = None
        self.udp_socket = None
        self.running = False
        self.connected = False
        self.thread = None
        
        # 创建日志队列和处理器
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        self.queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # 配置根日志记录器
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.queue_handler)
        
        # 创建UI
        self.create_ui()
        
        # 启动日志处理线程
        self.log_thread_running = True
        self.log_thread = threading.Thread(target=self.process_log_queue)
        self.log_thread.daemon = True
        self.log_thread.start()
        
        # 获取可用的JLink设备
        self.refresh_jlink_devices()
        
        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 创建菜单栏
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
    
    def create_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建配置框架
        config_frame = ttk.LabelFrame(main_frame, text="配置", padding="10")
        config_frame.pack(fill=tk.X, pady=5)
        
        # JLink设备选择
        ttk.Label(config_frame, text="JLink设备:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.jlink_device_var = tk.StringVar()
        self.jlink_device_combo = ttk.Combobox(config_frame, textvariable=self.jlink_device_var, state="readonly", width=40)
        self.jlink_device_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
        ttk.Button(config_frame, text="刷新", command=self.refresh_jlink_devices).grid(row=0, column=2, padx=5, pady=5)
        
        # 目标设备选择
        ttk.Label(config_frame, text="目标设备:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.target_device_var = tk.StringVar(value=self.config.target_device)
        self.target_device_entry = ttk.Entry(config_frame, textvariable=self.target_device_var, width=40)
        self.target_device_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Button(config_frame, text="选择设备", command=self.select_target_device).grid(row=1, column=2, padx=5, pady=5)
        self.target_device_var.trace_add("write", self.on_device_selected)
        
        # RTT配置
        rtt_frame = ttk.LabelFrame(config_frame, text="RTT配置", padding="5")
        rtt_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W+tk.E, pady=5)
        
        # 基本RTT配置
        basic_rtt_frame = ttk.Frame(rtt_frame)
        basic_rtt_frame.grid(row=0, column=0, columnspan=4, sticky=tk.W+tk.E, pady=2)
        
        # RTT缓冲区索引
        ttk.Label(basic_rtt_frame, text="缓冲区索引:").pack(side=tk.LEFT, padx=5)
        self.rtt_buffer_index_var = tk.IntVar(value=self.config.rtt_buffer_index)
        ttk.Spinbox(basic_rtt_frame, from_=0, to=10, textvariable=self.rtt_buffer_index_var, width=5, command=self.on_rtt_config_change).pack(side=tk.LEFT, padx=5)
        
        # RTT控制块配置模式
        ttk.Label(basic_rtt_frame, text="控制块模式:").pack(side=tk.LEFT, padx=5)
        self.rtt_mode_var = tk.StringVar(value="search" if self.config.rtt_ctrl_block_addr == 0 else "direct")
        ttk.Radiobutton(basic_rtt_frame, text="直接设置", variable=self.rtt_mode_var, value="direct", command=self.on_rtt_mode_change).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(basic_rtt_frame, text="搜索模式", variable=self.rtt_mode_var, value="search", command=self.on_rtt_mode_change).pack(side=tk.LEFT, padx=2)
        
        # 控制块地址（直接设置模式）
        self.direct_frame = ttk.Frame(rtt_frame)
        self.direct_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W+tk.E, pady=2)
        ttk.Label(self.direct_frame, text="控制块地址:").pack(side=tk.LEFT, padx=5)
        self.rtt_ctrl_block_addr_var = tk.StringVar(value=hex(self.config.rtt_ctrl_block_addr))
        ttk.Entry(self.direct_frame, textvariable=self.rtt_ctrl_block_addr_var, width=20).pack(side=tk.LEFT, padx=5)
        self.rtt_ctrl_block_addr_var.trace_add("write", self.on_rtt_config_change)
        
        # 添加从map文件加载按钮
        ttk.Button(self.direct_frame, text="从Map文件加载", command=self.load_from_map_file).pack(side=tk.LEFT, padx=5)
        
        # 搜索参数（搜索模式）
        self.search_frame = ttk.Frame(rtt_frame)
        self.search_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W+tk.E, pady=2)
        
        # 搜索起始地址
        start_frame = ttk.Frame(self.search_frame)
        start_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(start_frame, text="起始地址:").pack(side=tk.LEFT)
        self.rtt_search_start_var = tk.StringVar(value=hex(self.config.rtt_search_start))
        ttk.Entry(start_frame, textvariable=self.rtt_search_start_var, width=10).pack(side=tk.LEFT, padx=2)
        
        # 搜索长度
        length_frame = ttk.Frame(self.search_frame)
        length_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(length_frame, text="搜索长度:").pack(side=tk.LEFT)
        self.rtt_search_length_var = tk.StringVar(value=hex(self.config.rtt_search_length))
        ttk.Entry(length_frame, textvariable=self.rtt_search_length_var, width=10).pack(side=tk.LEFT, padx=2)
        
        # 搜索步长
        step_frame = ttk.Frame(self.search_frame)
        step_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(step_frame, text="步长:").pack(side=tk.LEFT)
        self.rtt_search_step_var = tk.IntVar(value=self.config.rtt_search_step)
        step_values = [1, 2, 4, 8, 16]
        ttk.OptionMenu(step_frame, self.rtt_search_step_var, self.config.rtt_search_step, *step_values).pack(side=tk.LEFT, padx=5)
        
        self.rtt_search_start_var.trace_add("write", self.on_rtt_config_change)
        self.rtt_search_length_var.trace_add("write", self.on_rtt_config_change)
        self.rtt_search_step_var.trace_add("write", self.on_rtt_config_change)
        
        # 根据当前模式显示/隐藏相应的框架
        self.on_rtt_mode_change()
        
        # UDP配置
        udp_frame = ttk.LabelFrame(config_frame, text="UDP配置", padding="5")
        udp_frame.grid(row=3, column=0, columnspan=3, sticky=tk.W+tk.E, pady=5)
        
        ttk.Label(udp_frame, text="IP地址:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.udp_ip_var = tk.StringVar(value=self.config.udp_ip)
        ttk.Entry(udp_frame, textvariable=self.udp_ip_var, width=15).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        self.udp_ip_var.trace_add("write", self.on_udp_config_change)
        
        ttk.Label(udp_frame, text="端口:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=5)
        self.udp_port_var = tk.IntVar(value=self.config.udp_port)
        ttk.Spinbox(udp_frame, from_=1024, to=65535, textvariable=self.udp_port_var, width=7, command=self.on_udp_config_change).grid(row=0, column=3, sticky=tk.W, pady=5, padx=5)
        
        # 轮询间隔
        ttk.Label(config_frame, text="轮询间隔(秒):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.polling_interval_var = tk.DoubleVar(value=self.config.polling_interval)
        ttk.Spinbox(config_frame, from_=0.001, to=1.0, increment=0.01, textvariable=self.polling_interval_var, width=5, command=self.on_rtt_config_change).grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # 调试模式和自动保存
        options_frame = ttk.Frame(config_frame)
        options_frame.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        self.debug_var = tk.BooleanVar(value=self.config.debug)
        ttk.Checkbutton(options_frame, text="调试模式", variable=self.debug_var, command=self.on_debug_mode_change).grid(row=0, column=0, sticky=tk.W, padx=5)
        
        self.auto_save_var = tk.BooleanVar(value=self.config.auto_save)
        ttk.Checkbutton(options_frame, text="自动保存配置", variable=self.auto_save_var, command=self.on_auto_save_change).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 控制按钮
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        self.start_button = ttk.Button(control_frame, text="启动", command=self.start_conversion)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="停止", command=self.stop_conversion, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(control_frame, textvariable=self.status_var)
        status_label.pack(side=tk.RIGHT, padx=5)
        ttk.Label(control_frame, text="状态:").pack(side=tk.RIGHT)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 添加初始日志
        self.logger.info("RTT2UDP转换器已启动，请配置参数并点击'启动'按钮")
    
    def refresh_jlink_devices(self):
        try:
            # 获取连接的JLink设备
            jlink_temp = pylink.JLink()
            connected_devices = jlink_temp.connected_emulators()
            jlink_temp.close()
            
            if connected_devices:
                devices = []
                for device in connected_devices:
                    device_str = f"{device.acProduct} (S/N: {device.SerialNumber})"
                    devices.append(device_str)
                
                self.jlink_device_combo['values'] = devices
                if devices:
                    self.jlink_device_combo.current(0)
                self.logger.info(f"找到 {len(devices)} 个JLink设备")
            else:
                self.jlink_device_combo['values'] = ["未找到JLink设备"]
                self.jlink_device_combo.current(0)
                self.logger.warning("未找到JLink设备，请连接JLink并刷新")
        except Exception as e:
            self.logger.error(f"刷新JLink设备列表失败: {str(e)}")
            self.jlink_device_combo['values'] = ["刷新失败"]
            self.jlink_device_combo.current(0)
    
    def process_log_queue(self):
        """处理日志队列的线程"""
        while self.log_thread_running:
            try:
                record = self.log_queue.get(block=False)
                self.display_log(record)
            except queue.Empty:
                self.root.after(100, self.process_logs)
                break
    
    def process_logs(self):
        """处理队列中的日志记录"""
        try:
            while True:
                record = self.log_queue.get(block=False)
                self.display_log(record)
        except queue.Empty:
            pass
        
        if self.log_thread_running:
            self.root.after(100, self.process_logs)
    
    def display_log(self, record):
        """将日志记录显示到文本框"""
        msg = self.queue_handler.format(record)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + '\n')
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # 根据日志级别设置颜色
        if record.levelno >= logging.ERROR:
            self.log_text.tag_add("error", "end-{}c linestart".format(len(msg) + 1), "end-1c")
            self.log_text.tag_config("error", foreground="red")
        elif record.levelno >= logging.WARNING:
            self.log_text.tag_add("warning", "end-{}c linestart".format(len(msg) + 1), "end-1c")
            self.log_text.tag_config("warning", foreground="orange")
        elif record.levelno >= logging.INFO:
            self.log_text.tag_add("info", "end-{}c linestart".format(len(msg) + 1), "end-1c")
            self.log_text.tag_config("info", foreground="blue")
    
    def update_config_from_ui(self):
        """从UI更新配置"""
        self.config.target_device = self.target_device_var.get()
        self.config.rtt_buffer_index = self.rtt_buffer_index_var.get()
        self.config.udp_ip = self.udp_ip_var.get()
        self.config.udp_port = self.udp_port_var.get()
        self.config.polling_interval = self.polling_interval_var.get()
        self.config.debug = self.debug_var.get()
    
    def connect_jlink(self):
        """连接到JLink设备"""
        # 获取连接的JLink设备
        selected_device = self.jlink_device_var.get()
        if "未找到" in selected_device or "刷新失败" in selected_device:
            self.logger.error("未选择有效的JLink设备")
            return False
        
        if self.jlink:
            self.jlink.close()
        
        # 解析序列号
        serial_number = selected_device.split("S/N: ")[1].split(")")[0]
        
        # 创建新的JLink对象并指定序列号
        import pylink
        self.jlink = pylink.JLink()
        
        try:
            # 连接JLink设备
            self.jlink.open()
            
            # 设置设备类型
            target_device = self.config.target_device
            if not target_device:
                self.logger.error("未选择目标设备")
                return False
            
            try:
                # 连接到目标设备
                self.jlink.connect(target_device)
                
                # 设置RTT
                self.logger.info("正在启动RTT...")
                
                # 设置RTT控制块参数
                if self.config.rtt_ctrl_block_addr > 0:
                    self.logger.info(f"使用指定的控制块地址: 0x{self.config.rtt_ctrl_block_addr:X}")
                    self.jlink.rtt_set_control_block(self.config.rtt_ctrl_block_addr)
                else:
                    self.logger.info(f"搜索控制块，起始地址: 0x{self.config.rtt_search_start:X}, 长度: 0x{self.config.rtt_search_length:X}, 步长: {self.config.rtt_search_step}")
                    self.jlink.rtt_set_search_range(self.config.rtt_search_start, self.config.rtt_search_start + self.config.rtt_search_length)
                    self.jlink.rtt_set_search_step(self.config.rtt_search_step)
                
                # 尝试启动RTT，最多重试5次
                max_retries = 5
                retry_count = 0
                rtt_started = False
                
                while retry_count < max_retries:
                    try:
                        self.jlink.rtt_start()
                        rtt_started = True
                        break
                    except Exception as e:
                        if "Control Block has not yet been found" in str(e):
                            retry_count += 1
                            if retry_count < max_retries:
                                self.logger.info(f"未找到RTT控制块，正在重试({retry_count}/{max_retries})...")
                                time.sleep(1)  # 等待1秒后重试
                            continue
                        else:
                            raise e
                
                if not rtt_started:
                    self.logger.error("RTT启动失败，未找到控制块")
                    return False
                
                # 等待RTT启动
                timeout = 10  # 10秒超时
                start_time = time.time()
                while not self.jlink.rtt_get_num_up_buffers() and time.time() - start_time < timeout:
                    time.sleep(0.1)
                
                if not self.jlink.rtt_get_num_up_buffers():
                    self.logger.error("RTT启动失败，未找到上行缓冲区")
                    return False
                
                # 如果找到了控制块，保存地址供下次使用
                if rtt_started and self.config.rtt_ctrl_block_addr == 0:
                    found_addr = self.jlink.rtt_get_control_block_addr()
                    if found_addr > 0:
                        self.config.rtt_ctrl_block_addr = found_addr
                        self.config.save_config()
                        self.rtt_ctrl_block_addr_var.set(hex(found_addr))
                        self.logger.info(f"已找到RTT控制块，地址: 0x{found_addr:X}")
                
                self.logger.info(f"JLink连接成功，找到 {self.jlink.rtt_get_num_up_buffers()} 个上行缓冲区")
                return True
            except Exception as e:
                self.logger.error(f"连接目标设备失败: {str(e)}")
                return False
        except Exception as e:
            self.logger.error(f"连接JLink设备失败: {str(e)}")
            if self.jlink:
                try:
                    self.jlink.close()
                except:
                    pass
                self.jlink = None
            return False
    
    def setup_udp(self):
        """设置UDP socket"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.logger.info(f"UDP socket已创建，目标地址: {self.config.udp_ip}:{self.config.udp_port}")
            return True
        except Exception as e:
            self.logger.error(f"创建UDP socket失败: {str(e)}")
            return False
    
    def start_conversion(self):
        """启动RTT到UDP的转发"""
        # 更新配置
        self.update_config_from_ui()
        
        if self.running:
            self.logger.warning("转发服务已经在运行")
            return
        
        # 连接JLink
        if not self.connect_jlink():
            return
        
        # 设置UDP
        if not self.setup_udp():
            if self.jlink:
                try:
                    self.jlink.close()
                except:
                    pass
                self.jlink = None
                self.connected = False
            return
        
        # 启动转发线程
        self.running = True
        self.thread = threading.Thread(target=self._forward_data)
        self.thread.daemon = True
        self.thread.start()
        
        # 更新UI状态
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("运行中")
        
        self.logger.info("RTT到UDP转发服务已启动")
    
    def stop_conversion(self):
        """停止转发服务"""
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        
        if self.jlink:
            try:
                self.jlink.rtt_stop()
                self.jlink.close()
            except:
                pass
            self.jlink = None
            self.connected = False
        
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
            self.udp_socket = None
        
        # 更新UI状态
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("已停止")
        
        self.logger.info("RTT到UDP转发服务已停止")
    
    def _forward_data(self):
        """转发RTT数据到UDP的主循环"""
        buffer_index = self.config.rtt_buffer_index
        
        try:
            while self.running:
                # 读取RTT数据
                data = self.jlink.rtt_read(buffer_index, 1024)
                
                if data:
                    # 发送数据到UDP
                    self.udp_socket.sendto(data, (self.config.udp_ip, self.config.udp_port))
                    
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
            
            # 更新UI状态（在主线程中）
            self.root.after(0, self.update_ui_after_error)
    
    def update_ui_after_error(self):
        """在发生错误后更新UI状态"""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("错误")
    
    def select_target_device(self):
        """打开设备选择对话框"""
        device = DeviceSelector.show_dialog(self.root, self.logger)
        if device:
            self.target_device_var.set(device)
            self.logger.info(f"已选择目标设备: {device}")
    
    def on_closing(self):
        """窗口关闭事件处理"""
        if self.running:
            if messagebox.askokcancel("退出", "转发服务正在运行，确定要退出吗？"):
                self.stop_conversion()
                self.log_thread_running = False
                self.root.destroy()
        else:
            self.log_thread_running = False
            self.root.destroy()
    
    def on_device_selected(self, *args):
        """设备选择回调"""
        selected_device = self.target_device_var.get()
        if selected_device:
            self.config.target_device = selected_device
            self.config.save_config()
            self.logger.info(f"已选择设备: {selected_device}")
    
    def on_udp_config_change(self, *args):
        """UDP配置更改回调"""
        try:
            ip = self.udp_ip_var.get()
            port = int(self.udp_port_var.get())
            
            # 验证IP地址格式
            try:
                socket.inet_aton(ip)
            except:
                self.logger.error("无效的IP地址格式")
                return
            
            # 验证端口范围
            if port < 1 or port > 65535:
                self.logger.error("端口号必须在1-65535之间")
                return
            
            self.config.udp_ip = ip
            self.config.udp_port = port
            self.config.save_config()
            self.logger.info(f"UDP配置已更新: {ip}:{port}")
        except ValueError:
            self.logger.error("端口号必须是数字")
    
    def on_rtt_config_change(self, *args):
        """RTT配置更改回调"""
        try:
            # 更新缓冲区索引
            self.config.rtt_buffer_index = self.rtt_buffer_index_var.get()
            
            # 更新控制块地址
            addr_str = self.rtt_ctrl_block_addr_var.get()
            if addr_str.startswith("0x"):
                self.config.rtt_ctrl_block_addr = int(addr_str, 16)
            else:
                self.config.rtt_ctrl_block_addr = int(addr_str)
            
            # 更新搜索参数
            start_str = self.rtt_search_start_var.get()
            if start_str.startswith("0x"):
                self.config.rtt_search_start = int(start_str, 16)
            else:
                self.config.rtt_search_start = int(start_str)
            
            length_str = self.rtt_search_length_var.get()
            if length_str.startswith("0x"):
                self.config.rtt_search_length = int(length_str, 16)
            else:
                self.config.rtt_search_length = int(length_str)
            
            self.config.rtt_search_step = self.rtt_search_step_var.get()
            
            # 保存配置
            if self.config.auto_save:
                self.config.save_config()
        except ValueError as e:
            self.logger.error(f"配置更新失败: {str(e)}")
    
    def on_rtt_mode_change(self):
        """RTT控制块配置模式更改回调"""
        mode = self.rtt_mode_var.get()
        if mode == "direct":
            self.direct_frame.grid()
            self.search_frame.grid_remove()
            # 如果之前是搜索模式，清除搜索参数
            if self.config.rtt_ctrl_block_addr == 0:
                self.config.rtt_ctrl_block_addr = 0x20000000  # 设置一个默认地址
                self.rtt_ctrl_block_addr_var.set(hex(self.config.rtt_ctrl_block_addr))
        else:
            self.direct_frame.grid_remove()
            self.search_frame.grid()
            # 如果之前是直接模式，清除控制块地址
            if self.config.rtt_ctrl_block_addr != 0:
                self.config.rtt_ctrl_block_addr = 0
                self.rtt_ctrl_block_addr_var.set("0x0")
        
        # 保存配置
        self.config.save_config()
        self.logger.info(f"RTT控制块配置模式已切换为: {'直接设置' if mode == 'direct' else '搜索模式'}")
    
    def on_debug_mode_change(self):
        """调试模式更改回调"""
        self.config.debug = self.debug_var.get()
        self.config.save_config()
        self.logger.info(f"调试模式已更新: {'启用' if self.config.debug else '禁用'}")
    
    def on_auto_save_change(self):
        """自动保存选项更改回调"""
        was_auto_save = self.config.auto_save
        self.config.auto_save = self.auto_save_var.get()
        
        # 强制保存自动保存选项的改变
        if was_auto_save or self.config.auto_save:
            self.config.save_config()
        
        self.logger.info(f"自动保存配置已{'启用' if self.config.auto_save else '禁用'}")
    
    def load_from_map_file(self):
        """从map文件加载RTT控制块地址"""
        file_path = filedialog.askopenfilename(
            title="选择Map文件",
            filetypes=[("Map文件", "*.map"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        self.logger.info(f"正在从Map文件加载RTT控制块地址: {file_path}")
        
        # 提取RTT控制块地址
        address = extract_rtt_address_from_map(file_path)
        
        if address > 0:
            # 更新UI和配置
            self.rtt_ctrl_block_addr_var.set(hex(address))
            self.config.rtt_ctrl_block_addr = address
            self.rtt_mode_var.set("direct")
            self.on_rtt_mode_change()
            
            if self.config.auto_save:
                self.config.save_config()
                
            self.logger.info(f"成功从Map文件提取RTT控制块地址: 0x{address:X}")
        else:
            messagebox.showerror("错误", "无法从Map文件中提取RTT控制块地址，请检查文件格式是否正确。")
            self.logger.error("无法从Map文件中提取RTT控制块地址")

def main():
    """主函数"""
    root = tk.Tk()
    app = RTT2UDPApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
