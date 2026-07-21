"""图片裁剪对话框 — 用于看板娘头像选择"""
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QRect, QPoint, QSize
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QImage, QMouseEvent


class ImageCropDialog(QDialog):
    """图片裁剪对话框

    用法:
        dlg = ImageCropDialog(image_path, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            cropped_path = dlg.save_cropped(save_path)
    """

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u88C1\u526A\u5934\u50CF")
        self.setMinimumSize(500, 500)
        self.resize(600, 600)

        self._source = QPixmap(image_path)
        if self._source.isNull():
            QMessageBox.warning(self, "\u9519\u8BEF", "\u65E0\u6CD5\u52A0\u8F7D\u56FE\u7247")
            self.reject()
            return

        self._crop_size = min(400, min(self._source.width(), self._source.height()))
        self._offset = QPoint(0, 0)
        self._dragging = False
        self._drag_start = QPoint(0, 0)
        self._result = None

        self._setup_ui()
        self._update_preview()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 预览标签
        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumSize(400, 400)
        self._preview.setStyleSheet("background-color: #1a1a1a; border: 1px solid #333; border-radius: 8px;")
        self._preview.mousePressEvent = self._on_mouse_press
        self._preview.mouseMoveEvent = self._on_mouse_move
        self._preview.mouseReleaseEvent = self._on_mouse_release
        layout.addWidget(self._preview, stretch=1)

        # 缩放滑块
        zoom_row = QHBoxLayout()
        zoom_label = QLabel("\u7F29\u653E:")
        zoom_label.setStyleSheet("background: transparent;")
        zoom_row.addWidget(zoom_label)

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setMinimum(50)
        self._zoom_slider.setMaximum(200)
        self._zoom_slider.setValue(100)
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)
        zoom_row.addWidget(self._zoom_slider)

        self._zoom_value_label = QLabel("100%")
        self._zoom_value_label.setStyleSheet("background: transparent;")
        self._zoom_value_label.setFixedWidth(50)
        zoom_row.addWidget(self._zoom_value_label)
        layout.addLayout(zoom_row)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("\u53D6\u6D88")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        confirm_btn = QPushButton("\u786E\u5B9A\u88C1\u526A")
        confirm_btn.setObjectName("primaryBtn")
        confirm_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(confirm_btn)

        layout.addLayout(btn_row)

    def _on_zoom_changed(self, val):
        self._zoom_value_label.setText(f"{val}%")
        self._update_preview()

    def _on_mouse_press(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start = event.pos()

    def _on_mouse_move(self, event: QMouseEvent):
        if self._dragging:
            delta = event.pos() - self._drag_start
            scale = self._display_scale()
            self._offset -= QPoint(int(delta.x() / scale), int(delta.y() / scale))
            self._drag_start = event.pos()
            self._clamp_offset()
            self._update_preview()

    def _on_mouse_release(self, event):
        self._dragging = False

    def _display_scale(self):
        """计算显示缩放比例"""
        pw = self._preview.width()
        ph = self._preview.height()
        if pw < 10 or ph < 10:
            return 1.0
        zoom = self._zoom_slider.value() / 100.0
        scale_w = pw / self._crop_size * zoom
        scale_h = ph / self._crop_size * zoom
        return min(scale_w, scale_h)

    def _clamp_offset(self):
        """限制偏移范围"""
        sw = self._source.width()
        sh = self._source.height()
        self._offset.setX(max(0, min(sw - self._crop_size, self._offset.x())))
        self._offset.setY(max(0, min(sh - self._crop_size, self._offset.y())))

    def _update_preview(self):
        """更新预览"""
        if self._source.isNull():
            return

        pw = self._preview.width()
        ph = self._preview.height()
        if pw < 10 or ph < 10:
            return

        zoom = self._zoom_slider.value() / 100.0
        crop_size = int(self._crop_size * zoom)
        scale = self._display_scale()

        # 裁剪区域
        crop_rect = QRect(self._offset.x(), self._offset.y(), self._crop_size, self._crop_size)

        # 缩放后的裁剪图片
        cropped = self._source.copy(crop_rect)
        display_size = QSize(int(crop_size * scale), int(crop_size * scale))
        display = cropped.scaled(display_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        # 在预览上绘制
        canvas = QPixmap(pw, ph)
        canvas.fill(QColor("#1a1a1a"))
        painter = QPainter(canvas)

        x = (pw - display.width()) // 2
        y = (ph - display.height()) // 2

        # 绘制裁剪后的图片
        painter.drawPixmap(x, y, display)

        # 绘制裁剪框
        pen = QPen(QColor("#ff4d5a"), 2)
        painter.setPen(pen)
        painter.drawRect(x, y, display.width(), display.height())

        painter.end()
        self._preview.setPixmap(canvas)

    def _on_confirm(self):
        """确认裁剪"""
        crop_rect = QRect(self._offset.x(), self._offset.y(), self._crop_size, self._crop_size)
        self._result = self._source.copy(crop_rect)
        self.accept()

    def cropped_result(self):
        """返回裁剪后的 QPixmap"""
        return self._result

    def save_cropped(self, save_path):
        """保存裁剪结果到文件"""
        if self._result and not self._result.isNull():
            self._result.save(save_path, "PNG")
            return save_path
        return None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_preview()


def open_and_crop_image(parent=None, save_dir=None):
    """打开文件对话框选择图片，裁剪后保存

    Returns:
        保存后的文件路径，取消则返回空字符串
    """
    path, _ = QFileDialog.getOpenFileName(
        parent, "\u9009\u62E9\u5934\u50CF\u56FE\u7247",
        "", "\u56FE\u7247\u6587\u4EF6 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
    )
    if not path:
        return ""

    dlg = ImageCropDialog(path, parent)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        if save_dir is None:
            # 保存到项目 assets 目录
            save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
            os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, "avatar_cropped.png")
        # 如果已存在，加序号
        base = save_path
        i = 1
        while os.path.exists(save_path):
            save_path = os.path.join(save_dir, f"avatar_cropped_{i}.png")
            i += 1
        saved = dlg.save_cropped(save_path)
        if saved:
            return saved
    return ""