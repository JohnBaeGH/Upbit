#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 캔들 차트 웹 서비스 - Flask 백엔드
실시간 업비트 API 데이터를 제공하는 웹 서버
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import requests
import json
from datetime import datetime
import logging
from threading import Thread    # ← 새로 추가
import time   
# json은 이미 있으므로 추가하지 않음

# Flask 애플리케이션 초기화
app = Flask(__name__)
CORS(app)  # CORS 설정으로 브라우저 요청 허용

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 #자동거래 상태 관리 (메모리에 저장)
auto_trading_state = {
    "is_running": False,
    "config": {},
    "performance": {
        "total_trades": 0,
        "total_profit": 0,
        "win_rate": 0,
        "current_position": None
    },
    "logs": []
}
class UpbitAPI:
    """업비트 API 클래스"""
    
    def __init__(self):
        self.base_url = "https://api.upbit.com"
    
    def get_candle_data(self, market="KRW-BTC", interval="5", count=50):
        """
        업비트 캔들 데이터 조회
        
        Args:
            market (str): 마켓 코드 (예: KRW-BTC)
            interval (str): 캔들 간격 (1,3,5,15,10,30,60,240)
            count (int): 조회할 캔들 개수 (1~200)
        
        Returns:
            list: 캔들 데이터 리스트
        """
        try:
            url = f"{self.base_url}/v1/candles/minutes/{interval}"
            params = {
                'market': market,
                'count': min(count, 200)  # 최대 200개로 제한
            }
            
            logger.info(f"업비트 API 호출: {market} {interval}분 캔들 {count}개")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"업비트 API 요청 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"데이터 처리 오류: {e}")
            return None
    
    def get_markets(self):
        """업비트 마켓 목록 조회"""
        try:
            url = f"{self.base_url}/v1/market/all"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            markets = response.json()
            # KRW 마켓만 필터링
            krw_markets = [m for m in markets if m['market'].startswith('KRW-')]
            
            return krw_markets
            
        except Exception as e:
            logger.error(f"마켓 정보 조회 실패: {e}")
            return []

# API 클래스 인스턴스 생성
upbit_api = UpbitAPI()

def convert_to_chart_format(candles):
    """
    업비트 캔들 데이터를 차트 라이브러리용 포맷으로 변환
    
    Args:
        candles (list): 업비트 원본 캔들 데이터
    
    Returns:
        list: 차트용 포맷 데이터
    """
    if not candles:
        return []
    
    chart_data = []
    
    # 시간순 정렬 (과거 → 현재)
    for candle in reversed(candles):
        try:
            # 시간을 JavaScript 타임스탬프로 변환
            dt = datetime.fromisoformat(candle['candle_date_time_kst'].replace('Z', '+00:00'))
            timestamp = int(dt.timestamp() * 1000)
            
            chart_item = {
                'timestamp': timestamp,
                'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
                'open': float(candle['opening_price']),
                'high': float(candle['high_price']),
                'low': float(candle['low_price']),
                'close': float(candle['trade_price']),
                'volume': float(candle['candle_acc_trade_volume'])
            }
            
            chart_data.append(chart_item)
            
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"캔들 데이터 변환 오류: {e}")
            continue
    
    return chart_data

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/api/candles')
def get_candles():
    """
    캔들 데이터 API 엔드포인트
    
    Query Parameters:
        - market: 마켓 코드 (기본값: KRW-BTC)
        - interval: 캔들 간격 (기본값: 5)
        - count: 조회 개수 (기본값: 50)
    
    Returns:
        JSON: 캔들 데이터 응답
    """
    try:
        # 쿼리 파라미터 추출
        market = request.args.get('market', 'KRW-BTC')
        interval = request.args.get('interval', '5')
        count = int(request.args.get('count', 50))
        
        # 파라미터 검증
        if not market.startswith('KRW-'):
            return jsonify({
                'status': 'error',
                'message': 'KRW 마켓만 지원됩니다.'
            }), 400
        
        if interval not in ['1', '3', '5', '15', '10', '30', '60', '240']:
            return jsonify({
                'status': 'error',
                'message': '지원하지 않는 캔들 간격입니다.'
            }), 400
        
        if count < 1 or count > 200:
            return jsonify({
                'status': 'error',
                'message': '조회 개수는 1~200 사이여야 합니다.'
            }), 400
        
        # 업비트 API에서 데이터 조회
        candles = upbit_api.get_candle_data(market, interval, count)
        
        if candles is None:
            return jsonify({
                'status': 'error',
                'message': '업비트 API 요청에 실패했습니다.'
            }), 500
        
        # 차트용 포맷으로 변환
        chart_data = convert_to_chart_format(candles)
        
        # 응답 데이터 구성
        response_data = {
            'status': 'success',
            'market': market,
            'interval': f'{interval}m',
            'count': len(chart_data),
            'data': chart_data,
            'updated_at': datetime.now().isoformat()
        }
        
        logger.info(f"캔들 데이터 응답: {market} {interval}분 {len(chart_data)}개")
        
        return jsonify(response_data)
        
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': f'잘못된 파라미터: {str(e)}'
        }), 400
        
    except Exception as e:
        logger.error(f"캔들 데이터 API 오류: {e}")
        return jsonify({
            'status': 'error',
            'message': '서버 내부 오류가 발생했습니다.'
        }), 500

