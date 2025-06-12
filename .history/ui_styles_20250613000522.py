#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PySide6 UI 스타일 테마 모듈
다크/라이트 테마와 모던한 금융 앱 스타일 정의
"""

DARK_THEME = """
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #1a1a2e, stop:1 #16213e);
    color: #ffffff;
    border: none;
    font-family: "맑은 고딕", "Apple Gothic", "Helvetica Neue", sans-serif;
}

QWidget {
    background-color: transparent;
    color: #ffffff;
    font-size: 14px;
}

/* 제목 및 헤더 */
QLabel[title="true"] {
    font-size: 18px;
    font-weight: bold;
    color: #4fc3f7;
    padding: 10px;
    border-bottom: 2px solid #4fc3f7;
    margin-bottom: 10px;
}

QLabel[subtitle="true"] {
    font-size: 16px;
    font-weight: bold;
    color: #81c784;
    padding: 8px 0px;
}

/* 상태 라벨 */
QLabel[status="connected"] {
    color: #4caf50;
    font-weight: bold;
}

QLabel[status="disconnected"] {
    color: #f44336;
    font-weight: bold;
}

QLabel[status="warning"] {
    color: #ff9800;
    font-weight: bold;
}

/* 버튼 스타일 */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4fc3f7, stop:1 #29b6f6);
    border: none;
    border-radius: 8px;
    color: white;
    font-weight: bold;
    font-size: 14px;
    padding: 12px 24px;
    min-height: 20px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #81d4fa, stop:1 #4fc3f7);
    transform: translateY(-1px);
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #0288d1, stop:1 #0277bd);
    margin-top: 1px;
}

QPushButton:disabled {
    background: #424242;
    color: #757575;
}

/* 주문 버튼 특별 스타일 */
QPushButton[orderType="buy"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4caf50, stop:1 #388e3c);
}

QPushButton[orderType="buy"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #66bb6a, stop:1 #4caf50);
}

QPushButton[orderType="sell"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #f44336, stop:1 #d32f2f);
}

QPushButton[orderType="sell"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ef5350, stop:1 #f44336);
}

/* 입력 필드 */
QLineEdit {
    background-color: rgba(255, 255, 255, 0.1);
    border: 2px solid rgba(79, 195, 247, 0.3);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 14px;
    color: white;
    selection-background-color: #4fc3f7;
}

QLineEdit:focus {
    border: 2px solid #4fc3f7;
    background-color: rgba(255, 255, 255, 0.15);
}

QLineEdit:hover {
    border: 2px solid rgba(79, 195, 247, 0.5);
}

/* 콤보박스 */
QComboBox {
    background-color: rgba(255, 255, 255, 0.1);
    border: 2px solid rgba(79, 195, 247, 0.3);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    color: white;
    min-width: 120px;
}

QComboBox:hover {
    border: 2px solid rgba(79, 195, 247, 0.5);
}

QComboBox:focus {
    border: 2px solid #4fc3f7;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: url(down_arrow.png);
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #2d2d44;
    border: 1px solid #4fc3f7;
    border-radius: 4px;
    color: white;
    selection-background-color: #4fc3f7;
}

/* 테이블 위젯 */
QTableWidget {
    background-color: rgba(255, 255, 255, 0.05);
    alternate-background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(79, 195, 247, 0.3);
    border-radius: 8px;
    gridline-color: rgba(255, 255, 255, 0.1);
    font-size: 13px;
    color: white;
}

QTableWidget::item {
    padding: 8px;
    border: none;
}

QTableWidget::item:selected {
    background-color: rgba(79, 195, 247, 0.3);
}

QTableWidget::item:hover {
    background-color: rgba(79, 195, 247, 0.1);
}

QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4fc3f7, stop:1 #29b6f6);
    color: white;
    font-weight: bold;
    padding: 8px;
    border: none;
    border-right: 1px solid rgba(255, 255, 255, 0.2);
}

QHeaderView::section:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #81d4fa, stop:1 #4fc3f7);
}

