"""文件列表组件 - 玻璃质感高级表格，支持自由调整列宽"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QHBoxLayout, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor
from ui.theme import theme_manager


class FileListWidget(QWidget):
    """文件列表表格 — 玻璃质感，列宽可自由拖拽调整"""

    item_selected = Signal(int)

    COLUMNS = ["类型", "Season", "Episode", "原文件名", "目标新名称"]

    def __init__(self):
        super().__init__()
        self._setup_ui()
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
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.table.setMouseTracking(True)

        # 所有列使用 Interactive 模式，允许用户自由拖拽调整宽度
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)

        # 默认列宽
        self.table.setColumnWidth(0, 64)
        self.table.setColumnWidth(1, 72)
        self.table.setColumnWidth(2, 72)
        self.table.setColumnWidth(3, 280)
        self.table.setColumnWidth(4, 280)

        # 最小列宽
        header.setMinimumSectionSize(50)

        # 最后一列自动拉伸填充剩余空间
        header.setStretchLastSection(True)

        layout.addWidget(self.table)

    def populate(self, rename_items):
        """填充表格数据"""
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

            # 行高
            self.table.setRowHeight(i, 44)

            # 交替行颜色
            if i % 2 == 1:
                for col in range(self.table.columnCount()):
                    item_widget = self.table.item(i, col)
                    if item_widget:
                        item_widget.setBackground(QColor(c["bg_table_alt"]))

    def clear(self):
        self.table.setRowCount(0)

    def _apply_theme(self):
        c = theme_manager.colors
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
                gridline-color: transparent;
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
                border-bottom: 1px solid {c["border_glow"]};
                font-weight: 600;
                font-size: 12px;
                letter-spacing: 0.3px;
            }}
        """)

    def refresh_theme(self):
        self._apply_theme()
        # 重新填充以更新行颜色
        if self.table.rowCount() > 0:
            self._refresh_row_colors()

    def _refresh_row_colors(self):
        """刷新所有行的交替颜色"""
        c = theme_manager.colors
        for i in range(self.table.rowCount()):
            if i % 2 == 1:
                for col in range(self.table.columnCount()):
                    item_widget = self.table.item(i, col)
                    if item_widget:
                        item_widget.setBackground(QColor(c["bg_table_alt"]))