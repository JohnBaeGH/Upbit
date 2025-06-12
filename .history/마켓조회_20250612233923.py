#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 마켓 정보 조회 스크립트
업비트에서 제공하는 모든 마켓(거래 쌍) 정보를 조회하고 출력합니다.
"""

import requests
import json
from datetime import datetime

def get_all_markets():
    """업비트 전체 마켓 정보를 조회합니다."""
    try:
        url = "https://api.upbit.com/v1/market/all"
        
        print("🔍 업비트 마켓 정보를 조회 중...")
        
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API 요청 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None

def categorize_markets(markets):
    """마켓을 기준 통화별로 분류합니다."""
    categories = {
        'KRW': [],  # 원화 마켓
        'BTC': [],  # 비트코인 마켓
        'USDT': [], # 테더 마켓
        'ETH': []   # 이더리움 마켓
    }
    
    for market in markets:
        market_code = market['market']
        base_currency = market_code.split('-')[0]
        
        if base_currency in categories:
            categories[base_currency].append(market)
    
    return categories

def print_market_info(markets):
    """마켓 정보를 보기 좋게 출력합니다."""
    if not markets:
        print("❌ 조회된 마켓 정보가 없습니다.")
        return
    
    print("\n" + "="*80)
    print("📊 업비트 전체 마켓 조회 결과")
    print("="*80)
    print(f"조회 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 마켓 수: {len(markets)}개")
    print("="*80)
    
    # 마켓을 카테고리별로 분류
    categories = categorize_markets(markets)
    
    # 각 카테고리별로 출력
    for base_currency, market_list in categories.items():
        if market_list:
            print(f"\n🏷️  {base_currency} 마켓 ({len(market_list)}개)")
            print("-" * 60)
            
            # 표 헤더
            print(f"{'번호':<4} {'마켓코드':<15} {'한글명':<20} {'영문명':<25}")
            print("-" * 60)
            
            for i, market in enumerate(market_list, 1):
                market_code = market['market']
                korean_name = market['korean_name']
                english_name = market['english_name']
                
                # 문자열 길이 조정 (한글 문자 고려)
                korean_name_display = korean_name[:18] + '...' if len(korean_name) > 18 else korean_name
                english_name_display = english_name[:23] + '...' if len(english_name) > 23 else english_name
                
                print(f"{i:<4} {market_code:<15} {korean_name_display:<20} {english_name_display:<25}")
    
    # 요약 정보
    print("\n" + "="*80)
    print("📈 마켓 요약")
    print("="*80)
    for base_currency, market_list in categories.items():
        if market_list:
            print(f"{base_currency} 마켓: {len(market_list):>3}개")
    
    print(f"{'총 마켓':<8}: {len(markets):>3}개")
    print("="*80)

def save_to_json(markets, filename="upbit_markets.json"):
    """마켓 정보를 JSON 파일로 저장합니다."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(markets, f, ensure_ascii=False, indent=2)
        print(f"📁 마켓 정보가 '{filename}' 파일로 저장되었습니다.")
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")

def main():
    """메인 함수"""
    print("🚀 업비트 마켓 정보 조회를 시작합니다...")
    
    # 마켓 정보 조회
    markets = get_all_markets()
    
    if markets:
        # 결과 출력
        print_market_info(markets)
        
        # JSON 파일로 저장 여부 확인
        try:
            save_choice = input("\n💾 결과를 JSON 파일로 저장하시겠습니까? (y/N): ").lower().strip()
            if save_choice in ['y', 'yes']:
                save_to_json(markets)
        except KeyboardInterrupt:
            print("\n")
        
        print("\n✅ 마켓 조회가 완료되었습니다.")
    else:
        print("\n❌ 마켓 조회에 실패했습니다.")

if __name__ == "__main__":
    main() 