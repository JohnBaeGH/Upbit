#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 5분 캔들 데이터 조회 스크립트 (간단 버전)
KRW-BTC 5분 캔들 3개를 조회하고 출력합니다.
"""

import requests
from datetime import datetime

def get_candle_data():
    """업비트 5분 캔들 데이터를 조회합니다."""
    try:
        url = "https://api.upbit.com/v1/candles/minutes/5"
        params = {
            'market': 'KRW-BTC',
            'count': 3
        }
        
        print("🕯️ KRW-BTC 5분 캔들 데이터를 조회 중... (최근 3개)")
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API 요청 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None

def format_price(price):
    """가격을 포맷팅합니다."""
    return f"{price:,.0f}"

def format_volume(volume):
    """거래량을 포맷팅합니다."""
    return f"{volume:.2f}"

def calculate_change(open_price, close_price):
    """변화율을 계산합니다."""
    if open_price == 0:
        return 0
    change = ((close_price - open_price) / open_price) * 100
    return change

def get_change_indicator(change):
    """변화율에 따른 표시 문자를 반환합니다."""
    if change > 0:
        return "🔺"
    elif change < 0:
        return "🔻"
    else:
        return "🔹"

def print_candle_data(candles):
    """캔들 데이터를 보기 좋게 출력합니다."""
    if not candles:
        print("❌ 조회된 캔들 데이터가 없습니다.")
        return
    
    print("\n" + "="*80)
    print("🕯️ KRW-BTC 5분 캔들 데이터 조회 결과")
    print("="*80)
    print(f"조회 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"데이터 개수: {len(candles)}개")
    print("-"*80)
    
    # 헤더 출력
    print(f"{'시간':<20} {'시가':<12} {'고가':<12} {'저가':<12} {'종가':<12} {'변화율':<8} {'거래량':<12}")
    print("-"*80)
    
    # 데이터는 최신순으로 정렬되어 있으므로 역순으로 출력 (시간 순서대로)
    for candle in reversed(candles):
        # 시간 포맷팅
        candle_time = datetime.fromisoformat(candle['candle_date_time_kst'].replace('Z', '+00:00'))
        time_str = candle_time.strftime('%m/%d %H:%M')
        
        # 가격 정보
        opening_price = candle['opening_price']
        high_price = candle['high_price']
        low_price = candle['low_price']
        trade_price = candle['trade_price']
        
        # 변화율 계산
        change = calculate_change(opening_price, trade_price)
        indicator = get_change_indicator(change)
        
        # 거래량
        candle_acc_trade_volume = candle['candle_acc_trade_volume']
        
        # 데이터 출력
        change_str = f"{indicator}{change:+.2f}%"
        print(f"{time_str:<20} "
              f"{format_price(opening_price):<12} "
              f"{format_price(high_price):<12} "
              f"{format_price(low_price):<12} "
              f"{format_price(trade_price):<12} "
              f"{change_str:<8} "
              f"{format_volume(candle_acc_trade_volume):<12}")
    
    print("-"*80)
    
    # 요약 정보
    if candles:
        latest = candles[0]  # 가장 최신 데이터
        oldest = candles[-1]  # 가장 오래된 데이터
        
        latest_price = latest['trade_price']
        oldest_price = oldest['opening_price']
        total_change = calculate_change(oldest_price, latest_price)
        total_indicator = get_change_indicator(total_change)
        
        print(f"📊 요약 정보")
        print(f"   최신 가격: {format_price(latest_price)} KRW")
        print(f"   전체 변화: {total_indicator} {total_change:+.2f}%")
        print(f"   최고가: {format_price(max(candle['high_price'] for candle in candles))} KRW")
        print(f"   최저가: {format_price(min(candle['low_price'] for candle in candles))} KRW")
        print(f"   총 거래량: {format_volume(sum(candle['candle_acc_trade_volume'] for candle in candles))}")
    
    print("="*80)

def main():
    """메인 함수"""
    print("🚀 업비트 캔들 데이터 조회를 시작합니다...")
    
    # 캔들 데이터 조회
    candles = get_candle_data()
    
    if candles:
        # 결과 출력
        print_candle_data(candles)
        print("\n✅ 캔들 데이터 조회가 완료되었습니다.")
    else:
        print("\n❌ 캔들 데이터 조회에 실패했습니다.")

if __name__ == "__main__":
    main() 