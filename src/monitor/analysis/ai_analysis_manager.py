"""
AIAnalysisManager - AI分析管理模块

负责分析页面的AI智能分析、投资建议生成、对话历史管理和分析报告生成
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

from base.monitor import StockData, MarketStatus
from base.futu_class import KLineData
from utils.global_vars import get_logger
from utils.global_vars import PATH_DATA

# AI分析配置
AI_ANALYSIS_CONFIG = {
    'max_dialog_history': 50,      # 最大对话历史记录数
    'analysis_cache_hours': 2,     # 分析结果缓存小时数
    'confidence_threshold': 0.6,   # 置信度阈值
    'max_recommendation_days': 7,  # 最大推荐持有天数
}

# 分析类型配置
ANALYSIS_TYPES = {
    'technical': '技术分析',
    'fundamental': '基本面分析',
    'capital_flow': '资金面分析',
    'sector_comparison': '同行对比',
    'risk_assessment': '风险评估'
}


@dataclass
class DialogMessage:
    """对话消息"""
    timestamp: datetime
    message_type: str  # 'user' or 'ai'
    content: str
    analysis_type: Optional[str] = None


@dataclass
class AIAnalysisResult:
    """AI分析结果"""
    stock_code: str
    analysis_type: str
    analysis_content: str
    key_points: List[str]
    recommendation: str
    confidence_level: float
    risk_level: str
    target_price_range: Optional[Tuple[float, float]]
    holding_period: Optional[int]
    generated_time: datetime


@dataclass
class AIRecommendation:
    """AI投资建议"""
    action: str  # 'buy', 'sell', 'hold'
    reason: str
    confidence: float
    price_target: Optional[float]
    stop_loss: Optional[float]
    time_horizon: str  # 'short', 'medium', 'long'


class AIAnalysisManager:
    """
    AI分析管理器
    负责AI智能分析和投资建议生成
    """
    
    def __init__(self, analysis_data_manager):
        """初始化AI分析管理器"""
        self.analysis_data_manager = analysis_data_manager
        self.logger = get_logger(__name__)
        
        # 对话历史管理
        self.dialog_history: List[DialogMessage] = []
        
        # 分析结果缓存
        self.analysis_cache: Dict[str, Dict[str, AIAnalysisResult]] = {}  # {stock_code: {analysis_type: result}}
        
        # AI分析状态
        self.current_stock_code: Optional[str] = None
        self.is_analyzing: bool = False
        self.last_analysis_time: Optional[datetime] = None
        
        # 快捷功能配置
        self.quick_functions = {
            'F1': ('technical', '技术分析'),
            'F2': ('fundamental', '基本面分析'),
            'F3': ('capital_flow', '资金面分析'),
            'F4': ('sector_comparison', '同行对比'),
            'F5': ('risk_assessment', '风险评估')
        }
        
        self.logger.info("AIAnalysisManager 初始化完成")
    
    async def set_current_stock(self, stock_code: str) -> bool:
        """设置当前分析的股票"""
        try:
            if stock_code == self.current_stock_code:
                return True
            
            self.current_stock_code = stock_code
            self.logger.info(f"AI分析切换到股票: {stock_code}")
            
            # 清理对话历史（可选）
            # self.dialog_history.clear()
            
            # 生成欢迎消息
            welcome_msg = f"🤖 您好！我是AI智能分析助手，现在为您分析股票 {stock_code}。\n\n" \
                         f"您可以：\n" \
                         f"• 直接提问关于该股票的任何问题\n" \
                         f"• 使用快捷功能键获取专业分析\n" \
                         f"• 输入 '?' 查看所有可用命令"
            
            await self.add_ai_message(welcome_msg)
            
            # 自动生成基础分析
            await self.generate_basic_analysis()
            
            return True
            
        except Exception as e:
            self.logger.error(f"设置AI分析股票失败: {e}")
            return False
    
    async def add_user_message(self, message: str) -> bool:
        """添加用户消息到对话历史"""
        try:
            dialog_msg = DialogMessage(
                timestamp=datetime.now(),
                message_type='user',
                content=message.strip()
            )
            
            self.dialog_history.append(dialog_msg)
            
            # 限制历史记录数量
            if len(self.dialog_history) > AI_ANALYSIS_CONFIG['max_dialog_history']:
                self.dialog_history = self.dialog_history[-AI_ANALYSIS_CONFIG['max_dialog_history']:]
            
            self.logger.debug(f"添加用户消息: {message[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"添加用户消息失败: {e}")
            return False
    
    async def add_ai_message(self, message: str, analysis_type: str = None) -> bool:
        """添加AI消息到对话历史"""
        try:
            dialog_msg = DialogMessage(
                timestamp=datetime.now(),
                message_type='ai',
                content=message.strip(),
                analysis_type=analysis_type
            )
            
            self.dialog_history.append(dialog_msg)
            
            # 限制历史记录数量
            if len(self.dialog_history) > AI_ANALYSIS_CONFIG['max_dialog_history']:
                self.dialog_history = self.dialog_history[-AI_ANALYSIS_CONFIG['max_dialog_history']:]
            
            self.logger.debug(f"添加AI消息: {message[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"添加AI消息失败: {e}")
            return False
    
    async def process_user_input(self, user_input: str) -> str:
        """处理用户输入并生成AI回复"""
        try:
            if not user_input.strip():
                return "请输入您的问题或使用快捷功能键。"
            
            # 添加用户消息到历史
            await self.add_user_message(user_input)
            
            # 检查是否是特殊命令
            if user_input.strip() == '?':
                return await self._generate_help_message()
            
            # 检查是否是快捷功能
            for key, (analysis_type, name) in self.quick_functions.items():
                if user_input.strip().upper() == key:
                    return await self.generate_analysis(analysis_type)
            
            # 分析用户问题类型并生成回复
            response = await self._analyze_question_and_respond(user_input)
            
            # 添加AI回复到历史
            await self.add_ai_message(response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"处理用户输入失败: {e}")
            error_msg = "抱歉，处理您的问题时出现了错误，请稍后重试。"
            await self.add_ai_message(error_msg)
            return error_msg
    
    async def _analyze_question_and_respond(self, question: str) -> str:
        """分析用户问题并生成回复"""
        try:
            question_lower = question.lower()
            
            # 获取当前股票分析数据
            analysis_data = self.analysis_data_manager.get_current_analysis_data()
            if not analysis_data:
                return "抱歉，当前没有可分析的股票数据。"
            
            # 问题分类和回复生成
            if any(keyword in question_lower for keyword in ['适合', '长期', '持有', '投资']):
                return await self._generate_investment_advice()
                
            elif any(keyword in question_lower for keyword in ['技术', '指标', 'ma', 'rsi', 'macd']):
                return await self.generate_analysis('technical')
                
            elif any(keyword in question_lower for keyword in ['基本面', '估值', 'pe', 'pb', 'roe']):
                return await self.generate_analysis('fundamental')
                
            elif any(keyword in question_lower for keyword in ['资金', '流入', '流出', '主力']):
                return await self.generate_analysis('capital_flow')
                
            elif any(keyword in question_lower for keyword in ['风险', '止损', '回撤']):
                return await self.generate_analysis('risk_assessment')
                
            elif any(keyword in question_lower for keyword in ['价格', '目标价', '涨跌']):
                return await self._generate_price_analysis()
                
            else:
                # 通用问题回复
                return await self._generate_general_response(question)
            
        except Exception as e:
            self.logger.error(f"分析问题失败: {e}")
            return "抱歉，分析您的问题时出现了错误。"
    
    async def generate_analysis(self, analysis_type: str) -> str:
        """生成指定类型的分析"""
        try:
            if analysis_type not in ANALYSIS_TYPES:
                return f"不支持的分析类型: {analysis_type}"
            
            # 检查缓存
            cached_result = self._get_cached_analysis(self.current_stock_code, analysis_type)
            if cached_result:
                return self._format_analysis_result(cached_result)
            
            # 获取分析数据
            analysis_data = self.analysis_data_manager.get_current_analysis_data()
            if not analysis_data:
                return "抱歉，当前没有可分析的股票数据。"
            
            self.is_analyzing = True
            
            # 根据分析类型生成分析结果
            if analysis_type == 'technical':
                result = await self._generate_technical_analysis(analysis_data)
            elif analysis_type == 'fundamental':
                result = await self._generate_fundamental_analysis(analysis_data)
            elif analysis_type == 'capital_flow':
                result = await self._generate_capital_flow_analysis(analysis_data)
            elif analysis_type == 'sector_comparison':
                result = await self._generate_sector_comparison(analysis_data)
            elif analysis_type == 'risk_assessment':
                result = await self._generate_risk_assessment(analysis_data)
            else:
                return f"暂不支持 {ANALYSIS_TYPES[analysis_type]} 分析"
            
            # 缓存结果
            self._cache_analysis_result(result)
            
            self.is_analyzing = False
            self.last_analysis_time = datetime.now()
            
            return self._format_analysis_result(result)
            
        except Exception as e:
            self.is_analyzing = False
            self.logger.error(f"生成分析失败: {e}")
            return f"生成{ANALYSIS_TYPES.get(analysis_type, '分析')}时出现错误，请稍后重试。"
    
    async def _generate_technical_analysis(self, analysis_data) -> AIAnalysisResult:
        """生成技术分析"""
        indicators = analysis_data.technical_indicators
        kline_data = analysis_data.kline_data
        
        key_points = []
        analysis_content = "📊 技术指标分析:\n\n"
        
        # RSI分析
        rsi = indicators.get('rsi', 0)
        if rsi > 70:
            key_points.append(f"RSI({rsi:.1f}) 超买，注意回调风险")
            analysis_content += f"• RSI: {rsi:.1f} ➤ 超买区域，建议谨慎追高\n"
        elif rsi < 30:
            key_points.append(f"RSI({rsi:.1f}) 超卖，可能存在反弹机会")
            analysis_content += f"• RSI: {rsi:.1f} ➤ 超卖区域，可关注反弹机会\n"
        else:
            analysis_content += f"• RSI: {rsi:.1f} ➤ 处于正常区间\n"
        
        # MACD分析
        macd_data = indicators.get('macd', {})
        dif = macd_data.get('dif', 0)
        dea = macd_data.get('dea', 0)
        histogram = macd_data.get('histogram', 0)
        
        if dif > dea and histogram > 0:
            key_points.append("MACD金叉，动能向上")
            analysis_content += "• MACD: 金叉信号，动能向上\n"
        elif dif < dea and histogram < 0:
            key_points.append("MACD死叉，动能向下")
            analysis_content += "• MACD: 死叉信号，动能向下\n"
        else:
            analysis_content += "• MACD: 信号不明确，观望为主\n"
        
        # 均线分析
        ma_analysis = []
        for ma_type in ['ma5', 'ma10', 'ma20']:
            ma_value = indicators.get(ma_type, 0)
            if ma_value > 0:
                ma_analysis.append(f"{ma_type.upper()}: {ma_value:.2f}")
        
        if ma_analysis:
            analysis_content += f"• 均线: {', '.join(ma_analysis)}\n"
        
        # 价格趋势分析
        price_trend = indicators.get('price_trend', '无明确趋势')
        key_points.append(f"价格趋势: {price_trend}")
        analysis_content += f"• 趋势: {price_trend}\n"
        
        # 成交量分析
        volume_trend = indicators.get('volume_trend', '量能平稳')
        analysis_content += f"• 成交量: {volume_trend}\n"
        
        # 生成建议
        if rsi < 30 and dif > dea:
            recommendation = "技术面偏向积极，可适量关注"
            confidence = 0.7
        elif rsi > 70:
            recommendation = "技术面存在调整压力，建议谨慎"
            confidence = 0.6
        else:
            recommendation = "技术面中性，建议观望"
            confidence = 0.5
        
        return AIAnalysisResult(
            stock_code=analysis_data.stock_code,
            analysis_type='technical',
            analysis_content=analysis_content,
            key_points=key_points,
            recommendation=recommendation,
            confidence_level=confidence,
            risk_level='中等',
            target_price_range=None,
            holding_period=None,
            generated_time=datetime.now()
        )
    
    async def _generate_fundamental_analysis(self, analysis_data) -> AIAnalysisResult:
        """生成基本面分析"""
        basic_info = analysis_data.basic_info
        realtime_quote = analysis_data.realtime_quote
        
        analysis_content = "🏢 基本面分析:\n\n"
        key_points = []
        
        # 股票基本信息
        stock_name = basic_info.get('name', analysis_data.stock_code)
        stock_type = basic_info.get('stock_type', '未知')
        listing_date = basic_info.get('listing_date', '')
        
        analysis_content += f"• 股票名称: {stock_name}\n"
        analysis_content += f"• 股票类型: {stock_type}\n"
        if listing_date:
            analysis_content += f"• 上市日期: {listing_date}\n"
        
        # 当前估值分析
        current_price = realtime_quote.get('cur_price', 0)
        if current_price > 0:
            analysis_content += f"• 当前价格: {current_price:.2f}\n"
            
            # 简单的估值判断（实际应该基于更多财务数据）
            if current_price < 10:
                key_points.append("股价相对较低，可能存在价值发现机会")
            elif current_price > 50:
                key_points.append("股价较高，需关注估值合理性")
        
        # 成交活跃度
        volume = realtime_quote.get('volume', 0)
        turnover = realtime_quote.get('turnover', 0)
        
        if volume > 1000000:  # 100万股以上
            analysis_content += "• 成交活跃度: 活跃\n"
            key_points.append("成交量较大，市场关注度高")
        else:
            analysis_content += "• 成交活跃度: 一般\n"
        
        analysis_content += "\n📝 分析说明:\n"
        analysis_content += "基本面分析需要更多财务数据支持，\n"
        analysis_content += "建议查阅最新财报和行业研究报告。"
        
        return AIAnalysisResult(
            stock_code=analysis_data.stock_code,
            analysis_type='fundamental',
            analysis_content=analysis_content,
            key_points=key_points,
            recommendation="需要更多财务数据进行深入分析",
            confidence_level=0.4,
            risk_level='中等',
            target_price_range=None,
            holding_period=None,
            generated_time=datetime.now()
        )
    
    async def _generate_capital_flow_analysis(self, analysis_data) -> AIAnalysisResult:
        """生成资金流向分析"""
        analysis_content = "💰 资金流向分析:\n\n"
        key_points = []
        
        # 这里应该分析资金流向数据
        # 目前使用模拟数据
        analysis_content += "• 主力资金: 数据获取中...\n"
        analysis_content += "• 散户资金: 数据获取中...\n"
        analysis_content += "• 北向资金: 数据获取中...\n\n"
        
        analysis_content += "📝 说明:\n"
        analysis_content += "资金流向分析功能正在开发中，\n"
        analysis_content += "将在后续版本中提供详细的资金流向数据。"
        
        key_points.append("资金流向数据待完善")
        
        return AIAnalysisResult(
            stock_code=analysis_data.stock_code,
            analysis_type='capital_flow',
            analysis_content=analysis_content,
            key_points=key_points,
            recommendation="等待资金流向数据完善",
            confidence_level=0.3,
            risk_level='中等',
            target_price_range=None,
            holding_period=None,
            generated_time=datetime.now()
        )
    
    async def _generate_sector_comparison(self, analysis_data) -> AIAnalysisResult:
        """生成同行对比分析"""
        analysis_content = "🏭 同行对比分析:\n\n"
        key_points = []
        
        analysis_content += "• 行业地位: 分析中...\n"
        analysis_content += "• 竞争优势: 分析中...\n"
        analysis_content += "• 估值对比: 分析中...\n\n"
        
        analysis_content += "📝 说明:\n"
        analysis_content += "同行对比分析需要获取行业数据，\n"
        analysis_content += "将在后续版本中提供详细对比。"
        
        key_points.append("同行对比功能开发中")
        
        return AIAnalysisResult(
            stock_code=analysis_data.stock_code,
            analysis_type='sector_comparison',
            analysis_content=analysis_content,
            key_points=key_points,
            recommendation="等待同行对比数据",
            confidence_level=0.3,
            risk_level='中等',
            target_price_range=None,
            holding_period=None,
            generated_time=datetime.now()
        )
    
    async def _generate_risk_assessment(self, analysis_data) -> AIAnalysisResult:
        """生成风险评估"""
        realtime_quote = analysis_data.realtime_quote
        indicators = analysis_data.technical_indicators
        
        analysis_content = "⚠️ 风险评估:\n\n"
        key_points = []
        
        # 价格波动风险
        amplitude = realtime_quote.get('amplitude', 0)
        if amplitude > 5:
            key_points.append(f"日内振幅{amplitude:.1f}%，波动较大")
            analysis_content += f"• 价格波动: 高 (振幅{amplitude:.1f}%)\n"
            risk_level = '高'
        elif amplitude > 3:
            analysis_content += f"• 价格波动: 中等 (振幅{amplitude:.1f}%)\n"
            risk_level = '中等'
        else:
            analysis_content += f"• 价格波动: 低 (振幅{amplitude:.1f}%)\n"
            risk_level = '低'
        
        # 技术指标风险
        rsi = indicators.get('rsi', 50)
        if rsi > 70:
            key_points.append("RSI超买，存在回调风险")
            analysis_content += "• 技术指标: 超买风险\n"
        elif rsi < 30:
            analysis_content += "• 技术指标: 超卖，风险相对较低\n"
        else:
            analysis_content += "• 技术指标: 正常范围\n"
        
        # 流动性风险
        volume = realtime_quote.get('volume', 0)
        if volume < 100000:  # 10万股以下
            key_points.append("成交量较小，存在流动性风险")
            analysis_content += "• 流动性风险: 较高\n"
        else:
            analysis_content += "• 流动性风险: 较低\n"
        
        # 综合风险评级
        analysis_content += f"\n🎯 综合风险等级: {risk_level}\n"
        
        # 风险建议
        if risk_level == '高':
            recommendation = "风险较高，建议谨慎投资，设置止损"
            confidence = 0.8
        elif risk_level == '中等':
            recommendation = "风险中等，建议适量投资，密切关注"
            confidence = 0.6
        else:
            recommendation = "风险较低，可适当关注投资机会"
            confidence = 0.5
        
        return AIAnalysisResult(
            stock_code=analysis_data.stock_code,
            analysis_type='risk_assessment',
            analysis_content=analysis_content,
            key_points=key_points,
            recommendation=recommendation,
            confidence_level=confidence,
            risk_level=risk_level,
            target_price_range=None,
            holding_period=None,
            generated_time=datetime.now()
        )
    
    async def generate_basic_analysis(self) -> None:
        """生成基础分析总览"""
        try:
            analysis_data = self.analysis_data_manager.get_current_analysis_data()
            if not analysis_data:
                return
            
            # 生成综合分析
            basic_analysis = await self._generate_comprehensive_analysis(analysis_data)
            await self.add_ai_message(basic_analysis, 'comprehensive')
            
        except Exception as e:
            self.logger.error(f"生成基础分析失败: {e}")
    
    async def _generate_comprehensive_analysis(self, analysis_data) -> str:
        """生成综合分析"""
        try:
            stock_name = analysis_data.basic_info.get('name', analysis_data.stock_code)
            realtime_quote = analysis_data.realtime_quote
            indicators = analysis_data.technical_indicators
            
            analysis = f"📈 {stock_name} 综合分析:\n\n"
            
            # 当前价格信息
            current_price = realtime_quote.get('cur_price', 0)
            change_rate = realtime_quote.get('change_rate', 0)
            
            if current_price > 0:
                trend_emoji = "📈" if change_rate > 0 else "📉" if change_rate < 0 else "➡️"
                analysis += f"💰 当前价格: {current_price:.2f} {trend_emoji} {change_rate:+.2f}%\n\n"
            
            # 技术指标概览
            analysis += "🔍 技术指标概览:\n"
            
            rsi = indicators.get('rsi', 0)
            if rsi > 0:
                if rsi > 70:
                    analysis += f"• RSI: {rsi:.1f} (超买区域) ⚠️\n"
                elif rsi < 30:
                    analysis += f"• RSI: {rsi:.1f} (超卖区域) 📢\n"
                else:
                    analysis += f"• RSI: {rsi:.1f} (正常区间) ✅\n"
            
            # MACD状态
            macd_data = indicators.get('macd', {})
            dif = macd_data.get('dif', 0)
            dea = macd_data.get('dea', 0)
            
            if dif > dea:
                analysis += "• MACD: 金叉状态，动能向上 📈\n"
            else:
                analysis += "• MACD: 死叉状态，动能向下 📉\n"
            
            # 价格趋势
            price_trend = indicators.get('price_trend', '无明确趋势')
            analysis += f"• 价格趋势: {price_trend}\n"
            
            # 成交量状态
            volume_trend = indicators.get('volume_trend', '量能平稳')
            analysis += f"• 成交量: {volume_trend}\n\n"
            
            # 初步建议
            analysis += "💡 初步建议:\n"
            
            if rsi < 30 and dif > dea:
                analysis += "技术面显示超卖反弹信号，可适度关注\n"
            elif rsi > 70:
                analysis += "技术面显示超买状态，建议谨慎追高\n"
            else:
                analysis += "技术面信号不明确，建议观望为主\n"
            
            analysis += "\n🎛️ 快捷分析:\n"
            analysis += "[F1]技术分析 [F2]基本面 [F3]资金面 [F4]同行对比 [F5]风险评估\n"
            analysis += "\n💭 有任何问题都可以直接提问哦！"
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"生成综合分析失败: {e}")
            return "生成分析时出现错误，请稍后重试。"
    
    async def _generate_help_message(self) -> str:
        """生成帮助信息"""
        help_text = """🔧 AI分析助手使用指南:

