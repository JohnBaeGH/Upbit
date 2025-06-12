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

# Flask 애플리케이션 초기화
app = Flask(__name__)
CORS(app)  # CORS 설정으로 브라우저 요청 허용

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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