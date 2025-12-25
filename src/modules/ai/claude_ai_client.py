"""
Claude AI Client - 基于claude-code-sdk的AI分析客户端

提供股票分析、投资建议、对话交互等AI功能
依赖: claude-code-sdk
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from base.order import OrderType
from base.trading import TradingAdvice, TradingOrder
from base.ai import AIRequest, AIAnalysisRequest, AITradingAdviceRequest, AIAnalysisResponse
from utils.global_vars import get_logger

try:
    from claude_code_sdk import query, ClaudeCodeOptions
    from claude_code_sdk.types import SystemMessage, AssistantMessage, ResultMessage
    CLAUDE_CODE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_CODE_SDK_AVAILABLE = False
    query = None
    ClaudeCodeOptions = None
    SystemMessage = None
    AssistantMessage = None
    ResultMessage = None




class ClaudeAIClient:
    """
    Claude AI客户端 - 基于claude-code-sdk
    在Claude Code环境中自动使用应用内认证，无需API key
    """
    
    def __init__(self):
        """初始化Claude AI客户端"""
        self.logger = get_logger(__name__)
        self.available = CLAUDE_CODE_SDK_AVAILABLE
        
        if self.available:
            self.logger.info("Claude AI客户端初始化成功 (使用claude-code-sdk)")
        else:
            self.logger.error("claude-code-sdk未安装，请运行: pip install claude-code-sdk")
    
    def is_available(self) -> bool:
        """检查Claude AI客户端是否可用"""
        return self.available
    
    async def generate_stock_analysis(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """生成股票分析"""
        try:
            if not self.is_available():
                return self._create_error_response(request, "Claude AI客户端不可用")
            
            # 构建分析提示词
            prompt = self._build_analysis_prompt(request)
            self.logger.debug(f"分析提示词: {prompt}")
            # 调用Claude Code SDK
            self.logger.info(f"开始生成{request.analysis_type}分析: {request.stock_code}")
            
            # 配置Claude Code选项
            options = None
            if ClaudeCodeOptions:
                options = ClaudeCodeOptions(
                    system_prompt="你是一位专业的股票分析师AI助手。请直接回复，不要使用任何工具。",
                    max_turns=1,
                    allowed_tools=[]  # 禁用所有工具
                )
            
            response_content = ""
            try:
                if options:
                    async for message in query(prompt=prompt, options=options):
                        # 跳过SystemMessage和ResultMessage，只处理AI响应
                        if SystemMessage and isinstance(message, SystemMessage):
                            continue
                        if ResultMessage and isinstance(message, ResultMessage):
                            continue
                        
                        # 处理AssistantMessage
                        if AssistantMessage and isinstance(message, AssistantMessage):
                            if hasattr(message, 'content') and message.content:
                                for content_block in message.content:
                                    if hasattr(content_block, 'text'):
                                        response_content += content_block.text
                        elif isinstance(message, str):
                            response_content += message
                        elif hasattr(message, 'content'):
                            response_content += str(message.content)
                        else:
                            response_content += str(message)
                else:
                    async for message in query(prompt=prompt):
                        # 跳过SystemMessage和ResultMessage，只处理AI响应
                        if SystemMessage and isinstance(message, SystemMessage):
                            continue
                        if ResultMessage and isinstance(message, ResultMessage):
                            continue
                        
                        # 处理AssistantMessage
                        if AssistantMessage and isinstance(message, AssistantMessage):
                            if hasattr(message, 'content') and message.content:
                                for content_block in message.content:
                                    if hasattr(content_block, 'text'):
                                        response_content += content_block.text
                        elif isinstance(message, str):
                            response_content += message
                        elif hasattr(message, 'content'):
                            response_content += str(message.content)
                        else:
                            response_content += str(message)
            except Exception as query_error:
                self.logger.error(f"Query调用异常: {query_error}")
                return self._create_error_response(request, f"Claude SDK调用异常: {str(query_error)}")
            
            if not response_content:
                return self._create_error_response(request, "Claude API调用失败")
            
            # 解析响应
            analysis_response = self._parse_analysis_response(request, response_content)
            
            self.logger.info(f"股票分析生成完成: {request.stock_code}, 类型: {request.analysis_type}")
            return analysis_response
            
        except Exception as e:
            self.logger.error(f"生成股票分析失败: {e}")
            return self._create_error_response(request, f"分析生成错误: {str(e)}")
    
    async def chat_with_ai(self, user_message: str, stock_context: Dict[str, Any] = None) -> str:
        """与AI进行对话交互"""
        try:
            if not self.is_available():
                return "抱歉，AI服务当前不可用，请稍后重试。"
            
            # 构建对话提示词
            prompt = self._build_chat_prompt(user_message, stock_context)
            
            # 配置Claude Code选项
            options = None
            if ClaudeCodeOptions:
                options = ClaudeCodeOptions(
                    system_prompt="你是一位专业的股票分析师AI助手，具有丰富的投资分析经验。请用中文与用户交流，请直接回复，不要使用任何工具。",
                    max_turns=1,
                    allowed_tools=[]  # 禁用所有工具
                )
            
            # 调用Claude Code SDK
            response_content = ""
            try:
                if options:
                    async for message in query(prompt=prompt, options=options):
                        # 跳过SystemMessage和ResultMessage，只处理AI响应
                        if SystemMessage and isinstance(message, SystemMessage):
                            continue
                        if ResultMessage and isinstance(message, ResultMessage):
                            continue
                        
                        # 处理AssistantMessage
                        if AssistantMessage and isinstance(message, AssistantMessage):
                            if hasattr(message, 'content') and message.content:
                                for content_block in message.content:
                                    if hasattr(content_block, 'text'):
                                        response_content += content_block.text
                        elif isinstance(message, str):
                            response_content += message
                        elif hasattr(message, 'content'):
                            response_content += str(message.content)
                        else:
                            response_content += str(message)
                else:
                    async for message in query(prompt=prompt):
                        # 跳过SystemMessage和ResultMessage，只处理AI响应
                        if SystemMessage and isinstance(message, SystemMessage):
                            continue
                        if ResultMessage and isinstance(message, ResultMessage):
                            continue
                        
                        # 处理AssistantMessage
                        if AssistantMessage and isinstance(message, AssistantMessage):
                            if hasattr(message, 'content') and message.content:
                                for content_block in message.content:
                                    if hasattr(content_block, 'text'):
                                        response_content += content_block.text
                        elif isinstance(message, str):
                            response_content += message
                        elif hasattr(message, 'content'):
                            response_content += str(message.content)
                        else:
                            response_content += str(message)
            except Exception as query_error:
                self.logger.error(f"Chat query调用异常: {query_error}")
                return f"对话服务异常: {str(query_error)}"
            
            return response_content if response_content else "抱歉，AI服务响应异常，请稍后重试。"
            
        except Exception as e:
            self.logger.error(f"AI对话失败: {e}")
            return f"对话过程中出现错误: {str(e)}"

    async def generate_trading_advice(self, request: AITradingAdviceRequest) -> TradingAdvice:
        """根据用户输入生成交易建议

        Args:
            request: AI交易建议请求对象

        Returns:
            TradingAdvice: 交易建议对象
        """
        try:
            if not self.is_available():
                return self._create_error_advice(request.user_input, "AI服务不可用")

            # 构建建议生成提示词 - 使用统一的request对象
            advice_prompt = self._build_advice_prompt(request)

            self.logger.debug(f"用户PROMPT: {advice_prompt}")

            # 调用AI生成建议
            ai_response = await self.chat_with_ai(advice_prompt)

            # 解析AI响应为交易建议
            trading_advice = self._parse_advice_response(request, ai_response)

            self.logger.info(f"交易建议生成完成: {request.user_input} -> {trading_advice.advice_id}")
            return trading_advice

        except Exception as e:
            self.logger.error(f"生成交易建议失败: {e}")
            return self._create_error_advice(request.user_input, f"建议生成失败: {str(e)}")

    async def confirm_and_execute_advice(self, advice: TradingAdvice, trade_manager=None, trd_env="SIMULATE") -> Dict[str, Any]:
        """确认并执行交易建议"""
        try:
            if advice.status != "pending":
                return {
                    "success": False,
                    "error": f"建议状态无效: {advice.status}，只能执行待确认的建议"
                }

            if not advice.suggested_orders:
                return {
                    "success": False,
                    "error": "建议中没有具体的交易订单"
                }

            # 标记为已确认
            advice.status = "confirmed"

            execution_results = []

            # 执行所有建议的订单
            for order in advice.suggested_orders:
                if trade_manager:
                    try:
                        self.logger.info(f"准备执行订单: {order.stock_code} {order.action} {order.quantity}")
                        # 调用交易管理器执行订单
                        result = trade_manager.place_order(
                            code=order.stock_code,
                            price=order.price or 0.0,
                            qty=order.quantity,
                            order_type=order.order_type,
                            trd_side=order.action.upper(),
                            aux_price=order.trigger_price,
                            trd_env=trd_env,  # 使用传入的交易环境参数
                            market=self._extract_market_from_code(order.stock_code)
                        )

                        execution_results.append({
                            "order": order,
                            "success": True,
                            "result": result
                        })

                        self.logger.info(f"订单执行成功: {order.stock_code} {order.action} {order.quantity}")

                    except Exception as order_error:
                        execution_results.append({
                            "order": order,
                            "success": False,
                            "error": str(order_error)
                        })

                        self.logger.error(f"订单执行失败: {order_error}")
                else:
                    # 没有交易管理器，无法执行订单
                    execution_results.append({
                        "order": order,
                        "success": False,
                        "error": f"交易管理器未提供，无法执行 {trd_env} 环境的交易"
                    })

            # 检查是否所有订单都成功
            all_success = all(result["success"] for result in execution_results)

            if all_success:
                advice.status = "executed"
            else:
                advice.status = "partial_executed"

            return {
                "success": all_success,
                "advice_id": advice.advice_id,
                "execution_results": execution_results,
                "status": advice.status
            }

        except Exception as e:
            self.logger.error(f"执行交易建议失败: {e}")
            advice.status = "error"
            return {
                "success": False,
                "error": f"执行过程异常: {str(e)}"
            }

    async def parse_trading_command(self, user_input: str, context: Dict[str, Any] = None) -> TradingOrder:
        """解析用户交易指令并转换为交易订单"""
        try:
            if not self.is_available():
                return TradingOrder(
                    stock_code="",
                    action="",
                    quantity=0,
                    confidence=0.0,
                    warnings=["AI服务不可用"]
                )

            # 构建解析提示词
            prompt = self._build_parsing_prompt(user_input, context or {})

            # 调用AI进行解析
            ai_response = await self.chat_with_ai(prompt)

            # 解析AI响应
            trading_order = self._parse_ai_response(ai_response)

            # 基础验证
            self._validate_order(trading_order)

            self.logger.info(f"交易指令解析完成: {user_input} -> {trading_order}")
            return trading_order

        except Exception as e:
            self.logger.error(f"交易指令解析失败: {e}")
            return TradingOrder(
                stock_code="",
                action="",
                quantity=0,
                confidence=0.0,
                warnings=[f"解析失败: {str(e)}"]
            )
    
    def _build_analysis_prompt(self, request: AIAnalysisRequest) -> str:
        """构建分析提示词

        Args:
            request: AI分析请求对象（使用统一的AIRequest基类）

        Returns:
            str: 格式化的分析提示词
        """
        try:
            # 使用统一的上下文获取方法
            basic_info = request.get_basic_info()
            realtime_quote = request.get_realtime_quote()
            technical_indicators = request.get_technical_indicators()
            capital_flow = request.get_capital_flow()
            orderbook = request.get_orderbook()

            # 基础分析模板
            prompt = f"""你是一位专业的股票分析师，请对股票 {request.stock_code} 进行{self._get_analysis_type_name(request.analysis_type)}。

