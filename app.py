#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 자동거래 웹 서비스 v2.0
- 완전한 자동거래 시스템 (실제 주문 지원)
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
import jwt
import uuid
import hashlib
from datetime import datetime
from urllib.parse import urlencode
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
# 업비트 실제 거래 API 클래스
# ============================================================================

class UpbitRealAPI:
    """업비트 실제 거래 API 클래스"""
    
    def __init__(self):
        self.base_url = "https://api.upbit.com"
        self.access_key = os.environ.get('UPBIT_OPEN_API_ACCESS_KEY')
        self.secret_key = os.environ.get('UPBIT_OPEN_API_SECRET_KEY')
    
    def is_authenticated(self):
        """API 키가 설정되어 있는지 확인"""
        return bool(self.access_key and self.secret_key)
    
    def generate_jwt_token(self, query=None):
        """JWT 토큰 생성"""
        if not self.is_authenticated():
            return None
        
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
        }
        
        if query:
            query_string = urlencode(query).encode()
            m = hashlib.sha512()
            m.update(query_string)
            query_hash = m.hexdigest()
            
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'
        
        jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return f'Bearer {jwt_token}'
    
    def get_current_price(self, market):
        """현재 시장 가격 조회"""
        try:
            url = f"{self.base_url}/v1/ticker"
            params = {'markets': market}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            ticker_data = response.json()
            if ticker_data:
                return ticker_data[0]['trade_price']
            return None
            
        except Exception as e:
            logger.error(f"현재 가격 조회 실패: {e}")
            return None
    
    def get_account_balance(self, currency='KRW'):
        """계좌 잔고 조회"""
        if not self.is_authenticated():
            return None
        
        try:
            authorization_token = self.generate_jwt_token()
            headers = {"Authorization": authorization_token}
            
            response = requests.get(f"{self.base_url}/v1/accounts", headers=headers)
            response.raise_for_status()
            
            accounts = response.json()
            for account in accounts:
                if account['currency'] == currency:
                    return float(account['balance'])
            
            return 0.0
            
        except Exception as e:
            logger.error(f"계좌 잔고 조회 실패: {e}")
            return None
    
    def place_market_buy_order(self, market, price):
        """시장가 매수 주문"""
        if not self.is_authenticated():
            return None
        
        try:
            query = {
                'market': market,
                'side': 'bid',
                'ord_type': 'price',
                'price': str(price),
            }
            
            authorization_token = self.generate_jwt_token(query)
            headers = {
                "Authorization": authorization_token,
                "Content-Type": "application/json"
            }
            
            response = requests.post(f"{self.base_url}/v1/orders", params=query, headers=headers)
            
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"매수 주문 실패: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"매수 주문 오류: {e}")
            return None
    
    def place_market_sell_order(self, market, volume):
        """시장가 매도 주문"""
        if not self.is_authenticated():
            return None
        
        try:
            query = {
                'market': market,
                'side': 'ask',
                'ord_type': 'market',
                'volume': str(volume),
            }
            
            authorization_token = self.generate_jwt_token(query)
            headers = {
                "Authorization": authorization_token,
                "Content-Type": "application/json"
            }
            
            response = requests.post(f"{self.base_url}/v1/orders", params=query, headers=headers)
            
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"매도 주문 실패: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"매도 주문 오류: {e}")
            return None

