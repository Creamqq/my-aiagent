from tqsdk import TqApi, TqAuth
from tqsdk.ta import MA, EMA, MACD
import pandas as pd
from database import SessionLocal, FinanceConfig
import os

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

def get_tq_auth(user_id: str = 'global'):
    db = SessionLocal()
    try:
        config = db.query(FinanceConfig).filter(
            FinanceConfig.user_id == user_id,
            FinanceConfig.status == 1
        ).first()
        
        if config and config.kuaiqi_account and config.kuaiqi_password:
            print(f"获取快期账户配置: {config.kuaiqi_account}")
            return TqAuth(config.kuaiqi_account, config.kuaiqi_password)
        else:
            raise ValueError(f"未找到用户 {user_id} 的快期账户配置，请在金融助手设置中配置快期账户和密码")
    finally:
        db.close()

TOOL_CODES = {
    "get_quote": {
        "name": "获取实时行情",
        "description": "获取指定合约的实时行情数据，包括最新价、买卖盘、成交量、持仓量等。",
        "code": '''
import sys
import os
sys.path.insert(0, r''' + f'"{PROJECT_PATH}"' + ''')

from tqsdk import TqApi, TqAuth
from database import SessionLocal, FinanceConfig

def get_tq_auth(user_id: str = 'global'):
    db = SessionLocal()
    try:
        config = db.query(FinanceConfig).filter(
            FinanceConfig.user_id == user_id,
            FinanceConfig.status == 1
        ).first()
        
        if config and config.kuaiqi_account and config.kuaiqi_password:
            print(f"获取快期账户配置: {config.kuaiqi_account}")
            return TqAuth(config.kuaiqi_account, config.kuaiqi_password)
        else:
            raise ValueError(f"未找到用户 {user_id} 的快期账户配置，请在金融助手设置中配置快期账户和密码")
    finally:
        db.close()

def get_quote(symbol_list: str, user_id: str = 'global'):
    import time
    api = None
    try:
        auth = get_tq_auth(user_id)
        api = TqApi(auth=auth)
        
        symbols = [s.strip() for s in symbol_list.split(',') if s.strip()]
        print(f"准备获取 {len(symbols)} 个合约的实时行情: {', '.join(symbols)}")
        
        quotes = {}
        failed_symbols = []
        valid_symbols = []
        result = {}
        for symbol in symbols:
            try:
                quote = api.get_quote(symbol=symbol)
                deadline = time.time() + 5
                api.wait_update(deadline=deadline)
                
                if not quote.instrument_id or quote.instrument_id == "":
                    failed_symbols.append(symbol)
                    result[symbol] = None
                    print(f"合约 {symbol} 不存在或已过期")
                else:
                    quotes[symbol] = quote
                    valid_symbols.append(symbol)
                    print(f"订阅合约成功: {symbol}")
            except Exception as e:
                failed_symbols.append(symbol)
                print(f"订阅合约 {symbol} 失败: {str(e)}")
        
        if not valid_symbols:
            return {"error": "没有有效的合约", "_failed_symbols": failed_symbols}
        
        
        for symbol in valid_symbols:
            quote = quotes[symbol]
            try:
                print(f"获取合约 {symbol} 的实时行情数据")
                print(f"行情时间: {quote.datetime}")
                
                result[symbol] = {
                    "合约代码": str(quote.instrument_id),
                    "行情时间": str(quote.datetime),
                    "最新价": float(quote.last_price) if quote.last_price else None,
                    "买一价": float(quote.bid_price1) if quote.bid_price1 else None,
                    "买一量": int(quote.bid_volume1) if quote.bid_volume1 else None,
                    "卖一价": float(quote.ask_price1) if quote.ask_price1 else None,
                    "卖一量": int(quote.ask_volume1) if quote.ask_volume1 else None,
                    "买二价": float(quote.bid_price2) if quote.bid_price2 else None,
                    "买二量": int(quote.bid_volume2) if quote.bid_volume2 else None,
                    "卖二价": float(quote.ask_price2) if quote.ask_price2 else None,
                    "卖二量": int(quote.ask_volume2) if quote.ask_volume2 else None,
                    "买三价": float(quote.bid_price3) if quote.bid_price3 else None,
                    "买三量": int(quote.bid_volume3) if quote.bid_volume3 else None,
                    "卖三价": float(quote.ask_price3) if quote.ask_price3 else None,
                    "卖三量": int(quote.ask_volume3) if quote.ask_volume3 else None,
                    "买四价": float(quote.bid_price4) if quote.bid_price4 else None,
                    "买四量": int(quote.bid_volume4) if quote.bid_volume4 else None,
                    "卖四价": float(quote.ask_price4) if quote.ask_price4 else None,
                    "卖四量": int(quote.ask_volume4) if quote.ask_volume4 else None,
                    "买五价": float(quote.bid_price5) if quote.bid_price5 else None,
                    "买五量": int(quote.bid_volume5) if quote.bid_volume5 else None,
                    "卖五价": float(quote.ask_price5) if quote.ask_price5 else None,
                    "卖五量": int(quote.ask_volume5) if quote.ask_volume5 else None,
                    "当日最高价": float(quote.highest) if quote.highest else None,
                    "当日最低价": float(quote.lowest) if quote.lowest else None,
                    "开盘价": float(quote.open) if quote.open else None,
                    "收盘价": float(quote.close) if quote.close else None,
                    "昨收盘价": float(quote.pre_close) if quote.pre_close else None,
                    "成交量": int(quote.volume) if quote.volume else None,
                    "持仓量": int(quote.open_interest) if quote.open_interest else None,
                    "成交额": float(quote.amount) if quote.amount else None,
                    "涨停价": float(quote.upper_limit) if quote.upper_limit else None,
                    "跌停价": float(quote.lower_limit) if quote.lower_limit else None,
                    "结算价": float(quote.settlement) if quote.settlement else None,
                    "昨结算价": float(quote.pre_settlement) if quote.pre_settlement else None,
                }
            except Exception as e:
                result[symbol] = {"error": f"获取行情失败: {str(e)}"}
                print(f"获取合约 {symbol} 行情失败: {str(e)}")
        
        if failed_symbols:
            result["_failed_symbols"] = failed_symbols
            print(f"失败的合约: {', '.join(failed_symbols)}")
        
        return result
        
    except Exception as e:
        return {"error": f"获取实时行情失败: {str(e)}"}
    finally:
        if api:
            api.close()
''',
        "params": {
            "symbol_list": {"type": "string", "description": "多个合约代码用逗号分隔，如 SHFE.cu2606,SHFE.cu2608"},
            "user_id": {"type": "string", "description": "用户ID，用于获取对应的快期账户配置，默认为 global"}
        }
    },
    
    "get_kline_serial": {
        "name": "获取K线数据",
        "description": "获取指定合约的历史K线序列数据，支持任意周期（不超过1日）。返回包含时间、开高低收、成交量、持仓量等字段的数据。",
        "code": '''
import sys
import os
sys.path.insert(0, r''' + f'"{PROJECT_PATH}"' + ''')

from tqsdk import TqApi, TqAuth
from database import SessionLocal, FinanceConfig

def get_tq_auth(user_id: str = 'global'):
    db = SessionLocal()
    try:
        config = db.query(FinanceConfig).filter(
            FinanceConfig.user_id == user_id,
            FinanceConfig.status == 1
        ).first()
        
        if config and config.kuaiqi_account and config.kuaiqi_password:
            print(f"获取快期账户配置: {config.kuaiqi_account}")
            return TqAuth(config.kuaiqi_account, config.kuaiqi_password)
        else:
            raise ValueError(f"未找到用户 {user_id} 的快期账户配置，请在金融助手设置中配置快期账户和密码")
    finally:
        db.close()

def get_kline_serial(symbol: str, duration_seconds: int, user_id: str = 'global', length: int = 100):
    """
    获取指定合约的历史K线序列数据
    
    Args:
        symbol: 合约代码，格式为"交易所代码.合约代码"，如"SHFE.cu2601"
        duration_seconds: K线周期，以秒为单位。例如：10（10秒线）、60（1分钟线）、3600（1小时线）、86400（日线）
        user_id: 用户ID，用于获取对应的快期账户配置
        length: 获取K线的数量，默认100根
    
    Returns:
        K线序列数据
    """
    import time

    try:
        duration_seconds = int(duration_seconds)
        length = int(length)
    except (ValueError, TypeError):
        return {"error": "duration_seconds 和 length 必须是整数"}
    api = None
    try:
        if duration_seconds > 86400:
            return {"error": "K线周期不能超过86400秒（1日）"}
        
        auth = get_tq_auth(user_id)
        api = TqApi(auth=auth)
        
        # 直接使用 duration_seconds，不需要乘以1000
        klines = api.get_kline_serial(symbol, duration_seconds, data_length=length)
        
        deadline = time.time() + 10
        api.wait_update(deadline=deadline)
        
        df = klines
        
        if df.empty or len(df) == 0:
            return {"error": f"合约 {symbol} 不存在或已过期，无法获取K线数据"}
        
        kline_list = []
        for idx, row in df.iterrows():
            kline_item = {
                "datetime": str(row.get("datetime", "")),
                "open": float(row.get("open", 0)) if row.get("open") else None,
                "high": float(row.get("high", 0)) if row.get("high") else None,
                "low": float(row.get("low", 0)) if row.get("low") else None,
                "close": float(row.get("close", 0)) if row.get("close") else None,
                "volume": int(row.get("volume", 0)) if row.get("volume") else None,
                "open_interest": int(row.get("open_oi", 0)) if row.get("open_oi") else None,
                "close_oi": int(row.get("close_oi", 0)) if row.get("close_oi") else None,
            }
            kline_list.append(kline_item)
        
        return {
            "symbol": symbol,
            "duration_seconds": duration_seconds,
            "count": len(kline_list),
            "klines": kline_list
        }
            
    except Exception as e:
        return {"error": f"获取K线数据失败: {str(e)}"}
    finally:
        if api:
            api.close()
''',
        "params": {
            "symbol": {"type": "string", "description": "合约代码，如 SHFE.cu2601"},
            "duration_seconds": {"type": "integer", "description": "K线周期，以秒为单位。例如：10（10秒线）、60（1分钟线）、3600（1小时线）、86400（日线）。最大不超过86400"},
            "user_id": {"type": "string", "description": "用户ID，用于获取对应的快期账户配置，默认为 global", "default": "global"},
            "length": {"type": "integer", "description": "获取K线的数量，默认100根", "default": 100}
        }
    },
    
    "get_tick_serial": {
        "name": "获取Tick数据",
        "description": "获取指定合约的Tick级逐笔行情数据，包含买卖盘口、成交价、成交量等。",
        "code": '''
import sys
import os
sys.path.insert(0, r''' + f'"{PROJECT_PATH}"' + ''')

from tqsdk import TqApi, TqAuth
from database import SessionLocal, FinanceConfig

def get_tq_auth(user_id: str = 'global'):
    db = SessionLocal()
    try:
        config = db.query(FinanceConfig).filter(
            FinanceConfig.user_id == user_id,
            FinanceConfig.status == 1
        ).first()
        
        if config and config.kuaiqi_account and config.kuaiqi_password:
            print(f"获取快期账户配置: {config.kuaiqi_account}")
            return TqAuth(config.kuaiqi_account, config.kuaiqi_password)
        else:
            raise ValueError(f"未找到用户 {user_id} 的快期账户配置，请在金融助手设置中配置快期账户和密码")
    finally:
        db.close()

def get_tick_serial(symbol: str, user_id: str = 'global', length: int = 100):
    """
    获取指定合约的Tick级逐笔行情数据
    
    Args:
        symbol: 合约代码，格式为"交易所代码.合约代码"，如"SHFE.cu2601"
        user_id: 用户ID，用于获取对应的快期账户配置
        length: 获取Tick的数量，默认100条
    
    Returns:
        Tick级逐笔行情数据
    """
    import time
    api = None
    try:
        auth = get_tq_auth(user_id)
        api = TqApi(auth=auth)
        
        ticks = api.get_tick_serial(symbol, data_length=length)
        
        deadline = time.time() + 10
        api.wait_update(deadline=deadline)
        
        df = ticks
        
        if df.empty or len(df) == 0:
            return {"error": f"合约 {symbol} 不存在或已过期，无法获取Tick数据"}
        
        tick_list = []
        for idx, row in df.iterrows():
            tick_item = {
                "datetime": str(row.get("datetime", "")),
                "last_price": float(row.get("last_price", 0)) if row.get("last_price") else None,
                "bid_price1": float(row.get("bid_price1", 0)) if row.get("bid_price1") else None,
                "ask_price1": float(row.get("ask_price1", 0)) if row.get("ask_price1") else None,
                "bid_volume1": int(row.get("bid_volume1", 0)) if row.get("bid_volume1") else None,
                "ask_volume1": int(row.get("ask_volume1", 0)) if row.get("ask_volume1") else None,
                "highest": float(row.get("highest", 0)) if row.get("highest") else None,
                "lowest": float(row.get("lowest", 0)) if row.get("lowest") else None,
                "volume": int(row.get("volume", 0)) if row.get("volume") else None,
                "open_interest": int(row.get("open_interest", 0)) if row.get("open_interest") else None,
            }
            tick_list.append(tick_item)
        
        return {
            "symbol": symbol,
            "count": len(tick_list),
            "ticks": tick_list
        }
            
    except Exception as e:
        return {"error": f"获取Tick数据失败: {str(e)}"}
    finally:
        if api:
            api.close()
''',
        "params": {
            "symbol": {"type": "string", "description": "合约代码，格式为 交易所代码.合约代码，如 SHFE.cu1812"},
            "user_id": {"type": "string", "description": "用户ID，用于获取对应的快期账户配置，默认为 global", "default": "global"},
            "length": {"type": "integer", "description": "获取Tick的数量，默认100条", "default": 100}
        }
    },
    "run_backtest": {
        "name": "运行回测",
        "description": "运行回测策略，对指定合约进行回测分析。",
        "code": '',
        "strategy_codes": {
            "ma_cross": '''
import sys
import os
sys.path.insert(0, r''' + f'"{PROJECT_PATH}"' + ''')

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from tqsdk import TqApi, TqAuth, TqSim, TqBacktest, TargetPosTask, BacktestFinished
from database import SessionLocal, FinanceConfig
from tqsdk.tafunc import ma

def get_tq_auth(user_id: str = 'global'):
    """获取快期账户认证"""
    db = SessionLocal()
    try:
        config = db.query(FinanceConfig).filter(
            FinanceConfig.user_id == user_id,
            FinanceConfig.status == 1
        ).first()
        if config and config.kuaiqi_account and config.kuaiqi_password:
            return TqAuth(config.kuaiqi_account, config.kuaiqi_password)
        else:
            raise ValueError("未找到快期账户配置")
    finally:
        db.close()
    
def run_backtest(symbol: str, strategy: str, start_date: str = None, end_date: str = None,
                 fast_ma: int = 5, slow_ma: int = 20, risk_per_trade: float = 0.02,
                 user_id: str = 'global', stop_loss: float = 0.02, take_profit: float = 0.03, **kwargs):
    """
    双均线交叉策略回测

    Args:
        symbol: 合约代码，必须是完整格式（如 "SHFE.cu2606"），包含交易所、品种和交割月份
        strategy: 固定为 'ma_cross'
        start_date: 回测开始日期，格式 "YYYY-MM-DD"，默认2025-08-01
        end_date: 回测结束日期，格式 "YYYY-MM-DD"，默认2025-09-30
        fast_ma: 短期均线周期
        slow_ma: 长期均线周期
        risk_per_trade: 每笔交易最大风险占资金比例（用于开仓手数计算）
        user_id: 用户ID
        stop_loss: 止损参数（百分比）（可选，默认0.02）
        take_profit: 止盈参数（百分比）（可选，默认0.03）
    Returns:
        dict: 回测结果，包含各项指标和权益曲线
    """
    if strategy != 'ma_cross':
        return {"error": f"策略 {strategy} 暂未实现，请使用 'ma_cross'"}

    # 验证合约代码格式（必须是完整格式，如 SHFE.cu2606）
    symbol_parts = symbol.split('.')
    if len(symbol_parts) != 2:
        return {"error": f"合约代码格式错误: {symbol}，正确格式为 '交易所.品种月份'，如 'SHFE.cu2606'"}
    
    exchange = symbol_parts[0]
    product_month = symbol_parts[1]
    
    # 检查是否包含交割月份（品种代码通常2个字母，后面跟年月）
    # 例如: cu2606 (铜2025年6月), au2502 (金2025年2月)
    if len(product_month) <= 2:
        return {"error": f"合约代码必须包含交割月份: {symbol}，正确格式如 'SHFE.cu2606'，请提供完整的合约代码"}

    # 参数类型转换
    try:
        fast_ma = int(fast_ma)
        slow_ma = int(slow_ma)
        risk_per_trade = float(risk_per_trade)
    except (ValueError, TypeError):
        return {"error": "fast_ma 和 slow_ma 必须是整数，risk_per_trade 必须是数字"}

    # 解析日期
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date(2025, 8, 1)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date(2025, 9, 30)
    except Exception:
        start_dt = date(2025, 8, 1)
        end_dt = date(2025, 9, 30)

    api = None
    try:
        acc = TqSim()
        api = TqApi(acc, backtest=TqBacktest(start_dt=start_dt, end_dt=end_dt), auth=get_tq_auth(user_id))
        #策略代码
        data_length = slow_ma + 2  # k线数据长度
        # 日线的duration_seconds参数为: 24*60*60
        klines = api.get_kline_serial(symbol, duration_seconds=24*60*60, data_length=data_length)
        # 创建任务
        target_pos = TargetPosTask(api, symbol)
        # 在循环外定义变量，用于记录开仓价格和方向
        entry_price = None
        entry_direction = None  # 'long' 或 'short'

        # 止损止盈参数（百分比）
        stop_loss = stop_loss   # 2% 止损
        take_profit = take_profit   # 3% 止盈

        while True:
            api.wait_update()
            try:
                quote = api.get_quote(symbol)

                # 风控检查
                if entry_price is not None and entry_direction is not None:
                    current_price = quote.last_price
                    if np.isnan(current_price):
                        continue   # 无最新价则跳过

                    if entry_direction == 'long':
                        pnl_ratio = (current_price - entry_price) / entry_price
                        if pnl_ratio <= -stop_loss:
                            print(f"触发多头止损，平仓 | 价格: {current_price:.2f} | 盈亏: {pnl_ratio:.2%}")
                            target_pos.set_target_volume(0)
                            entry_price = None
                            entry_direction = None
                        elif pnl_ratio >= take_profit:
                            print(f"触发多头止盈，平仓 | 价格: {current_price:.2f} | 盈亏: {pnl_ratio:.2%}")
                            target_pos.set_target_volume(0)
                            entry_price = None
                            entry_direction = None
                    elif entry_direction == 'short':
                        pnl_ratio = (entry_price - current_price) / entry_price
                        if pnl_ratio <= -stop_loss:
                            print(f"触发空头止损，平仓 | 价格: {current_price:.2f} | 盈亏: {pnl_ratio:.2%}")
                            target_pos.set_target_volume(0)
                            entry_price = None
                            entry_direction = None
                        elif pnl_ratio >= take_profit:
                            print(f"触发空头止盈，平仓 | 价格: {current_price:.2f} | 盈亏: {pnl_ratio:.2%}")
                            target_pos.set_target_volume(0)
                            entry_price = None
                            entry_direction = None

                # 信号判断
                if api.is_changing(klines.iloc[-1], "datetime"):
                    short_avg = ma(klines["close"], fast_ma)
                    long_avg = ma(klines["close"], slow_ma)

                    # 做空信号
                    if long_avg.iloc[-2] < short_avg.iloc[-2] and long_avg.iloc[-1] > short_avg.iloc[-1]:
                        # 确保开仓价有效
                        if np.isnan(quote.bid_price1):
                            continue
                        target_pos.set_target_volume(-3)
                        entry_price = quote.bid_price1
                        entry_direction = 'short'
                        print(f"均线下穿，做空，entry_price：{entry_price:.2f}")

                    # 做多信号
                    if short_avg.iloc[-2] < long_avg.iloc[-2] and short_avg.iloc[-1] > long_avg.iloc[-1]:
                        if np.isnan(quote.ask_price1):
                            continue
                        target_pos.set_target_volume(3)
                        entry_price = quote.ask_price1
                        entry_direction = 'long'
                        print(f"均线上穿，做多，entry_price：{entry_price:.2f}")

            except (ValueError, KeyError, IndexError) as e:
                print(f"处理k线数据时出错: {e}")
        
    except BacktestFinished as e:
        api.close()
        result = acc.tqsdk_stat
        if result:
            return {k: float(v) if hasattr(v, 'item') else (None if str(v) == 'nan' else v) for k, v in result.items()}
        return {}


''',
            "aberration": '''

''',
            "bollinger_break": '''

''',
            "rsi_mean_reversion": '''

'''
        },
        "params": {
            "symbol": {"type": "string", "description": "合约代码，格式为 交易所代码.合约代码，如 SHFE.cu1812"},
            "strategy": {"type": "string", "description": "策略类型", "enum": ["ma_cross", "aberration", "bollinger_break", "rsi_mean_reversion"], "enum_labels": {"ma_cross": "双均线交叉", "aberration": "Aberration趋势跟踪", "bollinger_break": "布林带突破", "rsi_mean_reversion": "RSI均值回归"}},
            "start_date": {"type": "string", "description": "回测开始日期，格式为YYYY-MM-DD", "default": "2025-08-01"},
            "end_date": {"type": "string", "description": "回测结束日期，格式为YYYY-MM-DD", "default": "2025-09-30"},
            "user_id": {"type": "string", "description": "用户ID，用于获取对应的快期账户配置，默认为 global", "default": "global"},
            "stop_loss": {"type": "number", "description": "止损参数（百分比）（可选，默认0.02）", "default": 0.02},
            "take_profit": {"type": "number", "description": "止盈参数（百分比）（可选，默认0.03）", "default": 0.03},
            "fast_ma": {"type": "integer", "description": "双均线策略的短期均线周期（仅 strategy=ma_cross 时有效）", "default": 5},
            "slow_ma": {"type": "integer", "description": "双均线策略的长期均线周期（仅 strategy=ma_cross 时有效）", "default": 20},
            "atr_multiplier": {"type": "number", "description": "ATR乘数，默认2", "default": 2},
            "risk_per_trade": {"type": "number", "description": "单笔风险占资金比例（0-1，默认0.02）", "default": 0.02}
        }
    }
}