股票数据:"""

            # 添加基本信息
            if basic_info:
                prompt += f"""
基本信息:
- 股票代码: {basic_info.get('code', request.stock_code)}
- 股票名称: {request.get_stock_name()}
- 股票类型: {basic_info.get('stock_type', '未知')}"""

            # 添加实时报价
            if realtime_quote:
                prompt += f"""
实时报价:
- 当前价格: {realtime_quote.get('cur_price', 0):.2f}
- 涨跌幅: {realtime_quote.get('change_rate', 0):+.2f}%
- 成交量: {realtime_quote.get('volume', 0):,}
- 换手率: {realtime_quote.get('turnover_rate', 0):.2f}%"""

            # 添加技术指标
            if technical_indicators:
                macd_data = technical_indicators.get('macd', {})
                prompt += f"""
技术指标:
- 均线: MA5={technical_indicators.get('ma5', 0):.2f}, MA10={technical_indicators.get('ma10', 0):.2f}, MA20={technical_indicators.get('ma20', 0):.2f}, MA60={technical_indicators.get('ma60', 0):.2f}
- RSI(14): {technical_indicators.get('rsi', 0):.1f}
- MACD: DIF={macd_data.get('dif', 0):.3f}, DEA={macd_data.get('dea', 0):.3f}, 柱状图={macd_data.get('histogram', 0):.3f}"""

            # 添加资金流向
            if capital_flow:
                main_flow = capital_flow.get('main_in_flow', 0)
                flow_direction = "流入" if main_flow > 0 else "流出"
                prompt += f"""
