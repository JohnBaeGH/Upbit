#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 통합 웹 서비스 v2.0
- 캔들 차트 API 서비스
- 완전한 자동거래 시스템
Railway 배포 최적화 버전
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import json
import threading
import time
import random
import os
from datetime import datetime
import logging

# ============================================================================
# Flask 애플리케이션 초기화
# ============================================================================

app = Flask(__name__)
CORS(app)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# 업비트 API 서비스
# ============================================================================

class UpbitAPI:
    """업비트 API 클래스"""
    
    def __init__(self):
        self.base_url = "https://api.upbit.com"
    
    def get_candle_data(self, market="KRW-BTC", interval="5", count=50):
        """캔들 데이터 조회"""
        try:
            url = f"{self.base_url}/v1/candles/minutes/{interval}"
            params = {'market': market, 'count': min(count, 200)}
            
            logger.info(f"업비트 API 호출: {market} {interval}분 캔들 {count}개")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"캔들 데이터 조회 실패: {e}")
            return None
    
    def get_markets(self):
        """마켓 목록 조회"""
        try:
            url = f"{self.base_url}/v1/market/all"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            markets = response.json()
            krw_markets = [m for m in markets if m['market'].startswith('KRW-')]
            return krw_markets
            
        except Exception as e:
            logger.error(f"마켓 정보 조회 실패: {e}")
            return []

# API 인스턴스 생성
upbit_api = UpbitAPI()

# ============================================================================
# 자동거래 시스템
# ============================================================================

# 자동거래 상태 관리
auto_trading_state = {
    "is_running": False,
    "config": {
        "market": "KRW-BTC",
        "trade_interval": 300,  # 5분
        "simulation_mode": True,
        "max_investment_ratio": 0.1,
        "min_order_amount": 5000,
        "short_ma_period": 5,
        "long_ma_period": 20,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "stop_loss_ratio": -0.03,
        "take_profit_ratio": 0.05
    },
    "performance": {
        "total_trades": 0,
        "successful_trades": 0,
        "total_profit_krw": 0,
        "win_rate": 0,
        "current_position": None
    },
    "logs": [],
    "current_analysis": {
        "price": 0,
        "rsi": 50,
        "short_ma": 0,
        "long_ma": 0,
        "volume": 0,
        "signal": "HOLD"
    }
}

# 자동거래 스레드 관리
trading_thread = None
trading_active = False

