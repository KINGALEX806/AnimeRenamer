"""文件列表组件 - 玻璃质感高级表格，支持自由调整列宽（列宽可记忆）+ 双击编辑目标名称"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QHBoxLayout, QAbstractItemView,
    QStyledItemDelegate, QLineEdit, QTableWidget
)
from PySide6.QtCore import Qt, Signal, QSize, QEvent, QTimer
from PySide6.QtGui import QFont, QColor
from ui.theme import theme_manager
from utils.config import load_config, set_config


class EditDelegate(QStyledItemDelegate):
    """列4的编辑代理，确保编辑器文字可见"""

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        c = theme_manager.colors
        editor.setStyleSheet(f"""
            QLineEdit {{
                background-color: {c["bg_card"]};
                color: {c["text_primary"]};
                border: 1px solid {c["accent"]};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                selection-background-color: {c["accent"]};
                selection-color: white;
            }}
        """)
        editor.setFrame(False)
        return editor

    def setEditorData(self, editor, index):
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if text:
            editor.setText(text)
            editor.selectAll()

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text(), Qt.ItemDataRole.DisplayRole)


class FileListWidget(QWidget):
    """文件列表表格 — 玻璃质感，列宽可自由拖拽调整并记忆"""

    item_selected = Signal(int)
    column_widths_changed = Signal(list)
    target_name_edited = Signal(int, str)  # row, new_name

    COLUMNS = ["\u7C7B\u578B", "Season", "Episode", "\u539F\u6587\u4EF6\u540D", "\u76EE\u6807\u65B0\u540D\u79F0"]
    _DEFAULT_WIDTHS = [70, 84, 84, 400, 300]

    def __init__(self):
        super().__init__()
        self._rename_items = []
        self._adjusting = False  # 防重入
        self._setup_ui()
        self._restore_column_widths()
        self._apply_theme()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.table.setMouseTracking(True)

        header = self.table.horizontalHeader()
        # 所有列 Interactive
        for col in range(5):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)

        for col, w in enumerate(self._DEFAULT_WIDTHS):
            self.table.setColumnWidth(col, w)

        # 每列最小宽度：确保栏位标题完整显示
        self._col_mins = [60, 84, 84, 120, 150]
        header.sectionResized.connect(self._on_section_resized)

        # 窗口 resize 时重新分配列 4
        self.table.installEventFilter(self)

        # 首次显示时自动填满
        QTimer.singleShot(0, self._fill_column_4)

        # 双击编辑目标名称
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table.cellChanged.connect(self._on_cell_changed)

        # 为列4设置自定义编辑代理
        self.table.setItemDelegateForColumn(4, EditDelegate(self.table))

        layout.addWidget(self.table)

    def _on_section_resized(self, col, old_size, new_size):
        """用户手动拖拽列宽后：保持列 4 填满，不重新均分"""
        self._fill_column_4(equal_split=False)
        self.column_widths_changed.emit(self.get_column_widths())

    def _fill_column_4(self, equal_split=True):
        """让列 4 填满剩余空间，确保每列不低于最小宽度。
        equal_split=True 时列 3/4 均分剩余空间（首开/窗口调整时居中效果）。
        """
        if self._adjusting:
            return
        self._adjusting = True

        total = self.table.viewport().width()
        if total <= 0:
            self._adjusting = False
            return

        mins = self._col_mins

        # 第一步：确保列 0-2 不低于各自的最小宽度
        for col in range(3):
            if self.table.columnWidth(col) < mins[col]:
                self.table.setColumnWidth(col, mins[col])

        fixed = sum(self.table.columnWidth(i) for i in range(3))
        remain = total - fixed

        if equal_split and remain >= mins[3] + mins[4]:
            # 列 3/4 各占一半
            half = remain // 2
            self.table.setColumnWidth(3, half)
            self.table.setColumnWidth(4, total - fixed - half)
        else:
            # 确保列 3 不低于最小值
            if self.table.columnWidth(3) < mins[3]:
                self.table.setColumnWidth(3, mins[3])

            used = sum(self.table.columnWidth(i) for i in range(4))
            c4 = total - used

            if c4 >= mins[4]:
                self.table.setColumnWidth(4, c4)
            else:
                need = mins[4] - c4
                for col in (3, 2, 1, 0):
                    if need <= 0:
                        break
                    cur = self.table.columnWidth(col)
                    can_shrink = cur - mins[col]
                    if can_shrink > 0:
                        shrink = min(can_shrink, need)
                        self.table.setColumnWidth(col, cur - shrink)
                        need -= shrink
                used = sum(self.table.columnWidth(i) for i in range(4))
                self.table.setColumnWidth(4, total - used)

        self._adjusting = False

    def eventFilter(self, obj, event):
        """窗口 resize 时重新分配列 4（延迟一帧等 viewport 更新）"""
        if obj is self.table and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self._fill_column_4)
        return super().eventFilter(obj, event)

    def _on_cell_double_clicked(self, row, col):
        if col == 4:
            self.table.editItem(self.table.item(row, col))

    def _on_cell_changed(self, row, col):
        if col == 4:
            item = self.table.item(row, col)
            if item and row < len(self._rename_items):
                new_name = item.text().strip()
                if new_name:
                    self._rename_items[row].new_name = new_name
                    self.target_name_edited.emit(row, new_name)

    def get_column_widths(self):
        return [self.table.columnWidth(i) for i in range(5)]

    def save_column_widths(self):
        set_config("column_widths", self.get_column_widths())

    def _restore_column_widths(self):
        config = load_config()
        saved = config.get("column_widths")
        if saved and isinstance(saved, list) and len(saved) >= 5:
            for col in range(5):
                self.table.setColumnWidth(col, max(saved[col], 40))

    def populate(self, rename_items):
        self._rename_items = rename_items
        self.table.setRowCount(0)
        self.table.setRowCount(len(rename_items))

        c = theme_manager.colors

        for i, item in enumerate(rename_items):
            is_subtitle = getattr(item, 'is_subtitle_match', False)
            is_video = not is_subtitle
            parsed = item.parsed_info

            # ---- 类型列 ----
            type_widget = QWidget()
            type_widget.setStyleSheet("background: transparent;")
            type_layout = QHBoxLayout(type_widget)
            type_layout.setContentsMargins(4, 4, 4, 4)
            type_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if is_video:
                badge = QLabel("\U0001F3AC")
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setStyleSheet(f"""
                    QLabel {{
                        background: transparent;
                        color: {c["success"]};
                        font-size: 16px;
                        padding: 0px;
                    }}
                """)
            else:
                badge = QLabel("\U0001F4AC")
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setStyleSheet(f"""
                    QLabel {{
                        background: transparent;
                        color: {c["info"]};
                        font-size: 16px;
                        padding: 0px;
                    }}
                """)

            type_layout.addWidget(badge)
            self.table.setCellWidget(i, 0, type_widget)

            # ---- Season 列 ----
            season_text = f"S{parsed.season:02d}" if parsed else "\u2014"
            season_item = QTableWidgetItem(season_text)
            season_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            season_item.setForeground(QColor(c["text_secondary"]))
            self.table.setItem(i, 1, season_item)

            # ---- Episode 列 ----
            ep_text = f"E{parsed.episode:02d}" if parsed and parsed.episode else "\u2014"
            ep_item = QTableWidgetItem(ep_text)
            ep_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            ep_item.setForeground(QColor(c["text_secondary"]))
            self.table.setItem(i, 2, ep_item)

            # ---- 原文件名 ----
            old_item = QTableWidgetItem(item.old_name)
            old_item.setToolTip(item.old_name)
            old_item.setForeground(QColor(c["text_primary"]))
            self.table.setItem(i, 3, old_item)

            # ---- 目标新名称 ----
            new_name = item.new_name if item.new_name else ""
            if item.status == "pending" and not new_name:
                new_display = "[\u7B49\u5F85\u8054\u7F51\u8BC6\u522B...]"
                new_item = QTableWidgetItem(new_display)
                new_item.setForeground(QColor(c["text_placeholder"]))
            else:
                new_item = QTableWidgetItem(new_name)
                new_item.setToolTip(new_name)

                if item.status == "done":
                    new_item.setForeground(QColor(c["success"]))
                elif item.status == "failed":
                    new_item.setForeground(QColor(c["error"]))
                elif item.status == "conflict":
                    new_item.setForeground(QColor(c["error"]))
                elif item.status == "ready":
                    new_item.setForeground(QColor(c["warning"]))
                else:
                    new_item.setForeground(QColor(c["text_secondary"]))

            self.table.setItem(i, 4, new_item)

            self.table.setRowHeight(i, 44)

            if i % 2 == 1:
                for col in range(self.table.columnCount()):
                    item_widget = self.table.item(i, col)
                    if item_widget:
                        item_widget.setBackground(QColor(c["bg_table_alt"]))

        # 填充数据后自动分配列宽
        QTimer.singleShot(0, self._fill_column_4)

    def clear(self):
        self._rename_items = []
        self.table.setRowCount(0)

    def _apply_theme(self):
        c = theme_manager.colors
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: 1px solid {c["grid"]};
                gridline-color: {c["grid"]};
                selection-background-color: {c["bg_table_hover"]};
                selection-color: {c["text_primary"]};
                outline: none;
                alternate-background-color: {c["bg_table_alt"]};
            }}
            QTableWidget::item {{
                padding: 10px 14px;
                border-bottom: 1px solid {c["border"]};
                background: transparent;
            }}
            QTableWidget::item:selected {{
                background-color: {c["bg_table_hover"]};
            }}
            QHeaderView::section {{
                background-color: {c["bg_table_header"]};
                color: {c["text_secondary"]};
                padding: 12px 14px;
                border: none;
                border-right: 1px solid {c["grid"]};
                border-bottom: 1px solid {c["border_glow"]};
                font-weight: 600;
                font-size: 12px;
                letter-spacing: 0.3px;
            }}
        """)

    def refresh_theme(self):
        self._apply_theme()
        if self._rename_items:
            self._refresh_all_cell_colors()

    def _refresh_all_cell_colors(self):
        c = theme_manager.colors
        for i, item in enumerate(self._rename_items):
            si = self.table.item(i, 1)
            if si:
                si.setForeground(QColor(c["text_secondary"]))

            ei = self.table.item(i, 2)
            if ei:
                ei.setForeground(QColor(c["text_secondary"]))

            oi = self.table.item(i, 3)
            if oi:
                oi.setForeground(QColor(c["text_primary"]))

            ni = self.table.item(i, 4)
            if ni:
                if item.status == "pending" and not item.new_name:
                    ni.setForeground(QColor(c["text_placeholder"]))
                elif item.status == "done":
                    ni.setForeground(QColor(c["success"]))
                elif item.status in ("failed", "conflict"):
                    ni.setForeground(QColor(c["error"]))
                elif item.status == "ready":
                    ni.setForeground(QColor(c["warning"]))
                else:
                    ni.setForeground(QColor(c["text_secondary"]))

            if i % 2 == 1:
                for col in range(1, self.table.columnCount()):
                    iw = self.table.item(i, col)
                    if iw:
                        iw.setBackground(QColor(c["bg_table_alt"]))
            else:
                for col in range(1, self.table.columnCount()):
                    iw = self.table.item(i, col)
                    if iw:
                        iw.setBackground(QColor("transparent"))

        for i, item in enumerate(self._rename_items):
            tw = self.table.cellWidget(i, 0)
            if tw:
                badge = tw.findChild(QLabel)
                if badge:
                    is_subtitle = getattr(item, 'is_subtitle_match', False)
                    color = c["info"] if is_subtitle else c["success"]
                    badge.setStyleSheet(f"""
                        QLabel {{
                            background: transparent;
                            color: {color};
                            font-size: 16px;
                            padding: 0px;
                        }}
                    """)