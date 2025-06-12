#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 API 데이터 구조 분석 스크립트
캔들 차트 구현을 위한 데이터 구조 및 포맷 분석
"""

import requests
import json
from datetime import datetime

def get_candle_data(count=10):
    """업비트 5분 캔들 데이터를 조회합니다."""
    try:
        url = "https://api.upbit.com/v1/candles/minutes/5"
        params = {
            'market': 'KRW-BTC',
            'count': count
        }
        
        print(f"🔍 KRW-BTC 5분 캔들 데이터 구조 분석 중... (최근 {count}개)")
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API 요청 실패: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None

def analyze_data_structure(candles):
    """캔들 데이터 구조를 분석합니다."""
    if not candles:
        print("❌ 분석할 데이터가 없습니다.")
        return
    
    print("\n" + "="*80)
    print("📊 업비트 캔들 데이터 구조 분석")
    print("="*80)
    
    # 첫 번째 캔들 데이터 구조 분석
    first_candle = candles[0]
    
    print("🔍 단일 캔들 데이터 구조:")
    print("-" * 50)
    for key, value in first_candle.items():
        data_type = type(value).__name__
        print(f"  {key:<25} : {data_type:<10} = {value}")
    
    print("\n📋 필드별 상세 설명:")
    print("-" * 50)
    field_descriptions = {
        'market': '마켓 코드 (예: KRW-BTC)',
        'candle_date_time_utc': 'UTC 기준 캔들 시간',
        'candle_date_time_kst': 'KST 기준 캔들 시간',
        'opening_price': '시가 (시작 가격)',
        'high_price': '고가 (최고 가격)',
        'low_price': '저가 (최저 가격)',
        'trade_price': '종가 (마감 가격)',
        'timestamp': '타임스탬프',
        'candle_acc_trade_price': '누적 거래 대금',
        'candle_acc_trade_volume': '누적 거래량',
        'unit': '분 단위'
    }
    
    for key, description in field_descriptions.items():
        if key in first_candle:
            print(f"  {key:<25} : {description}")
    
    print("\n📈 차트 구현에 필요한 핵심 데이터:")
    print("-" * 50)
    chart_data = {
        'timestamp': first_candle.get('candle_date_time_kst', ''),
        'open': first_candle.get('opening_price', 0),
        'high': first_candle.get('high_price', 0),
        'low': first_candle.get('low_price', 0),
        'close': first_candle.get('trade_price', 0),
        'volume': first_candle.get('candle_acc_trade_volume', 0)
    }
    
    for key, value in chart_data.items():
        print(f"  {key:<10} : {value}")

def convert_to_chart_format(candles):
    """캔들 데이터를 차트 라이브러리용 포맷으로 변환합니다."""
    if not candles:
        return []
    
    chart_data = []
    
    for candle in reversed(candles):  # 시간순 정렬
        # 시간을 타임스탬프로 변환
        dt = datetime.fromisoformat(candle['candle_date_time_kst'].replace('Z', '+00:00'))
        timestamp = int(dt.timestamp() * 1000)  # JavaScript 타임스탬프 (밀리초)
        
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
    
    return chart_data

def print_chart_format_sample(chart_data):
    """차트 포맷 샘플을 출력합니다."""
    if not chart_data:
        return
    
    print("\n" + "="*80)
    print("📊 차트 라이브러리용 데이터 포맷 (샘플 3개)")
    print("="*80)
    
    for i, data in enumerate(chart_data[:3], 1):
        print(f"\n📅 캔들 {i}:")
        print(f"  시간: {data['datetime']}")
        print(f"  타임스탬프: {data['timestamp']}")
        print(f"  시가: {data['open']:,.0f}")
        print(f"  고가: {data['high']:,.0f}")
        print(f"  저가: {data['low']:,.0f}")
        print(f"  종가: {data['close']:,.0f}")
        print(f"  거래량: {data['volume']:.2f}")
    
    print("\n🔧 JavaScript용 JSON 형태:")
    print("-" * 50)
    print(json.dumps(chart_data[:3], indent=2, ensure_ascii=False))

def generate_flask_data_format(chart_data):
    """Flask 응답용 데이터 포맷을 생성합니다."""
    response_data = {
        'status': 'success',
        'market': 'KRW-BTC',
        'interval': '5m',
        'count': len(chart_data),
        'data': chart_data,
        'updated_at': datetime.now().isoformat()
    }
    
    print("\n" + "="*80)
    print("🌐 Flask API 응답 포맷")
    print("="*80)
    print(json.dumps(response_data, indent=2, ensure_ascii=False))
    
    return response_data

def main():
    """메인 함수"""
    print("🚀 업비트 API 데이터 구조 분석을 시작합니다...")
    
    # 캔들 데이터 조회 (더 많은 데이터로 분석)
    candles = get_candle_data(count=10)
    
    if candles:
        # 1. 원본 데이터 구조 분석
        analyze_data_structure(candles)
        
        # 2. 차트용 포맷으로 변환
        chart_data = convert_to_chart_format(candles)
        
        # 3. 차트 포맷 샘플 출력
        print_chart_format_sample(chart_data)
        
        # 4. Flask API 응답 포맷 생성
        flask_response = generate_flask_data_format(chart_data)
        
        print("\n✅ 데이터 구조 분석이 완료되었습니다.")
        print("\n📋 분석 요약:")
        print("  ✓ 업비트 API 원본 데이터 구조 확인")
        print("  ✓ 차트 라이브러리용 포맷 변환")
        print("  ✓ Flask API 응답 포맷 설계")
        print("  ✓ JavaScript 호환 타임스탬프 변환")
        
    else:
        print("\n❌ 데이터 구조 분석에 실패했습니다.")

if __name__ == "__main__":
    main() 