def get_tool_code(tool_name: str) -> dict:
    """获取指定工具的代码信息"""
    return TOOL_CODES.get(tool_name)


def get_all_tools() -> list:
    """获取所有工具名称列表"""
    return list(TOOL_CODES.keys())


def get_tool_description(tool_name: str) -> str:
    """获取工具描述"""
    tool = TOOL_CODES.get(tool_name)
    return tool["description"] if tool else ""


def generate_kline_chart(klines_data: dict, chart_type: str = 'candle', user_id: str = 'global'):
    """
    根据K线数据生成图表图片
    
    Args:
        klines_data: K线数据字典，包含 symbol, duration_seconds, klines 等字段
        chart_type: 图表类型，'candle' 为K线图，'line' 为折线图
        user_id: 用户ID
    
    Returns:
        包含Base64编码图片的字典
    """
    import base64
    import io
    import pandas as pd
    import mplfinance as mpf
    import matplotlib.pyplot as plt
    from datetime import datetime
    
    try:
        if "error" in klines_data:
            return {"error": klines_data["error"]}
        
        klines = klines_data.get("klines", [])
        symbol = klines_data.get("symbol", "Unknown")
        duration_seconds = klines_data.get("duration_seconds", 60)
        
        if not klines or len(klines) == 0:
            return {"error": "没有K线数据"}
        
        df_data = []
        for k in klines:
            try:
                dt = None
                dt_value = k.get("datetime")
                
                if dt_value:
                    if isinstance(dt_value, (int, float)):
                        if dt_value > 1e15:
                            dt = datetime.fromtimestamp(dt_value / 1e9)
                        elif dt_value > 1e12:
                            dt = datetime.fromtimestamp(dt_value / 1e3)
                        else:
                            dt = datetime.fromtimestamp(dt_value)
                    elif isinstance(dt_value, str):
                        dt_str = dt_value.strip()
                        if dt_str:
                            try:
                                if " " in dt_str:
                                    if "." in dt_str:
                                        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
                                    else:
                                        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                                else:
                                    dt = datetime.strptime(dt_str, "%Y-%m-%d")
                            except ValueError:
                                try:
                                    ts = float(dt_str)
                                    if ts > 1e15:
                                        dt = datetime.fromtimestamp(ts / 1e9)
                                    elif ts > 1e12:
                                        dt = datetime.fromtimestamp(ts / 1e3)
                                    else:
                                        dt = datetime.fromtimestamp(ts)
                                except:
                                    pass
                
                if dt is None:
                    continue
                
                df_data.append({
                    "datetime": dt,
                    "open": float(k.get("open", 0)) if k.get("open") else None,
                    "high": float(k.get("high", 0)) if k.get("high") else None,
                    "low": float(k.get("low", 0)) if k.get("low") else None,
                    "close": float(k.get("close", 0)) if k.get("close") else None,
                    "volume": int(k.get("volume", 0)) if k.get("volume") else 0,
                })
            except Exception as e:
                print(f"解析K线数据失败: {e}")
                continue
        
        if not df_data:
            return {"error": "无法解析K线数据"}
        
        df = pd.DataFrame(df_data)
        df.set_index("datetime", inplace=True)
        df.sort_index(inplace=True)
        
        duration_name = {
            10: "10秒",
            30: "30秒",
            60: "1分钟",
            180: "3分钟",
            300: "5分钟",
            600: "10分钟",
            900: "15分钟",
            1800: "30分钟",
            3600: "1小时",
            7200: "2小时",
            14400: "4小时",
            86400: "日线",
        }.get(duration_seconds, f"{duration_seconds}秒")
        
        mc = mpf.make_marketcolors(
            up='#ef5350', down='#26a69a',
            edge='inherit',
            wick='inherit',
            volume={'up': '#ef5350', 'down': '#26a69a'},
        )
        
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        style = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='-',
            gridcolor='#2a2a2a',
            facecolor='#1a1a1a',
            edgecolor='#1a1a1a',
            figcolor='#1a1a1a',
            rc={
                'axes.labelcolor': '#ffffff',
                'axes.edgecolor': '#333333',
                'xtick.color': '#ffffff',
                'ytick.color': '#ffffff',
                'text.color': '#ffffff',
                'font.sans-serif': ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'DejaVu Sans'],
                'axes.unicode_minus': False,
            }
        )
        
        buf = io.BytesIO()
        
        title = f"{symbol} - {duration_name}K线图"
        
        if chart_type == 'line':
            mpf.plot(
                df,
                type='line',
                style=style,
                title=title,
                ylabel='价格',
                ylabel_lower='成交量',
                volume=True,
                savefig=buf,
                figsize=(14, 8),
                tight_layout=True,
            )
        else:
            mpf.plot(
                df,
                type='candle',
                style=style,
                title=title,
                ylabel='价格',
                ylabel_lower='成交量',
                volume=True,
                savefig=buf,
                figsize=(14, 8),
                tight_layout=True,
            )
        
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        return {
            "success": True,
            "symbol": symbol,
            "duration_seconds": duration_seconds,
            "chart_type": chart_type,
            "image_base64": img_base64,
            "image_format": "png",
            "data_count": len(df_data),
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"生成图表失败: {str(e)}"}


