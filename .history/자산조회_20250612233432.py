#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 전체 계좌 조회 스크립트
.env 파일에서 API 키를 읽어와서 업비트 계좌 정보를 조회하고 출력합니다.
"""

import os
import sys
import jwt
import uuid
import requests
from datetime import datetime
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def get_api_credentials():
    """환경 변수에서 API 인증 정보를 가져옵니다."""
    # 현재 디렉토리 확인
    current_dir = os.getcwd()
    env_file_path = os.path.join(current_dir, '.env')
    
    print(f"현재 디렉토리: {current_dir}")
    print(f".env 파일 경로: {env_file_path}")
    print(f".env 파일 존재 여부: {os.path.exists(env_file_path)}")
    
    # .env 파일을 명시적으로 로드
    if os.path.exists(env_file_path):
        load_dotenv(env_file_path)
        print(".env 파일을 로드했습니다.")
    else:
        print("❌ .env 파일을 찾을 수 없습니다.")
    
    access_key = os.getenv('UPBIT_OPEN_API_ACCESS_KEY')
    secret_key = os.getenv('UPBIT_OPEN_API_SECRET_KEY')
    server_url = os.getenv('UPBIT_OPEN_API_SERVER_URL', 'https://api.upbit.com')
    
    print(f"Access Key 로드됨: {'예' if access_key else '아니오'}")
    print(f"Secret Key 로드됨: {'예' if secret_key else '아니오'}")
    
    if not access_key or not secret_key:
        print("❌ 오류: .env 파일에 UPBIT_OPEN_API_ACCESS_KEY와 UPBIT_OPEN_API_SECRET_KEY가 설정되어 있는지 확인하세요.")
        sys.exit(1)
    
    return access_key, secret_key, server_url

def generate_jwt_token(access_key, secret_key):
    """JWT 토큰을 생성합니다."""
    payload = {
        'access_key': access_key,
        'nonce': str(uuid.uuid4()),
    }
    
    jwt_token = jwt.encode(payload, secret_key, algorithm='HS256')
    return f'Bearer {jwt_token}'

def get_accounts(access_key, secret_key, server_url):
    """전체 계좌 조회 API를 호출합니다."""
    try:
        # JWT 토큰 생성
        authorization_token = generate_jwt_token(access_key, secret_key)
        
        # API 요청 헤더
        headers = {
            "Authorization": authorization_token,
            "Accept": "application/json"
        }
        
        # API 요청
        response = requests.get(f"{server_url}/v1/accounts", headers=headers)
        
        # 응답 확인
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API 요청 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None

def format_currency_amount(amount):
    """통화 금액을 포맷팅합니다."""
    try:
        amount_float = float(amount)
        if amount_float == 0:
            return "0"
        elif amount_float < 0.01:
            return f"{amount_float:.8f}"
        else:
            return f"{amount_float:,.2f}"
    except:
        return amount

def print_accounts_info(accounts):
    """계좌 정보를 보기 좋게 출력합니다."""
    if not accounts:
        print("❌ 조회된 계좌 정보가 없습니다.")
        return
    
    print("\n" + "="*60)
    print("🏦 업비트 전체 계좌 조회 결과")
    print("="*60)
    print(f"조회 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 계좌 수: {len(accounts)}개")
    print("-"*60)
    
    total_krw_value = 0
    
    for i, account in enumerate(accounts, 1):
        currency = account.get('currency', 'N/A')
        balance = account.get('balance', '0')
        locked = account.get('locked', '0')
        avg_buy_price = account.get('avg_buy_price', '0')
        unit_currency = account.get('unit_currency', 'KRW')
        
        # 잔고와 잠긴 금액 합계
        total_balance = float(balance) + float(locked)
        
        # 원화 환산 가치 계산 (평균 매수가 기준)
        if currency != 'KRW' and float(avg_buy_price) > 0:
            krw_value = total_balance * float(avg_buy_price)
            total_krw_value += krw_value
        elif currency == 'KRW':
            krw_value = total_balance
            total_krw_value += krw_value
        else:
            krw_value = 0
        
        print(f"{i:2d}. {currency}")
        print(f"    💰 보유량: {format_currency_amount(balance)}")
        
        if float(locked) > 0:
            print(f"    🔒 잠긴 금액: {format_currency_amount(locked)}")
            
        if currency != 'KRW' and float(avg_buy_price) > 0:
            print(f"    📊 평균 매수가: {format_currency_amount(avg_buy_price)} {unit_currency}")
            
        if krw_value > 0:
            print(f"    💵 원화 환산: {format_currency_amount(krw_value)} KRW")
            
        print()
    
    print("-"*60)
    print(f"📈 총 자산 가치 (추정): {format_currency_amount(total_krw_value)} KRW")
    print("="*60)
    
    # 보유 중인 코인만 표시
    print("\n🪙 보유 중인 암호화폐:")
    crypto_assets = [acc for acc in accounts if acc.get('currency') != 'KRW' and float(acc.get('balance', 0)) > 0]
    
    if crypto_assets:
        for asset in crypto_assets:
            currency = asset.get('currency')
            balance = format_currency_amount(asset.get('balance', '0'))
            print(f"   • {currency}: {balance}")
    else:
        print("   보유 중인 암호화폐가 없습니다.")

def main():
    """메인 함수"""
    print("🚀 업비트 전체 계좌 조회를 시작합니다...")
    
    # API 인증 정보 가져오기
    access_key, secret_key, server_url = get_api_credentials()
    
    # 계좌 정보 조회
    accounts = get_accounts(access_key, secret_key, server_url)
    
    # 결과 출력
    if accounts:
        print_accounts_info(accounts)
        print("\n✅ 계좌 조회가 완료되었습니다.")
    else:
        print("\n❌ 계좌 조회에 실패했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    main() 