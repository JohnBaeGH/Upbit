#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 주문하기 스크립트
BTC-KRW를 1만원 시장가 매수 주문
.env 파일에서 API 키를 읽어와서 주문을 실행합니다.
"""

import os
import sys
import jwt
import uuid
import hashlib
import requests
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlencode

# .env 파일 로드
load_dotenv()

def get_api_credentials():
    """환경 변수에서 API 인증 정보를 가져옵니다."""
    env_file_path = os.path.join(os.getcwd(), '.env')
    if os.path.exists(env_file_path):
        load_dotenv(env_file_path)
    
    access_key = os.getenv('UPBIT_OPEN_API_ACCESS_KEY')
    secret_key = os.getenv('UPBIT_OPEN_API_SECRET_KEY')
    server_url = os.getenv('UPBIT_OPEN_API_SERVER_URL', 'https://api.upbit.com')
    
    if not access_key or not secret_key:
        print("❌ 오류: .env 파일에 UPBIT_OPEN_API_ACCESS_KEY와 UPBIT_OPEN_API_SECRET_KEY가 설정되어 있는지 확인하세요.")
        sys.exit(1)
    
    return access_key, secret_key, server_url

def generate_jwt_token_with_query(access_key, secret_key, query):
    """쿼리 파라미터를 포함한 JWT 토큰을 생성합니다."""
    query_string = urlencode(query).encode()
    
    m = hashlib.sha512()
    m.update(query_string)
    query_hash = m.hexdigest()
    
    payload = {
        'access_key': access_key,
        'nonce': str(uuid.uuid4()),
        'query_hash': query_hash,
        'query_hash_alg': 'SHA512',
    }
    
    jwt_token = jwt.encode(payload, secret_key, algorithm='HS256')
    return f'Bearer {jwt_token}'

def get_current_price(server_url, market):
    """현재 시장 가격을 조회합니다."""
    try:
        url = f"{server_url}/v1/ticker"
        params = {'markets': market}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        ticker_data = response.json()
        if ticker_data:
            current_price = ticker_data[0]['trade_price']
            return current_price
        else:
            return None
            
    except Exception as e:
        print(f"❌ 현재 가격 조회 실패: {e}")
        return None

def get_account_balance(access_key, secret_key, server_url, currency='KRW'):
    """계좌 잔고를 조회합니다."""
    try:
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
        }
        
        jwt_token = jwt.encode(payload, secret_key, algorithm='HS256')
        authorization_token = f'Bearer {jwt_token}'
        
        headers = {"Authorization": authorization_token}
        
        response = requests.get(f"{server_url}/v1/accounts", headers=headers)
        response.raise_for_status()
        
        accounts = response.json()
        for account in accounts:
            if account['currency'] == currency:
                return float(account['balance'])
        
        return 0.0
        
    except Exception as e:
        print(f"❌ 계좌 잔고 조회 실패: {e}")
        return None

def check_order_possibility(server_url, access_key, secret_key, market):
    """주문 가능 정보를 확인합니다."""
    try:
        query = {'market': market}
        authorization_token = generate_jwt_token_with_query(access_key, secret_key, query)
        
        headers = {"Authorization": authorization_token}
        
        response = requests.get(f"{server_url}/v1/orders/chance", params=query, headers=headers)
        response.raise_for_status()
        
        chance_data = response.json()
        return chance_data
        
    except Exception as e:
        print(f"❌ 주문 가능 정보 조회 실패: {e}")
        return None

def place_market_buy_order(access_key, secret_key, server_url, market, price):
    """
    시장가 매수 주문을 실행합니다.
    
    Args:
        access_key (str): 업비트 액세스 키
        secret_key (str): 업비트 시크릿 키
        server_url (str): API 서버 URL
        market (str): 마켓 코드 (예: KRW-BTC)
        price (str): 주문 금액 (원화)
    
    Returns:
        dict: 주문 결과
    """
    try:
        # 주문 파라미터 설정
        query = {
            'market': market,      # 마켓 코드
            'side': 'bid',         # 매수
            'ord_type': 'price',   # 시장가 (금액 기준)
            'price': str(price),   # 주문 금액
        }
        
        # JWT 토큰 생성
        authorization_token = generate_jwt_token_with_query(access_key, secret_key, query)
        
        # API 요청 헤더
        headers = {
            "Authorization": authorization_token,
            "Content-Type": "application/json"
        }
        
        print(f"📤 주문 요청 중...")
        print(f"   마켓: {market}")
        print(f"   주문 타입: 시장가 매수")
        print(f"   주문 금액: {price:,}원")
        
        # 주문 API 호출
        response = requests.post(f"{server_url}/v1/orders", params=query, headers=headers)
        
        # 응답 확인
        if response.status_code == 201:  # 주문 성공
            order_result = response.json()
            return order_result
        else:
            print(f"❌ 주문 실패: HTTP {response.status_code}")
            print(f"응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 주문 실행 오류: {e}")
        return None

def format_order_result(order_result):
    """주문 결과를 보기 좋게 출력합니다."""
    if not order_result:
        print("❌ 주문 결과가 없습니다.")
        return
    
    print("\n" + "="*60)
    print("✅ 주문이 성공적으로 체결되었습니다!")
    print("="*60)
    
    # 주문 정보 출력
    uuid = order_result.get('uuid', 'N/A')
    market = order_result.get('market', 'N/A')
    side = '매수' if order_result.get('side') == 'bid' else '매도'
    ord_type = order_result.get('ord_type', 'N/A')
    price = order_result.get('price', '0')
    volume = order_result.get('volume', '0')
    created_at = order_result.get('created_at', '')
    
    # 시간 포맷팅
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            formatted_time = created_at
    else:
        formatted_time = 'N/A'
    
    print(f"📋 주문 정보:")
    print(f"   주문 ID: {uuid}")
    print(f"   마켓: {market}")
    print(f"   주문 유형: {side} ({ord_type})")
    print(f"   주문 금액: {float(price):,.0f}원")
    print(f"   주문 시간: {formatted_time}")
    
    # 추가 정보
    if float(volume) > 0:
        print(f"   예상 수량: {volume}")
    
    print("="*60)

def main():
    """메인 함수"""
    print("🚀 업비트 BTC 매수 주문을 시작합니다...")
    
    # 주문 설정
    market = "KRW-BTC"
    order_amount = 10000  # 1만원
    
    print(f"📊 주문 설정:")
    print(f"   마켓: {market}")
    print(f"   주문 금액: {order_amount:,}원")
    print(f"   주문 타입: 시장가 매수")
    print("-" * 50)
    
    # API 인증 정보 가져오기
    access_key, secret_key, server_url = get_api_credentials()
    
    # 1. 현재 BTC 가격 확인
    print("1️⃣ 현재 BTC 가격 확인 중...")
    current_price = get_current_price(server_url, market)
    if current_price:
        print(f"   현재 BTC 가격: {current_price:,.0f}원")
        estimated_btc = order_amount / current_price
        print(f"   예상 구매량: {estimated_btc:.8f} BTC")
    else:
        print("   ⚠️ 현재 가격을 확인할 수 없습니다.")
    
    # 2. 계좌 잔고 확인
    print("\n2️⃣ 계좌 잔고 확인 중...")
    krw_balance = get_account_balance(access_key, secret_key, server_url, 'KRW')
    if krw_balance is not None:
        print(f"   KRW 잔고: {krw_balance:,.0f}원")
        if krw_balance < order_amount:
            print(f"❌ 잔고 부족: 주문 금액({order_amount:,}원)이 잔고({krw_balance:,.0f}원)보다 큽니다.")
            return
        else:
            print("   ✅ 잔고 충분")
    else:
        print("   ⚠️ 잔고를 확인할 수 없습니다.")
    
    # 3. 주문 가능 정보 확인
    print("\n3️⃣ 주문 가능 정보 확인 중...")
    chance_info = check_order_possibility(server_url, access_key, secret_key, market)
    if chance_info:
        bid_fee = chance_info.get('bid_fee', '0')
        print(f"   매수 수수료: {float(bid_fee)*100:.3f}%")
        print("   ✅ 주문 가능")
    else:
        print("   ⚠️ 주문 가능 정보를 확인할 수 없습니다.")
    
    # 4. 사용자 확인
    print(f"\n4️⃣ 주문 확인")
    print(f"   {market}를 {order_amount:,}원 시장가 매수 주문하시겠습니까?")
    
    try:
        confirm = input("   진행하시겠습니까? (y/N): ").lower().strip()
        if confirm not in ['y', 'yes']:
            print("   주문이 취소되었습니다.")
            return
    except KeyboardInterrupt:
        print("\n   주문이 취소되었습니다.")
        return
    
    # 5. 주문 실행
    print("\n5️⃣ 주문 실행 중...")
    order_result = place_market_buy_order(access_key, secret_key, server_url, market, order_amount)
    
    # 6. 결과 출력
    if order_result:
        format_order_result(order_result)
        print("\n✅ 주문이 완료되었습니다.")
        print("💡 주문 상태는 업비트 거래소에서 확인할 수 있습니다.")
    else:
        print("\n❌ 주문에 실패했습니다.")
        print("💡 API 키 권한, 잔고, 네트워크 상태를 확인해주세요.")

if __name__ == "__main__":
    main() 