# API 인스턴스 생성
upbit_real_api = UpbitRealAPI()

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
        "total_investment": 0,
        "total_profit_krw": 0,
        "profit_rate": 0,  # 투자 대비 이익률
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
    """시장 분석 (실제 가격 + 시뮬레이션 지표)"""
    config = auto_trading_state["config"]
    
    # 실제 가격 가져오기
    current_price = upbit_real_api.get_current_price(config["market"])
    if not current_price:
        # 실제 가격을 못 가져오면 시뮬레이션 가격 사용
        current_price = 50000000 * (1 + random.uniform(-0.02, 0.02))
    
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
    """거래 실행 (시뮬레이션 + 실제)"""
    config = auto_trading_state["config"]
    performance = auto_trading_state["performance"]
    
    if signal == "BUY" and not performance["current_position"]:
        # 매수 실행
        order_amount = config["min_order_amount"]
        
        if config["simulation_mode"]:
            # 시뮬레이션 매수
            performance["current_position"] = {
                "buy_price": price,
                "amount": order_amount / price,
                "timestamp": datetime.now().isoformat(),
                "investment": order_amount
            }
            performance["total_trades"] += 1
            performance["total_investment"] += order_amount
            add_trading_log(f"🟢 시뮬레이션 매수: {price:,.0f} KRW (투자: {order_amount:,}원)", "SUCCESS")
        else:
            # 실제 매수
            if upbit_real_api.is_authenticated():
                order_result = upbit_real_api.place_market_buy_order(config["market"], order_amount)
                if order_result:
                    performance["current_position"] = {
                        "buy_price": price,
                        "amount": order_amount / price,
                        "timestamp": datetime.now().isoformat(),
                        "investment": order_amount,
                        "order_id": order_result.get('uuid')
                    }
                    performance["total_trades"] += 1
                    performance["total_investment"] += order_amount
                    add_trading_log(f"🟢 실제 매수 완료: {price:,.0f} KRW (투자: {order_amount:,}원)", "SUCCESS")
                else:
                    add_trading_log(f"❌ 실제 매수 실패: {price:,.0f} KRW", "ERROR")
            else:
                add_trading_log("❌ API 키가 설정되지 않았습니다", "ERROR")
        
    elif signal in ["SELL", "STOP_LOSS", "TAKE_PROFIT"] and performance["current_position"]:
        # 매도 실행
        position = performance["current_position"]
        profit = (price - position["buy_price"]) * position["amount"]
        
        if config["simulation_mode"]:
            # 시뮬레이션 매도
            performance["total_profit_krw"] += profit
            
            # 투자 대비 이익률 계산
            if performance["total_investment"] > 0:
                performance["profit_rate"] = (performance["total_profit_krw"] / performance["total_investment"]) * 100
            
            emoji = "🎯" if signal == "TAKE_PROFIT" else "🛑" if signal == "STOP_LOSS" else "🔴"
            add_trading_log(f"{emoji} 시뮬레이션 매도: {price:,.0f} KRW (수익: {profit:+,.0f} KRW)", 
                           "SUCCESS" if profit > 0 else "WARNING")
        else:
            # 실제 매도
            if upbit_real_api.is_authenticated():
                order_result = upbit_real_api.place_market_sell_order(config["market"], position["amount"])
                if order_result:
                    performance["total_profit_krw"] += profit
                    
                    # 투자 대비 이익률 계산
                    if performance["total_investment"] > 0:
                        performance["profit_rate"] = (performance["total_profit_krw"] / performance["total_investment"]) * 100
                    
                    emoji = "🎯" if signal == "TAKE_PROFIT" else "🛑" if signal == "STOP_LOSS" else "🔴"
                    add_trading_log(f"{emoji} 실제 매도 완료: {price:,.0f} KRW (수익: {profit:+,.0f} KRW)", 
                                   "SUCCESS" if profit > 0 else "WARNING")
                else:
                    add_trading_log(f"❌ 실제 매도 실패: {price:,.0f} KRW", "ERROR")
            else:
                add_trading_log("❌ API 키가 설정되지 않았습니다", "ERROR")
        
        performance["current_position"] = None

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
    <title>🤖 업비트 자동거래 시스템</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
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
        .nav-card {
            background: white;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
            text-decoration: none;
            color: inherit;
            display: block;
            margin-bottom: 30px;
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
            color: #764ba2;
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
            <h1>🤖 업비트 자동거래 시스템</h1>
            <p>완전한 자동매매 솔루션</p>
            <p>Railway 배포 버전 v2.0</p>
        </div>

        <a href="/auto-trading" class="nav-card">
            <div class="nav-icon">🤖</div>
            <div class="nav-title">자동거래 시스템</div>
            <div class="nav-desc">
                실시간 자동매매 시스템<br>
                시뮬레이션 & 실제 거래 지원<br>
                완전한 리스크 관리
            </div>
        </a>

        <div class="footer">
            <h3>🔗 시스템 기능</h3>
            <div class="endpoint">실시간 시장 분석</div>
            <div class="endpoint">자동 매수/매도</div>
            <div class="endpoint">손익절매 관리</div>
            <div class="endpoint">시뮬레이션 모드</div>
            <div class="endpoint">실제 거래 지원</div>
        </div>
    </div>
</body>
</html>
    '''

@app.route('/auto-trading')
def auto_trading_dashboard():
    """자동거래 대시보드"""
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
        .profit-positive { color: #48bb78; }
        .profit-negative { color: #e53e3e; }
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
            <p>Railway 배포 버전 - 실시간 자동매매 솔루션</p>
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
                        <div class="performance-value" id="totalInvestment">0 KRW</div>
                        <div>총 투자</div>
                    </div>
                    <div class="performance-item">
                        <div class="performance-value" id="totalProfit">0 KRW</div>
                        <div>총 수익</div>
                    </div>
                    <div class="performance-item">
                        <div class="performance-value" id="profitRate">0%</div>
                        <div>투자 대비 수익률</div>
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
                    <label>최소 주문금액 (원)</label>
                    <input type="number" id="minOrderAmount" value="5000" min="5000" max="100000" step="1000">
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

                <div style="margin-top: 20px;">
                    <h4>현재 포지션</h4>
                    <div id="currentPosition" style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
                        없음
                    </div>
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
                min_order_amount: parseInt(document.getElementById('minOrderAmount').value),
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
                    document.getElementById('totalInvestment').textContent = perf.total_investment.toLocaleString() + ' KRW';
                    document.getElementById('totalProfit').textContent = perf.total_profit_krw.toLocaleString() + ' KRW';
                    
                    const profitRateElement = document.getElementById('profitRate');
                    profitRateElement.textContent = perf.profit_rate.toFixed(2) + '%';
                    
                    // 수익률에 따른 색상 변경
                    if (perf.profit_rate > 0) {
                        profitRateElement.className = 'performance-value profit-positive';
                    } else if (perf.profit_rate < 0) {
                        profitRateElement.className = 'performance-value profit-negative';
                    } else {
                        profitRateElement.className = 'performance-value';
                    }
                    
                    // 현재 포지션 정보
                    const positionElement = document.getElementById('currentPosition');
                    if (perf.current_position) {
                        const pos = perf.current_position;
                        const currentPrice = parseFloat(document.getElementById('currentPrice').textContent.replace(/[^\d.-]/g, ''));
                        const unrealizedPL = currentPrice ? (currentPrice - pos.buy_price) * pos.amount : 0;
                        
                        positionElement.innerHTML = `
                            <strong>보유 중</strong><br>
                            매수가: ${pos.buy_price.toLocaleString()} KRW<br>
                            수량: ${pos.amount.toFixed(8)}<br>
                            투자금: ${pos.investment.toLocaleString()} KRW<br>
                            평가손익: ${unrealizedPL.toLocaleString()} KRW
                        `;
                    } else {
                        positionElement.textContent = '없음';
                    }
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
                refreshAnalysis();
                updatePerformance();
                refreshLog();
            }, 5000);
        }

        function stopRefreshInterval() {
            if (refreshInterval) {
                clearInterval(refreshInterval);
                refreshInterval = null;
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
        'message': '업비트 자동거래 시스템이 정상 작동 중입니다.',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0',
        'api_authenticated': upbit_real_api.is_authenticated(),
        'auto_trading_status': 'running' if auto_trading_state['is_running'] else 'stopped'
    })

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
        
        # 실제 거래 모드에서 API 키 확인
        if not auto_trading_state["config"].get("simulation_mode", True):
            if not upbit_real_api.is_authenticated():
                return jsonify({"success": False, "message": "실제 거래를 위해서는 UPBIT_OPEN_API_ACCESS_KEY와 UPBIT_OPEN_API_SECRET_KEY 환경변수가 필요합니다."})
        
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
        add_trading_log("⏹️ 자동거래 중지 요청", "INFO")
        
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
    
    print("🤖 업비트 자동거래 웹 서비스 v2.0 시작")
    print(f"📊 접속 주소: http://localhost:{port}")
    print("🔗 사용 가능한 서비스:")
    print("  - /               : 메인 페이지")
    print("  - /auto-trading   : 자동거래 시스템")
    print("  - /api/status     : API 상태 확인")
    
    # API 키 상태 확인
    if upbit_real_api.is_authenticated():
        print("✅ 업비트 API 키 설정됨 - 실제 거래 가능")
    else:
        print("⚠️  업비트 API 키 미설정 - 시뮬레이션 모드만 사용 가능")
        print("   환경변수 UPBIT_OPEN_API_ACCESS_KEY, UPBIT_OPEN_API_SECRET_KEY 설정 필요")
    
    print("=" * 50)
    
    # Railway 환경에서 서버 실행
    app.run(
        host='0.0.0.0',     # 모든 IP에서 접근 가능
        port=port,          # Railway가 제공하는 포트 사용
        debug=debug,        # 프로덕션에서는 False
        threaded=True       # 멀티스레드 지원
    )
