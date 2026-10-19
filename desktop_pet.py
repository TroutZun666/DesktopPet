import sys
import random
import math
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction
from PyQt5.QtGui import QPixmap, QTransform, QPainter, QColor, QFont, QPainterPath
from PyQt5.QtCore import Qt, QTimer, QPoint

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

# 说话参数 (单位：毫秒)
TALK_INTERVAL_MIN = 8000       # 最短多久说一次话 (8秒)
TALK_INTERVAL_MAX = 20000      # 最长多久说一次话 (20秒)

# 台词库 (你可以随意添加或修改)
QUOTES = [
    "今天也是摸鱼的一天~",
    "咕噜咕噜...",
    "肚子饿了，想吃小鱼干...",
    "你在忙什么呢？",
    "不要戳我啦！",
    "好困，想睡觉了 zzz",
    "要一起玩吗？",
    "我可是最可爱的桌面宠物！",
    "水好少，我要干涸了...",
    "不要甩我啦，头晕！"
]
# ============================================

class SpeechBubble(QWidget):
    """气泡窗口类"""
    def __init__(self):
        super().__init__()
        # 窗口设置：无边框、置顶、工具窗口、鼠标穿透(防止挡住鼠标操作)
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool | 
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.text = ""
        self.arrow_pos = 0.5  # 小尾巴在气泡上的相对位置 (0~1)
        
        # 字体设置
        self.font = QFont("Microsoft YaHei", 10, QFont.Bold)
        
        # 自动隐藏定时器
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def show_text(self, text, duration=3000):
        self.text = text
        self.hide_timer.stop()
        
        # 动态计算气泡大小 (根据文字长度)
        font_metrics = self.fontMetrics()
        text_width = font_metrics.horizontalAdvance(self.text)
        text_height = font_metrics.height()
        
        # 气泡的宽度和高度 (加上内边距)
        self.bubble_width = max(text_width + 30, 80) 
        self.bubble_height = text_height + 20
        self.tail_height = 10 # 小尾巴高度
        
        # 设置窗口总大小 (气泡高度 + 尾巴高度)
        self.resize(int(self.bubble_width), int(self.bubble_height + self.tail_height))
        
        self.show()
        self.update() # 触发重绘
        self.hide_timer.start(duration)

    def paintEvent(self, event):
        """手绘漫画风格气泡"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 气泡背景颜色 (白底，带点淡蓝色边框)
        bg_color = QColor(255, 255, 255, 240)
        border_color = QColor(100, 150, 200)

        # 1. 绘制圆角矩形
        path = QPainterPath()
        rect_width = self.width()
        rect_height = self.height() - self.tail_height
        
        # 添加圆角矩形 (圆角半径为10)
        path.addRoundedRect(0, 0, rect_width, rect_height, 10, 10)
        
        # 2. 绘制下方的小三角尾巴 (指向宠物头顶)
        tail_x = rect_width * self.arrow_pos
        path.moveTo(tail_x - 8, rect_height)
        path.lineTo(tail_x, self.height())
        path.lineTo(tail_x + 8, rect_height)
        path.closeSubpath()

        # 填充和描边
        painter.setPen(border_color)
        painter.setBrush(bg_color)
        painter.drawPath(path)

        # 3. 绘制文字
        painter.setPen(QColor(50, 50, 50))
        painter.setFont(self.font)
        # 文字居中
        painter.drawText(0, 0, rect_width, rect_height, Qt.AlignCenter, self.text)

class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel(self)
        
        # 准备图片
        self.pixmap_left = QPixmap(IMAGE_PATH).scaledToHeight(TARGET_HEIGHT, Qt.SmoothTransformation)
        transform = QTransform().scale(-1, 1)
        self.pixmap_right = self.pixmap_left.transformed(transform)
        
        self.label.setPixmap(self.pixmap_left)
        self.resize(self.pixmap_left.size())

        self.screen_rect = QApplication.primaryScreen().availableGeometry()
        self.floor_y = self.screen_rect.height() - self.height()

        self.pos_x = float(self.screen_rect.width() - self.width() - 200)
        self.pos_y = float(self.floor_y)
        self.vx = 0.0
        self.vy = 0.0
        
        self.state = "idle"        
        self.ai_action = "standing" 
        self.action_timer = random.randint(STAND_TIME_MIN, STAND_TIME_MAX)
        self.current_direction = -1  
        self.walk_direction = -1     
        self.walk_bounce = 0.0      

        self.drag_position = None
        self.last_mouse_pos = None
        self.drag_vx = 0.0
        self.drag_vy = 0.0

        self.idle_offset = 0.0
        self.idle_direction = 1

        self.move(int(self.pos_x), int(self.pos_y))

        # ================= 初始化气泡和说话定时器 =================
        self.bubble = SpeechBubble()
        self.talk_timer = QTimer(self)
        self.talk_timer.timeout.connect(self.random_speak)
        self.reset_talk_timer() # 启动说话倒计时
        # ==========================================================

        # 核心帧循环
        self.game_loop = QTimer(self)
        self.game_loop.timeout.connect(self.update_physics)
        self.game_loop.start(16)

    def reset_talk_timer(self):
        """重置下一次说话的时间"""
        next_time = random.randint(TALK_INTERVAL_MIN, TALK_INTERVAL_MAX)
        self.talk_timer.start(next_time)

    def random_speak(self):
        """触发随机说话"""
        # 只有在闲置且不是正在拖拽时说话
        if self.state == "idle":
            text = random.choice(QUOTES)
            self.bubble.show_text(text, duration=random.randint(2000, 4000))
        
        # 重新设定下一次说话的时间
        self.reset_talk_timer()

    def update_bubble_position(self):
        """让气泡始终跟在宠物头顶"""
        if self.bubble.isVisible():
            # 气泡水平居中于宠物
            bubble_x = self.pos_x + (self.width() / 2) - (self.bubble.width() / 2)
            # 气泡垂直位于宠物头顶上方一点
            bubble_y = self.pos_y - self.bubble.height() - 5
            
            # 防止气泡超出屏幕左右边缘
            if bubble_x < 0:
                bubble_x = 0
            elif bubble_x + self.bubble.width() > self.screen_rect.width():
                bubble_x = self.screen_rect.width() - self.bubble.width()
                
            self.bubble.move(int(bubble_x), int(bubble_y))

    def set_direction(self, direction):
        if direction == self.current_direction:
            return 
        self.current_direction = direction
        if direction == 1: 
            self.label.setPixmap(self.pixmap_right)
        else:              
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
                    self.walk_direction = random.choice([-1, 1])
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
                
                if self.pos_x <= self.screen_rect.left():
                    self.pos_x = self.screen_rect.left()
                    self.walk_direction = 1
                    self.set_direction(self.walk_direction)
                elif self.pos_x >= self.screen_rect.right() - self.width():
                    self.pos_x = self.screen_rect.right() - self.width()
                    self.walk_direction = -1
                    self.set_direction(self.walk_direction)
                
                self.walk_bounce += 0.2
                bounce_y = abs(math.sin(self.walk_bounce)) * 10 
                
                self.move(int(self.pos_x), int(self.floor_y - bounce_y))

        # 每一帧更新完宠物位置后，同步更新气泡位置
        self.update_bubble_position()

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
            # 拖拽时气泡跟随
            self.update_bubble_position()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            if self.pos_y < self.floor_y - 5:
                self.state = "falling"
                self.vx = self.drag_vx * DRAG_INERTIA
                self.vy = self.drag_vy * DRAG_INERTIA
                
                if abs(self.vx) > 5:
                    new_dir = 1 if self.vx > 0 else -1
                    self.set_direction(new_dir)
                # 如果被甩飞，打断当前说话
                self.bubble.hide() 
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