#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 API 클래스 모듈
자산조회, 주문하기, 시세조회 등의 기능을 제공하는 통합 API 클래스
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
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UpbitAPI:
    """업비트 API 통합 클래스"""
    
    def __init__(self):
        """API 클래스 초기화"""
        self.base_url = "https://api.upbit.com"
        self.access_key = None
        self.secret_key = None
        self._load_credentials()
    
    def _load_credentials(self):
        """환경 변수에서 API 인증 정보를 로드합니다."""
        # .env 파일 로드
        env_file_path = os.path.join(os.getcwd(), '.env')
        if os.path.exists(env_file_path):
            load_dotenv(env_file_path)
        
        self.access_key = os.getenv('UPBIT_OPEN_API_ACCESS_KEY')
        self.secret_key = os.getenv('UPBIT_OPEN_API_SECRET_KEY')
        
        if not self.access_key or not self.secret_key:
            logger.warning("API 키가 설정되지 않았습니다. 인증이 필요한 기능은 사용할 수 없습니다.")
    
    def _generate_jwt_token(self, query=None):
        """JWT 토큰을 생성합니다."""
        if not self.access_key or not self.secret_key:
            raise Exception("API 키가 설정되지 않았습니다.")
        
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
        }
        
        if query:
            query_string = urlencode(query).encode()
            m = hashlib.sha512()
            m.update(query_string)
            query_hash = m.hexdigest()
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'
        
        jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return f'Bearer {jwt_token}'
    
    def get_accounts(self):
        """전체 계좌 조회"""
        try:
            authorization_token = self._generate_jwt_token()
            headers = {"Authorization": authorization_token}
            
            response = requests.get(f"{self.base_url}/v1/accounts", headers=headers)
            response.raise_for_status()
            
            return {
                'status': 'success',
                'data': response.json()
            }
            
        except Exception as e:
            logger.error(f"계좌 조회 실패: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'data': []
            }
    
    def get_markets(self, is_details=False):
        """마켓 목록 조회"""
        try:
            params = {}
            if is_details:
                params['isDetails'] = 'true'
            
            response = requests.get(f"{self.base_url}/v1/market/all", params=params)
            response.raise_for_status()
            
            markets = response.json()
            # KRW 마켓만 필터링
            krw_markets = [m for m in markets if m['market'].startswith('KRW-')]
            
            return {
                'status': 'success',
                'data': krw_markets
            }
            
        except Exception as e:
            logger.error(f"마켓 정보 조회 실패: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'data': []
            }
    
    def get_ticker(self, markets):
        """현재가 정보 조회"""
        try:
            if isinstance(markets, str):
                markets = [markets]
            
            params = {'markets': ','.join(markets)}
            response = requests.get(f"{self.base_url}/v1/ticker", params=params)
            response.raise_for_status()
            
            return {
                'status': 'success',
                'data': response.json()
            }
            
        except Exception as e:
            logger.error(f"현재가 조회 실패: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'data': []
            }
    
    def get_candles(self, market="KRW-BTC", interval="5", count=50):
        """캔들 데이터 조회"""
        try:
            url = f"{self.base_url}/v1/candles/minutes/{interval}"
            params = {
                'market': market,
                'count': min(count, 200)
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return {
                'status': 'success',
                'data': response.json()
            }
            
        except Exception as e:
            logger.error(f"캔들 데이터 조회 실패: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'data': []
            }
    
    def get_order_chance(self, market):
        """주문 가능 정보 조회"""
        try:
            query = {'market': market}
            authorization_token = self._generate_jwt_token(query)
            headers = {"Authorization": authorization_token}
            
            response = requests.get(f"{self.base_url}/v1/orders/chance", params=query, headers=headers)
            response.raise_for_status()
            
            return {
                'status': 'success',
                'data': response.json()
            }
            
        except Exception as e:
            logger.error(f"주문 가능 정보 조회 실패: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'data': {}
            }
    
    def place_order(self, market, side, ord_type, price=None, volume=None):
        """
        주문하기
        
        Args:
            market (str): 마켓 코드 (예: KRW-BTC)
            side (str): 주문 종류 (bid: 매수, ask: 매도)
            ord_type (str): 주문 타입 (limit: 지정가, price: 시장가(매수), market: 시장가(매도))
            price (str): 주문 가격 또는 금액
            volume (str): 주문 수량
        
        Returns:
            dict: 주문 결과
        """
        try:
            query = {
                'market': market,
                'side': side,
                'ord_type': ord_type,
            }
            
            if ord_type == 'limit':
                if not price or not volume:
                    raise ValueError("지정가 주문에는 가격과 수량이 모두 필요합니다.")
                query['price'] = str(price)
                query['volume'] = str(volume)
            elif ord_type == 'price':  # 시장가 매수
                if not price:
                    raise ValueError("시장가 매수에는 주문 금액이 필요합니다.")
                query['price'] = str(price)
            elif ord_type == 'market':  # 시장가 매도
                if not volume:
                    raise ValueError("시장가 매도에는 주문 수량이 필요합니다.")
                query['volume'] = str(volume)
            
            authorization_token = self._generate_jwt_token(query)
            headers = {
                "Authorization": authorization_token,
                "Content-Type": "application/json"
            }
            
            response = requests.post(f"{self.base_url}/v1/orders", params=query, headers=headers)
            
            if response.status_code == 201:
                return {
                    'status': 'success',
                    'data': response.json()
                }
            else:
                return {
                    'status': 'error',
                    'message': f"주문 실패: {response.status_code} - {response.text}",
                    'data': {}
                }
                
        except Exception as e:
            logger.error(f"주문 실행 오류: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'data': {}
            }
    
    def get_orders(self, market=None, state='wait', page=1, limit=100):
        """주문 리스트 조회"""
        try:
            query = {
                'state': state,
                'page': page,
                'limit': limit
            }
            
            if market:
                query['market'] = market
            
            authorization_token = self._generate_jwt_token(query)
            headers = {"Authorization": authorization_token}
            
            response = requests.get(f"{self.base_url}/v1/orders", params=query, headers=headers)
            response.raise_for_status()
            
            return {
                'status': 'success',
                'data': response.json()
            }
            
        except Exception as e:
            logger.error(f"주문 리스트 조회 실패: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'data': []
            }
    
    def cancel_order(self, uuid):
        """주문 취소"""
        try:
            query = {'uuid': uuid}
            authorization_token = self._generate_jwt_token(query)
            headers = {"Authorization": authorization_token}
            
            response = requests.delete(f"{self.base_url}/v1/order", params=query, headers=headers)
            response.raise_for_status()
            
            return {
                'status': 'success',
                'data': response.json()
            }
            
        except Exception as e:
            logger.error(f"주문 취소 실패: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'data': {}
            }
    
    def format_currency_amount(self, amount):
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
            return str(amount)
    
    def is_authenticated(self):
        """API 키 인증 여부 확인"""
        return bool(self.access_key and self.secret_key) 