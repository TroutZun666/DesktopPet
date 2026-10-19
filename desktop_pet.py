import sys
import random
import math
import time
import datetime  
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction
from PyQt5.QtGui import QPixmap, QTransform, QPainter, QColor, QFont, QPainterPath
from PyQt5.QtCore import Qt, QTimer, QRectF  # 引入 QRectF 用于精确绘制

# ================= 配置参数 =================
IMAGE_PATH = "pet.png"        
TARGET_HEIGHT = 250           

GRAVITY = 0.8                  
AIR_FRICTION = 0.98            
BOUNCE_FACTOR = 0.6            
MIN_BOUNCE_SPEED = 2.0         
DRAG_INERTIA = 0.5             

WALK_SPEED = 1.5               
STAND_TIME_MIN = 180           
STAND_TIME_MAX = 600           
WALK_TIME_MIN = 120            
WALK_TIME_MAX = 300            

TALK_INTERVAL_MIN = 8000       
TALK_INTERVAL_MAX = 20000      

# ================= 台词库 =================
IDLE_QUOTES = [
    "今天也是摸鱼的一天~", "咕噜咕噜...", "肚子饿了，想吃小鱼干...",
    "你在忙什么呢？", "好困，想睡觉了 zzz", "要一起玩吗？",
    "我可是最可爱的桌面宠物！", "水好少，我要干涸了..."
]

SCENE_QUOTES = {
    "click": ["我是一条爱吃白饭的大肥鱼！", "咕噜？你戳我干嘛？", "哎呀，别戳啦，会变胖的！", "白饭...哪里有白饭？"],
    "drag": ["哇啊！你要干嘛！", "放、放开我！", "救命呀！被抓住了！"],
    "land": ["不要甩我啦，头晕！", "哎哟...我的屁股...", "落地满分！", "再也不飞了，好可怕..."],
    "turn": ["哎呀，没路了...", "这里过不去啦。", "碰壁了..."]
}