资金流向:
- 主力净{flow_direction}: {abs(main_flow):.2f}
- 超大单: {capital_flow.get('super_in_flow', 0):+.2f}, 大单: {capital_flow.get('big_in_flow', 0):+.2f}
- 中单: {capital_flow.get('mid_in_flow', 0):+.2f}, 小单: {capital_flow.get('sml_in_flow', 0):+.2f}"""

            # 添加五档买卖盘
            if orderbook:
                ask_data = orderbook.get('ask', [])
                bid_data = orderbook.get('bid', [])
                if ask_data or bid_data:
                    prompt += "\n五档买卖盘:"
                    if ask_data:
                        prompt += "\n- 卖盘: "
                        ask_items = []
                        for i, ask in enumerate(ask_data[:5], 1):
                            price = ask.get('price', 0)
                            volume = ask.get('volume', 0)
                            if price > 0:
                                ask_items.append(f"卖{i}={price:.2f}({volume})")
                        prompt += ", ".join(ask_items) if ask_items else "无数据"
                    if bid_data:
                        prompt += "\n- 买盘: "
                        bid_items = []
                        for i, bid in enumerate(bid_data[:5], 1):
                            price = bid.get('price', 0)
                            volume = bid.get('volume', 0)
                            if price > 0:
                                bid_items.append(f"买{i}={price:.2f}({volume})")
                        prompt += ", ".join(bid_items) if bid_items else "无数据"

            # 添加分析要求
            prompt += f"""