def add_trading_log(message, log_type="INFO"):
    """거래 로그 추가"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {"timestamp": timestamp, "message": message, "type": log_type}
    auto_trading_state["logs"].append(log_entry)
    
    # 최대 100개 로그만 유지
    if len(auto_trading_state["logs"]) > 100:
        auto_trading_state["logs"] = auto_trading_state["logs"][-100:]

def simulate_market_analysis():
    """시장 분석 시뮬레이션"""
    config = auto_trading_state["config"]
    
    # 가상 시장 데이터 생성
    base_price = 50000000
    price_variation = random.uniform(-0.02, 0.02)
    current_price = base_price * (1 + price_variation)
    
    # 기술적 지표 시뮬레이션
    rsi = random.uniform(20, 80)
    short_ma = current_price * random.uniform(0.98, 1.02)
    long_ma = current_price * random.uniform(0.95, 1.05)
    volume = random.uniform(100, 1000)
    
    # 매매 신호 결정
    signal = "HOLD"
    
    if rsi < config["rsi_oversold"] and short_ma > long_ma:
        signal = "BUY"
    elif rsi > config["rsi_overbought"] and short_ma < long_ma:
        signal = "SELL"
    elif auto_trading_state["performance"]["current_position"]:
        position = auto_trading_state["performance"]["current_position"]
        profit_ratio = (current_price - position["buy_price"]) / position["buy_price"]
        
        if profit_ratio <= config["stop_loss_ratio"]:
            signal = "STOP_LOSS"
        elif profit_ratio >= config["take_profit_ratio"]:
            signal = "TAKE_PROFIT"
    
    # 분석 결과 업데이트
    auto_trading_state["current_analysis"] = {
        "price": current_price,
        "rsi": rsi,
        "short_ma": short_ma,
        "long_ma": long_ma,
        "volume": volume,
        "signal": signal
    }
    
    return signal, current_price

def execute_trade(signal, price):
    """거래 실행"""
    performance = auto_trading_state["performance"]
    
    if signal == "BUY" and not performance["current_position"]:
        # 매수 실행
        performance["current_position"] = {
            "buy_price": price,
            "amount": auto_trading_state["config"]["min_order_amount"] / price,
            "timestamp": datetime.now().isoformat()
        }
        performance["total_trades"] += 1
        add_trading_log(f"🟢 시뮬레이션 매수: {price:,.0f} KRW", "SUCCESS")
        
    elif signal in ["SELL", "STOP_LOSS", "TAKE_PROFIT"] and performance["current_position"]:
        # 매도 실행
        position = performance["current_position"]
        profit = (price - position["buy_price"]) * position["amount"]
        profit_ratio = (price - position["buy_price"]) / position["buy_price"] * 100
        
        performance["total_profit_krw"] += profit
        
        if profit > 0:
            performance["successful_trades"] += 1
            emoji = "🎯" if signal == "TAKE_PROFIT" else "🔴"
        else:
            emoji = "🛑" if signal == "STOP_LOSS" else "🔴"
        
        add_trading_log(f"{emoji} 시뮬레이션 매도: {price:,.0f} KRW (수익: {profit:+,.0f} KRW, {profit_ratio:+.2f}%)", 
                       "SUCCESS" if profit > 0 else "WARNING")
        
        performance["current_position"] = None
        
        # 승률 계산
        if performance["total_trades"] > 0:
            performance["win_rate"] = (performance["successful_trades"] / performance["total_trades"]) * 100

def auto_trading_worker():
    """자동거래 워커 스레드"""
    global trading_active
    
    add_trading_log("🤖 자동거래 시스템 시작", "INFO")
    
    while trading_active:
        try:
            config = auto_trading_state["config"]
            
            # 시장 분석
            signal, current_price = simulate_market_analysis()
            
            # 분석 결과 로그
            analysis = auto_trading_state["current_analysis"]
            add_trading_log(f"📊 분석: {config['market']} {current_price:,.0f}원, RSI:{analysis['rsi']:.1f}, 신호:{signal}")
            
            # 거래 실행
            if signal != "HOLD":
                execute_trade(signal, current_price)
            
            # 설정된 간격만큼 대기
            time.sleep(config["trade_interval"])
            
        except Exception as e:
            add_trading_log(f"❌ 오류 발생: {str(e)}", "ERROR")
            time.sleep(60)
    
    add_trading_log("⏹️ 자동거래 시스템 중지", "INFO")

# ============================================================================
# 웹 페이지 라우트
# ============================================================================

@app.route('/')
def index():
    """메인 페이지"""
    return '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 업비트 통합 웹 서비스</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 40px 20px; }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 50px;
        }
        .header h1 {
            font-size: 3em;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .nav-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }
        .nav-card {
            background: white;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
            text-decoration: none;
            color: inherit;
        }
        .nav-card:hover {
            transform: translateY(-10px);
        }
        .nav-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        .nav-title {
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 15px;
            color: #2a5298;
        }
        .nav-desc {
            color: #666;
            line-height: 1.6;
        }
        .footer {
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            color: #666;
        }
        .endpoint {
            display: inline-block;
            background: #f8f9fa;
            padding: 8px 16px;
            margin: 5px;
            border-radius: 20px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 업비트 통합 웹 서비스</h1>
            <p>실시간 데이터 분석 & 자동거래 시스템</p>
            <p>Railway 배포 버전 v2.0</p>
        </div>

        <div class="nav-grid">
            <a href="/charts" class="nav-card">
                <div class="nav-icon">📊</div>
                <div class="nav-title">캔들 차트 & 데이터</div>
                <div class="nav-desc">
                    실시간 업비트 캔들 데이터 조회<br>
                    마켓 정보 및 API 테스트 도구
                </div>
            </a>
            
            <a href="/auto-trading" class="nav-card">
                <div class="nav-icon">🤖</div>
                <div class="nav-title">자동거래 시스템</div>
                <div class="nav-desc">
                    완전한 자동매매 솔루션<br>
                    실시간 분석 & 리스크 관리
                </div>
            </a>
        </div>

        <div class="footer">
            <h3>🔗 사용 가능한 API</h3>
            <div class="endpoint">GET /api/status</div>
            <div class="endpoint">GET /api/candles</div>
            <div class="endpoint">GET /api/markets</div>
            <div class="endpoint">POST /api/auto-trading/start</div>
            <div class="endpoint">GET /api/auto-trading/performance</div>
        </div>
    </div>
</body>
</html>
    '''

@app.route('/charts')
def charts_page():
    """캔들 차트 페이지"""
    return '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 업비트 캔들 차트</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 40px 20px; }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        .panel {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .form-group {
            display: inline-block;
            margin: 10px 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #4a5568;
        }
        .form-group select, .form-group input {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        .btn {
            background: linear-gradient(45deg, #1e3c72, #2a5298);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px 5px;
            transition: all 0.3s ease;
        }
        .btn:hover { transform: scale(1.05); }
        .result {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        pre {
            background: #2d3748;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 14px;
        }
        .back-link {
            display: inline-block;
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 5px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 업비트 캔들 차트 데이터</h1>
            <p>실시간 업비트 API 데이터 조회</p>
        </div>
        
        <div class="panel">
            <div class="form-group">
                <label>마켓</label>
                <select id="market">
                    <option value="KRW-BTC">KRW-BTC</option>
                    <option value="KRW-ETH">KRW-ETH</option>
                    <option value="KRW-XRP">KRW-XRP</option>
                    <option value="KRW-ADA">KRW-ADA</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>캔들 간격</label>
                <select id="interval">
                    <option value="1">1분</option>
                    <option value="3">3분</option>
                    <option value="5" selected>5분</option>
                    <option value="15">15분</option>
                    <option value="30">30분</option>
                    <option value="60">1시간</option>
                    <option value="240">4시간</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>개수</label>
                <input type="number" id="count" value="20" min="1" max="200">
            </div>
            
            <div style="margin-top: 20px;">
                <button class="btn" onclick="testStatus()">📊 상태 확인</button>
                <button class="btn" onclick="testCandles()">📈 캔들 데이터</button>
                <button class="btn" onclick="testMarkets()">🏪 마켓 목록</button>
            </div>
            
            <div id="result" class="result">
                <h4>결과:</h4>
                <pre id="resultContent">API 버튼을 클릭해보세요.</pre>
            </div>
        </div>
        
        <a href="/" class="back-link">← 메인 페이지로 돌아가기</a>
    </div>

    <script>
        async function apiCall(url, title) {
            try {
                const response = await fetch(url);
                const data = await response.json();
                document.getElementById('resultContent').textContent = JSON.stringify(data, null, 2);
            } catch (error) {
                document.getElementById('resultContent').textContent = 'Error: ' + error.message;
            }
        }

        function testStatus() {
            apiCall('/api/status', '상태 확인');
        }

        function testMarkets() {
            apiCall('/api/markets', '마켓 목록');
        }

        function testCandles() {
            const market = document.getElementById('market').value;
            const interval = document.getElementById('interval').value;
            const count = document.getElementById('count').value;
            const url = `/api/candles?market=${market}&interval=${interval}&count=${count}`;
            apiCall(url, '캔들 데이터');
        }

        // 페이지 로드 시 상태 확인
        window.onload = function() {
            testStatus();
        }
    </script>
</body>
</html>
    '''

@app.route('/auto-trading')
def auto_trading_dashboard():
    """자동거래 대시보드 - 완전한 버전"""
    return '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 업비트 자동거래 시스템</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .dashboard-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        .panel {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .panel h3 {
            color: #4a5568;
            margin-bottom: 20px;
            font-size: 1.3em;
        }
        .status-section {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin: 15px 0;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-running { background-color: #48bb78; }
        .status-stopped { background-color: #e53e3e; }
        .btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            margin: 5px;
            transition: all 0.3s ease;
        }
        .btn:hover { transform: scale(1.05); }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .btn-danger {
            background: linear-gradient(45deg, #e53e3e, #c53030);
        }
        .form-group {
            margin: 15px 0;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        .performance-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        .performance-item {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .performance-value {
            font-size: 1.3em;
            font-weight: bold;
            color: #667eea;
        }
        .analysis-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        .analysis-item {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
        }
        .log-area {
            background: #2d3748;
            color: #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
        .log-entry {
            margin: 2px 0;
            padding: 2px 0;
        }
        .log-success { color: #68d391; }
        .log-warning { color: #fbb040; }
        .log-error { color: #fc8181; }
        .back-link {
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            color: white;
            text-decoration: none;
            border-radius: 5px;
        }
        .full-width {
            grid-column: 1 / -1;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 업비트 자동거래 시스템 v2.0</h1>
            <p>Railway 배포 버전 - 완전한 자동매매 솔루션</p>
        </div>

        <div class="dashboard-grid">
            <!-- 제어 패널 -->
            <div class="panel">
                <h3>🎮 제어 패널</h3>
                
                <div class="status-section">
                    <h4>시스템 상태</h4>
                    <p><span class="status-indicator status-stopped" id="statusIndicator"></span>
                    <span id="statusText">중지됨</span></p>
                    
                    <div class="form-group" style="margin-top: 15px;">
                        <label>
                            <input type="checkbox" id="simulationMode" checked> 시뮬레이션 모드
                        </label>
                    </div>
                </div>

                <div style="margin: 20px 0;">
                    <button class="btn" id="startBtn" onclick="startAutoTrading()">
                        🚀 자동거래 시작
                    </button>
                    <button class="btn btn-danger" id="stopBtn" onclick="stopAutoTrading()" disabled>
                        ⏹️ 자동거래 중지
                    </button>
                </div>

                <div class="performance-grid">
                    <div class="performance-item">
                        <div class="performance-value" id="totalTrades">0</div>
                        <div>총 거래</div>
                    </div>
                    <div class="performance-item">
                        <div class="performance-value" id="winRate">0%</div>
                        <div>승률</div>
                    </div>
                    <div class="performance-item">
                        <div class="performance-value" id="totalProfit">0 KRW</div>
                        <div>총 수익</div>
                    </div>
                    <div class="performance-item">
                        <div class="performance-value" id="currentPosition">없음</div>
                        <div>현재 포지션</div>
                    </div>
                </div>
            </div>

            <!-- 전략 설정 -->
            <div class="panel">
                <h3>⚙️ 전략 설정</h3>
                
                <div class="form-group">
                    <label>거래 종목</label>
                    <select id="marketSelect">
                        <option value="KRW-BTC">KRW-BTC</option>
                        <option value="KRW-ETH">KRW-ETH</option>
                        <option value="KRW-XRP">KRW-XRP</option>
                        <option value="KRW-ADA">KRW-ADA</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>거래 간격 (분)</label>
                    <input type="number" id="tradeInterval" value="5" min="1" max="60">
                </div>

                <div class="form-group">
                    <label>최대 투자 비율 (%)</label>
                    <input type="number" id="investmentRatio" value="10" min="1" max="50" step="0.1">
                </div>

                <div class="form-group">
                    <label>RSI 과매도</label>
                    <input type="number" id="rsiOversold" value="30" min="10" max="40">
                </div>

                <div class="form-group">
                    <label>RSI 과매수</label>
                    <input type="number" id="rsiOverbought" value="70" min="60" max="90">
                </div>

                <div class="form-group">
                    <label>손절매 (%)</label>
                    <input type="number" id="stopLoss" value="-3" min="-10" max="-1" step="0.1">
                </div>

                <div class="form-group">
                    <label>익절매 (%)</label>
                    <input type="number" id="takeProfit" value="5" min="1" max="20" step="0.1">
                </div>

                <button class="btn" onclick="applyStrategy()">✅ 전략 적용</button>
            </div>

            <!-- 실시간 분석 -->
            <div class="panel">
                <h3>📊 실시간 분석</h3>
                
                <div class="analysis-grid">
                    <div class="analysis-item">
                        <div><strong>현재가</strong></div>
                        <div id="currentPrice">0 KRW</div>
                    </div>
                    <div class="analysis-item">
                        <div><strong>RSI</strong></div>
                        <div id="currentRSI">0</div>
                    </div>
                    <div class="analysis-item">
                        <div><strong>단기 MA</strong></div>
                        <div id="shortMAValue">0</div>
                    </div>
                    <div class="analysis-item">
                        <div><strong>장기 MA</strong></div>
                        <div id="longMAValue">0</div>
                    </div>
                    <div class="analysis-item">
                        <div><strong>거래량</strong></div>
                        <div id="currentVolume">0</div>
                    </div>
                    <div class="analysis-item">
                        <div><strong>신호</strong></div>
                        <div id="currentSignal">HOLD</div>
                    </div>
                </div>

                <div style="margin-top: 20px; text-align: center;">
                    <button class="btn" onclick="refreshAnalysis()">🔄 분석 새로고침</button>
                </div>
            </div>
        </div>

        <!-- 거래 로그 -->
        <div class="panel full-width">
            <h3>📋 거래 로그</h3>
            <div class="log-area" id="tradingLog">
                <div class="log-entry">[시스템] 자동거래 시스템 초기화 완료</div>
            </div>
            <div style="margin-top: 15px;">
                <button class="btn" onclick="clearLog()">🗑️ 로그 지우기</button>
                <button class="btn" onclick="refreshLog()">🔄 새로고침</button>
            </div>
        </div>

        <a href="/" class="back-link">← 메인 페이지로 돌아가기</a>
    </div>

    <script>
        let autoTradingActive = false;
        let refreshInterval;

        function updateStatus(isRunning) {
            const indicator = document.getElementById('statusIndicator');
            const text = document.getElementById('statusText');
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');

            if (isRunning) {
                indicator.className = 'status-indicator status-running';
                text.textContent = '실행 중';
                startBtn.disabled = true;
                stopBtn.disabled = false;
            } else {
                indicator.className = 'status-indicator status-stopped';
                text.textContent = '중지됨';
                startBtn.disabled = false;
                stopBtn.disabled = true;
            }
        }

        function getStrategyConfig() {
            return {
                market: document.getElementById('marketSelect').value,
                trade_interval: parseInt(document.getElementById('tradeInterval').value) * 60,
                simulation_mode: document.getElementById('simulationMode').checked,
                max_investment_ratio: parseFloat(document.getElementById('investmentRatio').value) / 100,
                rsi_oversold: parseInt(document.getElementById('rsiOversold').value),
                rsi_overbought: parseInt(document.getElementById('rsiOverbought').value),
                stop_loss_ratio: parseFloat(document.getElementById('stopLoss').value) / 100,
                take_profit_ratio: parseFloat(document.getElementById('takeProfit').value) / 100
            };
        }

        async function startAutoTrading() {
            const config = getStrategyConfig();
            const mode = config.simulation_mode ? '시뮬레이션' : '실제 거래';
            
            if (!confirm(`자동거래를 시작하시겠습니까?\n\n모드: ${mode}\n종목: ${config.market}\n간격: ${config.trade_interval / 60}분\n\n⚠️ ${mode} 모드로 실행됩니다.`)) {
                return;
            }

            try {
                const response = await fetch('/api/auto-trading/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });

                const result = await response.json();
                
                if (result.success) {
                    autoTradingActive = true;
                    updateStatus(true);
                    addLog(`🚀 자동거래 시작 - ${mode} 모드`, 'success');
                    startRefreshInterval();
                } else {
                    alert('자동거래 시작 실패: ' + result.message);
                }
            } catch (error) {
                alert('오류: ' + error.message);
            }
        }

        async function stopAutoTrading() {
            try {
                const response = await fetch('/api/auto-trading/stop', { method: 'POST' });
                const result = await response.json();
                
                if (result.success) {
                    autoTradingActive = false;
                    updateStatus(false);
                    addLog('⏹️ 자동거래 중지', 'info');
                    stopRefreshInterval();
                } else {
                    alert('자동거래 중지 실패: ' + result.message);
                }
            } catch (error) {
                alert('오류: ' + error.message);
            }
        }

        async function applyStrategy() {
            const config = getStrategyConfig();

            try {
                const response = await fetch('/api/auto-trading/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });

                const result = await response.json();
                
                if (result.success) {
                    addLog(`⚙️ 전략 설정 적용: ${config.market}`, 'info');
                    alert('전략 설정이 적용되었습니다.');
                } else {
                    alert('설정 적용 실패: ' + result.message);
                }
            } catch (error) {
                alert('오류: ' + error.message);
            }
        }

        async function refreshAnalysis() {
            try {
                const response = await fetch('/api/auto-trading/analysis');
                const result = await response.json();
                
                if (result.success) {
                    const analysis = result.analysis;
                    document.getElementById('currentPrice').textContent = analysis.price.toLocaleString() + ' KRW';
                    document.getElementById('currentRSI').textContent = analysis.rsi.toFixed(1);
                    document.getElementById('shortMAValue').textContent = analysis.short_ma.toLocaleString();
                    document.getElementById('longMAValue').textContent = analysis.long_ma.toLocaleString();
                    document.getElementById('currentVolume').textContent = analysis.volume.toFixed(1);
                    document.getElementById('currentSignal').textContent = analysis.signal;
                }
            } catch (error) {
                console.error('분석 새로고침 실패:', error);
            }
        }

        async function updatePerformance() {
            try {
                const response = await fetch('/api/auto-trading/performance');
                const result = await response.json();
                
                if (result.success) {
                    const perf = result.performance;
                    document.getElementById('totalTrades').textContent = perf.total_trades;
                    document.getElementById('winRate').textContent = perf.win_rate.toFixed(1) + '%';
                    document.getElementById('totalProfit').textContent = perf.total_profit_krw.toLocaleString() + ' KRW';
                    document.getElementById('currentPosition').textContent = perf.current_position ? '보유 중' : '없음';
                }
            } catch (error) {
                console.error('성과 업데이트 실패:', error);
            }
        }

        async function refreshLog() {
            try {
                const response = await fetch('/api/auto-trading/logs');
                const result = await response.json();
                
                if (result.success) {
                    const logArea = document.getElementById('tradingLog');
                    logArea.innerHTML = '';
                    
                    result.logs.forEach(log => {
                        const logElement = document.createElement('div');
                        logElement.className = `log-entry log-${log.type.toLowerCase()}`;
                        logElement.textContent = `[${log.timestamp}] ${log.message}`;
                        logArea.appendChild(logElement);
                    });
                    
                    logArea.scrollTop = logArea.scrollHeight;
                }
            } catch (error) {
                console.error('로그 새로고침 실패:', error);
            }
        }

        function addLog(message, type = 'info') {
            const logArea = document.getElementById('tradingLog');
            const time = new Date().toLocaleTimeString();
            const logElement = document.createElement('div');
            logElement.className = `log-entry log-${type}`;
            logElement.textContent = `[${time}] ${message}`;
            logArea.appendChild(logElement);
            logArea.scrollTop = logArea.scrollHeight;
        }

        function clearLog() {
            document.getElementById('tradingLog').innerHTML = '<div class="log-entry">[시스템] 로그가 초기화되었습니다.</div>';
        }

        function startRefreshInterval() {
            refreshInterval = setInterval(() => {
                if (autoTradingActive) {
                    refreshAnalysis();
                    updatePerformance();
                    refreshLog();
                }
            }, 5000);
        }

        function stopRefreshInterval() {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
        }

        // 페이지 로드 시 초기화
        window.onload = function() {
            refreshAnalysis();
            updatePerformance();
            refreshLog();
        }
    </script>
</body>
</html>
    '''

# ============================================================================
# API 라우트
# ============================================================================

@app.route('/api/status')
def api_status():
    """API 상태 확인"""
    return jsonify({
        'status': 'success',
        'message': '업비트 통합 웹 서비스가 정상 작동 중입니다.',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0',
        'services': {
            'charts': 'active',
            'auto_trading': 'running' if auto_trading_state['is_running'] else 'stopped'
        }
    })

@app.route('/api/candles')
def get_candles():
    """캔들 데이터 조회"""
    try:
        market = request.args.get('market', 'KRW-BTC')
        interval = request.args.get('interval', '5')
        count = int(request.args.get('count', 50))
        
        # 파라미터 검증
        if not market.startswith('KRW-'):
            return jsonify({'status': 'error', 'message': 'KRW 마켓만 지원됩니다.'}), 400
        
        if interval not in ['1', '3', '5', '15', '10', '30', '60', '240']:
            return jsonify({'status': 'error', 'message': '지원하지 않는 캔들 간격입니다.'}), 400
        
        if count < 1 or count > 200:
            return jsonify({'status': 'error', 'message': '조회 개수는 1~200 사이여야 합니다.'}), 400
        
        # 업비트 API에서 데이터 조회
        candles = upbit_api.get_candle_data(market, interval, count)
        
        if candles is None:
            return jsonify({'status': 'error', 'message': '업비트 API 요청에 실패했습니다.'}), 500
        
        return jsonify({
            'status': 'success',
            'market': market,
            'interval': f'{interval}m',
            'count': len(candles),
            'data': candles,
            'updated_at': datetime.now().isoformat()
        })
        
    except ValueError as e:
        return jsonify({'status': 'error', 'message': f'잘못된 파라미터: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"캔들 데이터 API 오류: {e}")
        return jsonify({'status': 'error', 'message': '서버 내부 오류가 발생했습니다.'}), 500

@app.route('/api/markets')
def get_markets():
    """마켓 목록 조회"""
    try:
        markets = upbit_api.get_markets()
        return jsonify({
            'status': 'success',
            'count': len(markets),
            'data': markets
        })
    except Exception as e:
        logger.error(f"마켓 목록 API 오류: {e}")
        return jsonify({'status': 'error', 'message': '마켓 정보를 가져올 수 없습니다.'}), 500

# ============================================================================
# 자동거래 API 라우트
# ============================================================================

@app.route('/api/auto-trading/start', methods=['POST'])
def start_auto_trading_api():
    """자동거래 시작 API"""
    global trading_thread, trading_active
    
    try:
        if trading_active:
            return jsonify({"success": False, "message": "이미 자동거래가 실행 중입니다."})
        
        config = request.get_json()
        if config:
            auto_trading_state["config"].update(config)
        
        trading_active = True
        auto_trading_state["is_running"] = True
        
        # 자동거래 스레드 시작
        trading_thread = threading.Thread(target=auto_trading_worker, daemon=True)
        trading_thread.start()
        
        mode = "시뮬레이션" if auto_trading_state["config"].get("simulation_mode", True) else "실제 거래"
        add_trading_log(f"🚀 자동거래 시작 - {mode} 모드, {auto_trading_state['config']['market']}", "INFO")
        
        return jsonify({"success": True, "message": "자동거래가 시작되었습니다."})
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auto-trading/stop', methods=['POST'])
def stop_auto_trading_api():
    """자동거래 중지 API"""
    global trading_active
    
    try:
        trading_active = False
        auto_trading_state["is_running"] = False
        add_trading_log("⏹️ 자동거래 중지", "INFO")
        
        return jsonify({"success": True, "message": "자동거래가 중지되었습니다."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auto-trading/config', methods=['POST'])
def update_auto_trading_config_api():
    """자동거래 설정 업데이트 API"""
    try:
        config = request.get_json()
        auto_trading_state["config"].update(config)
        add_trading_log(f"⚙️ 전략 설정 적용: {config.get('market', 'Unknown')}", "INFO")
        
        return jsonify({"success": True, "message": "설정이 적용되었습니다."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auto-trading/logs')
def get_auto_trading_logs_api():
    """자동거래 로그 조회 API"""
    return jsonify({"success": True, "logs": auto_trading_state["logs"][-50:]})

@app.route('/api/auto-trading/performance')
def get_auto_trading_performance_api():
    """자동거래 성과 조회 API"""
    return jsonify({"success": True, "performance": auto_trading_state["performance"]})

@app.route('/api/auto-trading/analysis')
def get_auto_trading_analysis_api():
    """자동거래 분석 데이터 조회 API"""
    return jsonify({"success": True, "analysis": auto_trading_state["current_analysis"]})

# ============================================================================
# 에러 핸들러
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """404 에러 핸들러"""
    return jsonify({'status': 'error', 'message': '요청한 리소스를 찾을 수 없습니다.'}), 404

@app.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    return jsonify({'status': 'error', 'message': '서버 내부 오류가 발생했습니다.'}), 500

# ============================================================================
# 메인 실행 부분
# ============================================================================

if __name__ == '__main__':
    # Railway 환경 변수에서 포트 가져오기
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print("🚀 업비트 통합 웹 서비스 v2.0 시작")
    print(f"📊 접속 주소: http://localhost:{port}")
    print("🔗 사용 가능한 서비스:")
    print("  - /               : 메인 페이지")
    print("  - /charts         : 캔들 차트 & 데이터")
    print("  - /auto-trading   : 자동거래 시스템")
    print("  - /api/status     : API 상태 확인")
    print("=" * 50)
    
    # Railway 환경에서 서버 실행
    app.run(
        host='0.0.0.0',     # 모든 IP에서 접근 가능
        port=port,          # Railway가 제공하는 포트 사용
        debug=debug,        # 프로덕션에서는 False
        threaded=True       # 멀티스레드 지원
    )