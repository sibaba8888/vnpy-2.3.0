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

class XlsTradeStrategy(CtaTemplate):
    """"""
    author = "xls"


    fixed_size = 50
    long_period = 90
    middle_period = 30
    short_period = 10
    ma_distance = 0.01     #  the distance of 3 ma in period
    dis_ma_close = 0.01    # the close price distance with ma
    stop_loss = 0.02
    break_value = 4   # break  price  即  now.close - last.close>break_value  需要考虑 价格跳动，比如BU 一次为5
    draw_back = 0.4  #  从最高点回落百分之几
    fun_period = 15

    parameters = ["long_period", "middle_period",
                  "short_period", "ma_distance",
                  "dis_ma_close", "stop_loss", "fun_period"]
    variables = ["slop_vlaue"]

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

        if self.pos == 0:
            if self.ema5_long[-1]>self.emad_long[-2]:
                self.buy(bar.close_price+5, 1)
            if self.ema5_long[-1]<self.emad_long[-2]:
                self.short(bar.close_price-5, 1)
        if self.pos > 0:
            if self.ema5_long[-1]<self.emad_long[-2]:
                self.sell(bar.close_price-5, 1)
        if self.pos < 0:
            if self.ema5_long[-1]<self.emad_long[-2]:
                self.cover(bar.close_price+5, abs(self.pos))
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
    def on_account(self,account):
        """
        账户信息balance:总资金, available:可用资金, commission:今日手续费，pre_balance上个交易日总资金 实盘需要改
        """
        self.account = account
        self.available_capital = self.account.get('available')
        self.xls_pos = self.account.get("traded_pos")
        self.open = [i[1].price for i in self.xls_pos if i[1].offset==Offset.OPEN]
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
