import sys
import random
import math
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer

# ================= 配置参数 =================
IMAGE_PATH = "pet.png"        
TARGET_HEIGHT = 250           

# 物理参数
GRAVITY = 0.8                  
AIR_FRICTION = 0.98            
BOUNCE_FACTOR = 0.6            
MIN_BOUNCE_SPEED = 2.0         
DRAG_INERTIA = 0.5             

# AI行为参数
WALK_SPEED = 1.5               # 走路速度 (像素/帧)
STAND_TIME_MIN = 180           # 站立停留最少帧数 (约3秒，按60fps算)
STAND_TIME_MAX = 600           # 站立停留最多帧数 (约10秒)
WALK_TIME_MIN = 120            # 走路最少帧数 (约2秒)
WALK_TIME_MAX = 300            # 走路最多帧数 (约5秒)
# ============================================

class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 加载图片
        self.label = QLabel(self)
        self.pixmap = QPixmap(IMAGE_PATH).scaledToHeight(TARGET_HEIGHT, Qt.SmoothTransformation)
        self.label.setPixmap(self.pixmap)
        self.resize(self.pixmap.size())

        # 获取屏幕边界
        self.screen_rect = QApplication.primaryScreen().availableGeometry()
        self.floor_y = self.screen_rect.height() - self.height()

        # 物理变量
        self.pos_x = float(self.screen_rect.width() - self.width() - 200)
        self.pos_y = float(self.floor_y)
        self.vx = 0.0
        self.vy = 0.0
        
        self.state = "idle"        # 主状态: idle, dragging, falling
        
        # AI 子状态变量
        self.ai_action = "standing" # 行为: standing(站立), walking(走动)
        self.action_timer = random.randint(STAND_TIME_MIN, STAND_TIME_MAX) # 倒计时帧数
        self.walk_direction = 1     # 1向右，-1向左
        self.walk_bounce = 0.0      # 走路时蹦跳的相位

        # 拖拽变量
        self.drag_position = None
        self.last_mouse_pos = None
        self.drag_vx = 0.0
        self.drag_vy = 0.0

        # 浮动动画变量
        self.idle_offset = 0.0
        self.idle_direction = 1

        self.move(int(self.pos_x), int(self.pos_y))

        # 核心帧循环 (16ms 约 60FPS)
        self.game_loop = QTimer(self)
        self.game_loop.timeout.connect(self.update_physics)
        self.game_loop.start(16)

    def update_physics(self):
        if self.state == "falling":
            # 物理下落逻辑 (同上一版)
            self.vy += GRAVITY
            self.vx *= AIR_FRICTION
            self.pos_x += self.vx
            self.pos_y += self.vy

            # 左右墙壁反弹
            if self.pos_x <= self.screen_rect.left():
                self.pos_x = self.screen_rect.left()
                self.vx = -self.vx * BOUNCE_FACTOR
            elif self.pos_x >= self.screen_rect.right() - self.width():
                self.pos_x = self.screen_rect.right() - self.width()
                self.vx = -self.vx * BOUNCE_FACTOR

            # 底部碰撞
            if self.pos_y >= self.floor_y:
                self.pos_y = self.floor_y
                if abs(self.vy) > MIN_BOUNCE_SPEED:
                    self.vy = -self.vy * BOUNCE_FACTOR
                else:
                    self.vy = 0
                    self.vx = 0
                    self.state = "idle"
                    # 落地后先愣住一会儿
                    self.ai_action = "standing"
                    self.action_timer = random.randint(STAND_TIME_MIN, STAND_TIME_MAX)
            
            self.move(int(self.pos_x), int(self.pos_y))

        elif self.state == "idle":
            # ======== AI 行为逻辑 ========
            self.action_timer -= 1
            
            # 倒计时结束，切换状态
            if self.action_timer <= 0:
                if self.ai_action == "standing":
                    # 站立结束，开始走动
                    self.ai_action = "walking"
                    self.walk_direction = random.choice([-1, 1]) # 随机方向
                    self.action_timer = random.randint(WALK_TIME_MIN, WALK_TIME_MAX)
                else:
                    # 走动结束，开始站立
                    self.ai_action = "standing"
                    self.action_timer = random.randint(STAND_TIME_MIN, STAND_TIME_MAX)
                    self.idle_offset = 0 # 重置站立浮动的基准

            # ======== 执行当前行为 ========
            if self.ai_action == "standing":
                # 呼吸浮动
                self.idle_offset += self.idle_direction * 0.5
                if abs(self.idle_offset) > 6:
                    self.idle_direction *= -1
                self.move(int(self.pos_x), int(self.floor_y + self.idle_offset))
                
            elif self.ai_action == "walking":
                # 水平移动
                self.pos_x += WALK_SPEED * self.walk_direction
                
                # 走到屏幕边缘时自动掉头
                if self.pos_x <= self.screen_rect.left():
                    self.pos_x = self.screen_rect.left()
                    self.walk_direction = 1
                elif self.pos_x >= self.screen_rect.right() - self.width():
                    self.pos_x = self.screen_rect.right() - self.width()
                    self.walk_direction = -1
                
                # 模拟走路时一蹦一跳的效果 (利用正弦波)
                self.walk_bounce += 0.2
                bounce_y = abs(math.sin(self.walk_bounce)) * 10 # 跳跃高度10像素
                
                self.move(int(self.pos_x), int(self.floor_y - bounce_y))

    # --- 鼠标交互 ---
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

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.state == "dragging":
            current_mouse_pos = event.globalPos()
            if self.last_mouse_pos:
                self.drag_vx = current_mouse_pos.x() - self.last_mouse_pos.x()
                self.drag_vy = current_mouse_pos.y() - self.last_mouse_pos.y()
            
            self.last_mouse_pos = current_mouse_pos
            new_pos = current_mouse_pos - self.drag_position
            
            self.pos_x = float(new_pos.x())
            self.pos_y = float(new_pos.y())
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            if self.pos_y < self.floor_y - 5:
                self.state = "falling"
                self.vx = self.drag_vx * DRAG_INERTIA
                self.vy = self.drag_vy * DRAG_INERTIA
            else:
                self.pos_x = float(self.x())
                self.pos_y = float(self.floor_y)
                self.state = "idle"
                # 被放下后重新开始AI逻辑
                self.ai_action = "standing"
                self.action_timer = random.randint(STAND_TIME_MIN, STAND_TIME_MAX)
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