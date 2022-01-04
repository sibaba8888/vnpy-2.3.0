from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
    XlsArrayManager
)
from vnpy.trader.constant import Interval, Offset
import numpy as np
from datetime import time

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn import linear_model

class XlcDoublemaStrategy(CtaTemplate):
    """"""
    author = "xlc"



    long_period = 60
    middle_period = 30
    short_period = 10
    ma_distance = 10     #  the distance of 3 ma in period
    k_distance = 100

    parameters = ["long_period", "middle_period",
                  "short_period", "ma_distance", "k_distance"
                  ]
    variables = []
# k线在两根线中间，黄色绿色距离越来越小，然后黄色在绿色下面，两个都是凹函数，方向向上
# 定义长周期均线，短周期均线，定义两均线前6个值，6个值差逐渐变小，最后一个差值小于某个值，方向向上，凹函数，中均线小于长均线，当前值位于两均线之间；

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.inited = False

        self.available_capital = 0
        self.buy_method = None
        self.xls_pos = None
        self.open = []
        self.open_method = None
        self.pos_change = []
        self.maxpos = 0
        self.max_min_close = 0
        self.move_max_min_close = 0

        self.bg5 = BarGenerator(self.on_bar, 5, self.on_5min_bar)
        self.am5 = ArrayManager()

        self.bg30 = BarGenerator(self.on_bar, 30, self.on_30min_bar)
        self.am30 = XlsArrayManager()
        self.bgh = BarGenerator(self.on_bar, 1, self.on_hour_bar, interval=Interval.HOUR)
        self.amh = XlsArrayManager()
        self.bgd = BarGenerator(self.on_bar, 1, self.on_daily_bar, interval=Interval.DAILY)
        self.amd = XlsArrayManager()

        self.last_bar = None

        self.ema5_short = None
        self.ema5_middle = None
        self.ema5_long = None

        self.ema15_short = None
        self.ema15_middle = None
        self.ema15_long = None

        self.ema30_short = None
        self.ema30_middle = None
        self.ema30_long = None

        self.emah_short = None
        self.emah_middle = None
        self.emah_long = None

        self.emad_short = None
        self.emad_middle = None
        self.emad_long = None


    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        self.load_bar(120)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.bg5.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.bg5.update_bar(bar)
        self.bg30.update_bar(bar)
        self.bgh.update_bar(bar)
        self.bgd.update_bar(bar)

    def on_5min_bar(self, bar: BarData):
        self.am5.update_bar(bar)
        self.am30.update_bar(bar, finish=False)
        self.amh.update_bar(bar, finish=False)
        self.amd.update_bar(bar, finish=False)
        if not self.inited:
            return


        self.ema5_long = self.am5.ema(self.long_period, array=True)
        self.ema5_middle = self.am5.ema(self.middle_period, array=True)
        self.ema5_short = self.am5.ema(self.short_period, array=True)

        self.ema30_long = self.am30.ema(self.long_period, array=True)
        self.ema30_middle = self.am30.ema(self.middle_period, array=True)
        self.ema30_short = self.am30.ema(self.short_period, array=True)

        self.emah_long = self.amh.ema(self.long_period, array=True)
        self.emah_middle = self.amh.ema(self.middle_period, array=True)
        self.emah_short = self.amh.ema(self.short_period, array=True)

        self.emad_long = self.amd.ema(self.long_period, array=True)
        self.emad_middle = self.amd.ema(self.middle_period, array=True)
        self.emad_short = self.amd.ema(self.short_period, array=True)

        # k线在两根线中间，黄色绿色距离越来越小，然后黄色在绿色下面，两个都是凹函数，方向向上
        # 定义长周期均线，短周期均线，定义两均线前6个值，6个值差逐渐变小，最后一个差值小于某个值，方向向上，凹函数，中均线小于长均线，当前值位于两均线之间；
        trend_h_long = np.array([[self.emah_long[-1] - self.emah_long[-2], self.emah_long[-2] - self.emah_long[-3],
                   self.emah_long[-3] - self.emah_long[-4], self.emah_long[-4] - self.emah_long[-5],
                   self.emah_long[-5] - self.emah_long[-6], self.emah_long[-6] - self.emah_long[-7],
                   ]])
        trend_h_middle = np.array([[self.emah_middle[-1] - self.emah_middle[-2], self.emah_middle[-2] - self.emah_middle[-3],
                                  self.emah_middle[-3] - self.emah_middle[-4], self.emah_middle[-4] - self.emah_middle[-5],
                                  self.emah_middle[-5] - self.emah_middle[-6], self.emah_middle[-6] - self.emah_middle[-7],
                                  ]])

        if self.pos == 0:
            if np.all(trend_h_long > 0) and np.all(trend_h_middle > 0):   #均线向上
                if self.emah_middle[-1] < self.emah_long[-1]:      #中均线小于长均线
                    if self.emah_long[-1] - self.emah_middle[-1] < self.emah_long[-2] - self.emah_middle[-2] \
                           < self.emah_long[-3] - self.emah_middle[-3] < self.emah_long[-4] - self.emah_middle[-4]\
                        < self.emah_long[-5] - self.emah_middle[-5] < self.emah_long[-6] - self.emah_middle[-6]:     #均线距离越来越小
                        if 0 < self.emah_long[-1] - self.emah_middle[-1] < self.ma_distance:    # 均线距离小于多少值，单大于0
                            #if bar.close_price < self.ema5_long[-1]:
                            self.buy(bar.close_price+5, 2)
                            self.open_method = 'open1'

            self.pos_change = []
            self.max_min_close = bar.close_price

        if self.pos > 0:
            if self.open_method == 'open1':
                if bar.close_price > self.dict_account.get("price") + 3*self.k_distance or\
                        bar.close_price < self.dict_account.get("price") - self.k_distance:
                    self.sell(bar.close_price-5, self.pos)
                                                                                                    # elf.emad_middle[-1]

        self.put_event()



    def on_30min_bar(self, bar: BarData):

        self.am30.update_bar(bar, finish=True)
        if self.inited:
            self.ema30_long = self.am30.ema(self.long_period, array=True)
            self.ema30_middle = self.am30.ema(self.middle_period, array=True)
            self.ema30_short = self.am30.ema(self.short_period, array=True)
    def on_hour_bar(self, bar: BarData):

        self.amh.update_bar(bar, finish=True)
        if self.inited:
            self.emah_long = self.amh.ema(self.long_period, array=True)
            self.emah_middle = self.amh.ema(self.middle_period, array=True)
            self.emah_short = self.amh.ema(self.short_period, array=True)
    def on_daily_bar(self, bar: BarData):

        self.amd.update_bar(bar, finish=True)
        if self.inited:
            self.emad_long = self.amd.ema(self.long_period, array=True)
            self.emad_middle = self.amd.ema(self.middle_period, array=True)
            self.emad_short = self.amd.ema(self.short_period, array=True)
    def calculate_slope(self, ma):

        pass

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass

    def on_account(self, account):
        """
        账户信息balance:总资金, available:可用资金, commission:今日手续费，pre_balance上个交易日总资金 实盘需要改
        """
        self.account = account
        self.available_capital = self.account.get('available')
        self.xls_pos = self.account.get("traded_pos")
        if self.xls_pos:
            self.dict_account = {"method": self.open_method, "price": self.xls_pos[-1][1].price}
        self.open = [i[1].price for i in self.xls_pos if i[1].offset == Offset.OPEN]
    # def mechine_learning_data(self,bar:BarData):
    #     dt = bar.datetime
    #     close = bar.close_price
    #     close_ma_long = close - ema_long
    #     close_ma_middle = close - ema_middle
    #     close_ma_short = close - ema_short
    #
    #     close_ma5_long = close - ema5_long
    #     close_ma5_middle = close - ema5_middle
    #     close_ma5_short = close - ema5_short
    #
    #     close_ma15_long = close - ema15_long
    #     close_ma15_middle = close - ema15_middle
    #     close_ma15_short = close - ema15_short
    #
    #
    #     close_ma30_long = close - ema30_long
    #     close_ma30_middle = close - ema30_middle
    #     close_ma30_short = close - ema30_short
    #
    #
    #     close_mah_long = close - emah_long
    #     close_mah_middle = close - emah_middle
    #     close_mah_short = close - emah_short
    #
    #     close_mad_long = close - emad_long
    #     close_mad_middle = close - emad_middle
    #     close_mad_short = close - emad_short
    #
