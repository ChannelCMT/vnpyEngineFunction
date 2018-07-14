from __future__ import division

from vnpy.trader.vtConstant import EMPTY_STRING, EMPTY_FLOAT
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarGenerator,
                                                     ArrayManager)
import talib as ta

########################################################################
# 策略继承CtaTemplate
class MultiFrameMaStrategy(CtaTemplate):
    """双指数均线策略Demo"""
    className = 'MultiFrameMaStrategy'
    author = u'用Python的交易员'

    # 策略交易标的的列表
    symbolList = []         # 初始化为空
    posDict = {}  # 初始化仓位字典

    # 多空仓位
    Longpos = EMPTY_STRING        # 多头品种仓位
    Shortpos = EMPTY_STRING       # 空头品种仓位

    # 策略参数
    fastWindow = 40     # 快速均线参数
    slowWindow = 70     # 慢速均线参数
    initDays = 1       # 初始化数据所用的天数

    # 策略变量
    fastMa0 = EMPTY_FLOAT   # 当前最新的快速EMA
    fastMa1 = EMPTY_FLOAT   # 上一根的快速EMA
    slowMa0 = EMPTY_FLOAT   # 当前最新的慢速EMA
    slowMa1 = EMPTY_FLOAT   # 上一根的慢速EMA
    maTrend = 0             # 均线趋势，多头1，空头-1

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'symbolList',
                 'fastWindow',
                 'slowWindow']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'posDict',
               'fastMa0',
               'fastMa1',
               'slowMa0',
               'slowMa1',
               'maTrend']

    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['posDict']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):

        # 首先找到策略的父类（就是类CtaTemplate），然后把DoubleMaStrategy的对象转换为类CtaTemplate的对象
        super(MultiFrameMaStrategy, self).__init__(ctaEngine, setting)

        # 生成仓位记录的字典
        symbol = self.symbolList[0]
        self.Longpos = symbol.replace('.','_')+"_LONG"
        self.Shortpos = symbol.replace('.','_')+"_SHORT"


        self.bg60 = BarGenerator(self.onBar, 60, self.on60MinBar)
        self.bg60Dict = {
            sym: self.bg60
            for sym in self.symbolList
        }


        self.bg15 = BarGenerator(self.onBar, 15, self.on15MinBar)
        self.bg15Dict = {
            sym: self.bg15
            for sym in self.symbolList
        }

        # 生成Bar数组
        self.am60Dict = {
            sym: ArrayManager(size=self.slowWindow+10)
            for sym in self.symbolList
        }

        self.am15Dict = {
            sym: ArrayManager(size=self.slowWindow+10)
            for sym in self.symbolList
        }

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略初始化')
        # 初始化仓位字典
        if not self.posDict:
            for symbolPos in [self.Longpos,self.Shortpos]:
                self.posDict[symbolPos] = 0

        # 初始化历史数据天数
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略启动')
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略停止')
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.cancelAll()
        symbol = bar.vtSymbol
        # 基于60分钟判断趋势过滤，因此先更新
        bg60 = self.bg60Dict[symbol]
        bg60.updateBar(bar)

        # 基于15分钟判断
        bg15 = self.bg15Dict[symbol]
        bg15.updateBar(bar)

    #----------------------------------------------------------------------
    def on60MinBar(self, bar):
        """60分钟K线推送"""
        symbol = bar.vtSymbol
        am60 = self.am60Dict[symbol]
        am60.updateBar(bar)

        if not am60.inited:
            return

        # 计算均线并判断趋势
        fastMa = ta.MA(am60.close, self.fastWindow)
        slowMa = ta.MA(am60.close, self.slowWindow)
