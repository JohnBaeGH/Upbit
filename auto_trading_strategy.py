#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업비트 자동매매 전략 모듈
이동평균선 + RSI 복합 전략 구현
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import json

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TradingStrategy:
    """자동매매 전략 클래스"""
    
    def __init__(self, api, config=None):
        """
        전략 초기화
        
        Args:
            api: UpbitAPI 인스턴스
            config: 전략 설정 딕셔너리
        """
        self.api = api
        self.config = config or self.get_default_config()
        
        # 거래 상태
        self.is_running = False
        self.current_position = None  # 현재 포지션 정보
        self.last_trade_time = None
        self.trade_history = []
        
        # 데이터 저장용
        self.price_data = []
        self.indicators = {}
        
        logger.info("자동매매 전략 초기화 완료")
        logger.info(f"설정: {json.dumps(self.config, indent=2, ensure_ascii=False)}")
    
    def get_default_config(self) -> Dict:
        """기본 전략 설정 반환"""
        return {
            # 기본 설정
            "market": "KRW-BTC",
            "trade_interval": 300,  # 5분 (초)
            "simulation_mode": True,  # 시뮬레이션 모드
            
            # 투자 설정
            "max_investment_ratio": 0.1,  # 총 잔고의 10%
            "min_order_amount": 5000,     # 최소 주문 금액 (KRW)
            
            # 기술적 지표 설정
            "short_ma_period": 5,   # 단기 이동평균 기간
            "long_ma_period": 20,   # 장기 이동평균 기간
            "rsi_period": 14,       # RSI 기간
            "rsi_oversold": 30,     # RSI 과매도 기준
            "rsi_overbought": 70,   # RSI 과매수 기준
            
            # 리스크 관리
            "stop_loss_ratio": -0.03,   # 손절매 -3%
            "take_profit_ratio": 0.05,  # 익절매 +5%
            "max_holding_time": 24,     # 최대 보유 시간 (시간)
            
            # 거래 조건
            "min_volume_threshold": 1000000,  # 최소 거래량 임계값
            "price_change_threshold": 0.01,   # 최소 가격 변동률 1%
        }
    
    def get_candle_data(self, count: int = 50) -> List[Dict]:
        """캔들 데이터 조회"""
        try:
            result = self.api.get_candles(
                market=self.config["market"],
                interval="5",  # 5분 캔들
                count=count
            )
            
            if result["status"] == "success":
                # 시간순으로 정렬 (오래된 것부터)
                candles = sorted(result["data"], key=lambda x: x["candle_date_time_utc"])
                return candles
            else:
                logger.error(f"캔들 데이터 조회 실패: {result.get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"캔들 데이터 조회 중 오류: {e}")
            return []
    
    def calculate_moving_average(self, prices: List[float], period: int) -> float:
        """이동평균 계산"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """RSI (상대강도지수) 계산"""
        if len(prices) < period + 1:
            return 50  # 기본값
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def analyze_market(self, candles: List[Dict]) -> Dict:
        """시장 분석 및 지표 계산"""
        if len(candles) < self.config["long_ma_period"]:
            return {"status": "insufficient_data"}
        
        # 가격 데이터 추출
        prices = [float(candle["trade_price"]) for candle in candles]
        volumes = [float(candle["candle_acc_trade_volume"]) for candle in candles]
        
        # 이동평균 계산
        short_ma = self.calculate_moving_average(prices, self.config["short_ma_period"])
        long_ma = self.calculate_moving_average(prices, self.config["long_ma_period"])
        
        # RSI 계산
        rsi = self.calculate_rsi(prices, self.config["rsi_period"])
        
        # 현재 가격
        current_price = prices[-1]
        prev_price = prices[-2] if len(prices) > 1 else current_price
        price_change_ratio = (current_price - prev_price) / prev_price
        
        # 거래량 확인
        current_volume = volumes[-1]
        avg_volume = sum(volumes[-5:]) / min(5, len(volumes))
        
        analysis = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "current_price": current_price,
            "price_change_ratio": price_change_ratio,
            "short_ma": short_ma,
            "long_ma": long_ma,
            "rsi": rsi,
            "current_volume": current_volume,
            "avg_volume": avg_volume,
            "volume_ratio": current_volume / avg_volume if avg_volume > 0 else 1
        }
        
        logger.info(f"시장 분석 결과: 현재가={current_price:,.0f}, RSI={rsi:.1f}, 단기MA={short_ma:.0f}, 장기MA={long_ma:.0f}")
        
        return analysis
    
    def generate_signal(self, analysis: Dict) -> str:
        """매매 신호 생성"""
        if analysis["status"] != "success":
            return "HOLD"
        
        short_ma = analysis["short_ma"]
        long_ma = analysis["long_ma"]
        rsi = analysis["rsi"]
        volume_ratio = analysis["volume_ratio"]
        price_change_ratio = abs(analysis["price_change_ratio"])
        
        # 거래량 확인
        if volume_ratio < 0.5:  # 거래량이 너무 적음
            logger.info("거래량 부족으로 거래 신호 무시")
            return "HOLD"
        
        # 가격 변동이 너무 작음
        if price_change_ratio < self.config["price_change_threshold"]:
            logger.info("가격 변동률 부족으로 거래 신호 무시")
            return "HOLD"
        
        # 매수 신호 조건
        if (short_ma > long_ma and  # 골든 크로스
            rsi < self.config["rsi_overbought"] and  # 과매수 아님
            not self.current_position):  # 현재 포지션 없음
            
            # 추가 확인: RSI가 과매도에서 회복 중인지
            if rsi > self.config["rsi_oversold"]:
                logger.info(f"매수 신호 발생: 골든크로스 & RSI={rsi:.1f}")
                return "BUY"
        
        # 매도 신호 조건
        elif (short_ma < long_ma and  # 데드 크로스
              rsi > self.config["rsi_oversold"] and  # 과매도 아님
              self.current_position):  # 현재 포지션 있음
            
            logger.info(f"매도 신호 발생: 데드크로스 & RSI={rsi:.1f}")
            return "SELL"
        
        # RSI 기반 추가 신호
        elif self.current_position:
            # 과매수 구간에서 매도
            if rsi > self.config["rsi_overbought"]:
                logger.info(f"RSI 과매수 매도 신호: RSI={rsi:.1f}")
                return "SELL"
        
        return "HOLD"
    
    def check_risk_management(self, current_price: float) -> Optional[str]:
        """리스크 관리 확인 (손절매/익절매)"""
        if not self.current_position:
            return None
        
        entry_price = self.current_position["entry_price"]
        entry_time = datetime.fromisoformat(self.current_position["entry_time"])
        
        # 수익률 계산
        profit_ratio = (current_price - entry_price) / entry_price
        
        # 손절매 확인
        if profit_ratio <= self.config["stop_loss_ratio"]:
            logger.warning(f"손절매 발동: {profit_ratio*100:.2f}%")
            return "STOP_LOSS"
        
        # 익절매 확인
        if profit_ratio >= self.config["take_profit_ratio"]:
            logger.info(f"익절매 발동: {profit_ratio*100:.2f}%")
            return "TAKE_PROFIT"
        
        # 최대 보유 시간 확인
        holding_hours = (datetime.now() - entry_time).total_seconds() / 3600
        if holding_hours >= self.config["max_holding_time"]:
            logger.info(f"최대 보유 시간 초과: {holding_hours:.1f}시간")
            return "TIME_LIMIT"
        
        return None
    
    def calculate_order_amount(self) -> float:
        """주문 금액 계산"""
        try:
            # 현재 잔고 조회
            accounts = self.api.get_accounts()
            if accounts["status"] != "success":
                return 0
            
            krw_balance = 0
            for account in accounts["data"]:
                if account["currency"] == "KRW":
                    krw_balance = float(account["balance"])
                    break
            
            # 최대 투자 금액 계산
            max_amount = krw_balance * self.config["max_investment_ratio"]
            
            # 최소 주문 금액 확인
            if max_amount < self.config["min_order_amount"]:
                logger.warning(f"투자 가능 금액 부족: {max_amount:,.0f} KRW")
                return 0
            
            logger.info(f"주문 금액 계산: {max_amount:,.0f} KRW (잔고의 {self.config['max_investment_ratio']*100}%)")
            return max_amount
            
        except Exception as e:
            logger.error(f"주문 금액 계산 오류: {e}")
            return 0
    
    def execute_trade(self, signal: str, current_price: float, amount: float = None) -> bool:
        """거래 실행"""
        try:
            if self.config["simulation_mode"]:
                return self.simulate_trade(signal, current_price, amount)
            
            if signal == "BUY":
                if amount is None:
                    amount = self.calculate_order_amount()
                
                if amount < self.config["min_order_amount"]:
                    logger.warning("주문 금액이 최소 금액보다 작음")
                    return False
                
                # 시장가 매수 주문
                result = self.api.place_order(
                    market=self.config["market"],
                    side="bid",
                    ord_type="price",
                    price=str(int(amount))
                )
                
                if result["status"] == "success":
                    # 포지션 정보 저장
                    self.current_position = {
                        "type": "LONG",
                        "entry_price": current_price,
                        "entry_time": datetime.now().isoformat(),
                        "amount": amount,
                        "order_id": result["data"].get("uuid")
                    }
                    
                    self.trade_history.append({
                        "action": "BUY",
                        "price": current_price,
                        "amount": amount,
                        "timestamp": datetime.now().isoformat(),
                        "order_id": result["data"].get("uuid")
                    })
                    
                    logger.info(f"매수 주문 성공: {amount:,.0f} KRW @ {current_price:,.0f}")
                    return True
                else:
                    logger.error(f"매수 주문 실패: {result.get('message')}")
                    return False
            
            elif signal in ["SELL", "STOP_LOSS", "TAKE_PROFIT", "TIME_LIMIT"]:
                if not self.current_position:
                    return False
                
                # 보유 수량 확인
                accounts = self.api.get_accounts()
                if accounts["status"] != "success":
                    return False
                
                crypto_balance = 0
                crypto_currency = self.config["market"].split("-")[1]
                
                for account in accounts["data"]:
                    if account["currency"] == crypto_currency:
                        crypto_balance = float(account["balance"])
                        break
                
                if crypto_balance <= 0:
                    logger.warning("매도할 암호화폐가 없음")
                    self.current_position = None
                    return False
                
                # 시장가 매도 주문
                result = self.api.place_order(
                    market=self.config["market"],
                    side="ask",
                    ord_type="market",
                    volume=str(crypto_balance)
                )
                
                if result["status"] == "success":
                    # 수익률 계산
                    entry_price = self.current_position["entry_price"]
                    profit_ratio = (current_price - entry_price) / entry_price
                    
                    self.trade_history.append({
                        "action": signal,
                        "price": current_price,
                        "amount": crypto_balance,
                        "profit_ratio": profit_ratio,
                        "timestamp": datetime.now().isoformat(),
                        "order_id": result["data"].get("uuid")
                    })
                    
                    logger.info(f"{signal} 주문 성공: {crypto_balance:.8f} @ {current_price:,.0f} (수익률: {profit_ratio*100:+.2f}%)")
                    
                    # 포지션 클리어
                    self.current_position = None
                    return True
                else:
                    logger.error(f"{signal} 주문 실패: {result.get('message')}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"거래 실행 오류: {e}")
            return False
    
    def simulate_trade(self, signal: str, current_price: float, amount: float = None) -> bool:
        """시뮬레이션 거래 (실제 주문 없이 로직 테스트)"""
        try:
            if signal == "BUY":
                if amount is None:
                    amount = 100000  # 시뮬레이션 기본 금액
                
                self.current_position = {
                    "type": "LONG",
                    "entry_price": current_price,
                    "entry_time": datetime.now().isoformat(),
                    "amount": amount,
                    "simulation": True
                }
                
                self.trade_history.append({
                    "action": "BUY",
                    "price": current_price,
                    "amount": amount,
                    "timestamp": datetime.now().isoformat(),
                    "simulation": True
                })
                
                logger.info(f"🔸 [시뮬레이션] 매수: {amount:,.0f} KRW @ {current_price:,.0f}")
                return True
            
            elif signal in ["SELL", "STOP_LOSS", "TAKE_PROFIT", "TIME_LIMIT"]:
                if not self.current_position:
                    return False
                
                entry_price = self.current_position["entry_price"]
                amount = self.current_position["amount"]
                profit_ratio = (current_price - entry_price) / entry_price
                profit_krw = amount * profit_ratio
                
                self.trade_history.append({
                    "action": signal,
                    "price": current_price,
                    "amount": amount,
                    "profit_ratio": profit_ratio,
                    "profit_krw": profit_krw,
                    "timestamp": datetime.now().isoformat(),
                    "simulation": True
                })
                
                logger.info(f"🔸 [시뮬레이션] {signal}: @ {current_price:,.0f} (수익률: {profit_ratio*100:+.2f}%, 수익: {profit_krw:+,.0f} KRW)")
                
                self.current_position = None
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"시뮬레이션 거래 오류: {e}")
            return False
    
    def run_strategy(self) -> Dict:
        """전략 실행 (한 번의 사이클)"""
        try:
            # 캔들 데이터 조회
            candles = self.get_candle_data(50)
            if not candles:
                return {"status": "error", "message": "캔들 데이터 조회 실패"}
            
            # 시장 분석
            analysis = self.analyze_market(candles)
            if analysis["status"] != "success":
                return {"status": "error", "message": "시장 분석 실패"}
            
            current_price = analysis["current_price"]
            
            # 리스크 관리 우선 확인
            risk_signal = self.check_risk_management(current_price)
            if risk_signal:
                success = self.execute_trade(risk_signal, current_price)
                return {
                    "status": "success",
                    "action": risk_signal,
                    "price": current_price,
                    "success": success,
                    "analysis": analysis
                }
            
            # 일반 매매 신호 확인
            signal = self.generate_signal(analysis)
            
            if signal in ["BUY", "SELL"]:
                success = self.execute_trade(signal, current_price)
                self.last_trade_time = datetime.now()
                
                return {
                    "status": "success",
                    "action": signal,
                    "price": current_price,
                    "success": success,
                    "analysis": analysis
                }
            
            return {
                "status": "success",
                "action": "HOLD",
                "price": current_price,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"전략 실행 오류: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_status_summary(self) -> Dict:
        """현재 상태 요약"""
        return {
            "is_running": self.is_running,
            "current_position": self.current_position,
            "trade_count": len(self.trade_history),
            "config": self.config,
            "last_trade_time": self.last_trade_time.isoformat() if self.last_trade_time else None
        }
    
    def get_performance_summary(self) -> Dict:
        """성과 요약"""
        if not self.trade_history:
            return {"total_trades": 0, "total_profit": 0, "win_rate": 0}
        
        buy_trades = [t for t in self.trade_history if t["action"] == "BUY"]
        sell_trades = [t for t in self.trade_history if t["action"] in ["SELL", "STOP_LOSS", "TAKE_PROFIT", "TIME_LIMIT"]]
        
        total_profit = sum(t.get("profit_krw", 0) for t in sell_trades)
        winning_trades = len([t for t in sell_trades if t.get("profit_ratio", 0) > 0])
        win_rate = winning_trades / len(sell_trades) * 100 if sell_trades else 0
        
        return {
            "total_trades": len(sell_trades),
            "total_profit_krw": total_profit,
            "win_rate": win_rate,
            "current_position": self.current_position is not None
        } 