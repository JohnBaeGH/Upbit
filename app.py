#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 통합 웹 서비스
- 캔들 차트 API
- 자동거래 시스템
Railway 배포 버전
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

# Flask 애플리케이션 초기화
app = Flask(__name__)
CORS(app)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# 업비트 API 클래스
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
            return [m for m in markets if m['market'].startswith('KRW-')]
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
        "trade_interval": 300,
        "simulation_mode": True,
        "max_investment_ratio": 0.1,
        "stop_loss_ratio": -0.03,
        "take_profit_ratio": 0.05,
        "rsi_oversold": 30,
        "rsi_overbought": 70
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
        "signal": "HOLD"
    }
}

# 자동거래 실행 변수
trading_thread = None
trading_active = False

def add_trading_log(message, log_type="INFO"):
    """거래 로그 추가"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {"timestamp": timestamp, "message": message, "type": log_type}
    auto_trading_state["logs"].append(log_entry)
    
    if len(auto_trading_state["logs"]) > 100:
        auto_trading_state["logs"] = auto_trading_state["logs"][-100:]

def simulate_market_analysis():
    """시장 분석 시뮬레이션"""
    base_price = 50000000
    price_variation = random.uniform(-0.02, 0.02)
    current_price = base_price * (1 + price_variation)
    rsi = random.uniform(20, 80)
    
    config = auto_trading_state["config"]
    signal = "HOLD"
    
    if rsi < config["rsi_oversold"]:
        signal = "BUY"
    elif rsi > config["rsi_overbought"]:
        signal = "SELL"
    elif auto_trading_state["performance"]["current_position"]:
        position = auto_trading_state["performance"]["current_position"]
        profit_ratio = (current_price - position["buy_price"]) / position["buy_price"]
        
        if profit_ratio <= config["stop_loss_ratio"]:
            signal = "STOP_LOSS"
        elif profit_ratio >= config["take_profit_ratio"]:
            signal = "TAKE_PROFIT"
    
    auto_trading_state["current_analysis"] = {
        "price": current_price,
        "rsi": rsi,
        "signal": signal
    }
    
    return signal, current_price

def execute_trade(signal, price):
    """거래 실행"""
    performance = auto_trading_state["performance"]
    
    if signal == "BUY" and not performance["current_position"]:
        performance["current_position"] = {
            "buy_price": price,
            "timestamp": datetime.now().isoformat()
        }
        performance["total_trades"] += 1
        add_trading_log(f"🟢 매수: {price:,.0f} KRW", "SUCCESS")
        
    elif signal in ["SELL", "STOP_LOSS", "TAKE_PROFIT"] and performance["current_position"]:
        position = performance["current_position"]
        profit = price - position["buy_price"]
        
        if profit > 0:
            performance["successful_trades"] += 1
            performance["total_profit_krw"] += profit
            emoji = "🎯" if signal == "TAKE_PROFIT" else "🔴"
        else:
            emoji = "🛑" if signal == "STOP_LOSS" else "🔴"
        
        add_trading_log(f"{emoji} 매도: {price:,.0f} KRW (수익: {profit:+,.0f} KRW)", 
                       "SUCCESS" if profit > 0 else "WARNING")
        
        performance["current_position"] = None
        
        if performance["total_trades"] > 0:
            performance["win_rate"] = (performance["successful_trades"] / performance["total_trades"]) * 100

def auto_trading_worker():
    """자동거래 워커 스레드"""
    global trading_active
    
    add_trading_log("🤖 자동거래 시스템 시작", "INFO")
    
    while trading_active:
        try:
            signal, current_price = simulate_market_analysis()
            add_trading_log(f"📊 분석: {current_price:,.0f}원, RSI:{auto_trading_state['current_analysis']['rsi']:.1f}, 신호:{signal}")
            
            if signal != "HOLD":
                execute_trade(signal, current_price)
            
            time.sleep(auto_trading_state["config"]["trade_interval"])
            
        except Exception as e:
            add_trading_log(f"❌ 오류: {str(e)}", "ERROR")
            time.sleep(60)
    
    add_trading_log("⏹️ 자동거래 시스템 중지", "INFO")

# ============================================================================
# 웹 라우트 - 페이지
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
        .api-section {
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
        }
        .api-section h2 {
            color: #2a5298;
            margin-bottom: 20px;
        }
        .endpoint {
            display: inline-block;
            background: #f8f9fa;
            padding: 10px 20px;
            margin: 10px;
            border-radius: 25px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            color: #495057;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 업비트 통합 웹 서비스</h1>
            <p>실시간 데이터 분석 & 자동거래 시스템</p>
            <p>Railway 배포 버전</p>
        </div>

        <div class="nav-grid">
            <a href="/charts" class="nav-card">
                <div class="nav-icon">📊</div>
                <div class="nav-title">캔들 차트 & 데이터</div>
                <div class="nav-desc">
                    실시간 업비트 캔들 데이터 조회<br>
                    마켓 정보 및 API 테스트
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

        <div class="api-section">
            <h2>🔗 API 엔드포인트</h2>
            <div class="endpoint">GET /api/status</div>
            <div class="endpoint">GET /api/candles</div>
            <div class="endpoint">GET /api/markets</div>
            <div class="endpoint">POST /api/auto-trading/start</div>
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
    <!-- 기존 캔들 차트 HTML 코드 (간소화) -->
    <style>
        /* 기존 스타일 */
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
        .btn { padding: 10px 20px; margin: 10px; border: none; border-radius: 5px; cursor: pointer; background: #2a5298; color: white; }
        .result { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; max-height: 400px; overflow-y: auto; }
        pre { background: #2d3748; color: #e2e8f0; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 업비트 캔들 차트 데이터</h1>
        
        <div>
            <label>마켓: </label>
            <select id="market">
                <option value="KRW-BTC">KRW-BTC</option>
                <option value="KRW-ETH">KRW-ETH</option>
                <option value="KRW-XRP">KRW-XRP</option>
            </select>
            
            <label>간격: </label>
            <select id="interval">
                <option value="1">1분</option>
                <option value="5" selected>5분</option>
                <option value="15">15분</option>
                <option value="60">1시간</option>
            </select>
            
            <label>개수: </label>
            <input type="number" id="count" value="20" min="1" max="200">
        </div>
        
        <div>
            <button class="btn" onclick="testStatus()">📊 상태 확인</button>
            <button class="btn" onclick="testCandles()">📈 캔들 데이터</button>
            <button class="btn" onclick="testMarkets()">🏪 마켓 목록</button>
        </div>
        
        <div id="result" class="result">
            <h4>결과:</h4>
            <pre id="resultContent">API 버튼을 클릭해보세요.</pre>
        </div>
        
        <div>
            <a href="/" style="color: #2a5298;">← 메인 페이지로</a>
        </div>
    </div>

    <script>
        async function apiCall(url) {
            try {
                const response = await fetch(url);
                const data = await response.json();
                document.getElementById('resultContent').textContent = JSON.stringify(data, null, 2);
            } catch (error) {
                document.getElementById('resultContent').textContent = 'Error: ' + error.message;
            }
        }

        function testStatus() { apiCall('/api/status'); }
        function testMarkets() { apiCall('/api/markets'); }
        function testCandles() {
            const market = document.getElementById('market').value;
            const interval = document.getElementById('interval').value;
            const count = document.getElementById('count').value;
            apiCall(`/api/candles?market=${market}&interval=${interval}&count=${count}`);
        }
    </script>
</body>
</html>
    '''

# ============================================================================
# 웹 라우트 - API
# ============================================================================

@app.route('/api/status')
def api_status():
    """API 상태 확인"""
    return jsonify({
        'status': 'success',
        'message': '업비트 통합 웹 서비스가 정상 작동 중입니다.',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'charts': 'active',
            'auto_trading': 'active' if auto_trading_state['is_running'] else 'stopped'
        }
    })

@app.route('/api/candles')
def get_candles():
    """캔들 데이터 조회"""
    try:
        market = request.args.get('market', 'KRW-BTC')
        interval = request.args.get('interval', '5')
        count = int(request.args.get('count', 50))
        
        candles = upbit_api.get_candle_data(market, interval, count)
        
        if candles is None:
            return jsonify({'status': 'error', 'message': '데이터 조회 실패'}), 500
        
        return jsonify({
            'status': 'success',
            'market': market,
            'interval': f'{interval}m',
            'count': len(candles),
            'data': candles[:10],  # 처음 10개만 표시
            'updated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/markets')
def get_markets():
    """마켓 목록 조회"""
    try:
        markets = upbit_api.get_markets()
        return jsonify({'status': 'success', 'count': len(markets), 'data': markets})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# 자동거래 API 라우트
# ============================================================================

@app.route('/auto-trading')
def auto_trading_dashboard():
    """자동거래 대시보드 - 앞서 만든 완전한 HTML 코드"""
    # 여기에 앞서 만든 완전한 자동거래 HTML을 넣으면 됩니다
    return "자동거래 대시보드 (완전한 HTML 코드는 길어서 생략)"

@app.route('/api/auto-trading/start', methods=['POST'])
def start_auto_trading():
    """자동거래 시작"""
    global trading_thread, trading_active
    
    try:
        if trading_active:
            return jsonify({"success": False, "message": "이미 실행 중입니다."})
        
        config = request.get_json()
        if config:
            auto_trading_state["config"].update(config)
        
        trading_active = True
        auto_trading_state["is_running"] = True
        
        trading_thread = threading.Thread(target=auto_trading_worker, daemon=True)
        trading_thread.start()
        
        return jsonify({"success": True, "message": "자동거래 시작"})
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auto-trading/stop', methods=['POST'])
def stop_auto_trading():
    """자동거래 중지"""
    global trading_active
    
    try:
        trading_active = False
        auto_trading_state["is_running"] = False
        return jsonify({"success": True, "message": "자동거래 중지"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auto-trading/performance')
def get_performance():
    """성과 조회"""
    return jsonify({"success": True, "performance": auto_trading_state["performance"]})

@app.route('/api/auto-trading/logs')
def get_logs():
    """로그 조회"""
    return jsonify({"success": True, "logs": auto_trading_state["logs"][-50:]})

@app.route('/api/auto-trading/analysis')
def get_analysis():
    """분석 데이터 조회"""
    return jsonify({"success": True, "analysis": auto_trading_state["current_analysis"]})

# ============================================================================
# 메인 실행
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print("🚀 업비트 통합 웹 서비스 시작")
    print(f"📊 접속 주소: http://localhost:{port}")
    print("🔗 서비스:")
    print("  - /          : 메인 페이지")
    print("  - /charts    : 캔들 차트")
    print("  - /auto-trading : 자동거래")
    print("-" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)