请进行{self._get_analysis_type_name(request.analysis_type)}，用中文回答，格式要求:
- 结合技术指标和资金流向进行综合分析
- 分析五档买卖盘判断短期买卖力量对比
- 提供明确的分析结论
- 给出投资建议和风险评估
- 评估置信度和风险等级"""

            # 添加用户问题（使用统一的user_input字段）
            if request.user_input:
                prompt += f"\n\n用户特别关心的问题: {request.user_input}\n请在分析中特别回答这个问题。"

            return prompt

        except Exception as e:
            self.logger.error(f"构建分析提示词失败: {e}")
            return f"分析股票 {request.stock_code} 的{self._get_analysis_type_name(request.analysis_type)}"
    
    def _build_chat_prompt(self, user_message: str, stock_context: Dict[str, Any] = None) -> str:
        """构建对话提示词"""
        prompt = f"用户问题: {user_message}"
        
        # 添加股票上下文
        if stock_context:
            context_info = ""
            if 'stock_code' in stock_context:
                context_info += f"股票代码: {stock_context['stock_code']}\n"
            if 'stock_name' in stock_context:
                context_info += f"股票名称: {stock_context['stock_name']}\n"
            if 'current_price' in stock_context:
                context_info += f"当前价格: {stock_context['current_price']}\n"
            
            if context_info:
                prompt = f"股票信息:\n{context_info}\n{prompt}"
        
        return prompt
    
    def _parse_analysis_response(self, request: AIAnalysisRequest, response: str) -> AIAnalysisResponse:
        """解析分析响应"""
        try:
            # 提取关键点
            key_points = self._extract_key_points(response)
            
            # 提取建议
            recommendation = self._extract_recommendation(response)
            
            # 评估置信度和风险等级
            confidence_score = self._estimate_confidence(response)
            risk_level = self._estimate_risk_level(response)
            
            return AIAnalysisResponse(
                request_id=f"{request.stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                stock_code=request.stock_code,
                analysis_type=request.analysis_type,
                content=response,
                key_points=key_points,
                recommendation=recommendation,
                confidence_score=confidence_score,
                risk_level=risk_level,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"解析分析响应失败: {e}")
            return self._create_error_response(request, f"响应解析错误: {str(e)}")
    
    def _extract_key_points(self, response: str) -> List[str]:
        """从响应中提取关键点"""
        try:
            key_points = []
            lines = response.split('\n')
            
            for line in lines:
                line = line.strip()
                if (line.startswith('•') or line.startswith('-') or 
                    line.startswith('*') or '关键' in line or '重要' in line):
                    key_points.append(line.lstrip('•-*').strip())
            
            return key_points[:5]  # 最多返回5个关键点
            
        except Exception as e:
            self.logger.error(f"提取关键点失败: {e}")
            return []
    
    def _extract_recommendation(self, response: str) -> str:
        """从响应中提取投资建议"""
        try:
            recommendation_keywords = ['建议', '推荐', '操作', '策略', '投资']
            lines = response.split('。')
            
            for line in lines:
                if any(keyword in line for keyword in recommendation_keywords):
                    return line.strip()
            
            # 如果没找到特定建议，返回最后一段
            paragraphs = response.split('\n\n')
            if paragraphs:
                return paragraphs[-1].strip()
            
            return "请根据个人风险承受能力谨慎投资"
            
        except Exception as e:
            self.logger.error(f"提取投资建议失败: {e}")
            return "投资建议提取失败"

    def _build_parsing_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        """构建AI解析提示词"""
        return f"""
你是一个专业的股票交易指令解析器。请将用户的自然语言指令转换为结构化的交易订单。

用户指令: {user_input}

当前上下文:
- 当前选择股票: {context.get('current_stock', '无')}
- 当前股价: {context.get('current_price', '未知')}
- 可用资金: {context.get('available_funds', '未知')}

请按以下JSON格式返回解析结果:
{{
    "stock_code": "股票代码 (如HK.00700)",
    "action": "buy或sell",
    "quantity": 数量(整数),
    "price": 价格(数字,null表示市价),
    "order_type": "MARKET, NORMAL, STOP, STOP_LIMIT其中之一",
    "trigger_price": 触发价格(数字,仅止盈止损订单需要),
    "confidence": 0.0到1.0的置信度,
    "reasoning": "解析推理过程",
    "warnings": ["警告信息列表"]
}}

