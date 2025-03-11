import pylink
import time
import logging
import re


def extract_serial_numbers(text):
    """从文本中提取序列号"""
    pattern = r"Serial No\. (\d+)"
    matches = re.findall(pattern, text)
    return matches


class RTTManager:
    def __init__(self, config):
        self.config = config
        self.jlink = None
        self.logger = logging.getLogger("RTTManager")
        
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

    def connect(self, serial_number):
        """连接到JLink设备"""
        try:
            if self.jlink:
                self.jlink.close()
            
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
                    self.jlink.set_speed(speed_khz)
                    self.logger.info(f"设置调试速度为 {speed_khz} kHz")
                    # 连接到目标设备
                    self.jlink.connect(self.config.target_device)
                except ValueError:
                    self.logger.warning(f"无效的调试速度值: {speed}，使用auto模式")
                    self.jlink.connect(self.config.target_device, "auto")
            
            self.logger.info(f"已连接到目标设备 {self.config.target_device}")
            
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

    def disconnect(self):
        """断开JLink连接"""
        try:
            if self.jlink:
                self.jlink.rtt_stop()
                self.jlink.close()
                self.jlink = None
            self.logger.info("已断开JLink连接")
        except Exception as e:
            self.logger.error(f"断开连接失败: {str(e)}")

    def is_connected(self):
        """检查是否已连接JLink"""
        return self.jlink and self.jlink.connected()

    def target_connected(self):
        """检查是否已连接目标设备"""
        if not self.is_connected():
            return False
        return self.jlink.target_connected()

    def get_supported_devices(self):
        """获取支持的设备列表"""
        try:
            if not self.jlink:
                self.jlink = pylink.JLink()
            num_devices = self.jlink.num_supported_devices()
            devices = [self.jlink.supported_device(i) for i in range(num_devices)]
            return devices
        except Exception as e:
            self.logger.error(f"获取设备列表失败: {str(e)}")
            return []

    def _setup_rtt(self):
        """设置RTT"""
        try:
            if self.config.rtt_ctrl_block_addr:
                # 使用指定地址
                self.jlink.rtt_start(self.config.rtt_ctrl_block_addr)
                self.logger.info(f"RTT已启动，控制块地址: 0x{self.config.rtt_ctrl_block_addr:08X}")
            else:
                # 自动搜索RTT控制块
                self.jlink.rtt_region_start = self.config.rtt_search_start
                self.jlink.rtt_region_end = self.config.rtt_search_start + self.config.rtt_search_length
                self.jlink.rtt_search_step = self.config.rtt_search_step
                self.logger.info(f"正在搜索RTT控制块，范围: 0x{self.jlink.rtt_region_start:08X} - 0x{self.jlink.rtt_region_end:08X}")
                self.jlink.rtt_start()
                
                # 等待搜索完成
                for _ in range(50):  # 最多等待5秒
                    try:
                        # 尝试读取数据，如果成功说明RTT已就绪
                        data = self.jlink.rtt_read(self.config.rtt_buffer_index, 1)
                        if data is not None:
                            self.logger.info("RTT控制块搜索完成")
                            return
                    except:
                        pass
                    time.sleep(0.1)
                self.logger.warning("未找到RTT控制块")
        except Exception as e:
            self.logger.error(f"RTT启动失败: {str(e)}")
            raise

    def read_data(self, buffer_index=None, size=1024):
        """从RTT缓冲区读取数据"""
        try:
            if buffer_index is None:
                buffer_index = self.config.rtt_buffer_index
            data = self.jlink.rtt_read(buffer_index, size)
            if data:
                # 将列表转换为字节
                return bytes(data)
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
