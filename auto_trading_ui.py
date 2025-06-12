#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 자동매매 UI 확장 프로그램
기존 거래 UI에 자동매매 기능 추가
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QLineEdit,
    QComboBox, QFrame, QGroupBox, QTabWidget, QStatusBar, QMessageBox,
    QSplitter, QProgressBar, QHeaderView, QAbstractItemView, QCheckBox,
    QSpinBox, QDoubleSpinBox, QTextEdit, QGridLayout
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, Signal, QPropertyAnimation, QEasingCurve,
    QRect, QSize
)
from PySide6.QtGui import QFont, QIcon, QPalette, QPixmap, QColor, QBrush

# 기존 모듈 import
from upbit_trader_ui import UpbitTraderMainWindow, DataUpdateThread
from upbit_api import UpbitAPI
from ui_styles import get_theme_style, get_price_color, format_currency, format_percentage
from auto_trading_strategy import TradingStrategy

class AutoTradingThread(QThread):
    """자동매매 실행 스레드"""
    
    trade_executed = Signal(dict)
    strategy_updated = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, strategy: TradingStrategy):
        super().__init__()
        self.strategy = strategy
        self.running = False
    
    def run(self):
        """자동매매 스레드 실행"""
        self.running = True
        self.strategy.is_running = True
        
        while self.running:
            try:
                # 전략 실행
                result = self.strategy.run_strategy()
                
                if result["status"] == "success":
                    self.strategy_updated.emit(result)
                    
                    if result["action"] in ["BUY", "SELL", "STOP_LOSS", "TAKE_PROFIT", "TIME_LIMIT"]:
                        self.trade_executed.emit(result)
                else:
                    self.error_occurred.emit(result.get("message", "Unknown error"))
                
                # 설정된 간격만큼 대기
                self.msleep(self.strategy.config["trade_interval"] * 1000)
                
            except Exception as e:
                self.error_occurred.emit(str(e))
                self.msleep(60000)  # 에러 시 1분 대기
    
    def stop(self):
        """자동매매 중지"""
        self.running = False
        self.strategy.is_running = False
        self.quit()
        self.wait()

