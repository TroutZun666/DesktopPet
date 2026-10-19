import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer

# ================= 配置参数 =================
IMAGE_PATH = "pet.png"        # 你的透明背景图片路径
TARGET_HEIGHT = 250           # 宠物高度像素

GRAVITY = 1.5                 # 重力加速度 (越大掉落越快)
MAX_FALL_SPEED = 30           # 最大下落速度限制 (防止掉太快穿模)
# ============================================

class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        
        # 1. 窗口基础设置
        self.setWindowFlags(
            Qt.FramelessWindowHint |      
            Qt.WindowStaysOnTopHint |     
            Qt.Tool                       
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 2. 加载并缩放图片
        self.label = QLabel(self)
        self.pixmap = QPixmap(IMAGE_PATH)
        self.pixmap = self.pixmap.scaledToHeight(TARGET_HEIGHT, Qt.SmoothTransformation)
        self.label.setPixmap(self.pixmap)
        self.resize(self.pixmap.size())

        # 3. 获取屏幕边界 (Dock栏边界)
        screen = QApplication.primaryScreen().availableGeometry()
        self.floor_y = screen.height() - self.height() # 宠物站在地面的Y坐标

        # 4. 物理与状态变量
        self.state = "idle"        # 状态: idle(闲置), dragging(拖拽), falling(下落)
        self.velocity_y = 0        # 垂直下落速度
        self.drag_position = None
        
        # 浮动动画变量
        self.idle_offset = 0
        self.idle_direction = 1

        # 5. 初始位置
        self.base_x = screen.width() - self.width() - 200 
        self.base_y = self.floor_y
        self.move(self.base_x, self.base_y)

        # 6. 核心帧循环 (16ms 约等于 60帧/秒，保证物理动画流畅)
        self.game_loop = QTimer(self)
        self.game_loop.timeout.connect(self.update_physics)
        self.game_loop.start(16)

    def update_physics(self):
        """核心帧循环逻辑"""
        if self.state == "falling":
            # 增加下落速度
            self.velocity_y = min(self.velocity_y + GRAVITY, MAX_FALL_SPEED)
            
            # 计算新的Y坐标
            new_y = self.y() + self.velocity_y
            
            # 落地检测
            if new_y >= self.floor_y:
                new_y = self.floor_y
                self.velocity_y = 0
                self.state = "idle"  # 落地后恢复站立
                self.base_y = self.floor_y
                self.idle_offset = 0 # 重置浮动
                
            self.move(self.x(), int(new_y))
            
        elif self.state == "idle":
            # 闲置时的呼吸浮动动画
            self.idle_offset += self.idle_direction * 1
            if abs(self.idle_offset) > 8:
                self.idle_direction *= -1
            
            self.move(self.base_x, self.base_y + self.idle_offset)

    # --- 鼠标交互事件 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.state = "dragging"
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.state == "dragging":
            # 更新位置
            new_pos = event.globalPos() - self.drag_position
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            
            # 松开鼠标时，判断当前高度
            if self.y() < self.floor_y:
                self.state = "falling"  # 如果在半空中，触发下落
                self.velocity_y = 0     # 初始下落速度为0
            else:
                self.state = "idle"     # 如果就在地上，直接恢复站立
                self.base_y = self.floor_y
                self.move(self.x(), self.floor_y)
                
            # 更新 X 轴基准坐标，让它在掉落后的水平位置继续浮动
            self.base_x = self.x()
            event.accept()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        quit_action = QAction("退下吧，鱼鱼", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        menu.exec_(pos)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())