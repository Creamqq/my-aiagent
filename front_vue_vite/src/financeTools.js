const financeTools = [
    {
        "type": "function",
        "name": "get_quote",
        "description": "获取指定合约的当前行情数据，包括最新价、买卖盘、成交量、持仓量等。",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol_list": {
                    "type": "string",
                    "description": "合约代码，多个合约代码用逗号分隔，不要有空格。合约代码格式为“交易所代码.合约代码”，如“SHFE.cu2606”，支持期货、期权、股票、指数等。"
                }
            },
            "required": ["symbol_list"]
        }
    },
    {
        "type": "function",
        "name": "get_kline_serial",
        "description": "获取指定合约的历史K线序列数据，支持任意周期（不超过1日）。返回包含时间、开高低收、成交量、持仓量等字段的DataFrame。",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "合约代码，格式为“交易所代码.合约代码”，如“SHFE.cu2601”。"
                },
                "duration_seconds": {
                    "type": "integer",
                    "description": "K线周期，以秒为单位。例如：10（10秒线）、60（1分钟线）、3600（1小时线）、86400（日线）。最大不超过86400。"
                }
            },
            "required": ["symbol", "duration_seconds"]
        }
    },
    {
        "type": "function",
        "name": "get_tick_serial",
        "description": "获取指定合约的Tick级逐笔行情数据，包含买卖盘口、成交价、成交量等。",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "合约代码，格式为“交易所代码.合约代码”，如“SHFE.cu2601”。"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "type": "function",
        "name": "run_backtest",
        "description": "运行交易策略回测，支持双均线、Aberration等策略，返回绩效指标和权益曲线。",
        "parameters": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "合约代码，必须是完整格式（包含交易所、品种和交割月份），如 SHFE.cu2606、DCE.m2505。不支持品种代码（如 SHFE.cu），必须提供具体交割月份。"
            },
            "strategy": {
                "type": "string",
                "enum": ["ma_cross", "aberration", "bollinger_break", "rsi_mean_reversion"],
                "description": "策略类型：ma_cross（双均线交叉），aberration（Aberration趋势跟踪），bollinger_break（布林带突破），rsi_mean_reversion（RSI均值回归）"
            },
            "start_date": {
                "type": "string",
                "description": "回测开始日期，格式 YYYY-MM-DD，可选，默认为2025-08-01"
            },
            "end_date": {
                "type": "string",
                "description": "回测结束日期，格式 YYYY-MM-DD，可选，默认为2025-09-30"
            },
            "fast_ma": {
                "type": "integer",
                "description": "双均线策略的短期均线周期（仅 strategy=ma_cross 时有效）"
            },
            "slow_ma": {
                "type": "integer",
                "description": "双均线策略的长期均线周期（仅 strategy=ma_cross 时有效）"
            },
            "stop_loss": {
                "type": "number",
                "description": "止损参数（百分比）（可选，默认0.02）"
            },
            "take_profit": {
                "type": "number",
                "description": "止盈参数（百分比）（可选，默认0.03）"
            },
            "atr_multiplier": {
                "type": "number",
                "description": "ATR止损倍数（可选，默认2）"
            },
            "risk_per_trade": {
                "type": "number",
                "description": "单笔风险占资金比例（0-1，默认0.02）"
            }
        },
            "required": ["symbol", "strategy"]
        }
    }
];

export default financeTools;
