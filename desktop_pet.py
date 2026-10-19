import sys
import random
import math
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction
from PyQt5.QtGui import QPixmap, QTransform  # 引入 QTransform 用于翻转图片
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
WALK_SPEED = 1.5               
STAND_TIME_MIN = 180           
STAND_TIME_MAX = 600           
WALK_TIME_MIN = 120            
WALK_TIME_MAX = 300            
# ============================================

class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel(self)
        
        # ================= 核心修改：准备两个方向的图片 =================
        # 1. 原图（假设原图默认朝左）
        self.pixmap_left = QPixmap(IMAGE_PATH).scaledToHeight(TARGET_HEIGHT, Qt.SmoothTransformation)
        
        # 2. 水平翻转图（朝右）
        transform = QTransform().scale(-1, 1) # 沿Y轴翻转
        self.pixmap_right = self.pixmap_left.transformed(transform)
        
        # 默认显示原图
        self.label.setPixmap(self.pixmap_left)
        self.resize(self.pixmap_left.size())
        # ================================================================

        self.screen_rect = QApplication.primaryScreen().availableGeometry()
        self.floor_y = self.screen_rect.height() - self.height()

        self.pos_x = float(self.screen_rect.width() - self.width() - 200)
        self.pos_y = float(self.floor_y)
        self.vx = 0.0
        self.vy = 0.0
        
        self.state = "idle"        
        
        # AI 变量
        self.ai_action = "standing" 
        self.action_timer = random.randint(STAND_TIME_MIN, STAND_TIME_MAX)
        self.current_direction = -1  # 当前朝向：-1 为左，1 为右
        self.walk_direction = -1     
        self.walk_bounce = 0.0      

        # 拖拽变量
        self.drag_position = None
        self.last_mouse_pos = None
        self.drag_vx = 0.0
        self.drag_vy = 0.0

        # 浮动变量
        self.idle_offset = 0.0
        self.idle_direction = 1

        self.move(int(self.pos_x), int(self.pos_y))

        self.game_loop = QTimer(self)
        self.game_loop.timeout.connect(self.update_physics)
        self.game_loop.start(16)

    def set_direction(self, direction):
        """根据方向切换图片"""
        if direction == self.current_direction:
            return # 方向没变就不重复渲染
            
        self.current_direction = direction
        if direction == 1: # 向右
            self.label.setPixmap(self.pixmap_right)
        else:              # 向左
            self.label.setPixmap(self.pixmap_left)

    def update_physics(self):
        if self.state == "falling":
            self.vy += GRAVITY
            self.vx *= AIR_FRICTION
            self.pos_x += self.vx
            self.pos_y += self.vy

            if self.pos_x <= self.screen_rect.left():
                self.pos_x = self.screen_rect.left()
                self.vx = -self.vx * BOUNCE_FACTOR
            elif self.pos_x >= self.screen_rect.right() - self.width():
                self.pos_x = self.screen_rect.right() - self.width()
                self.vx = -self.vx * BOUNCE_FACTOR

            if self.pos_y >= self.floor_y:
                self.pos_y = self.floor_y
                if abs(self.vy) > MIN_BOUNCE_SPEED:
                    self.vy = -self.vy * BOUNCE_FACTOR
                else:
                    self.vy = 0
                    self.vx = 0
                    self.state = "idle"
                    self.ai_action = "standing"
                    self.action_timer = random.randint(STAND_TIME_MIN, STAND_TIME_MAX)
            
            self.move(int(self.pos_x), int(self.pos_y))

        elif self.state == "idle":
            self.action_timer -= 1
            
            if self.action_timer <= 0:
                if self.ai_action == "standing":
                    self.ai_action = "walking"
                    # 随机决定新方向
                    self.walk_direction = random.choice([-1, 1])
                    # 切换图像
                    self.set_direction(self.walk_direction) 
                    self.action_timer = random.randint(WALK_TIME_MIN, WALK_TIME_MAX)
                else:
                    self.ai_action = "standing"
                    self.action_timer = random.randint(STAND_TIME_MIN, STAND_TIME_MAX)
                    self.idle_offset = 0 

            if self.ai_action == "standing":
                self.idle_offset += self.idle_direction * 0.5
                if abs(self.idle_offset) > 6:
                    self.idle_direction *= -1
                self.move(int(self.pos_x), int(self.floor_y + self.idle_offset))
                
            elif self.ai_action == "walking":
                self.pos_x += WALK_SPEED * self.walk_direction
                
                # 撞到边缘掉头
                if self.pos_x <= self.screen_rect.left():
                    self.pos_x = self.screen_rect.left()
                    self.walk_direction = 1
                    self.set_direction(self.walk_direction) # 掉头时翻转图像
                elif self.pos_x >= self.screen_rect.right() - self.width():
                    self.pos_x = self.screen_rect.right() - self.width()
                    self.walk_direction = -1
                    self.set_direction(self.walk_direction) # 掉头时翻转图像
                
                self.walk_bounce += 0.2
                bounce_y = abs(math.sin(self.walk_bounce)) * 10 
                
                self.move(int(self.pos_x), int(self.floor_y - bounce_y))

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
                
                # 可选：如果被甩出去的速度很快，可以自动面朝飞行的方向
                if abs(self.vx) > 5:
                    new_dir = 1 if self.vx > 0 else -1
                    self.set_direction(new_dir)
                    
            else:
                self.pos_x = float(self.x())
                self.pos_y = float(self.floor_y)
                self.state = "idle"
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