def generate_tick_chart(ticks_data: dict, user_id: str = 'global'):
    """
    根据Tick数据生成图表图片
    
    Args:
        ticks_data: Tick数据字典，包含 symbol, ticks 等字段
        user_id: 用户ID
    
    Returns:
        包含Base64编码图片的字典
    """
    import base64
    import io
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime
    
    try:
        if "error" in ticks_data:
            return {"error": ticks_data["error"]}
        
        ticks = ticks_data.get("ticks", [])
        symbol = ticks_data.get("symbol", "Unknown")
        
        if not ticks or len(ticks) == 0:
            return {"error": "没有Tick数据"}
        
        df_data = []
        for t in ticks:
            try:
                dt = None
                dt_value = t.get("datetime")
                
                if dt_value:
                    if isinstance(dt_value, (int, float)):
                        if dt_value > 1e15:
                            dt = datetime.fromtimestamp(dt_value / 1e9)
                        elif dt_value > 1e12:
                            dt = datetime.fromtimestamp(dt_value / 1e3)
                        else:
                            dt = datetime.fromtimestamp(dt_value)
                    elif isinstance(dt_value, str):
                        dt_str = dt_value.strip()
                        if dt_str:
                            try:
                                if " " in dt_str:
                                    if "." in dt_str:
                                        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
                                    else:
                                        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                                else:
                                    dt = datetime.strptime(dt_str, "%Y-%m-%d")
                            except ValueError:
                                try:
                                    ts = float(dt_str)
                                    if ts > 1e15:
                                        dt = datetime.fromtimestamp(ts / 1e9)
                                    elif ts > 1e12:
                                        dt = datetime.fromtimestamp(ts / 1e3)
                                    else:
                                        dt = datetime.fromtimestamp(ts)
                                except:
                                    pass
                
                if dt is None:
                    continue
                
                last_price = t.get("last_price")
                if last_price is None:
                    continue
                    
                df_data.append({
                    "datetime": dt,
                    "last_price": float(last_price),
                    "bid_price1": float(t.get("bid_price1", 0)) if t.get("bid_price1") else None,
                    "ask_price1": float(t.get("ask_price1", 0)) if t.get("ask_price1") else None,
                })
            except Exception as e:
                print(f"解析Tick数据失败: {e}")
                continue
        
        if not df_data:
            return {"error": "无法解析Tick数据"}
        
        df = pd.DataFrame(df_data)
        df.set_index("datetime", inplace=True)
        df.sort_index(inplace=True)
        
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(14, 8), facecolor='#1a1a1a')
        ax.set_facecolor('#1a1a1a')
        
        ax.plot(df.index, df['last_price'], color='#42a5f5', linewidth=1, label='最新价')
        
        if 'bid_price1' in df.columns and df['bid_price1'].notna().any():
            ax.plot(df.index, df['bid_price1'], color='#26a69a', linewidth=0.8, alpha=0.7, label='买一价')
        if 'ask_price1' in df.columns and df['ask_price1'].notna().any():
            ax.plot(df.index, df['ask_price1'], color='#ef5350', linewidth=0.8, alpha=0.7, label='卖一价')
        
        ax.set_title(f"{symbol} - Tick分时图", color='white', fontsize=14)
        ax.set_xlabel('时间', color='white')
        ax.set_ylabel('价格', color='white')
        ax.legend(loc='upper right', facecolor='#2a2a2a', edgecolor='#333333')
        ax.grid(True, alpha=0.3, color='#333333')
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, facecolor='#1a1a1a', edgecolor='none')
        buf.seek(0)
        plt.close()
        
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        return {
            "success": True,
            "symbol": symbol,
            "chart_type": "tick",
            "image_base64": img_base64,
            "image_format": "png",
            "data_count": len(df_data),
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"生成图表失败: {str(e)}"}