订单类型解析规则:
1. 现价订单 (MARKET): "市价买入"、"立即买入"、"现价卖出"等
2. 限价订单 (NORMAL): "420元买入"、"限价卖出450元"等
3. 止损订单 (STOP): "跌破400元止损"、"止损价设在380"等
4. 止盈限价订单 (STOP_LIMIT): "涨到500元止盈"、"止盈价设在480"等

通用解析规则:
1. 如果未明确指定股票，使用当前选择的股票
2. 如果未指定价格，默认为现价订单
3. 如果指令不明确，降低置信度并在warnings中说明
4. 仅支持买入(buy)和卖出(sell)操作
"""

    def _parse_ai_response(self, ai_response: str) -> TradingOrder:
        """解析AI响应并提取交易参数"""
        try:
            # 尝试从响应中提取JSON
            json_str = self._extract_json_from_response(ai_response)
            if json_str:
                order_data = json.loads(json_str)

                return TradingOrder(
                    stock_code=order_data.get('stock_code', ''),
                    action=order_data.get('action', ''),
                    quantity=int(order_data.get('quantity', 0)),
                    price=order_data.get('price'),
                    order_type=order_data.get('order_type', 'MARKET'),
                    trigger_price=order_data.get('trigger_price'),
                    confidence=float(order_data.get('confidence', 0.0)),
                    reasoning=order_data.get('reasoning', ''),
                    warnings=order_data.get('warnings', [])
                )
            else:
                # 如果无法提取JSON，返回错误订单
                return TradingOrder(
                    stock_code="",
                    action="",
                    quantity=0,
                    confidence=0.0,
                    warnings=["AI响应格式无效，无法解析为交易订单"]
                )

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
            return TradingOrder(
                stock_code="",
                action="",
                quantity=0,
                confidence=0.0,
                warnings=[f"JSON格式错误: {str(e)}"]
            )
        except Exception as e:
            self.logger.error(f"AI响应解析失败: {e}")
            return TradingOrder(
                stock_code="",
                action="",
                quantity=0,
                confidence=0.0,
                warnings=[f"响应解析异常: {str(e)}"]
            )

    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """从AI响应中提取JSON字符串"""
        try:
            # 查找JSON块
            start_markers = ['```json', '```', '{']

            # 查找JSON开始位置
            start_pos = -1
            for marker in start_markers:
                pos = response.find(marker)
                if pos != -1:
                    start_pos = pos + len(marker) if marker != '{' else pos
                    break

            if start_pos == -1:
                # 尝试查找第一个{
                start_pos = response.find('{')

            if start_pos == -1:
                return None

            # 查找JSON结束位置
            end_pos = -1
            if start_pos >= 0:
                # 从开始位置查找最后一个}
                remaining = response[start_pos:]
                last_brace = remaining.rfind('}')
                if last_brace != -1:
                    end_pos = start_pos + last_brace + 1

            if end_pos == -1:
                return None

            # 提取JSON字符串
            json_str = response[start_pos:end_pos].strip()

            # 清理可能的markdown标记
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]

            return json_str.strip()

        except Exception as e:
            self.logger.error(f"提取JSON失败: {e}")
            return None

    def _validate_order(self, order: TradingOrder) -> None:
        """验证交易订单的基本有效性"""
        try:
            warnings = list(order.warnings) if order.warnings else []

            # 验证股票代码
            if not order.stock_code:
                warnings.append("缺少股票代码")

            # 验证买卖方向
            if order.action not in ['buy', 'sell']:
                warnings.append(f"无效的交易方向: {order.action}")

            # 验证数量
            if order.quantity <= 0:
                warnings.append(f"无效的交易数量: {order.quantity}")

            # 验证订单类型
            valid_types = [OrderType.MARKET, OrderType.NORMAL, OrderType.STOP, OrderType.STOP_LIMIT]
            if order.order_type not in valid_types:
                warnings.append(f"无效的订单类型: {order.order_type}")

            # 验证价格
            if order.order_type == OrderType.NORMAL and (order.price is None or order.price <= 0):
                warnings.append("限价订单必须指定有效价格")

            # 验证触发价格
            if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
                if order.trigger_price is None or order.trigger_price <= 0:
                    warnings.append("止损止盈订单必须指定有效触发价格")

            # 更新警告列表
            order.warnings = warnings

        except Exception as e:
            self.logger.error(f"订单验证失败: {e}")
            if not order.warnings:
                order.warnings = []
            order.warnings.append(f"验证过程异常: {str(e)}")

    def _build_advice_prompt(self, request: AITradingAdviceRequest) -> str:
        """构建AI建议生成提示词

        Args:
            request: AI交易建议请求对象

        Returns:
            str: 格式化的提示词
        """
        # 从统一的request对象中提取信息
        realtime_quote = request.get_realtime_quote()
        technical_indicators = request.get_technical_indicators()
        capital_flow = request.get_capital_flow()
        orderbook = request.get_orderbook()

        # 构建技术指标信息文本
        technical_info = ""
        if technical_indicators:
            technical_info = "\n技术指标数据:"

            # MA均线
            if 'ma5' in technical_indicators:
                technical_info += f"\n- MA5: {technical_indicators['ma5']:.2f}"
            if 'ma10' in technical_indicators:
                technical_info += f", MA10: {technical_indicators['ma10']:.2f}"
            if 'ma20' in technical_indicators:
                technical_info += f", MA20: {technical_indicators['ma20']:.2f}"
            if 'ma60' in technical_indicators:
                technical_info += f", MA60: {technical_indicators['ma60']:.2f}"

            # RSI指标
            if 'rsi' in technical_indicators:
                rsi_value = technical_indicators['rsi']
                technical_info += f"\n- RSI(14): {rsi_value:.1f}"

            # MACD指标
            if 'macd' in technical_indicators and isinstance(technical_indicators['macd'], dict):
                macd_data = technical_indicators['macd']
                dif = macd_data.get('dif', 0)
                dea = macd_data.get('dea', 0)
                histogram = macd_data.get('histogram', 0)
                technical_info += f"\n- MACD: DIF={dif:.3f}, DEA={dea:.3f}, 柱状图={histogram:.3f}"

        # 构建资金流向信息文本
        capital_flow_info = ""
        if capital_flow:
            capital_flow_info = "\n资金流向数据:"

            # 主力资金流向
            if 'main_in_flow' in capital_flow:
                main_flow = capital_flow['main_in_flow']
                flow_direction = "流入" if main_flow > 0 else "流出"
                capital_flow_info += f"\n- 主力净{flow_direction}: {abs(main_flow):.2f}"

            # 超大单、大单、中单、小单
            flow_types = [
                ('super_in_flow', '超大单'),
                ('big_in_flow', '大单'),
                ('mid_in_flow', '中单'),
                ('sml_in_flow', '小单')
            ]
            for flow_key, flow_label in flow_types:
                if flow_key in capital_flow:
                    flow_value = capital_flow[flow_key]
                    capital_flow_info += f", {flow_label}: {flow_value:+.2f}"

        # 构建五档买卖盘信息文本
        orderbook_info = ""
        if orderbook:
            ask_data = orderbook.get('ask', [])
            bid_data = orderbook.get('bid', [])
            if ask_data or bid_data:
                orderbook_info = "\n五档买卖盘:"
                if ask_data:
                    ask_items = []
                    for i, ask in enumerate(ask_data[:5], 1):
                        price = ask.get('price', 0)
                        volume = ask.get('volume', 0)
                        if price > 0:
                            ask_items.append(f"卖{i}={price:.2f}({volume})")
                    if ask_items:
                        orderbook_info += f"\n- 卖盘: {', '.join(ask_items)}"
                if bid_data:
                    bid_items = []
                    for i, bid in enumerate(bid_data[:5], 1):
                        price = bid.get('price', 0)
                        volume = bid.get('volume', 0)
                        if price > 0:
                            bid_items.append(f"买{i}={price:.2f}({volume})")
                    if bid_items:
                        orderbook_info += f"\n- 买盘: {', '.join(bid_items)}"

        return f"""
