import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer, QPointF

# ================= 物理参数配置 =================
IMAGE_PATH = "pet.png"        
TARGET_HEIGHT = 250           

GRAVITY = 0.8                  # 重力加速度
AIR_FRICTION = 0.98            # 空气阻力 (X轴衰减，越小停得越快)
BOUNCE_FACTOR = 0.6            # 墙壁和底部的弹性系数 (0.6表示每次反弹损失40%能量)
MIN_BOUNCE_SPEED = 2.0         # 当垂直速度小于这个值时，就不再弹跳，直接落地
DRAG_INERTIA = 0.5             # 鼠标拖拽结束时的惯性系数 (越大甩得越远)

# ============================================

class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        
        # 1. 窗口设置
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 2. 加载图片
        self.label = QLabel(self)
        self.pixmap = QPixmap(IMAGE_PATH).scaledToHeight(TARGET_HEIGHT, Qt.SmoothTransformation)
        self.label.setPixmap(self.pixmap)
        self.resize(self.pixmap.size())

        # 3. 获取屏幕边界
        self.screen_rect = QApplication.primaryScreen().availableGeometry()
        self.floor_y = self.screen_rect.height() - self.height()

        # 4. 物理变量 (使用浮点数保存精确位置，防止取整导致卡顿)
        self.pos_x = float(self.screen_rect.width() - self.width() - 200)
        self.pos_y = float(self.floor_y)
        self.vx = 0.0
        self.vy = 0.0
        
        self.state = "idle"        # idle, dragging, falling
        
        # 拖拽惯性记录
        self.drag_position = None
        self.last_mouse_pos = None
        self.drag_vx = 0.0
        self.drag_vy = 0.0

        # 浮动动画
        self.idle_offset = 0.0
        self.idle_direction = 1

        self.move(int(self.pos_x), int(self.pos_y))

        # 5. 核心帧循环 (16ms 约 60FPS)
        self.game_loop = QTimer(self)
        self.game_loop.timeout.connect(self.update_physics)
        self.game_loop.start(16)

    def update_physics(self):
        """物理引擎核心更新"""
        if self.state == "falling":
            # 1. 应用重力与空气阻力
            self.vy += GRAVITY
            self.vx *= AIR_FRICTION
            
            # 2. 计算下一帧的位置
            self.pos_x += self.vx
            self.pos_y += self.vy

            # 3. 左右边缘碰撞检测 (反弹)
            if self.pos_x <= self.screen_rect.left():
                self.pos_x = self.screen_rect.left()
                self.vx = -self.vx * BOUNCE_FACTOR
            elif self.pos_x >= self.screen_rect.right() - self.width():
                self.pos_x = self.screen_rect.right() - self.width()
                self.vx = -self.vx * BOUNCE_FACTOR

            # 4. 底部碰撞检测 (落地弹跳或静止)
            if self.pos_y >= self.floor_y:
                self.pos_y = self.floor_y
                
                # 如果下落速度较快，则反弹
                if abs(self.vy) > MIN_BOUNCE_SPEED:
                    self.vy = -self.vy * BOUNCE_FACTOR
                else:
                    # 速度太小，停止弹跳，恢复站立
                    self.vy = 0
                    self.vx = 0
                    self.state = "idle"
                    self.idle_offset = 0
            
            self.move(int(self.pos_x), int(self.pos_y))

        elif self.state == "idle":
            # 闲置时的呼吸浮动
            self.idle_offset += self.idle_direction * 0.5
            if abs(self.idle_offset) > 6:
                self.idle_direction *= -1
            
            # 记录基准位置，用于浮动
            base_y = self.screen_rect.height() - self.height()
            self.move(int(self.pos_x), int(base_y + self.idle_offset))

    # --- 鼠标交互 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.state = "dragging"
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.last_mouse_pos = event.globalPos()
            self.drag_vx = 0
            self.drag_vy = 0
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.state == "dragging":
            # 计算鼠标移动的瞬时速度 (用于松手时的惯性)
            current_mouse_pos = event.globalPos()
            if self.last_mouse_pos:
                self.drag_vx = current_mouse_pos.x() - self.last_mouse_pos.x()
                self.drag_vy = current_mouse_pos.y() - self.last_mouse_pos.y()
            
            self.last_mouse_pos = current_mouse_pos
            
            # 更新窗口位置
            new_pos = current_mouse_pos - self.drag_position
            self.pos_x = float(new_pos.x())
            self.pos_y = float(new_pos.y())
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            
            # 松手时，如果不在底部，则转为抛物线掉落
            if self.pos_y < self.floor_y - 5:
                self.state = "falling"
                # 将鼠标移动速度转化为初始物理速度 (带上惯性系数)
                self.vx = self.drag_vx * DRAG_INERTIA
                self.vy = self.drag_vy * DRAG_INERTIA
            else:
                # 如果已经在地上，直接进入闲置
                self.pos_x = float(self.x())
                self.pos_y = float(self.floor_y)
                self.state = "idle"
            event.accept()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        quit_action = QAction("退下吧，鱼鱼", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        menu.exec_(pos)

    # 右键菜单事件
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.state = "dragging"
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.last_mouse_pos = event.globalPos()
            self.drag_vx = 0.0
            self.drag_vy = 0.0
            event.accept()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPos())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())