@app.route('/api/markets')
def get_markets():
    """
    마켓 목록 API 엔드포인트
    
    Returns:
        JSON: KRW 마켓 목록
    """
    try:
        markets = upbit_api.get_markets()
        
        return jsonify({
            'status': 'success',
            'count': len(markets),
            'data': markets
        })
        
    except Exception as e:
        logger.error(f"마켓 목록 API 오류: {e}")
        return jsonify({
            'status': 'error',
            'message': '마켓 정보를 가져올 수 없습니다.'
        }), 500

@app.route('/api/status')
def api_status():
    """API 상태 확인 엔드포인트"""
    return jsonify({
        'status': 'success',
        'message': '업비트 캔들 차트 API 서버가 정상 작동 중입니다.',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.errorhandler(404)
def not_found(error):
    """404 에러 핸들러"""
    return jsonify({
        'status': 'error',
        'message': '요청한 리소스를 찾을 수 없습니다.'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    return jsonify({
        'status': 'error',
        'message': '서버 내부 오류가 발생했습니다.'
    }), 500
def render_template_string(template):
    """간단한 템플릿 렌더링 (자동거래용)"""
    import datetime
    return template.replace('{{ datetime.now().strftime(\'%Y-%m-%d %H:%M:%S\') }}', 
                          datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

# 자동거래 라우트 추가
@app.route('/auto-trading')
def auto_trading_dashboard():
    """자동거래 대시보드 페이지"""
    return render_template_string('''
    <!-- 여기에 위에서 제공한 HTML 코드 전체 복사 -->
    ''')

@app.route('/api/auto-trading/start', methods=['POST'])
def start_auto_trading():
    """자동거래 시작"""
    try:
        config = request.get_json()
        auto_trading_state["config"] = config
        auto_trading_state["is_running"] = True
        
        # 자동거래 로그 추가
        mode = "시뮬레이션" if config.get("simulation_mode", True) else "실제 거래"
        log_message = f"🚀 자동거래 시작 - {mode} 모드, {config['market']}"
        auto_trading_state["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_message}")
        
        return jsonify({
            "success": True,
            "message": "자동거래가 시작되었습니다."
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/auto-trading/stop', methods=['POST'])
def stop_auto_trading():
    """자동거래 중지"""
    try:
        auto_trading_state["is_running"] = False
        
        log_message = "⏹️ 자동거래 중지"
        auto_trading_state["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_message}")
        
        return jsonify({
            "success": True,
            "message": "자동거래가 중지되었습니다."
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/auto-trading/config', methods=['POST'])
def update_auto_trading_config():
    """자동거래 설정 업데이트"""
    try:
        config = request.get_json()
        auto_trading_state["config"].update(config)
        
        log_message = f"⚙️ 전략 설정 적용: {config.get('market', 'Unknown')}"
        auto_trading_state["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_message}")
        
        return jsonify({
            "success": True,
            "message": "설정이 적용되었습니다."
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/auto-trading/logs')
def get_auto_trading_logs():
    """자동거래 로그 조회"""
    return jsonify({
        "success": True,
        "logs": auto_trading_state["logs"][-50:]  # 최근 50개만
    })

@app.route('/api/auto-trading/performance')
def get_auto_trading_performance():
    """자동거래 성과 조회"""
    return jsonify({
        "success": True,
        "performance": auto_trading_state["performance"]
    })

@app.route('/auto-trading')
def auto_trading_page():
    """자동거래 페이지"""
    return '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 업비트 자동거래</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 40px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container { 
            max-width: 800px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #4a5568;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .btn { 
            padding: 12px 24px; 
            margin: 10px; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px;
            transition: all 0.3s ease;
        }
        .start-btn { 
            background: linear-gradient(45deg, #48bb78, #38a169); 
            color: white; 
        }
        .stop-btn { 
            background: linear-gradient(45deg, #e53e3e, #c53030); 
            color: white; 
        }
        .btn:hover { transform: scale(1.05); }
        .status { 
            padding: 20px; 
            margin: 20px 0; 
            border-radius: 10px; 
            text-align: center;
            font-size: 1.2em;
            font-weight: bold;
        }
        .stopped { 
            background: #fed7d7; 
            color: #721c24; 
        }
        .running { 
            background: #c6f6d5; 
            color: #22543d; 
        }
        .log { 
            background: #2d3748; 
            color: #e2e8f0;
            padding: 20px; 
            height: 200px; 
            overflow-y: auto; 
            border-radius: 10px; 
            font-family: 'Courier New', monospace; 
            font-size: 14px;
        }
        .back-link {
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 업비트 자동거래 시스템</h1>
            <p>Railway 배포 버전</p>
        </div>
        
        <div class="status stopped" id="status">
            ⏹️ 상태: 중지됨
        </div>
        
        <div style="text-align: center;">
            <button class="btn start-btn" onclick="startTrading()">🚀 자동거래 시작 (시뮬레이션)</button>
            <button class="btn stop-btn" onclick="stopTrading()">⏹️ 자동거래 중지</button>
        </div>
        
        <h3>📋 거래 로그</h3>
        <div class="log" id="log">
[시스템] 자동거래 시스템 초기화 완료
[알림] 현재 시뮬레이션 모드로 설정되어 있습니다
        </div>
        
        <a href="/" class="back-link">← 메인 페이지로 돌아가기</a>
    </div>

    <script>
        let isRunning = false;

        function startTrading() {
            if (!isRunning) {
                isRunning = true;
                
                // UI 업데이트
                const status = document.getElementById('status');
                status.className = 'status running';
                status.innerHTML = '🟢 상태: 실행 중 (시뮬레이션)';
                
                // 로그 추가
                addLog('🚀 자동거래 시작 - 시뮬레이션 모드');
                addLog('📊 BTC 데이터 분석 중...');
                
                // 시뮬레이션 로그 생성
                setTimeout(() => {
                    addLog('📈 매수 신호 감지: BTC @ 50,000,000 KRW');
                }, 3000);
                
                setTimeout(() => {
                    addLog('💰 시뮬레이션 매수 완료: 0.001 BTC');
                }, 5000);
            }
        }

        function stopTrading() {
            if (isRunning) {
                isRunning = false;
                
                // UI 업데이트
                const status = document.getElementById('status');
                status.className = 'status stopped';
                status.innerHTML = '⏹️ 상태: 중지됨';
                
                // 로그 추가
                addLog('⏹️ 자동거래 중지');
            }
        }

        function addLog(message) {
            const log = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            log.innerHTML += '\\n[' + time + '] ' + message;
            log.scrollTop = log.scrollHeight;
        }

        // 5초마다 시뮬레이션 로그 추가
        setInterval(() => {
            if (isRunning) {
                const messages = [
                    '📊 시장 분석 중...',
                    '💹 RSI 지표 확인: 45.2',
                    '📈 이동평균선 분석 완료',
                    '🔍 매매 기회 탐색 중...'
                ];
                const randomMessage = messages[Math.floor(Math.random() * messages.length)];
                addLog(randomMessage);
            }
        }, 5000);
    </script>
</body>
</html>
    '''



if __name__ == '__main__':
    import os
    
    # Railway 환경 변수에서 포트 가져오기 (Railway에서 자동으로 설정됨)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print("🚀 업비트 캔들 차트 웹 서비스 시작")
    print(f"📊 접속 주소: http://localhost:{port}")
    print("🔗 API 문서:")
    print("  - GET /                    : 메인 페이지")
    print("  - GET /api/candles         : 캔들 데이터 조회")
    print("  - GET /api/markets         : 마켓 목록 조회")
    print("  - GET /api/status          : API 상태 확인")
    print("-" * 50)
    
    # Railway 환경에서 서버 실행
    app.run(
        host='0.0.0.0',     # 모든 IP에서 접근 가능
        port=port,          # Railway가 제공하는 포트 사용
        debug=debug,        # 프로덕션에서는 False
        threaded=True       # 멀티스레드 지원
    )