你是一位专业的股票投资顾问AI助手。用户向你咨询投资建议，请根据用户的需求和当前市场情况，生成专业的交易建议。

用户需求: {request.user_input}

当前市场上下文:
- 当前关注股票: {request.stock_code}
- 股票名称: {request.get_stock_name()}
- 当前股价: {realtime_quote.get('cur_price', '未知')}
- 今日涨跌幅: {realtime_quote.get('change_rate', '未知')}
- 成交量: {realtime_quote.get('volume', '未知')}
- 可用资金: {request.get_available_funds()}
- 当前持仓: {request.get_current_position()}
- 风险偏好: {request.risk_preference}
{technical_info}{capital_flow_info}{orderbook_info}

请按以下JSON格式返回投资建议:
{{
    "advice_summary": "简短的建议摘要（1-2句话）",
    "detailed_analysis": "详细的市场和技术分析（包含基本面、技术面、资金面等）",
    "recommended_action": "buy, sell, hold, wait 其中之一",
    "suggested_orders": [
        {{
            "stock_code": "股票代码",
            "action": "buy或sell",
            "quantity": 建议数量,
            "price": 建议价格(null表示市价),
            "order_type": "MARKET, NORMAL, STOP, STOP_LIMIT其中之一",
            "trigger_price": 触发价格(可选),
            "reasoning": "这个订单的具体原因"
        }}
    ],
    "risk_assessment": "低, 中, 高 其中之一",
    "confidence_score": 0.0到1.0的置信度,
    "expected_return": "预期收益描述",
    "risk_factors": ["风险因素1", "风险因素2"],
    "key_points": ["关键要点1", "关键要点2", "关键要点3"]
}}