📝 直接提问:
• "这只股票适合长期持有吗？"
• "当前技术指标怎么样？"
• "有什么风险需要注意？"

🎛️ 快捷功能:
• F1 - 技术分析 (RSI, MACD, 均线等)
• F2 - 基本面分析 (估值, 财务等)
• F3 - 资金面分析 (主力资金流向)
• F4 - 同行对比 (行业地位对比)
• F5 - 风险评估 (风险等级评估)

💡 使用技巧:
• 可以询问具体的技术指标
• 可以询问投资建议和持有期
• 可以询问止损和目标价位
• 输入 '?' 随时查看此帮助

🤖 我会根据实时数据为您提供专业的投资分析，但请注意投资有风险，决策需谨慎！"""
        
        return help_text
    
    async def _generate_investment_advice(self) -> str:
        """生成投资建议"""
        try:
            analysis_data = self.analysis_data_manager.get_current_analysis_data()
            if not analysis_data:
                return "抱歉，当前没有可分析的股票数据。"
            
            stock_name = analysis_data.basic_info.get('name', analysis_data.stock_code)
            indicators = analysis_data.technical_indicators
            realtime_quote = analysis_data.realtime_quote
            
            advice = f"🎯 {stock_name} 投资建议:\n\n"
            
            # 基于技术指标的建议
            rsi = indicators.get('rsi', 50)
            macd_data = indicators.get('macd', {})
            dif = macd_data.get('dif', 0)
            dea = macd_data.get('dea', 0)
            
            # 风险等级评估
            current_price = realtime_quote.get('cur_price', 0)
            amplitude = realtime_quote.get('amplitude', 0)
            
            if amplitude > 5:
                risk_desc = "高风险"
                risk_emoji = "🔴"
            elif amplitude > 3:
                risk_desc = "中等风险"
                risk_emoji = "🟡"
            else:
                risk_desc = "低风险"
                risk_emoji = "🟢"
            
            advice += f"📊 技术面评估:\n"
            advice += f"• RSI: {rsi:.1f} - {'超买' if rsi > 70 else '超卖' if rsi < 30 else '正常'}\n"
            advice += f"• MACD: {'金叉' if dif > dea else '死叉'}信号\n"
            advice += f"• 风险等级: {risk_emoji} {risk_desc}\n\n"
            
            # 投资建议
            advice += "💰 投资建议:\n"
            
            if rsi < 30 and dif > dea and amplitude < 5:
                advice += "✅ 适合关注: 技术面偏向积极，风险可控\n"
                advice += "📅 建议持有期: 中短期 (1-3个月)\n"
                advice += "🎯 策略: 分批建仓，设置止损\n"
            elif rsi > 70:
                advice += "⚠️ 谨慎追高: 存在技术面调整风险\n"
                advice += "📅 建议: 等待回调机会\n"
                advice += "🎯 策略: 观望为主，不建议追高\n"
            else:
                advice += "➡️ 中性观望: 技术信号不明确\n"
                advice += "📅 建议: 等待明确信号\n"
                advice += "🎯 策略: 保持关注，伺机而动\n"
            
            advice += "\n⚠️ 风险提示:\n"
            advice += "• 投资有风险，入市需谨慎\n"
            advice += "• 建议分散投资，控制仓位\n"
            advice += "• 密切关注市场变化和公司基本面\n"
            advice += "• 设置合理的止损和止盈点"
            
            return advice
            
        except Exception as e:
            self.logger.error(f"生成投资建议失败: {e}")
            return "生成投资建议时出现错误，请稍后重试。"
    
    async def _generate_price_analysis(self) -> str:
        """生成价格分析"""
        try:
            analysis_data = self.analysis_data_manager.get_current_analysis_data()
            if not analysis_data:
                return "抱歉，当前没有可分析的股票数据。"
            
            realtime_quote = analysis_data.realtime_quote
            indicators = analysis_data.technical_indicators
            
            current_price = realtime_quote.get('cur_price', 0)
            high_price = realtime_quote.get('high_price', 0)
            low_price = realtime_quote.get('low_price', 0)
            
            analysis = "💹 价格分析:\n\n"
            
            if current_price > 0:
                analysis += f"📊 今日价格区间:\n"
                analysis += f"• 最高价: {high_price:.2f}\n"
                analysis += f"• 最低价: {low_price:.2f}\n"
                analysis += f"• 当前价: {current_price:.2f}\n\n"
                
                # 价格位置分析
                if high_price > low_price:
                    price_position = (current_price - low_price) / (high_price - low_price)
                    if price_position > 0.8:
                        analysis += "📈 当前价格接近今日高点，注意高位风险\n"
                    elif price_position < 0.2:
                        analysis += "📉 当前价格接近今日低点，可能存在支撑\n"
                    else:
                        analysis += "➡️ 当前价格处于今日中位区间\n"
                
                # 基于技术指标的目标价预测（简化版）
                ma20 = indicators.get('ma20', current_price)
                if ma20 > 0:
                    analysis += f"\n🎯 参考价位:\n"
                    analysis += f"• 20日均线: {ma20:.2f} (重要支撑/阻力)\n"
                    
                    if current_price > ma20:
                        target_high = current_price * 1.05
                        support = ma20
                        analysis += f"• 上方目标: {target_high:.2f} (5%涨幅)\n"
                        analysis += f"• 下方支撑: {support:.2f}\n"
                    else:
                        resistance = ma20
                        target_low = current_price * 0.95
                        analysis += f"• 上方阻力: {resistance:.2f}\n"
                        analysis += f"• 下方目标: {target_low:.2f} (5%跌幅)\n"
            
            analysis += "\n⚠️ 价格预测仅供参考，实际走势受多种因素影响"
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"生成价格分析失败: {e}")
            return "生成价格分析时出现错误，请稍后重试。"
    
    async def _generate_general_response(self, question: str) -> str:
        """生成通用回复"""
        responses = [
            f"关于您的问题「{question}」，我需要更多具体信息才能给出准确分析。",
            "您可以尝试使用快捷功能键获取详细分析，或者询问更具体的问题。",
            "比如您可以问：\n• 技术指标怎么样？\n• 适合长期投资吗？\n• 有什么风险？"
        ]
        
        return "\n".join(responses)
    
    def _get_cached_analysis(self, stock_code: str, analysis_type: str) -> Optional[AIAnalysisResult]:
        """获取缓存的分析结果"""
        try:
            if stock_code not in self.analysis_cache:
                return None
            
            if analysis_type not in self.analysis_cache[stock_code]:
                return None
            
            cached_result = self.analysis_cache[stock_code][analysis_type]
            
            # 检查缓存是否过期
            cache_age = (datetime.now() - cached_result.generated_time).total_seconds() / 3600
            if cache_age > AI_ANALYSIS_CONFIG['analysis_cache_hours']:
                return None
            
            return cached_result
            
        except Exception as e:
            self.logger.error(f"获取缓存分析失败: {e}")
            return None
    
    def _cache_analysis_result(self, result: AIAnalysisResult):
        """缓存分析结果"""
        try:
            if result.stock_code not in self.analysis_cache:
                self.analysis_cache[result.stock_code] = {}
            
            self.analysis_cache[result.stock_code][result.analysis_type] = result
            
        except Exception as e:
            self.logger.error(f"缓存分析结果失败: {e}")
    
    def _format_analysis_result(self, result: AIAnalysisResult) -> str:
        """格式化分析结果"""
        try:
            formatted = f"🤖 {ANALYSIS_TYPES[result.analysis_type]}结果:\n\n"
            formatted += result.analysis_content
            
            if result.key_points:
                formatted += "\n\n🔍 关键要点:\n"
                for point in result.key_points:
                    formatted += f"• {point}\n"
            
            formatted += f"\n💡 建议: {result.recommendation}\n"
            formatted += f"📊 置信度: {result.confidence_level:.0%}"
            
            if result.risk_level:
                formatted += f" | 风险等级: {result.risk_level}"
            
            return formatted
            
        except Exception as e:
            self.logger.error(f"格式化分析结果失败: {e}")
            return "格式化分析结果时出现错误"
    
    def get_dialog_history(self, limit: int = None) -> List[DialogMessage]:
        """获取对话历史"""
        if limit:
            return self.dialog_history[-limit:]
        return self.dialog_history.copy()
    
    def get_analysis_status(self) -> Dict[str, Any]:
        """获取分析状态"""
        return {
            'current_stock_code': self.current_stock_code,
            'is_analyzing': self.is_analyzing,
            'last_analysis_time': self.last_analysis_time,
            'dialog_count': len(self.dialog_history),
            'cached_analysis_count': sum(len(analyses) for analyses in self.analysis_cache.values())
        }
    
    async def clear_dialog_history(self):
        """清空对话历史"""
        try:
            self.dialog_history.clear()
            self.logger.info("对话历史已清空")
            
        except Exception as e:
            self.logger.error(f"清空对话历史失败: {e}")
    
    async def cleanup(self):
        """清理AI分析管理器"""
        try:
            self.dialog_history.clear()
            self.analysis_cache.clear()
            self.current_stock_code = None
            self.is_analyzing = False
            self.last_analysis_time = None
            
            self.logger.info("AIAnalysisManager 清理完成")
            
        except Exception as e:
            self.logger.error(f"AIAnalysisManager 清理失败: {e}")