#         print(fastMa)

        if fastMa[-1] > slowMa[-1]:
            self.maTrend = 1
        else:
            self.maTrend = -1

    #----------------------------------------------------------------------
    def on15MinBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.cancelAll() # 全部撤单
        symbol = bar.vtSymbol


        am15 = self.am15Dict[symbol]
        am15.updateBar(bar)
        if not am15.inited:
            return

        fastMa = ta.EMA(am15.close, self.fastWindow)

        self.fastMa0 = fastMa[-1]
        self.fastMa1 = fastMa[-2]

        slowMa = ta.EMA(am15.close, self.slowWindow)
        self.slowMa0 = slowMa[-1]
        self.slowMa1 = slowMa[-2]

        # 判断买卖
        crossOver = self.fastMa0>self.fastMa1 and self.slowMa0>self.slowMa1     # 均线上涨
        crossBelow = self.fastMa0<self.fastMa1 and self.slowMa0<self.slowMa1    # 均线下跌



        # 金叉和死叉的条件是互斥
        if crossOver and self.maTrend==1:
            # 如果金叉时手头没有持仓，则直接做多
            if (self.posDict[self.Longpos]==0) and (self.posDict[self.Shortpos]==0):
                self.buy(symbol,bar.close, 1)
            # 如果有空头持仓，则先平空，再做多
            elif self.posDict[self.Shortpos] == 1:
                self.cover(symbol,bar.close, 1)
                self.buy(symbol,bar.close, 1)

        # 死叉和金叉相反
        elif crossBelow and self.maTrend==-1:
            if (self.posDict[self.Longpos]==0) and (self.posDict[self.Shortpos]==0):
                self.short(symbol,bar.close, 1)
            elif self.posDict[self.Longpos] == 1:
                self.sell(symbol,bar.close, 1)
                self.short(symbol,bar.close, 1)


        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
#         print(self.posDict)
        pass

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass

from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine, OptimizationSetting, MINUTE_DB_NAME
import pandas as pd

def backTest(startDate, endDate):
    engine = BacktestingEngine()
    engine.setBacktestingMode(engine.BAR_MODE)    # 设置引擎的回测模式为K线
    engine.setDatabase(MINUTE_DB_NAME)  # 设置使用的历史数据库

    engine.setStartDate(startDate,initDays=1)               # 设置回测用的数据起始日期
    engine.setEndDate(endDate)

    engine.setSlippage(0.2)     # 设置滑点为股指1跳
    engine.setRate(1/1000)   # 设置手续费万0.3
    engine.setSize(1)         # 设置股指合约大小
    engine.setPriceTick(0.01)    # 设置股指最小价格变动
    engine.setCapital(1000000)  # 设置回测本金
    engine.initStrategy(MultiFrameMaStrategy, {'symbolList':['tBTCUSD:bitfinex']})
    engine.setCapital(100000)
    engine.runBacktesting()
    # 优化配置
    setting = OptimizationSetting()                 # 新建一个优化任务设置对象
    setting.setOptimizeTarget('totalNetPnl')        # 设置优化排序的目标是策略净盈利
    setting.addParameter('fastWindow', 20, 40, 10)    # 增加第一个优化参数atrLength，起始12，结束20，步进2
    setting.addParameter('slowWindow', 50, 80, 10)        # 增加第二个优化参数atrMa，起始20，结束30，步进5
    setting.addParameter('symbolList', ['tBTCUSD:bitfinex'])

    # 执行多进程优化
    import time
    import json
    start = time.time()
    resultList = engine.runParallelOptimization(MultiFrameMaStrategy, setting)
    # resultList = engine.runOptimization(MultiFrameMaStrategy, setting)
    print('耗时：%s' %(time.time()-start))
    performance = pd.DataFrame(resultList).sort_values(1,  ascending=False).iloc[0:2]
    bestParameter = performance.iloc[0,0].replace("'",'"')
    newParameter = json.loads(bestParameter)

    return newParameter

def stepParameterDF(startDate, endDate):
    allBestParameter = {endDate: backTest(startDate, endDate) for startDate, endDate in tuple(zip(startDate, endDate))}
    stepParameter= pd.DataFrame(allBestParameter).T
    stepParameter.index = pd.Index(map(lambda x: datetime.strptime(str(x),"%Y%m%d") , stepParameter.index))
    return stepParameter

from datetime import date,timedelta, datetime

def step_optimize(startTime, backTestDay, paraDate, stepDate):
    #startDate:开始时间为日期, backTestDay: 回测的总天数, paraDate： 用于优化参数的时间长度, stepDate: 用于回测的时间长度
    startDate = [str(startTime+timedelta(days=t)).replace('-','') for t in range(0,backTestDay,stepDate)]
    endDate = [str(startTime+timedelta(days=t)).replace('-','') for t in range(paraDate, backTestDay+paraDate, stepDate)]
    stepParameter = stepParameterDF(startDate, endDate)
    return stepParameter

if __name__ == '__main__':
    stepParameter = step_optimize(date(2018,1,1), 150, 50, 20)
    stepParameter.to_excel('stepParameter.xlsx')