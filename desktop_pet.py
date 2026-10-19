import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer
from PIL import Image

# ================= 配置参数 =================
IMAGE_PATH = "pet.png"        # 原始图片路径
SCALE_FACTOR = 0.8            # 宠物缩放比例（可以调整大小）
# ============================================

def make_background_transparent(image_path, output_path):
    """将图片的白色背景替换为透明"""
    try:
        img = Image.open(image_path).convert("RGBA")
        datas = img.getdata()
        newData = []
        for item in datas:
            # 判断像素是否接近纯白色 (RGB值都大于240)
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                newData.append((255, 255, 255, 0)) # 变成完全透明
            else:
                newData.append(item)
        img.putdata(newData)
        img.save(output_path, "PNG")
        print("背景透明化处理完成！")
    except Exception as e:
        print(f"处理图片失败，请确保图片存在: {e}")

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

        # 2. 加载图片
        self.label = QLabel(self)
        self.pixmap = QPixmap(IMAGE_PATH)
        
        # 缩放图片
        self.pixmap = self.pixmap.scaled(
            int(self.pixmap.width() * SCALE_FACTOR),
            int(self.pixmap.height() * SCALE_FACTOR),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.label.setPixmap(self.pixmap)
        self.resize(self.pixmap.size())

        # 3. 初始化拖动相关变量
        self.drag_position = None

        # 4. 定位到任务栏（Dock栏）上方
        self.move_to_dock()

        # 5. 添加一个轻微的呼吸浮动动画 (上下摆动)
        self.offset = 0
        self.direction = 1
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.float_animation)
        self.timer.start(100) # 每100毫秒移动一次

    def move_to_dock(self):
        """将宠物放置在屏幕下方任务栏上方"""
        screen = QApplication.primaryScreen().availableGeometry()
        # x: 屏幕右侧留出一定距离; y: 屏幕高度 - 宠物高度
        x = screen.width() - self.width() - 200 
        y = screen.height() - self.height()
        self.move(x, y)

    def float_animation(self):
        """上下轻微浮动的动画效果"""
        # 如果用户正在拖动，暂停动画
        if self.drag_position is not None:
            return
            
        self.offset += self.direction * 2
        if abs(self.offset) > 8: # 浮动幅度
            self.direction *= -1
            
        # 更新位置
        current_pos = self.pos()
        self.move(current_pos.x(), current_pos.y() + self.direction * 2)

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
            event.accept()

    def show_context_menu(self, pos):
        """右键菜单，用于退出程序"""
        menu = QMenu(self)
        quit_action = QAction("退下吧，鱼鱼", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        menu.exec_(pos)

if __name__ == '__main__':
    # 自动处理图片背景透明
    make_background_transparent(IMAGE_PATH, "pet_transparent.png")
    IMAGE_PATH = "pet_transparent.png"

    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())