class AutoUpbitTraderMainWindow(UpbitTraderMainWindow):
    """자동매매 기능이 추가된 업비트 거래 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        # 자동매매 관련 초기화
        self.trading_strategy = None
        self.auto_trading_thread = None
        self.strategy_config = {}
        
        # 기존 UI 수정
        self.modify_ui_for_auto_trading()
        
        # 자동매매 초기화
        self.init_auto_trading()
    
    def modify_ui_for_auto_trading(self):
        """기존 UI에 자동매매 기능 추가"""
        # 윈도우 제목 변경
        self.setWindowTitle("업비트 자동매매 프로그램 v2.0")
        
        # 우측 패널에 자동매매 탭 추가
        right_widget = self.centralWidget().layout().itemAt(0).widget().widget(1)
        right_layout = right_widget.layout()
        
        # 기존 위젯들 가져오기
        trading_panel = right_layout.itemAt(0).widget()
        orders_panel = right_layout.itemAt(1).widget()
        
        # 새로운 탭 위젯 생성
        right_tab_widget = QTabWidget()
        
        # 수동 거래 탭
        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)
        manual_layout.addWidget(trading_panel)
        manual_layout.addWidget(orders_panel)
        right_tab_widget.addTab(manual_tab, "🔧 수동 거래")
        
        # 자동매매 탭
        auto_tab = self.create_auto_trading_tab()
        right_tab_widget.addTab(auto_tab, "🤖 자동매매")
        
        # 기존 레이아웃 클리어 후 탭 위젯 추가
        while right_layout.count():
            right_layout.takeAt(0)
        right_layout.addWidget(right_tab_widget)
    
    def create_auto_trading_tab(self):
        """자동매매 탭 생성"""
        auto_widget = QWidget()
        auto_layout = QVBoxLayout(auto_widget)
        
        # 자동매매 컨트롤 패널
        control_panel = self.create_auto_trading_control()
        auto_layout.addWidget(control_panel)
        
        # 전략 설정 패널
        strategy_panel = self.create_strategy_config_panel()
        auto_layout.addWidget(strategy_panel)
        
        # 거래 로그 패널
        log_panel = self.create_trading_log_panel()
        auto_layout.addWidget(log_panel)
        
        return auto_widget
    
    def create_auto_trading_control(self):
        """자동매매 컨트롤 패널 생성"""
        control_group = QGroupBox("🤖 자동매매 제어")
        control_layout = QVBoxLayout(control_group)
        
        # 상태 표시
        status_layout = QHBoxLayout()
        self.auto_status_label = QLabel("⏹️ 중지됨")
        self.auto_status_label.setProperty("subtitle", True)
        status_layout.addWidget(QLabel("상태:"))
        status_layout.addWidget(self.auto_status_label)
        status_layout.addStretch()
        control_layout.addLayout(status_layout)
        
        # 시뮬레이션 모드
        sim_layout = QHBoxLayout()
        self.simulation_checkbox = QCheckBox("시뮬레이션 모드 (실제 거래 안함)")
        self.simulation_checkbox.setChecked(True)
        self.simulation_checkbox.stateChanged.connect(self.on_simulation_mode_changed)
        sim_layout.addWidget(self.simulation_checkbox)
        control_layout.addLayout(sim_layout)
        
        # 컨트롤 버튼들
        button_layout = QHBoxLayout()
        
        self.start_auto_btn = QPushButton("🚀 자동매매 시작")
        self.start_auto_btn.setProperty("orderType", "buy")
        self.start_auto_btn.clicked.connect(self.start_auto_trading)
        button_layout.addWidget(self.start_auto_btn)
        
        self.stop_auto_btn = QPushButton("⏹️ 자동매매 중지")
        self.stop_auto_btn.setProperty("orderType", "sell")
        self.stop_auto_btn.clicked.connect(self.stop_auto_trading)
        self.stop_auto_btn.setEnabled(False)
        button_layout.addWidget(self.stop_auto_btn)
        
        control_layout.addLayout(button_layout)
        
        # 성과 요약
        performance_layout = QGridLayout()
        performance_layout.addWidget(QLabel("총 거래:"), 0, 0)
        self.total_trades_label = QLabel("0")
        performance_layout.addWidget(self.total_trades_label, 0, 1)
        
        performance_layout.addWidget(QLabel("총 수익:"), 0, 2)
        self.total_profit_label = QLabel("0 KRW")
        performance_layout.addWidget(self.total_profit_label, 0, 3)
        
        performance_layout.addWidget(QLabel("승률:"), 1, 0)
        self.win_rate_label = QLabel("0%")
        performance_layout.addWidget(self.win_rate_label, 1, 1)
        
        performance_layout.addWidget(QLabel("현재 포지션:"), 1, 2)
        self.position_label = QLabel("없음")
        performance_layout.addWidget(self.position_label, 1, 3)
        
        control_layout.addLayout(performance_layout)
        
        return control_group
    
    def create_strategy_config_panel(self):
        """전략 설정 패널 생성"""
        config_group = QGroupBox("⚙️ 전략 설정")
        config_layout = QGridLayout(config_group)
        
        row = 0
        
        # 기본 설정
        config_layout.addWidget(QLabel("종목:"), row, 0)
        self.market_config_combo = QComboBox()
        self.market_config_combo.addItems(["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-ADA"])
        config_layout.addWidget(self.market_config_combo, row, 1)
        
        config_layout.addWidget(QLabel("거래 간격(분):"), row, 2)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(5)
        config_layout.addWidget(self.interval_spin, row, 3)
        row += 1
        
        # 투자 설정
        config_layout.addWidget(QLabel("최대 투자 비율(%):"), row, 0)
        self.investment_ratio_spin = QDoubleSpinBox()
        self.investment_ratio_spin.setRange(1, 50)
        self.investment_ratio_spin.setValue(10)
        self.investment_ratio_spin.setSuffix("%")
        config_layout.addWidget(self.investment_ratio_spin, row, 1)
        
        config_layout.addWidget(QLabel("최소 주문금액:"), row, 2)
        self.min_amount_spin = QSpinBox()
        self.min_amount_spin.setRange(5000, 100000)
        self.min_amount_spin.setValue(5000)
        self.min_amount_spin.setSuffix(" KRW")
        config_layout.addWidget(self.min_amount_spin, row, 3)
        row += 1
        
        # 이동평균 설정
        config_layout.addWidget(QLabel("단기 이동평균:"), row, 0)
        self.short_ma_spin = QSpinBox()
        self.short_ma_spin.setRange(3, 20)
        self.short_ma_spin.setValue(5)
        config_layout.addWidget(self.short_ma_spin, row, 1)
        
        config_layout.addWidget(QLabel("장기 이동평균:"), row, 2)
        self.long_ma_spin = QSpinBox()
        self.long_ma_spin.setRange(10, 50)
        self.long_ma_spin.setValue(20)
        config_layout.addWidget(self.long_ma_spin, row, 3)
        row += 1
        
        # RSI 설정
        config_layout.addWidget(QLabel("RSI 과매도:"), row, 0)
        self.rsi_oversold_spin = QSpinBox()
        self.rsi_oversold_spin.setRange(10, 40)
        self.rsi_oversold_spin.setValue(30)
        config_layout.addWidget(self.rsi_oversold_spin, row, 1)
        
        config_layout.addWidget(QLabel("RSI 과매수:"), row, 2)
        self.rsi_overbought_spin = QSpinBox()
        self.rsi_overbought_spin.setRange(60, 90)
        self.rsi_overbought_spin.setValue(70)
        config_layout.addWidget(self.rsi_overbought_spin, row, 3)
        row += 1
        
        # 리스크 관리 설정
        config_layout.addWidget(QLabel("손절매(%):"), row, 0)
        self.stop_loss_spin = QDoubleSpinBox()
        self.stop_loss_spin.setRange(-10, -1)
        self.stop_loss_spin.setValue(-3)
        self.stop_loss_spin.setSuffix("%")
        config_layout.addWidget(self.stop_loss_spin, row, 1)
        
        config_layout.addWidget(QLabel("익절매(%):"), row, 2)
        self.take_profit_spin = QDoubleSpinBox()
        self.take_profit_spin.setRange(1, 20)
        self.take_profit_spin.setValue(5)
        self.take_profit_spin.setSuffix("%")
        config_layout.addWidget(self.take_profit_spin, row, 3)
        row += 1
        
        # 설정 적용 버튼
        apply_btn = QPushButton("✅ 설정 적용")
        apply_btn.clicked.connect(self.apply_strategy_config)
        config_layout.addWidget(apply_btn, row, 0, 1, 4)
        
        return config_group
    
    def create_trading_log_panel(self):
        """거래 로그 패널 생성"""
        log_group = QGroupBox("📋 거래 로그")
        log_layout = QVBoxLayout(log_group)
        
        # 로그 텍스트 영역
        self.trading_log = QTextEdit()
        self.trading_log.setMaximumHeight(200)
        self.trading_log.setReadOnly(True)
        log_layout.addWidget(self.trading_log)
        
        # 로그 제어 버튼
        log_btn_layout = QHBoxLayout()
        
        clear_log_btn = QPushButton("🗑️ 로그 지우기")
        clear_log_btn.clicked.connect(self.clear_trading_log)
        log_btn_layout.addWidget(clear_log_btn)
        
        save_log_btn = QPushButton("💾 로그 저장")
        save_log_btn.clicked.connect(self.save_trading_log)
        log_btn_layout.addWidget(save_log_btn)
        
        log_btn_layout.addStretch()
        log_layout.addLayout(log_btn_layout)
        
        return log_group
    
    def init_auto_trading(self):
        """자동매매 초기화"""
        self.apply_strategy_config()
        self.add_trading_log("자동매매 시스템 초기화 완료")
    
    def apply_strategy_config(self):
        """전략 설정 적용"""
        try:
            config = {
                "market": self.market_config_combo.currentText(),
                "trade_interval": self.interval_spin.value() * 60,  # 분을 초로 변환
                "simulation_mode": self.simulation_checkbox.isChecked(),
                
                "max_investment_ratio": self.investment_ratio_spin.value() / 100,
                "min_order_amount": self.min_amount_spin.value(),
                
                "short_ma_period": self.short_ma_spin.value(),
                "long_ma_period": self.long_ma_spin.value(),
                "rsi_period": 14,
                "rsi_oversold": self.rsi_oversold_spin.value(),
                "rsi_overbought": self.rsi_overbought_spin.value(),
                
                "stop_loss_ratio": self.stop_loss_spin.value() / 100,
                "take_profit_ratio": self.take_profit_spin.value() / 100,
                "max_holding_time": 24,
                
                "min_volume_threshold": 1000000,
                "price_change_threshold": 0.01,
            }
            
            self.strategy_config = config
            self.trading_strategy = TradingStrategy(self.api, config)
            
            self.add_trading_log(f"전략 설정 적용 완료: {config['market']}")
            QMessageBox.information(self, "설정 완료", "전략 설정이 적용되었습니다.")
            
        except Exception as e:
            self.add_trading_log(f"설정 적용 실패: {e}")
            self.show_error_message(f"설정 적용 실패: {e}")
    
    def start_auto_trading(self):
        """자동매매 시작"""
        try:
            if not self.trading_strategy:
                self.apply_strategy_config()
            
            if not self.api.is_authenticated() and not self.simulation_checkbox.isChecked():
                self.show_error_message("실제 거래를 위해서는 API 키가 필요합니다.")
                return
            
            # 확인 다이얼로그
            mode_text = "시뮬레이션" if self.simulation_checkbox.isChecked() else "실제 거래"
            reply = QMessageBox.question(
                self,
                "자동매매 시작 확인",
                f"자동매매를 시작하시겠습니까?\n\n"
                f"모드: {mode_text}\n"
                f"종목: {self.strategy_config['market']}\n"
                f"거래 간격: {self.strategy_config['trade_interval']//60}분\n"
                f"최대 투자 비율: {self.strategy_config['max_investment_ratio']*100}%\n\n"
                f"⚠️ {mode_text} 모드로 실행됩니다.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # 자동매매 스레드 시작
            if self.auto_trading_thread and self.auto_trading_thread.isRunning():
                self.auto_trading_thread.stop()
            
            self.auto_trading_thread = AutoTradingThread(self.trading_strategy)
            self.auto_trading_thread.trade_executed.connect(self.on_trade_executed)
            self.auto_trading_thread.strategy_updated.connect(self.on_strategy_updated)
            self.auto_trading_thread.error_occurred.connect(self.on_auto_trading_error)
            
            self.auto_trading_thread.start()
            
            # UI 상태 업데이트
            self.auto_status_label.setText("🟢 실행 중")
            self.start_auto_btn.setEnabled(False)
            self.stop_auto_btn.setEnabled(True)
            
            mode_emoji = "🎮" if self.simulation_checkbox.isChecked() else "💰"
            self.add_trading_log(f"{mode_emoji} 자동매매 시작 - {mode_text} 모드")
            
        except Exception as e:
            self.add_trading_log(f"자동매매 시작 실패: {e}")
            self.show_error_message(f"자동매매 시작 실패: {e}")
    
    def stop_auto_trading(self):
        """자동매매 중지"""
        try:
            if self.auto_trading_thread and self.auto_trading_thread.isRunning():
                self.auto_trading_thread.stop()
            
            # UI 상태 업데이트
            self.auto_status_label.setText("⏹️ 중지됨")
            self.start_auto_btn.setEnabled(True)
            self.stop_auto_btn.setEnabled(False)
            
            self.add_trading_log("⏹️ 자동매매 중지")
            
        except Exception as e:
            self.add_trading_log(f"자동매매 중지 실패: {e}")
            self.show_error_message(f"자동매매 중지 실패: {e}")
    
    def on_trade_executed(self, result):
        """거래 실행 이벤트 처리"""
        action = result["action"]
        price = result["price"]
        success = result["success"]
        
        if success:
            emoji_map = {
                "BUY": "🟢",
                "SELL": "🔴", 
                "STOP_LOSS": "🛑",
                "TAKE_PROFIT": "🎯",
                "TIME_LIMIT": "⏰"
            }
            emoji = emoji_map.get(action, "🔄")
            
            self.add_trading_log(f"{emoji} {action} 실행 성공 @ {price:,.0f} KRW")
            
            # 성과 업데이트
            self.update_performance_display()
        else:
            self.add_trading_log(f"❌ {action} 실행 실패 @ {price:,.0f} KRW")
    
    def on_strategy_updated(self, result):
        """전략 업데이트 이벤트 처리"""
        action = result["action"]
        price = result["price"]
        analysis = result.get("analysis", {})
        
        if action == "HOLD":
            rsi = analysis.get("rsi", 0)
            short_ma = analysis.get("short_ma", 0)
            long_ma = analysis.get("long_ma", 0)
            
            # 간단한 상태 로그 (너무 많으면 스팸이 되므로 간소화)
            log_text = f"📊 분석: 가격={price:,.0f}, RSI={rsi:.1f}, MA({short_ma:.0f}/{long_ma:.0f})"
            
            # 기존 HOLD 로그가 있으면 업데이트, 없으면 추가
            cursor = self.trading_log.textCursor()
            cursor.movePosition(cursor.End)
            text = self.trading_log.toPlainText()
            
            if "📊 분석:" in text.split('\n')[-1]:
                # 마지막 줄이 분석 로그이면 업데이트
                cursor.select(cursor.LineUnderCursor)
                cursor.removeSelectedText()
                cursor.deletePreviousChar()  # 줄바꿈 제거
            
            self.trading_log.append(log_text)
        
        # 성과 표시 업데이트
        self.update_performance_display()
    
    def on_auto_trading_error(self, error_msg):
        """자동매매 에러 이벤트 처리"""
        self.add_trading_log(f"❌ 오류: {error_msg}")
    
    def on_simulation_mode_changed(self, state):
        """시뮬레이션 모드 변경 이벤트"""
        if self.trading_strategy:
            self.trading_strategy.config["simulation_mode"] = state == Qt.Checked
            mode_text = "시뮬레이션" if state == Qt.Checked else "실제 거래"
            self.add_trading_log(f"⚙️ 모드 변경: {mode_text}")
    
    def update_performance_display(self):
        """성과 표시 업데이트"""
        if not self.trading_strategy:
            return
        
        try:
            performance = self.trading_strategy.get_performance_summary()
            
            self.total_trades_label.setText(str(performance["total_trades"]))
            
            if self.simulation_checkbox.isChecked():
                self.total_profit_label.setText(f"{performance['total_profit_krw']:+,.0f} KRW")
            else:
                self.total_profit_label.setText("실제 거래 중")
            
            self.win_rate_label.setText(f"{performance['win_rate']:.1f}%")
            
            if performance["current_position"]:
                self.position_label.setText("포지션 보유 중")
                self.position_label.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.position_label.setText("없음")
                self.position_label.setStyleSheet("")
                
        except Exception as e:
            self.add_trading_log(f"성과 표시 업데이트 오류: {e}")
    
    def add_trading_log(self, message):
        """거래 로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.trading_log.append(log_entry)
        
        # 스크롤을 맨 아래로
        scrollbar = self.trading_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_trading_log(self):
        """거래 로그 지우기"""
        self.trading_log.clear()
        self.add_trading_log("로그가 초기화되었습니다.")
    
    def save_trading_log(self):
        """거래 로그 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trading_log_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.trading_log.toPlainText())
            
            self.add_trading_log(f"로그 저장 완료: {filename}")
            QMessageBox.information(self, "저장 완료", f"거래 로그가 {filename}에 저장되었습니다.")
            
        except Exception as e:
            self.add_trading_log(f"로그 저장 실패: {e}")
            self.show_error_message(f"로그 저장 실패: {e}")
    
    def closeEvent(self, event):
        """윈도우 종료 이벤트"""
        # 자동매매 중지
        if self.auto_trading_thread and self.auto_trading_thread.isRunning():
            self.stop_auto_trading()
        
        # 부모 클래스의 종료 이벤트 호출
        super().closeEvent(event)

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("업비트 자동매매 프로그램")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Auto Upbit Trader")
    
    # 메인 윈도우 생성 및 표시
    window = AutoUpbitTraderMainWindow()
    window.show()
    
    # 시작 안내 메시지
    QMessageBox.information(
        window,
        "자동매매 프로그램 시작",
        "🤖 업비트 자동매매 프로그램 v2.0\n\n"
        "⚠️ 중요한 안내사항:\n"
        "• 처음에는 반드시 '시뮬레이션 모드'로 테스트하세요\n"
        "• 실제 거래는 충분한 테스트 후 진행하세요\n"
        "• 투자 손실에 대한 책임은 사용자에게 있습니다\n"
        "• 전략 설정을 신중하게 검토하세요\n\n"
        "우측 '🤖 자동매매' 탭에서 설정할 수 있습니다."
    )
    
    # 이벤트 루프 실행
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 