/* 스크롤바 */
QScrollBar:vertical {
    background: rgba(255, 255, 255, 0.1);
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #4fc3f7;
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background: #81d4fa;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* 프레임 및 그룹박스 */
QFrame {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(79, 195, 247, 0.2);
    border-radius: 10px;
    padding: 10px;
    margin: 5px;
}

QGroupBox {
    background-color: rgba(255, 255, 255, 0.05);
    border: 2px solid rgba(79, 195, 247, 0.3);
    border-radius: 10px;
    margin-top: 1em;
    font-weight: bold;
    color: #4fc3f7;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}

/* 상태바 */
QStatusBar {
    background-color: rgba(0, 0, 0, 0.3);
    border-top: 1px solid rgba(79, 195, 247, 0.3);
    color: #b0bec5;
}

QStatusBar::item {
    border: none;
}

/* 툴바 */
QToolBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 rgba(79, 195, 247, 0.8), stop:1 rgba(41, 182, 246, 0.8));
    border: none;
    padding: 5px;
    spacing: 3px;
}

QToolBar::separator {
    background-color: rgba(255, 255, 255, 0.3);
    width: 1px;
    margin: 5px;
}

/* 탭 위젯 */
QTabWidget::pane {
    border: 1px solid rgba(79, 195, 247, 0.3);
    border-radius: 8px;
    background-color: rgba(255, 255, 255, 0.05);
}

QTabBar::tab {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(79, 195, 247, 0.3);
    padding: 8px 16px;
    margin-right: 2px;
    border-radius: 4px 4px 0px 0px;
}

QTabBar::tab:selected {
    background: #4fc3f7;
    color: white;
    font-weight: bold;
}

QTabBar::tab:hover {
    background: rgba(79, 195, 247, 0.3);
}

/* 프로그레스바 */
QProgressBar {
    border: 2px solid rgba(79, 195, 247, 0.3);
    border-radius: 8px;
    text-align: center;
    color: white;
    background-color: rgba(255, 255, 255, 0.1);
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #4fc3f7, stop:1 #29b6f6);
    border-radius: 6px;
}
"""

LIGHT_THEME = """
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #f5f5f5, stop:1 #e8eaf6);
    color: #212121;
    border: none;
    font-family: "맑은 고딕", "Apple Gothic", "Helvetica Neue", sans-serif;
}

QWidget {
    background-color: transparent;
    color: #212121;
    font-size: 14px;
}

/* 제목 및 헤더 */
QLabel[title="true"] {
    font-size: 18px;
    font-weight: bold;
    color: #1976d2;
    padding: 10px;
    border-bottom: 2px solid #1976d2;
    margin-bottom: 10px;
}

QLabel[subtitle="true"] {
    font-size: 16px;
    font-weight: bold;
    color: #388e3c;
    padding: 8px 0px;
}

/* 상태 라벨 */
QLabel[status="connected"] {
    color: #4caf50;
    font-weight: bold;
}

QLabel[status="disconnected"] {
    color: #f44336;
    font-weight: bold;
}

QLabel[status="warning"] {
    color: #ff9800;
    font-weight: bold;
}

/* 버튼 스타일 */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #2196f3, stop:1 #1976d2);
    border: none;
    border-radius: 8px;
    color: white;
    font-weight: bold;
    font-size: 14px;
    padding: 12px 24px;
    min-height: 20px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #42a5f5, stop:1 #2196f3);
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #1565c0, stop:1 #0d47a1);
}

QPushButton:disabled {
    background: #bdbdbd;
    color: #757575;
}

/* 주문 버튼 특별 스타일 */
QPushButton[orderType="buy"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4caf50, stop:1 #388e3c);
}

QPushButton[orderType="buy"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #66bb6a, stop:1 #4caf50);
}

QPushButton[orderType="sell"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #f44336, stop:1 #d32f2f);
}

QPushButton[orderType="sell"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ef5350, stop:1 #f44336);
}

/* 입력 필드 */
QLineEdit {
    background-color: white;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 14px;
    color: #212121;
    selection-background-color: #2196f3;
}

QLineEdit:focus {
    border: 2px solid #2196f3;
    background-color: #f8f9fa;
}

QLineEdit:hover {
    border: 2px solid #42a5f5;
}

