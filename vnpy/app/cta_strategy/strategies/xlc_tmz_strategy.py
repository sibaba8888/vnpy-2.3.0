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

class XlcTmzStrategy(CtaTemplate):
    """"""
    author = "xlc"

    long_period = 90
    middle_period = 30
    short_period = 10
    stop_loss = 0.02
    atr_window = 0
    atr_value = 0
    intra_trade_high = 0
    intra_trade_low = 0
    parameters = ["long_period", "middle_period",
                  "short_period",  "stop_loss"]
    variables = ["intra_trade_high", "intra_trade_low"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.inited = False

        self.available_capital = 0
        self.buy_method = None
        self.xls_pos = None
        self.open = []
        self.open_method = None
        # self.pos_change = []
        #self.maxpos = 0
        #self.max_min_close = 0
        #self.move_max_min_close = 0
        self.list_account = []
        self.get_account = {}
        self.dict_account = {}


        self.bg5 = BarGenerator(self.on_bar, 5, self.on_5min_bar)
        self.am5 = ArrayManager()

        self.bg30 = BarGenerator(self.on_bar, 30, self.on_30min_bar)
        self.am30 = XlsArrayManager()
        self.bgh = BarGenerator(self.on_bar, 1, self.on_hour_bar, interval=Interval.HOUR)
        self.amh = XlsArrayManager()
        self.bgd = BarGenerator(self.on_bar, 1, self.on_daily_bar, interval=Interval.DAILY)
        self.amd = XlsArrayManager()

        #self.last_bar = None

        #self.ema5_short = None
        #self.ema5_middle = None
        #self.ema5_long = None

        #self.ema15_short = None
        #self.ema15_middle = None
        #self.ema15_long = None

        #self.ema30_short = None
        #self.ema30_middle = None
        #self.ema30_long = None

        #self.emah_short = None
        #self.emah_middle = None
        self.emah_long = None

        self.emad_short = None
        #self.emad_middle = None
        #self.emad_long = None


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

        self.emah_long = self.amh.ema(self.long_period, array=True)
        #self.emah_middle = self.amh.ema(self.middle_period, array=True)
        #self.emah_short = self.amh.ema(self.short_period, array=True)

        self.emad_long = self.amd.ema(self.long_period, array=True)
        #self.emad_middle = self.amd.ema(self.middle_period, array=True)
        #self.emad_short = self.amd.ema(self.short_period, array=True)

        # 均线趋势向上，下,90d. 30d.10d.90h.30h.10h向上
        #trend_d = np.array([[self.emad_long[-1] - self.emad_long[-2], self.emad_middle[-1] - self.emad_middle[-2],
                             #self.emad_short[-1] - self.emad_short[-2]]])
        trend_d_close = np.array([self.emad_long[-1] - self.emad_long[-2], self.emad_long[-2] - self.emad_long[-3],
                                   self.emad_long[-3] - self.emad_long[-4]])

        # 买多，卖空价格与前面几根K线均值大小判断，用于过滤

        # 各周期均线靠的比较近


        if self.pos == 0:
            # 买多
            if np.all(trend_d_close > 0) and bar.close_price > self.emad_long[-1]:
                if bar.close_price > self.amd.high_array[-2]:
                    self.buy(bar.close_price+5, 1)
                    self.open_method = "open1"
                elif bar.close_price > self.amh.high_array[-2]:
                    self.buy(bar.close_price+5, 1)
                    self.open_method = "open2"
            # 卖空
            if np.all(trend_d_close < 0) and bar.close_price < self.emad_long[-1]:
                if bar.close_price < self.amd.low_array[-2]:
                    self.short(bar.close_price-5, 1)
                    self.open_method = 'open3'
                    self.intra_trade_low = bar.close_price
                elif bar.close_price < self.amh.low_array[-2]:
                    self.short(bar.close_price-5, 1)
                    self.open_method = "open4"
                    self.intra_trade_low = bar.close_price

            # self.pos_change = []
            # self.max_min_close = bar.close_price


        if self.pos > 0:
            self.intra_trade_high = max(self.intra_trade_high, bar.high_price)
            self.intra_trade_low = bar.low_price

            if self.dict_account.get("open1"):
                if bar.close_price < self.amd.low_array[-2]:
                    self.sell(bar.close_price-5, self.pos)
                    self.dict_account['open1'] = None
                elif self.intra_trade_high > self.dict_account.get("open1") + self.atr_value:
                    if bar.close_price < self.dict_account.get("open1") + 5 or bar.close_price < self.amh.low_array[-2]:
                        self.sell(bar.close_price - 5, self.pos)
                        self.dict_account['open1'] = None

            elif self.dict_account.get("open2"):
                if bar.close_price < self.amh.low_array[-2]:
                    self.sell(bar.close_price-5,self.pos)
                    self.dict_account['open2'] = None
                elif self.intra_trade_high > self.dict_account.get("open2") + self.atr_value:
                    if bar.close_price < self.dict_account.get("open2") + 5 or bar.close_price < self.amh.low_array[-2]:
                        self.sell(bar.close_price - 5, self.pos)
                        self.dict_account['open2'] = None



        if self.pos < 0:
            self.intra_trade_low = min(self.intra_trade_low, bar.low_price)
            self.intra_trade_high = bar.high_price

            if self.dict_account.get("open3"):
                if bar.close_price > self.amd.low_array[-2]:
                    self.cover(bar.close_price + 5, abs(self.pos))
                    self.dict_account['open3'] = None
                elif self.intra_trade_low < self.dict_account.get("open3") - self.atr_value:
                    if bar.close_price > self.dict_account.get("open3") - 5 or bar.close_price > self.amh.high_array[-2]:
                        self.cover(bar.close_price + 5, abs(self.pos))
                        self.dict_account['open3'] = None

            elif self.dict_account.get("open4"):
                if bar.close_price > self.amh.low_array[-2]:
                    self.cover(bar.close_price + 5, abs(self.pos))
                    self.dict_account['open4'] = None
                elif self.intra_trade_low < self.dict_account.get("open4") - self.atr_value:
                    if bar.close_price > self.dict_account.get("open4") - 5 or bar.close_price > self.amh.high_array[-2]:
                        self.cover(bar.close_price + 5, abs(self.pos))
                        self.dict_account['open4'] = None

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

        if self.xls_pos:
            # self.dict_account ={"1": {"method":self.open_method, "price":self.xls_pos[-1][1].price}}
            self.dict_account[self.open_method] = self.xls_pos[-1][1].price
            # self.get_account = {"method": self.open_method, "price": self.xls_pos[-1][1].price}
            # self.dict_account[self.get_account.get("method")] = self.get_account
            # self.get_account["open"]= self.dict_account.get("price")
            # self.list_account.append({self.get_account["method"]: self.dict_account.get("price")})
        self.open = [i[1].price for i in self.xls_pos if i[1].offset==Offset.OPEN]


    # account = {'available': self.xls_capital, 'cpos':self.strategy.pos, 'traded_pos': self.xls_pos}
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
