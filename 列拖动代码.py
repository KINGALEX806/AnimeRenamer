"""
QTableWidget 列拖动「最后一列弹性填充」模式
============================================

效果：
  - 所有列可自由独立拖拽调整宽度
  - 拖拽时只影响被拖拽列和相邻列，其他列不动
  - 所有列总宽度始终等于 viewport 宽度，不脱出屏幕、不留空白
  - 窗口 resize 时最后一列自动吸收多余空间

关键禁忌：
  - 弹性列必须放最后一列，不要放第一列或中间
  - _on_section_resized 里直接调用 fill，不要用 QTimer 延迟
  - 不要加 debounce/throttle 中间方法
  - 不要加额外的 _clamp_* 方法，逻辑全在 fill 里
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, QEvent, QTimer


class ColumnDragTable(QWidget):
    """带最后一列弹性填充的表格组件"""

    N_COLS = 4
    HEADERS = ["列1", "列2", "列3", "列4"]
    DEFAULT_WIDTHS = [200, 100, 100, 80]       # 初始列宽
    COL_MINS = [120, 80, 60, 60]               # 每列最小宽度

    def __init__(self):
        super().__init__()
        self._adjusting = False  # 防重入标志
        self._setup_ui()

    # ══════════════════════════════════════════════════════════
    #  核心代码
    # ══════════════════════════════════════════════════════════

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(self.N_COLS)
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.horizontalHeader().setStretchLastSection(False)

        # ① 所有列设为 Interactive
        header = self.table.horizontalHeader()
        for col in range(self.N_COLS):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)

        for col, w in enumerate(self.DEFAULT_WIDTHS):
            self.table.setColumnWidth(col, w)

        # ② 拖拽回调：直接调用 fill，不延迟
        header.sectionResized.connect(self._on_section_resized)

        # ③ 窗口 resize 时触发 fill（延迟一帧等 viewport 更新）
        self.table.installEventFilter(self)

        # ④ 首次显示时填满
        QTimer.singleShot(0, self._fill_last_column)

        layout.addWidget(self.table)

    def _on_section_resized(self, col, old_size, new_size):
        """用户拖拽列宽 → 直接填充最后一列"""
        self._fill_last_column()

    def _fill_last_column(self):
        """最后一列 = viewport 宽度 - 前面所有列宽度"""
        if self._adjusting:
            return
        self._adjusting = True

        total = self.table.viewport().width()
        if total <= 0:
            self._adjusting = False
            return

        mins = self.COL_MINS
        N = self.N_COLS

        # 保前面列不低于最小宽度
        for col in range(N - 1):
            if self.table.columnWidth(col) < mins[col]:
                self.table.setColumnWidth(col, mins[col])

        used = sum(self.table.columnWidth(c) for c in range(N - 1))
        last_w = total - used

        if last_w >= mins[N - 1]:
            self.table.setColumnWidth(N - 1, last_w)
        else:
            # 不够时从右向左依次压缩前面的列
            need = mins[N - 1] - last_w
            for col in reversed(range(N - 1)):
                if need <= 0:
                    break
                cur = self.table.columnWidth(col)
                can_shrink = cur - mins[col]
                if can_shrink > 0:
                    shrink = min(can_shrink, need)
                    self.table.setColumnWidth(col, cur - shrink)
                    need -= shrink
            used = sum(self.table.columnWidth(c) for c in range(N - 1))
            self.table.setColumnWidth(N - 1, max(total - used, mins[N - 1]))

        self._adjusting = False

    def eventFilter(self, obj, event):
        """窗口 resize → 延迟填充"""
        if obj is self.table and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self._fill_last_column)
        return super().eventFilter(obj, event)


# ══════════════════════════════════════════════════════════════
#  使用示例
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    widget = ColumnDragTable()
    widget.show()
    sys.exit(app.exec())