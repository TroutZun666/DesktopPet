import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer

# ================= 配置参数 =================
IMAGE_PATH = "pet.png"        # 你的透明背景图片路径
TARGET_HEIGHT = 250           # 【核心修改】设定宠物的像素高度，觉得大就改小（如200），觉得小就改大（如300）
# ============================================

class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        
        # 1. 窗口基础设置
        self.setWindowFlags(
            Qt.FramelessWindowHint |      # 无边框
            Qt.WindowStaysOnTopHint |     # 永远置顶
            Qt.Tool                       # 不在任务栏显示图标
        )
        self.setAttribute(Qt.WA_TranslucentBackground) # 背景透明

        # 2. 加载并缩放图片
        self.label = QLabel(self)
        self.pixmap = QPixmap(IMAGE_PATH)
        
        # 【尺寸控制】：按照固定高度进行等比缩放
        self.pixmap = self.pixmap.scaledToHeight(TARGET_HEIGHT, Qt.SmoothTransformation)
        
        self.label.setPixmap(self.pixmap)
        self.resize(self.pixmap.size())

        # 3. 初始化拖动相关变量
        self.drag_position = None
        self.base_x = 0
        self.base_y = 0

        # 4. 定位到任务栏（Dock栏）上方
        self.move_to_dock()

        # 5. 呼吸浮动动画
        self.offset = 0
        self.direction = 1
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.float_animation)
        self.timer.start(100) # 每100毫秒移动一次

    def move_to_dock(self):
        """将宠物放置在屏幕下方任务栏上方"""
        screen = QApplication.primaryScreen().availableGeometry()
        # x: 屏幕右侧留出200像素距离; y: 屏幕高度减去宠物高度
        self.base_x = screen.width() - self.width() - 200 
        self.base_y = screen.height() - self.height()
        self.move(self.base_x, self.base_y)

    def float_animation(self):
        """上下轻微浮动的动画效果（已修复漂移Bug）"""
        # 如果用户正在拖动，暂停动画
        if self.drag_position is not None:
            return
            
        self.offset += self.direction * 1
        if abs(self.offset) > 10: # 浮动幅度（上下10像素）
            self.direction *= -1
            
        # 使用基准坐标 + 偏移量，防止坐标一直往下偏移
        self.move(self.base_x, self.base_y + self.offset)

    # --- 鼠标交互事件 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            # 拖动结束后，更新基准坐标，这样她就会在新位置继续浮动
            self.base_x = self.x()
            self.base_y = self.y() - self.offset 
            event.accept()

    def show_context_menu(self, pos):
        """右键菜单，用于退出程序"""
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