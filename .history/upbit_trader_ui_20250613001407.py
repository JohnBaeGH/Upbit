#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 암호화폐 거래 UI 프로그램
PySide6 기반의 모던한 거래 인터페이스
"""

import sys
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QLineEdit,
    QComboBox, QFrame, QGroupBox, QTabWidget, QStatusBar, QMessageBox,
    QSplitter, QProgressBar, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, Signal, QPropertyAnimation, QEasingCurve,
    QRect, QSize
)
from PySide6.QtGui import QFont, QIcon, QPalette, QPixmap, QColor, QBrush

# 자체 모듈 import
from upbit_api import UpbitAPI
from ui_styles import get_theme_style, get_price_color, format_currency, format_percentage

class DataUpdateThread(QThread):
    """백그라운드 데이터 업데이트 스레드"""
    
    data_updated = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, api: UpbitAPI):
        super().__init__()
        self.api = api
        self.running = True
        self.update_interval = 3  # 3초마다 업데이트
    
    def run(self):
        """스레드 실행"""
        while self.running:
            try:
                # 계좌 정보 업데이트
                accounts_result = self.api.get_accounts()
                
                # 현재가 정보 업데이트 (주요 코인들)
                major_markets = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-ADA', 'KRW-DOT']
                ticker_result = self.api.get_ticker(major_markets)
                
                # 결과 전송
                self.data_updated.emit({
                    'accounts': accounts_result,
                    'tickers': ticker_result,
                    'timestamp': datetime.now()
                })
                
                self.msleep(self.update_interval * 1000)
                
            except Exception as e:
                self.error_occurred.emit(str(e))
                self.msleep(5000)  # 에러 시 5초 대기
    
    def stop(self):
        """스레드 중지"""
        self.running = False
        self.quit()
        self.wait()

class UpbitTraderMainWindow(QMainWindow):
    """업비트 거래 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        # API 초기화
        self.api = UpbitAPI()
        
        # UI 설정
        self.is_dark_theme = True
        self.current_market = "KRW-BTC"
        self.markets_data = []
        self.accounts_data = []
        
        # 타이머 설정
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        
        # 백그라운드 업데이트 스레드
        self.data_thread = DataUpdateThread(self.api)
        self.data_thread.data_updated.connect(self.on_data_updated)
        self.data_thread.error_occurred.connect(self.on_error_occurred)
        
        # UI 초기화
        self.init_ui()
        self.apply_theme()
        self.load_markets()
        
        # 자동 업데이트 시작
        if self.api.is_authenticated():
            self.start_auto_update()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("업비트 암호화폐 거래 프로그램")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout(central_widget)
        
        # 스플리터로 좌우 분할
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 좌측 패널 (자산 및 시세)
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # 우측 패널 (거래)
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # 스플리터 비율 설정 (7:3)
        splitter.setSizes([700, 300])
        
        # 상태바 설정
        self.create_status_bar()
        
        # 메뉴바 설정
        self.create_menu_bar()
    
    def create_left_panel(self):
        """좌측 패널 생성 (자산 현황 및 시세)"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 탭 위젯 생성
        tab_widget = QTabWidget()
        
        # 자산 현황 탭
        assets_tab = self.create_assets_tab()
        tab_widget.addTab(assets_tab, "💰 자산 현황")
        
        # 시세 현황 탭
        market_tab = self.create_market_tab()
        tab_widget.addTab(market_tab, "📈 시세 현황")
        
        left_layout.addWidget(tab_widget)
        
        return left_widget
    
    def create_right_panel(self):
        """우측 패널 생성 (거래)"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 거래 패널
        trading_panel = self.create_trading_panel()
        right_layout.addWidget(trading_panel)
        
        # 주문 현황 패널
        orders_panel = self.create_orders_panel()
        right_layout.addWidget(orders_panel)
        
        return right_widget
    
    def create_assets_tab(self):
        """자산 현황 탭 생성"""
        assets_widget = QWidget()
        assets_layout = QVBoxLayout(assets_widget)
        
        # 제목
        title_label = QLabel("보유 자산 현황")
        title_label.setProperty("title", True)
        assets_layout.addWidget(title_label)
        
        # 자산 요약 카드
        summary_frame = self.create_assets_summary()
        assets_layout.addWidget(summary_frame)
        
        # 자산 테이블
        self.assets_table = QTableWidget()
        self.setup_assets_table()
        assets_layout.addWidget(self.assets_table)
        
        # 새로고침 버튼
        refresh_btn = QPushButton("🔄 자산 새로고침")
        refresh_btn.clicked.connect(self.refresh_assets)
        assets_layout.addWidget(refresh_btn)
        
        return assets_widget
    
    def create_market_tab(self):
        """시세 현황 탭 생성"""
        market_widget = QWidget()
        market_layout = QVBoxLayout(market_widget)
        
        # 제목
        title_label = QLabel("실시간 시세")
        title_label.setProperty("title", True)
        market_layout.addWidget(title_label)
        
        # 시세 테이블
        self.market_table = QTableWidget()
        self.setup_market_table()
        market_layout.addWidget(self.market_table)
        
        return market_widget
    
    def create_trading_panel(self):
        """거래 패널 생성"""
        trading_group = QGroupBox("💱 주문하기")
        trading_layout = QVBoxLayout(trading_group)
        
        # 종목 선택
        market_layout = QHBoxLayout()
        market_layout.addWidget(QLabel("종목:"))
        self.market_combo = QComboBox()
        self.market_combo.currentTextChanged.connect(self.on_market_changed)
        market_layout.addWidget(self.market_combo)
        trading_layout.addLayout(market_layout)
        
        # 현재가 표시
        self.current_price_label = QLabel("현재가: -")
        self.current_price_label.setProperty("subtitle", True)
        trading_layout.addWidget(self.current_price_label)
        
        # 주문 타입
        order_type_layout = QHBoxLayout()
        order_type_layout.addWidget(QLabel("주문타입:"))
        self.order_type_combo = QComboBox()
        self.order_type_combo.addItems(["시장가 매수", "지정가 매수", "시장가 매도", "지정가 매도"])
        order_type_layout.addWidget(self.order_type_combo)
        trading_layout.addLayout(order_type_layout)
        
        # 주문 금액/수량
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("금액(KRW):"))
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("예: 10000")
        amount_layout.addWidget(self.amount_input)
        trading_layout.addLayout(amount_layout)
        
        # 주문 버튼
        self.order_button = QPushButton("🛒 주문 실행")
        self.order_button.setProperty("orderType", "buy")
        self.order_button.clicked.connect(self.place_order)
        trading_layout.addWidget(self.order_button)
        
        return trading_group
    
    def create_orders_panel(self):
        """주문 현황 패널 생성"""
        orders_group = QGroupBox("📋 주문 현황")
        orders_layout = QVBoxLayout(orders_group)
        
        # 주문 테이블
        self.orders_table = QTableWidget()
        self.setup_orders_table()
        orders_layout.addWidget(self.orders_table)
        
        # 주문 새로고침 버튼
        refresh_orders_btn = QPushButton("🔄 주문 현황 새로고침")
        refresh_orders_btn.clicked.connect(self.refresh_orders)
        orders_layout.addWidget(refresh_orders_btn)
        
        return orders_group
    
    def create_assets_summary(self):
        """자산 요약 카드 생성"""
        summary_frame = QFrame()
        summary_layout = QHBoxLayout(summary_frame)
        
        # 총 자산
        total_asset_layout = QVBoxLayout()
        total_asset_layout.addWidget(QLabel("총 자산"))
        self.total_asset_label = QLabel("0 KRW")
        self.total_asset_label.setProperty("subtitle", True)
        total_asset_layout.addWidget(self.total_asset_label)
        summary_layout.addLayout(total_asset_layout)
        
        # 보유 KRW
        krw_balance_layout = QVBoxLayout()
        krw_balance_layout.addWidget(QLabel("보유 KRW"))
        self.krw_balance_label = QLabel("0 KRW")
        self.krw_balance_label.setProperty("subtitle", True)
        krw_balance_layout.addWidget(self.krw_balance_label)
        summary_layout.addLayout(krw_balance_layout)
        
        # 암호화폐 평가액
        crypto_value_layout = QVBoxLayout()
        crypto_value_layout.addWidget(QLabel("암호화폐"))
        self.crypto_value_label = QLabel("0 KRW")
        self.crypto_value_label.setProperty("subtitle", True)
        crypto_value_layout.addWidget(self.crypto_value_label)
        summary_layout.addLayout(crypto_value_layout)
        
        return summary_frame
    
    def setup_assets_table(self):
        """자산 테이블 설정"""
        headers = ["코인", "보유수량", "평균매수가", "현재가", "평가금액", "수익률"]
        self.assets_table.setColumnCount(len(headers))
        self.assets_table.setHorizontalHeaderLabels(headers)
        
        # 테이블 설정
        self.assets_table.setAlternatingRowColors(True)
        self.assets_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.assets_table.horizontalHeader().setStretchLastSection(True)
        
        # 컬럼 너비 조정
        header = self.assets_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        
        self.assets_table.setColumnWidth(0, 80)
        self.assets_table.setColumnWidth(5, 100)
    
    def setup_market_table(self):
        """시세 테이블 설정"""
        headers = ["종목", "현재가", "전일대비", "변동률", "거래량"]
        self.market_table.setColumnCount(len(headers))
        self.market_table.setHorizontalHeaderLabels(headers)
        
        # 테이블 설정
        self.market_table.setAlternatingRowColors(True)
        self.market_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.market_table.horizontalHeader().setStretchLastSection(True)
        
        # 컬럼 너비 조정
        header = self.market_table.horizontalHeader()
        for i in range(len(headers)):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
    
    def setup_orders_table(self):
        """주문 테이블 설정"""
        headers = ["종목", "주문타입", "수량", "가격", "상태", "시간"]
        self.orders_table.setColumnCount(len(headers))
        self.orders_table.setHorizontalHeaderLabels(headers)
        
        # 테이블 설정
        self.orders_table.setAlternatingRowColors(True)
        self.orders_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.orders_table.horizontalHeader().setStretchLastSection(True)
        
        # 컬럼 너비 조정
        header = self.orders_table.horizontalHeader()
        for i in range(len(headers)):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
    
    def create_status_bar(self):
        """상태바 생성"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 연결 상태
        self.connection_label = QLabel("연결 상태: 확인 중...")
        self.connection_label.setProperty("status", "warning")
        self.status_bar.addWidget(self.connection_label)
        
        # 마지막 업데이트 시간
        self.last_update_label = QLabel("마지막 업데이트: -")
        self.status_bar.addPermanentWidget(self.last_update_label)
        
        # 프로그레스바
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
    
    def create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일")
        
        # 설정 메뉴
        settings_menu = menubar.addMenu("설정")
        
        # 테마 변경 액션
        theme_action = settings_menu.addAction("다크/라이트 테마 전환")
        theme_action.triggered.connect(self.toggle_theme)
        
        # 자동 업데이트 설정
        auto_update_action = settings_menu.addAction("자동 업데이트 ON/OFF")
        auto_update_action.triggered.connect(self.toggle_auto_update)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")
        about_action = help_menu.addAction("정보")
        about_action.triggered.connect(self.show_about)
    
    def apply_theme(self):
        """테마 적용"""
        style = get_theme_style(self.is_dark_theme)
        self.setStyleSheet(style)
        
        # 연결 상태 업데이트
        if self.api.is_authenticated():
            self.connection_label.setText("연결 상태: 연결됨")
            self.connection_label.setProperty("status", "connected")
        else:
            self.connection_label.setText("연결 상태: API 키 없음")
            self.connection_label.setProperty("status", "disconnected")
        
        # 스타일 새로고침
        self.connection_label.style().unpolish(self.connection_label)
        self.connection_label.style().polish(self.connection_label)
    
    def load_markets(self):
        """마켓 목록 로드"""
        try:
            result = self.api.get_markets(is_details=True)
            if result['status'] == 'success':
                self.markets_data = result['data']
                
                # 콤보박스에 마켓 추가
                self.market_combo.clear()
                for market in self.markets_data:
                    self.market_combo.addItem(f"{market['market']} ({market['korean_name']})")
                
                # 기본값 설정
                if self.markets_data:
                    btc_index = next((i for i, m in enumerate(self.markets_data) if m['market'] == 'KRW-BTC'), 0)
                    self.market_combo.setCurrentIndex(btc_index)
                
        except Exception as e:
            self.show_error_message(f"마켓 정보 로드 실패: {e}")
    
    def start_auto_update(self):
        """자동 업데이트 시작"""
        if not self.data_thread.isRunning():
            self.data_thread.start()
        
        self.update_timer.start(3000)  # 3초마다 UI 업데이트
    
    def stop_auto_update(self):
        """자동 업데이트 중지"""
        self.update_timer.stop()
        if self.data_thread.isRunning():
            self.data_thread.stop()
    
    def on_data_updated(self, data):
        """데이터 업데이트 이벤트 처리"""
        try:
            # 계좌 정보 업데이트
            if 'accounts' in data and data['accounts']['status'] == 'success':
                self.accounts_data = data['accounts']['data']
                self.update_assets_display()
            
            # 시세 정보 업데이트
            if 'tickers' in data and data['tickers']['status'] == 'success':
                self.update_market_display(data['tickers']['data'])
            
            # 마지막 업데이트 시간
            self.last_update_label.setText(f"마지막 업데이트: {data['timestamp'].strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.show_error_message(f"데이터 업데이트 오류: {e}")
    
    def on_error_occurred(self, error_msg):
        """에러 발생 이벤트 처리"""
        self.show_error_message(f"백그라운드 업데이트 오류: {error_msg}")
    
    def update_data(self):
        """데이터 업데이트"""
        # 현재가 업데이트 (선택된 종목)
        if hasattr(self, 'market_combo') and self.market_combo.currentText():
            try:
                market_code = self.market_combo.currentText().split(' ')[0]
                result = self.api.get_ticker([market_code])
                if result['status'] == 'success' and result['data']:
                    ticker = result['data'][0]
                    price = format_currency(ticker['trade_price'])
                    change = ticker['change']
                    change_rate = format_percentage(ticker['change_rate'] * 100)
                    
                    # 현재가 라벨 업데이트
                    price_color = get_price_color(ticker['change_price'])
                    self.current_price_label.setText(f"현재가: {price} KRW ({change_rate})")
                    self.current_price_label.setStyleSheet(f"color: {price_color};")
                    
            except Exception as e:
                pass  # 에러 무시
    
    def update_assets_display(self):
        """자산 현황 표시 업데이트"""
        try:
            if not self.accounts_data:
                return
            
            # 테이블 초기화
            self.assets_table.setRowCount(0)
            
            total_krw = 0
            total_crypto = 0
            
            for account in self.accounts_data:
                currency = account['currency']
                balance = float(account['balance'])
                locked = float(account['locked'])
                total_balance = balance + locked
                
                if total_balance <= 0:
                    continue
                
                if currency == 'KRW':
                    total_krw = total_balance
                    continue
                
                # 암호화폐 자산 추가
                row = self.assets_table.rowCount()
                self.assets_table.insertRow(row)
                
                # 현재가 조회
                market_code = f"KRW-{currency}"
                current_price = 0
                try:
                    ticker_result = self.api.get_ticker([market_code])
                    if ticker_result['status'] == 'success' and ticker_result['data']:
                        current_price = ticker_result['data'][0]['trade_price']
                except:
                    pass
                
                # 평가금액 계산
                evaluation = total_balance * current_price
                total_crypto += evaluation
                
                # 테이블에 데이터 추가
                self.assets_table.setItem(row, 0, QTableWidgetItem(currency))
                self.assets_table.setItem(row, 1, QTableWidgetItem(f"{total_balance:.8f}"))
                self.assets_table.setItem(row, 2, QTableWidgetItem("-"))  # 평균매수가는 별도 API 필요
                self.assets_table.setItem(row, 3, QTableWidgetItem(format_currency(current_price)))
                self.assets_table.setItem(row, 4, QTableWidgetItem(format_currency(evaluation)))
                self.assets_table.setItem(row, 5, QTableWidgetItem("-"))  # 수익률은 별도 계산 필요
            
            # 요약 정보 업데이트
            total_asset = total_krw + total_crypto
            self.total_asset_label.setText(format_currency(total_asset))
            self.krw_balance_label.setText(format_currency(total_krw))
            self.crypto_value_label.setText(format_currency(total_crypto))
            
        except Exception as e:
            self.show_error_message(f"자산 표시 업데이트 오류: {e}")
    
    def update_market_display(self, tickers_data):
        """시세 현황 표시 업데이트"""
        try:
            self.market_table.setRowCount(len(tickers_data))
            
            for row, ticker in enumerate(tickers_data):
                market = ticker['market']
                current_price = format_currency(ticker['trade_price'])
                change_price = ticker['change_price']
                change_rate = format_percentage(ticker['change_rate'] * 100)
                volume = format_currency(ticker['acc_trade_volume_24h'])
                
                # 색상 설정
                price_color = get_price_color(change_price)
                
                # 테이블에 데이터 추가
                market_item = QTableWidgetItem(market)
                self.market_table.setItem(row, 0, market_item)
                
                price_item = QTableWidgetItem(current_price)
                price_item.setForeground(price_color)
                self.market_table.setItem(row, 1, price_item)
                
                change_item = QTableWidgetItem(format_currency(change_price))
                change_item.setForeground(price_color)
                self.market_table.setItem(row, 2, change_item)
                
                rate_item = QTableWidgetItem(change_rate)
                rate_item.setForeground(price_color)
                self.market_table.setItem(row, 3, rate_item)
                
                volume_item = QTableWidgetItem(volume)
                self.market_table.setItem(row, 4, volume_item)
                
        except Exception as e:
            self.show_error_message(f"시세 표시 업데이트 오류: {e}")
    
    def on_market_changed(self, market_text):
        """종목 변경 이벤트"""
        if market_text:
            self.current_market = market_text.split(' ')[0]
            self.update_data()
    
    def place_order(self):
        """주문 실행"""
        try:
            if not self.api.is_authenticated():
                self.show_error_message("API 키가 설정되지 않았습니다.")
                return
            
            market = self.current_market
            order_type_text = self.order_type_combo.currentText()
            amount_text = self.amount_input.text().strip()
            
            if not amount_text:
                self.show_error_message("주문 금액을 입력해주세요.")
                return
            
            # 주문 확인 다이얼로그
            reply = QMessageBox.question(
                self, 
                "주문 확인",
                f"종목: {market}\n주문타입: {order_type_text}\n금액: {amount_text} KRW\n\n주문을 실행하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # 주문 파라미터 설정
            side = 'bid' if '매수' in order_type_text else 'ask'
            ord_type = 'price' if '시장가' in order_type_text else 'limit'
            
            # 진행바 표시
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            
            # 주문 실행
            result = self.api.place_order(
                market=market,
                side=side,
                ord_type=ord_type,
                price=amount_text
            )
            
            # 진행바 숨김
            self.progress_bar.setVisible(False)
            
            if result['status'] == 'success':
                QMessageBox.information(self, "주문 성공", "주문이 성공적으로 실행되었습니다.")
                self.amount_input.clear()
                self.refresh_orders()
                self.refresh_assets()
            else:
                self.show_error_message(f"주문 실패: {result['message']}")
                
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.show_error_message(f"주문 실행 오류: {e}")
    
    def refresh_assets(self):
        """자산 새로고침"""
        try:
            if not self.api.is_authenticated():
                return
            
            result = self.api.get_accounts()
            if result['status'] == 'success':
                self.accounts_data = result['data']
                self.update_assets_display()
                
        except Exception as e:
            self.show_error_message(f"자산 새로고침 오류: {e}")
    
    def refresh_orders(self):
        """주문 현황 새로고침"""
        try:
            if not self.api.is_authenticated():
                return
            
            result = self.api.get_orders(state='wait')
            if result['status'] == 'success':
                orders_data = result['data']
                
                # 테이블 업데이트
                self.orders_table.setRowCount(len(orders_data))
                
                for row, order in enumerate(orders_data):
                    self.orders_table.setItem(row, 0, QTableWidgetItem(order['market']))
                    self.orders_table.setItem(row, 1, QTableWidgetItem(order['side']))
                    self.orders_table.setItem(row, 2, QTableWidgetItem(order.get('volume', '-')))
                    self.orders_table.setItem(row, 3, QTableWidgetItem(order.get('price', '-')))
                    self.orders_table.setItem(row, 4, QTableWidgetItem(order['state']))
                    
                    # 시간 포맷팅
                    created_at = order['created_at'][:19].replace('T', ' ')
                    self.orders_table.setItem(row, 5, QTableWidgetItem(created_at))
                
        except Exception as e:
            self.show_error_message(f"주문 현황 새로고침 오류: {e}")
    
    def toggle_theme(self):
        """테마 전환"""
        self.is_dark_theme = not self.is_dark_theme
        self.apply_theme()
    
    def toggle_auto_update(self):
        """자동 업데이트 전환"""
        if self.update_timer.isActive():
            self.stop_auto_update()
            QMessageBox.information(self, "알림", "자동 업데이트가 중지되었습니다.")
        else:
            self.start_auto_update()
            QMessageBox.information(self, "알림", "자동 업데이트가 시작되었습니다.")
    
    def show_about(self):
        """정보 다이얼로그 표시"""
        QMessageBox.about(
            self,
            "업비트 거래 프로그램 정보",
            "업비트 암호화폐 거래 UI 프로그램 v1.0\n\n"
            "PySide6 기반의 모던한 거래 인터페이스\n"
            "- 실시간 자산 현황 조회\n"
            "- 실시간 시세 확인\n"
            "- 주문 실행 및 관리\n"
            "- 다크/라이트 테마 지원\n\n"
            "⚠️ 실제 거래 시 신중하게 진행하세요!"
        )
    
    def show_error_message(self, message):
        """에러 메시지 표시"""
        QMessageBox.critical(self, "오류", message)
    
    def closeEvent(self, event):
        """윈도우 종료 이벤트"""
        self.stop_auto_update()
        event.accept()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("업비트 거래 프로그램")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Upbit Trader")
    
    # 메인 윈도우 생성 및 표시
    window = UpbitTraderMainWindow()
    window.show()
    
    # 이벤트 루프 실행
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 