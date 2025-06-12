#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 API 캔들 데이터 조회 테스트
1단계: 비트코인(KRW-BTC) 5분 캔들 데이터 조회 및 출력
"""

import requests
import json
from datetime import datetime
import sys

def fetch_upbit_candles(market="KRW-BTC", interval=5, count=3):
    """
    업비트 API에서 캔들 데이터 조회
    
    Args:
        market (str): 마켓 코드 (예: KRW-BTC)
        interval (int): 분 단위 (1, 3, 5, 10, 15, 30, 60, 240)
        count (int): 조회할 캔들 개수 (최대 200)
    
    Returns:
        dict: API 응답 결과
    """
    try:
        # API 엔드포인트 구성
        base_url = "https://api.upbit.com"
        endpoint = f"/v1/candles/minutes/{interval}"
        
        # 파라미터 설정
        params = {
            'market': market,
            'count': count
        }
        
        # API 호출
        print(f"🔍 업비트 API 호출 중...")
        print(f"📊 종목: {market}")
        print(f"⏱️  간격: {interval}분")
        print(f"📈 개수: {count}개")
        print("-" * 50)
        
        response = requests.get(f"{base_url}{endpoint}", params=params)
        response.raise_for_status()
        
        # JSON 데이터 파싱
        candle_data = response.json()
        
        return {
            'status': 'success',
            'data': candle_data,
            'total_count': len(candle_data)
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'status': 'error',
            'message': f"API 호출 오류: {e}",
            'data': []
        }
    except json.JSONDecodeError as e:
        return {
            'status': 'error',
            'message': f"JSON 파싱 오류: {e}",
            'data': []
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f"예상치 못한 오류: {e}",
            'data': []
        }

def format_datetime(dt_string):
    """ISO 8601 날짜 문자열을 한국 시간으로 포맷팅"""
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        # UTC를 KST로 변환 (UTC+9)
        from datetime import timezone, timedelta
        kst = dt.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
        return kst.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return dt_string

def format_price(price):
    """가격을 읽기 쉽게 포맷팅"""
    if price >= 1000000:
        return f"{price:,.0f}"
    elif price >= 1000:
        return f"{price:,.1f}"
    else:
        return f"{price:.4f}"

def format_volume(volume):
    """거래량을 읽기 쉽게 포맷팅"""
    if volume >= 1000000:
        return f"{volume/1000000:.2f}M"
    elif volume >= 1000:
        return f"{volume/1000:.1f}K"
    else:
        return f"{volume:.4f}"

def display_candle_data(result):
    """캔들 데이터를 보기 좋게 출력"""
    if result['status'] != 'success':
        print(f"❌ 오류 발생: {result['message']}")
        return
    
    candles = result['data']
    
    if not candles:
        print("📭 조회된 데이터가 없습니다.")
        return
    
    print(f"✅ 총 {result['total_count']}개의 캔들 데이터 조회 성공!")
    print("=" * 80)
    
    # 테이블 헤더
    print(f"{'시간':<20} {'시가':<12} {'고가':<12} {'저가':<12} {'종가':<12} {'거래량':<12}")
    print("-" * 80)
    
    # 캔들 데이터 출력 (최신 순서로 정렬)
    for i, candle in enumerate(candles):
        time_str = format_datetime(candle['candle_date_time_kst'])
        opening_price = format_price(candle['opening_price'])
        high_price = format_price(candle['high_price'])
        low_price = format_price(candle['low_price'])
        trade_price = format_price(candle['trade_price'])  # 종가
        candle_acc_trade_volume = format_volume(candle['candle_acc_trade_volume'])
        
        print(f"{time_str:<20} {opening_price:<12} {high_price:<12} {low_price:<12} {trade_price:<12} {candle_acc_trade_volume:<12}")
    
    print("=" * 80)
    
    # 추가 정보 출력
    latest_candle = candles[0]  # 가장 최근 캔들
    print(f"\n📊 최신 캔들 상세 정보:")
    print(f"   • 시간: {format_datetime(latest_candle['candle_date_time_kst'])}")
    print(f"   • 시가: {format_price(latest_candle['opening_price'])} KRW")
    print(f"   • 고가: {format_price(latest_candle['high_price'])} KRW")
    print(f"   • 저가: {format_price(latest_candle['low_price'])} KRW")
    print(f"   • 종가: {format_price(latest_candle['trade_price'])} KRW")
    print(f"   • 거래량: {format_volume(latest_candle['candle_acc_trade_volume'])}")
    print(f"   • 거래대금: {format_volume(latest_candle['candle_acc_trade_price'])} KRW")
    
    # 가격 변동 계산
    price_change = latest_candle['trade_price'] - latest_candle['opening_price']
    price_change_rate = (price_change / latest_candle['opening_price']) * 100
    
    change_symbol = "📈" if price_change > 0 else "📉" if price_change < 0 else "➡️"
    change_color = "🔴" if price_change > 0 else "🔵" if price_change < 0 else "⚪"
    
    print(f"\n{change_symbol} 캔들 내 가격 변동:")
    print(f"   {change_color} 변동금액: {price_change:+,.0f} KRW")
    print(f"   {change_color} 변동률: {price_change_rate:+.2f}%")

def main():
    """메인 함수"""
    print("🚀 업비트 API 캔들 데이터 조회 테스트 시작")
    print("=" * 50)
    
    # 테스트 파라미터
    test_cases = [
        {"market": "KRW-BTC", "interval": 5, "count": 3, "desc": "비트코인 5분 캔들 3개"},
        {"market": "KRW-BTC", "interval": 5, "count": 10, "desc": "비트코인 5분 캔들 10개"},
        {"market": "KRW-ETH", "interval": 5, "count": 5, "desc": "이더리움 5분 캔들 5개"},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 테스트 케이스 {i}: {test_case['desc']}")
        print("-" * 30)
        
        # API 호출
        result = fetch_upbit_candles(
            market=test_case['market'],
            interval=test_case['interval'],
            count=test_case['count']
        )
        
        # 결과 출력
        display_candle_data(result)
        
        if i < len(test_cases):
            print("\n" + "="*50 + "\n")
    
    print("\n✨ 모든 테스트 완료!")
    
    # 원시 JSON 데이터도 보여주기
    print("\n📄 원시 JSON 데이터 샘플:")
    print("-" * 30)
    result = fetch_upbit_candles("KRW-BTC", 5, 1)
    if result['status'] == 'success' and result['data']:
        print(json.dumps(result['data'][0], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main() 