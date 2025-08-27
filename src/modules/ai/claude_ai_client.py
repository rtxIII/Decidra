"""
Claude AI Client - 基于claude-code-sdk的AI分析客户端

提供股票分析、投资建议、对话交互等AI功能
依赖: claude-code-sdk
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from utils.logger import get_logger

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


@dataclass
class AIAnalysisRequest:
    """AI分析请求"""
    stock_code: str
    analysis_type: str  # 'technical', 'fundamental', 'comprehensive'
    data_context: Dict[str, Any]
    user_question: Optional[str] = None
    language: str = 'zh-CN'


@dataclass
class AIAnalysisResponse:
    """AI分析响应"""
    request_id: str
    stock_code: str
    analysis_type: str
    content: str
    key_points: List[str]
    recommendation: str
    confidence_score: float
    risk_level: str
    timestamp: datetime


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
    
    def _build_analysis_prompt(self, request: AIAnalysisRequest) -> str:
        """构建分析提示词"""
        try:
            # 基础分析模板
            prompt = f"""你是一位专业的股票分析师，请对股票 {request.stock_code} 进行{self._get_analysis_type_name(request.analysis_type)}。

股票数据:"""
            
            # 添加数据上下文
            if 'basic_info' in request.data_context:
                basic_info = request.data_context['basic_info']
                prompt += f"""
基本信息:
- 股票代码: {basic_info.get('code', request.stock_code)}
- 股票名称: {basic_info.get('name', '未知')}
- 股票类型: {basic_info.get('stock_type', '未知')}"""
            
            if 'realtime_quote' in request.data_context:
                quote = request.data_context['realtime_quote']
                prompt += f"""
实时报价:
- 当前价格: {quote.get('cur_price', 0):.2f}
- 涨跌幅: {quote.get('change_rate', 0):+.2f}%
- 成交量: {quote.get('volume', 0):,}
- 换手率: {quote.get('turnover_rate', 0):.2f}%"""
            
            if 'technical_indicators' in request.data_context:
                indicators = request.data_context['technical_indicators']
                prompt += f"""
技术指标:
- RSI: {indicators.get('rsi', 0):.1f}
- MACD: DIF={indicators.get('macd', {}).get('dif', 0):.3f}
- 均线: MA5={indicators.get('ma5', 0):.2f}, MA20={indicators.get('ma20', 0):.2f}"""
            
            # 添加分析要求
            prompt += f"""

请进行{self._get_analysis_type_name(request.analysis_type)}，用中文回答，格式要求:
- 提供明确的分析结论
- 给出投资建议和风险评估
- 评估置信度和风险等级"""
            
            # 添加用户问题
            if request.user_question:
                prompt += f"\n\n用户特别关心的问题: {request.user_question}\n请在分析中特别回答这个问题。"
            
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