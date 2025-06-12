#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 캔들 데이터 조회 스크립트
업비트에서 제공하는 캔들 차트 데이터를 조회하고 출력합니다.
"""

import requests
import json
from datetime import datetime

def get_candle_data(market="KRW-BTC", minutes=5, count=3):
    """업비트 분 캔들 데이터를 조회합니다."""
    try:
        url = f"https://api.upbit.com/v1/candles/minutes/{minutes}"
        params = {
            'market': market,
            'count': count
        }
        
        print(f"🕯️ {market} {minutes}분 캔들 데이터를 조회 중... (최근 {count}개)")
        
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
    if price >= 1000:
        return f"{price:,.0f}"
    elif price >= 1:
        return f"{price:,.2f}"
    else:
        return f"{price:.8f}"

def format_volume(volume):
    """거래량을 포맷팅합니다."""
    return f"{volume:,.8f}"

def calculate_change(open_price, close_price):
    """변화율을 계산합니다."""
    if open_price == 0:
        return 0
    change = ((close_price - open_price) / open_price) * 100
    return change

def get_change_indicator(change):
    """변화율에 따른 표시 문자를 반환합니다."""
    if change > 0:
        return "🔺", "상승"
    elif change < 0:
        return "🔻", "하락"
    else:
        return "🔹", "보합"

def print_candle_data(candles, market, minutes):
    """캔들 데이터를 보기 좋게 출력합니다."""
    if not candles:
        print("❌ 조회된 캔들 데이터가 없습니다.")
        return
    
    print("\n" + "="*100)
    print(f"🕯️ {market} - {minutes}분 캔들 데이터 조회 결과")
    print("="*100)
    print(f"조회 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"데이터 개수: {len(candles)}개")
    print("-"*100)
    
    # 테이블 헤더
    headers = [
        "시간", "시가", "고가", "저가", "종가", "변화율", "거래량"
    ]
    
    # 헤더 출력
    print(f"{'시간':<20} {'시가':<12} {'고가':<12} {'저가':<12} {'종가':<12} {'변화율':<10} {'거래량':<15}")
    print("-"*100)
    
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
        indicator, status = get_change_indicator(change)
        
        # 거래량
        candle_acc_trade_volume = candle['candle_acc_trade_volume']
        
        # 데이터 출력
        print(f"{time_str:<20} "
              f"{format_price(opening_price):<12} "
              f"{format_price(high_price):<12} "
              f"{format_price(low_price):<12} "
              f"{format_price(trade_price):<12} "
              f"{indicator} {change:+.2f}%"[:10].ljust(10) + " "
              f"{format_volume(candle_acc_trade_volume):<15}")
    
    print("-"*100)
    
    # 요약 정보
    if candles:
        latest = candles[0]  # 가장 최신 데이터
        oldest = candles[-1]  # 가장 오래된 데이터
        
        latest_price = latest['trade_price']
        oldest_price = oldest['opening_price']
        total_change = calculate_change(oldest_price, latest_price)
        total_indicator, total_status = get_change_indicator(total_change)
        
        print(f"📊 요약 정보")
        print(f"   최신 가격: {format_price(latest_price)} KRW")
        print(f"   전체 변화: {total_indicator} {total_change:+.2f}% ({total_status})")
        print(f"   최고가: {format_price(max(candle['high_price'] for candle in candles))} KRW")
        print(f"   최저가: {format_price(min(candle['low_price'] for candle in candles))} KRW")
        print(f"   총 거래량: {format_volume(sum(candle['candle_acc_trade_volume'] for candle in candles))}")
    
    print("="*100)

def save_to_json(candles, filename="upbit_candles.json"):
    """캔들 데이터를 JSON 파일로 저장합니다."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(candles, f, ensure_ascii=False, indent=2)
        print(f"📁 캔들 데이터가 '{filename}' 파일로 저장되었습니다.")
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")

def main():
    """메인 함수"""
    print("🚀 업비트 캔들 데이터 조회를 시작합니다...")
    
    # 기본 설정값
    market = "KRW-BTC"
    minutes = 5
    count = 3
    
    # 사용자 입력 받기 (선택사항)
    try:
        print(f"\n기본 설정: {market}, {minutes}분 캔들, 최근 {count}개")
        custom = input("설정을 변경하시겠습니까? (y/N): ").lower().strip()
        
        if custom in ['y', 'yes']:
            market = input(f"마켓 코드 (기본값: {market}): ").strip() or market
            minutes_input = input(f"캔들 간격 (1,3,5,15,10,30,60,240) (기본값: {minutes}): ").strip()
            if minutes_input:
                minutes = int(minutes_input)
            count_input = input(f"조회할 개수 (기본값: {count}): ").strip()
            if count_input:
                count = int(count_input)
    except (KeyboardInterrupt, ValueError):
        print("\n기본값으로 진행합니다.")
    
    # 캔들 데이터 조회
    candles = get_candle_data(market, minutes, count)
    
    if candles:
        # 결과 출력
        print_candle_data(candles, market, minutes)
        
        # JSON 파일로 저장 여부 확인
        try:
            save_choice = input("\n💾 결과를 JSON 파일로 저장하시겠습니까? (y/N): ").lower().strip()
            if save_choice in ['y', 'yes']:
                filename = f"upbit_{market}_{minutes}min_candles.json"
                save_to_json(candles, filename)
        except KeyboardInterrupt:
            print("\n")
        
        print("\n✅ 캔들 데이터 조회가 완료되었습니다.")
    else:
        print("\n❌ 캔들 데이터 조회에 실패했습니다.")

if __name__ == "__main__":
    main() 