/* 콤보박스 */
QComboBox {
    background-color: white;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    color: #212121;
    min-width: 120px;
}

QComboBox:hover {
    border: 2px solid #42a5f5;
}

QComboBox:focus {
    border: 2px solid #2196f3;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: white;
    border: 1px solid #2196f3;
    border-radius: 4px;
    color: #212121;
    selection-background-color: #e3f2fd;
}

/* 테이블 위젯 */
QTableWidget {
    background-color: white;
    alternate-background-color: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    gridline-color: #e0e0e0;
    font-size: 13px;
    color: #212121;
}

QTableWidget::item {
    padding: 8px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #e3f2fd;
}

QTableWidget::item:hover {
    background-color: #f5f5f5;
}

QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #2196f3, stop:1 #1976d2);
    color: white;
    font-weight: bold;
    padding: 8px;
    border: none;
    border-right: 1px solid rgba(255, 255, 255, 0.2);
}

QHeaderView::section:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #42a5f5, stop:1 #2196f3);
}

/* 스크롤바 */
QScrollBar:vertical {
    background: #f5f5f5;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #2196f3;
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background: #42a5f5;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* 프레임 및 그룹박스 */
QFrame {
    background-color: white;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 10px;
    margin: 5px;
}

QGroupBox {
    background-color: white;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    margin-top: 1em;
    font-weight: bold;
    color: #1976d2;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}

/* 상태바 */
QStatusBar {
    background-color: rgba(255, 255, 255, 0.9);
    border-top: 1px solid #e0e0e0;
    color: #616161;
}

QStatusBar::item {
    border: none;
}

/* 툴바 */
QToolBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 rgba(33, 150, 243, 0.8), stop:1 rgba(25, 118, 210, 0.8));
    border: none;
    padding: 5px;
    spacing: 3px;
}

QToolBar::separator {
    background-color: rgba(255, 255, 255, 0.3);
    width: 1px;
    margin: 5px;
}

/* 탭 위젯 */
QTabWidget::pane {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background-color: white;
}

QTabBar::tab {
    background: #f5f5f5;
    border: 1px solid #e0e0e0;
    padding: 8px 16px;
    margin-right: 2px;
    border-radius: 4px 4px 0px 0px;
}

QTabBar::tab:selected {
    background: #2196f3;
    color: white;
    font-weight: bold;
}

QTabBar::tab:hover {
    background: #e3f2fd;
}

/* 프로그레스바 */
QProgressBar {
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    text-align: center;
    color: #212121;
    background-color: #f5f5f5;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #2196f3, stop:1 #1976d2);
    border-radius: 6px;
}
"""

# 가격 변동 색상
PRICE_COLORS = {
    'up': '#f44336',      # 빨간색 (상승)
    'down': '#2196f3',    # 파란색 (하락)
    'same': '#757575'     # 회색 (보합)
}

# 애니메이션 설정
ANIMATION_DURATION = 300
FADE_DURATION = 200

def get_theme_style(is_dark=True):
    """테마에 따른 스타일 시트 반환"""
    return DARK_THEME if is_dark else LIGHT_THEME

def get_price_color(change):
    """가격 변동에 따른 색상 반환"""
    if change > 0:
        return PRICE_COLORS['up']
    elif change < 0:
        return PRICE_COLORS['down']
    else:
        return PRICE_COLORS['same']

def format_currency(amount, currency='KRW'):
    """통화 포맷팅"""
    try:
        amount_float = float(amount)
        if currency == 'KRW':
            if amount_float >= 1000000:
                return f"{amount_float/1000000:.1f}M"
            elif amount_float >= 1000:
                return f"{amount_float/1000:.0f}K"
            else:
                return f"{amount_float:,.0f}"
        else:
            if amount_float < 0.01:
                return f"{amount_float:.8f}"
            else:
                return f"{amount_float:,.4f}"
    except:
        return str(amount)

def format_percentage(percentage):
    """퍼센트 포맷팅"""
    try:
        pct = float(percentage)
        sign = "+" if pct > 0 else ""
        return f"{sign}{pct:.2f}%"
    except:
        return "0.00%" 