class SpeechBubble(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.text = ""
        self.arrow_pos = 0.5  
        # 字体稍微调大了一点点，更清楚
        self.font = QFont("Microsoft YaHei", 10, QFont.Bold)
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def show_text(self, text, duration=3000):
        self.text = text
        self.hide_timer.stop()
        
        # 【修复核心1】计算折行后的文本真实尺寸
        max_text_width = 220  # 限制文字区域的最大宽度
        font_metrics = self.fontMetrics()
        
        # boundingRect 会根据最大宽度自动计算折行后所需的高度
        text_rect = font_metrics.boundingRect(
            0, 0, max_text_width, 1000, Qt.TextWordWrap, self.text
        )
        
        # 加上内边距 (padding)
        self.padding_x = 15
        self.padding_y = 12
        
        self.bubble_width = text_rect.width() + self.padding_x * 2
        self.bubble_height = text_rect.height() + self.padding_y * 2
        self.tail_height = 10 
        
        # 调整窗口总大小
        self.resize(int(self.bubble_width), int(self.bubble_height + self.tail_height))
        self.show()
        self.update() 
        self.hide_timer.start(duration)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        rect_width = self.width()
        rect_height = self.height() - self.tail_height
        
        # 绘制圆角矩形背景
        path.addRoundedRect(0, 0, rect_width, rect_height, 10, 10)
        
        # 绘制小尾巴
        tail_x = rect_width * self.arrow_pos
        path.moveTo(tail_x - 8, rect_height)
        path.lineTo(tail_x, self.height())
        path.lineTo(tail_x + 8, rect_height)
        path.closeSubpath()
        
        painter.setPen(QColor(100, 150, 200))
        painter.setBrush(QColor(255, 255, 255, 240))
        painter.drawPath(path)

        # 【修复核心2】绘制文字时启用自动换行，并精准定位
        painter.setPen(QColor(50, 50, 50))
        painter.setFont(self.font)
        
        # 计算文字绘制的矩形区域
        text_draw_rect = QRectF(
            self.padding_x, 
            self.padding_y, 
            rect_width - self.padding_x * 2, 
            rect_height - self.padding_y * 2
        )
        
        # 使用 AlignCenter 和 TextWordWrap 确保文字居中且自动折行
        painter.drawText(text_draw_rect, Qt.AlignCenter | Qt.TextWordWrap, self.text)


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel(self)
        self.pixmap_left = QPixmap(IMAGE_PATH).scaledToHeight(TARGET_HEIGHT, Qt.SmoothTransformation)
        self.pixmap_right = self.pixmap_left.transformed(QTransform().scale(-1, 1))
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

        self.is_dragging = False
        self.press_time = 0
        self.press_pos = None
        self.drag_position = None
        self.last_mouse_pos = None
        self.drag_vx = 0.0
        self.drag_vy = 0.0
        self.just_double_clicked = False 

        self.idle_offset = 0.0
        self.idle_direction = 1
        self.move(int(self.pos_x), int(self.pos_y))

        self.bubble = SpeechBubble()
        self.talk_timer = QTimer(self)
        self.talk_timer.timeout.connect(self.random_speak)
        self.reset_talk_timer()

        self.single_click_timer = QTimer(self)
        self.single_click_timer.setSingleShot(True)
        self.single_click_timer.timeout.connect(self.handle_single_click)

        self.game_loop = QTimer(self)
        self.game_loop.timeout.connect(self.update_physics)
        self.game_loop.start(16)

    def reset_talk_timer(self):
        self.talk_timer.start(random.randint(TALK_INTERVAL_MIN, TALK_INTERVAL_MAX))

    def random_speak(self):
        if self.state == "idle" and self.ai_action == "standing":
            self.bubble.show_text(random.choice(IDLE_QUOTES), duration=random.randint(2000, 4000))
        self.reset_talk_timer()

    def force_speak(self, text_list, duration=2500):
        text = random.choice(text_list) if isinstance(text_list, list) else text_list
        self.bubble.show_text(text, duration=duration)
        self.reset_talk_timer()

    def handle_single_click(self):
        self.force_speak(SCENE_QUOTES["click"])
        self.idle_offset = -10 

    def update_bubble_position(self):
        if self.bubble.isVisible():
            bubble_x = self.pos_x + (self.width() / 2) - (self.bubble.width() / 2)
            bubble_y = self.pos_y - self.bubble.height() - 5
            
            # 【修复核心3】防止气泡变宽后超出屏幕左右边缘
            if bubble_x < 10:
                bubble_x = 10
            elif bubble_x + self.bubble.width() > self.screen_rect.width() - 10:
                bubble_x = self.screen_rect.width() - self.bubble.width() - 10
                
            self.bubble.move(int(bubble_x), int(bubble_y))

    def set_direction(self, direction):
        if direction == self.current_direction: return 
        self.current_direction = direction
        self.label.setPixmap(self.pixmap_right if direction == 1 else self.pixmap_left)

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
                    self.vy, self.vx = 0, 0
                    self.state = "idle"
                    self.ai_action = "standing"
                    self.action_timer = random.randint(STAND_TIME_MIN, STAND_TIME_MAX)
                    if hasattr(self, 'fall_start_y') and self.fall_start_y - self.floor_y > 50:
                        self.force_speak(SCENE_QUOTES["land"])
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
                if abs(self.idle_offset) > 6: self.idle_direction *= -1
                self.move(int(self.pos_x), int(self.floor_y + self.idle_offset))
            elif self.ai_action == "walking":
                self.pos_x += WALK_SPEED * self.walk_direction
                if self.pos_x <= self.screen_rect.left():
                    self.pos_x = self.screen_rect.left()
                    self.walk_direction = 1
                    self.set_direction(self.walk_direction)
                    self.force_speak(SCENE_QUOTES["turn"])
                elif self.pos_x >= self.screen_rect.right() - self.width():
                    self.pos_x = self.screen_rect.right() - self.width()
                    self.walk_direction = -1
                    self.set_direction(self.walk_direction)
                    self.force_speak(SCENE_QUOTES["turn"])
                self.walk_bounce += 0.2
                bounce_y = abs(math.sin(self.walk_bounce)) * 10 
                self.move(int(self.pos_x), int(self.floor_y - bounce_y))

        self.update_bubble_position()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.press_time = time.time()
            self.press_pos = event.pos()
            self.is_dragging = False
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.last_mouse_pos = event.globalPos()
            self.drag_vx = 0.0
            self.drag_vy = 0.0
            self.fall_start_y = self.pos_y
            event.accept()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if not self.is_dragging:
                if (event.pos() - self.press_pos).manhattanLength() > 5:
                    self.is_dragging = True
                    self.state = "dragging"
                    self.single_click_timer.stop()
                    self.force_speak(SCENE_QUOTES["drag"])

            if self.is_dragging:
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
            click_duration = time.time() - self.press_time
            
            if self.just_double_clicked:
                self.just_double_clicked = False
                self.is_dragging = False
                self.drag_position = None
                event.accept()
                return

            if not self.is_dragging and click_duration < 0.3:
                self.single_click_timer.start(250) 
                event.accept()
                return

            self.drag_position = None
            if self.is_dragging:
                if self.pos_y < self.floor_y - 5:
                    self.state = "falling"
                    self.vx = self.drag_vx * DRAG_INERTIA
                    self.vy = self.drag_vy * DRAG_INERTIA
                    if abs(self.vx) > 5:
                        self.set_direction(1 if self.vx > 0 else -1)
                else:
                    self.pos_x = float(self.x())
                    self.pos_y = float(self.floor_y)
                    self.state = "idle"
                    self.ai_action = "standing"
                    self.action_timer = random.randint(STAND_TIME_MIN, STAND_TIME_MAX)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.just_double_clicked = True
            self.single_click_timer.stop()
            
            now = datetime.datetime.now()
            # 格式：2023年10月27日 15:30:00
            time_str = f"现在是 {now.strftime('%Y年%m月%d日 %H:%M:%S')} 啦"
            
            self.force_speak(time_str, duration=4000)
            self.idle_offset = -15
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