分析要求:
1. 结合当前股价、技术指标、资金流向和市场情况进行综合分析
2. 充分利用技术指标(MA、RSI、MACD等)进行技术面分析
3. 结合资金流向数据分析主力资金动向和市场情绪
4. 分析五档买卖盘数据判断短期买卖力量对比和支撑阻力位
5. 考虑用户的资金状况和风险承受能力
6. 提供具体可执行的交易策略
7. 明确指出风险因素和注意事项
8. 如果市场条件不适合交易，建议等待
9. 所有建议必须基于风险控制原则

回答请用中文，格式严格按照上述JSON结构。
"""

    def _parse_advice_response(self, request: AITradingAdviceRequest, ai_response: str) -> TradingAdvice:
        """解析AI响应为交易建议

        Args:
            request: AI交易建议请求对象
            ai_response: AI返回的响应文本

        Returns:
            TradingAdvice: 解析后的交易建议对象
        """
        try:
            # 调试日志：记录原始响应
            self.logger.debug(f"AI原始响应: {ai_response[:500]}...")

            # 提取JSON数据
            json_str = self._extract_json_from_response(ai_response)
            if json_str:
                self.logger.debug(f"提取的JSON字符串: {json_str[:500]}...")
                advice_data = json.loads(json_str)

                # 调试日志：记录解析后的数据
                self.logger.info(f"解析后的建议数据: recommended_action={advice_data.get('recommended_action')}, "
                               f"suggested_orders数量={len(advice_data.get('suggested_orders', []))}")

                # 解析建议的订单
                suggested_orders = []
                for order_data in advice_data.get('suggested_orders', []):
                    order = TradingOrder(
                        stock_code=order_data.get('stock_code', request.stock_code),
                        action=order_data.get('action', ''),
                        quantity=int(order_data.get('quantity', 0)),
                        price=order_data.get('price'),
                        order_type=order_data.get('order_type', 'MARKET'),
                        trigger_price=order_data.get('trigger_price'),
                        reasoning=order_data.get('reasoning', '')
                    )
                    # 验证订单
                    self._validate_order(order)
                    suggested_orders.append(order)

                # 如果没有订单但有recommended_action，记录警告
                if not suggested_orders and advice_data.get('recommended_action') not in ['wait', 'hold']:
                    self.logger.warning(f"AI建议操作为{advice_data.get('recommended_action')}但未提供具体订单！")

                # 生成建议ID
                advice_id = f"advice_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.user_input) % 10000}"

                return TradingAdvice(
                    advice_id=advice_id,
                    user_prompt=request.user_input,
                    stock_code=request.stock_code,
                    stock_name=request.get_stock_name(),
                    advice_summary=advice_data.get('advice_summary', ''),
                    detailed_analysis=advice_data.get('detailed_analysis', ''),
                    recommended_action=advice_data.get('recommended_action', 'wait'),
                    suggested_orders=suggested_orders,
                    risk_assessment=advice_data.get('risk_assessment', '中'),
                    confidence_score=float(advice_data.get('confidence_score', 0.0)),
                    expected_return=advice_data.get('expected_return'),
                    risk_factors=advice_data.get('risk_factors', []),
                    key_points=advice_data.get('key_points', []),
                    status="pending"
                )
            else:
                # 无法解析JSON，创建基于文本的建议
                return self._create_text_based_advice(request, ai_response)

        except json.JSONDecodeError as e:
            self.logger.error(f"建议JSON解析失败: {e}")
            return self._create_error_advice(request.user_input, f"AI响应格式错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"解析交易建议失败: {e}")
            return self._create_error_advice(request.user_input, f"建议解析异常: {str(e)}")

    def _create_text_based_advice(self, request: AITradingAdviceRequest, ai_response: str) -> TradingAdvice:
        """基于纯文本响应创建建议

        Args:
            request: AI交易建议请求对象
            ai_response: AI返回的文本响应

        Returns:
            TradingAdvice: 基于文本的建议对象
        """
        advice_id = f"text_advice_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.user_input) % 10000}"

        return TradingAdvice(
            advice_id=advice_id,
            user_prompt=request.user_input,
            stock_code=request.stock_code,
            stock_name=request.get_stock_name(),
            advice_summary="AI提供了文本建议，请查看详细分析",
            detailed_analysis=ai_response,
            recommended_action="wait",
            suggested_orders=[],
            risk_assessment="中",
            confidence_score=0.5,
            expected_return="请参考详细分析",
            risk_factors=["AI响应格式不标准，请谨慎参考"],
            key_points=["请仔细阅读详细分析内容"],
            status="pending"
        )

    def _create_error_advice(self, user_prompt: str, error_message: str) -> TradingAdvice:
        """创建错误建议"""
        advice_id = f"error_advice_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        return TradingAdvice(
            advice_id=advice_id,
            user_prompt=user_prompt,
            stock_code="",
            stock_name="",
            advice_summary=f"建议生成失败: {error_message}",
            detailed_analysis=f"由于技术问题无法生成投资建议: {error_message}",
            recommended_action="wait",
            suggested_orders=[],
            risk_assessment="高",
            confidence_score=0.0,
            expected_return="无法评估",
            risk_factors=["AI服务异常", "建议不可用"],
            key_points=["请稍后重试", "如有需要请咨询专业投资顾问"],
            status="error"
        )

    def _extract_market_from_code(self, stock_code: str) -> str:
        """从股票代码提取市场信息"""
        if stock_code.startswith('HK.'):
            return 'HK'
        elif stock_code.startswith('US.'):
            return 'US'
        elif stock_code.startswith(('SH.', 'SZ.')):
            return 'CN'
        else:
            return 'HK'  # 默认港股
    
    def _estimate_confidence(self, response: str) -> float:
        """估算分析置信度"""
        try:
            high_confidence_words = ['明确', '强烈', '确定', '显著', '明显']
            low_confidence_words = ['不确定', '谨慎', '观望', '等待', '可能']
            
            response_lower = response.lower()
            
            high_count = sum(1 for word in high_confidence_words if word in response_lower)
            low_count = sum(1 for word in low_confidence_words if word in response_lower)
            
            if high_count > low_count:
                return 0.8
            elif low_count > high_count:
                return 0.4
            else:
                return 0.6
                
        except Exception as e:
            self.logger.error(f"估算置信度失败: {e}")
            return 0.5
    
    def _estimate_risk_level(self, response: str) -> str:
        """估算风险等级"""
        try:
            response_lower = response.lower()
            
            high_risk_words = ['高风险', '风险较高', '谨慎', '风险', '波动大']
            low_risk_words = ['低风险', '稳健', '保守', '安全']
            
            high_risk_count = sum(1 for word in high_risk_words if word in response_lower)
            low_risk_count = sum(1 for word in low_risk_words if word in response_lower)
            
            if high_risk_count > low_risk_count:
                return '高'
            elif low_risk_count > high_risk_count:
                return '低'
            else:
                return '中'
                
        except Exception as e:
            self.logger.error(f"估算风险等级失败: {e}")
            return '中'
    
    def _create_error_response(self, request: AIAnalysisRequest, error_message: str) -> AIAnalysisResponse:
        """创建错误响应"""
        return AIAnalysisResponse(
            request_id=f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            stock_code=request.stock_code,
            analysis_type=request.analysis_type,
            content=f"分析过程中出现错误: {error_message}",
            key_points=[],
            recommendation="由于技术问题，建议稍后重试或咨询专业投资顾问",
            confidence_score=0.0,
            risk_level='未知',
            timestamp=datetime.now()
        )
    
    def _get_analysis_type_name(self, analysis_type: str) -> str:
        """获取分析类型中文名称"""
        type_names = {
            'technical': '技术分析',
            'fundamental': '基本面分析',
            'comprehensive': '综合分析',
            'risk_assessment': '风险评估',
            'capital_flow': '资金流向分析'
        }
        return type_names.get(analysis_type, '综合分析')
    
    def get_client_status(self) -> Dict[str, Any]:
        """获取客户端状态"""
        return {
            'available': self.available,
            'sdk_available': CLAUDE_CODE_SDK_AVAILABLE,
            'authentication': 'Claude Code App' if self.available else 'Unavailable'
        }
    
    def test_connection(self) -> bool:
        """测试Claude AI连接 - 简化版本，只检查SDK可用性"""
        return self.is_available()


# 便捷函数
async def create_claude_client() -> ClaudeAIClient:
    """创建Claude AI客户端的便捷函数"""
    client = ClaudeAIClient()
    
    if client.is_available():
        # 简化版本：只检查SDK可用性，避免异步任务冲突
        connection_ok = client.test_connection()
        if connection_ok:
            client.logger.info("Claude AI客户端就绪")
        else:
            client.logger.warning("Claude AI SDK不可用")
    
    return client


async def quick_stock_analysis(stock_code: str, analysis_type: str = 'comprehensive', 
                              data_context: Dict[str, Any] = None) -> str:
    """快速股票分析的便捷函数"""
    try:
        client = await create_claude_client()
        
        if not client.is_available():
            return "Claude AI服务不可用，请检查claude-code-sdk安装状态。"
        
        request = AIAnalysisRequest(
            stock_code=stock_code,
            analysis_type=analysis_type,
            data_context=data_context or {}
        )
        
        response = await client.generate_stock_analysis(request)
        return response.content
        
    except Exception as e:
        return f"快速分析失败: {str(e)}"