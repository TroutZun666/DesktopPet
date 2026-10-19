import sys
import random
import math
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction
from PyQt5.QtGui import QPixmap, QTransform, QPainter, QColor, QFont, QPainterPath
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

# 说话参数
TALK_INTERVAL_MIN = 8000       
TALK_INTERVAL_MAX = 20000      

# ================= 台词库 =================
# 1. 闲置时随机说的废话
IDLE_QUOTES = [
    "今天也是摸鱼的一天~",
    "咕噜咕噜...",
    "肚子饿了，想吃小鱼干...",
    "你在忙什么呢？",
    "好困，想睡觉了 zzz",
    "要一起玩吗？",
    "我可是最可爱的桌面宠物！",
    "水好少，我要干涸了..."
]

# 2. 特定场景触发的专属台词
SCENE_QUOTES = {
    "drag": [      # 被鼠标按住的瞬间
        "哇啊！你要干嘛！",
        "放、放开我！",
        "救命呀！被抓住了！"
    ],
    "land": [      # 从高处落地（被甩飞后）的瞬间
        "不要甩我啦，头晕！",
        "哎哟...我的屁股...",
        "落地满分！",
        "再也不飞了，好可怕..."
    ],
    "turn": [      # 走到屏幕边缘被迫掉头的瞬间
        "哎呀，没路了...",
        "这里过不去啦。",
        "碰壁了..."
    ]
}
# ============================================

class SpeechBubble(QWidget):
    """气泡窗口类"""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool | 
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.text = ""
        self.arrow_pos = 0.5  
        
        self.font = QFont("Microsoft YaHei", 10, QFont.Bold)
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def show_text(self, text, duration=3000):
        self.text = text
        self.hide_timer.stop()
        
        font_metrics = self.fontMetrics()
        text_width = font_metrics.horizontalAdvance(self.text)
        text_height = font_metrics.height()
        
        self.bubble_width = max(text_width + 30, 80) 
        self.bubble_height = text_height + 20
        self.tail_height = 10 
        
        self.resize(int(self.bubble_width), int(self.bubble_height + self.tail_height))
        
        self.show()
        self.update() 
        self.hide_timer.start(duration)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        bg_color = QColor(255, 255, 255, 240)
        border_color = QColor(100, 150, 200)

        path = QPainterPath()
        rect_width = self.width()
        rect_height = self.height() - self.tail_height
        
        path.addRoundedRect(0, 0, rect_width, rect_height, 10, 10)
        
        tail_x = rect_width * self.arrow_pos
        path.moveTo(tail_x - 8, rect_height)
        path.lineTo(tail_x, self.height())
        path.lineTo(tail_x + 8, rect_height)
        path.closeSubpath()

        painter.setPen(border_color)
        painter.setBrush(bg_color)
        painter.drawPath(path)

        painter.setPen(QColor(50, 50, 50))
        painter.setFont(self.font)
        painter.drawText(0, 0, rect_width, rect_height, Qt.AlignCenter, self.text)


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel(self)
        
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

        # 初始化气泡和说话定时器
        self.bubble = SpeechBubble()
        self.talk_timer = QTimer(self)
        self.talk_timer.timeout.connect(self.random_speak)
        self.reset_talk_timer()

        self.game_loop = QTimer(self)
        self.game_loop.timeout.connect(self.update_physics)
        self.game_loop.start(16)

    def reset_talk_timer(self):
        next_time = random.randint(TALK_INTERVAL_MIN, TALK_INTERVAL_MAX)
        self.talk_timer.start(next_time)

    def random_speak(self):
        """闲置时的随机说话"""
        if self.state == "idle" and self.ai_action == "standing":
            text = random.choice(IDLE_QUOTES)
            self.bubble.show_text(text, duration=random.randint(2000, 4000))
        self.reset_talk_timer()

    def force_speak(self, text_list):
        """
        【新增功能】特定场景强制说话
        打断随机计时器，强制播放专属台词
        """
        text = random.choice(text_list)
        # 落地等场景说的话，展示时间稍微长一点
        self.bubble.show_text(text, duration=2500)
        # 因为刚说了话，重置一下下一次随机说话的时间
        self.reset_talk_timer()

    def update_bubble_position(self):
        if self.bubble.isVisible():
            bubble_x = self.pos_x + (self.width() / 2) - (self.bubble.width() / 2)
            bubble_y = self.pos_y - self.bubble.height() - 5
            
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
                    # ---- 场景2：被甩飞落地 ----
                    self.vy = 0
                    self.vx = 0
                    self.state = "idle"
                    self.ai_action = "standing"
                    self.action_timer = random.randint(STAND_TIME_MIN, STAND_TIME_MAX)
                    
                    # 如果是从高处掉落（比如高度差大于50），才会触发抱怨
                    if hasattr(self, 'fall_start_y') and self.fall_start_y - self.floor_y > 50:
                        self.force_speak(SCENE_QUOTES["land"])
                    # ----------------------------
            
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
                
                # 左右边缘碰撞
                if self.pos_x <= self.screen_rect.left():
                    self.pos_x = self.screen_rect.left()
                    self.walk_direction = 1
                    self.set_direction(self.walk_direction)
                    # ---- 场景3：走到边缘掉头 ----
                    self.force_speak(SCENE_QUOTES["turn"])
                    # ----------------------------
                elif self.pos_x >= self.screen_rect.right() - self.width():
                    self.pos_x = self.screen_rect.right() - self.width()
                    self.walk_direction = -1
                    self.set_direction(self.walk_direction)
                    # ---- 场景3：走到边缘掉头 ----
                    self.force_speak(SCENE_QUOTES["turn"])
                    # ----------------------------
                
                self.walk_bounce += 0.2
                bounce_y = abs(math.sin(self.walk_bounce)) * 10 
                
                self.move(int(self.pos_x), int(self.floor_y - bounce_y))

        self.update_bubble_position()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.state = "dragging"
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.last_mouse_pos = event.globalPos()
            self.drag_vx = 0.0
            self.drag_vy = 0.0
            
            # ---- 场景1：被鼠标抓起来 ----
            # 记录被抓起的起始高度，用于判断是否是从高处落下
            self.fall_start_y = self.pos_y
            self.force_speak(SCENE_QUOTES["drag"])
            # ----------------------------
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