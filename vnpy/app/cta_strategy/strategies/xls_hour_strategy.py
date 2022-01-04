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

class XlsHourStrategy(CtaTemplate):
    """"""
    author = "xls"


    fixed_size = 50
    long_period = 90
    middle_period = 30
    short_period = 10
    ma_distance = 0.01     #  the distance of 3 ma in period
    dis_ma_close = 0.01    # the close price distance with ma
    shock_area = 0.02     # the shock area
    max_dis_ma_close = 0.2
    stop_loss = 0.02
    stop_profit = 0.05
    break_value = 3   # break  price  即  now.close - last.close>break_value  需要考虑 价格跳动，比如BU 一次为5
    draw_back = 0.4  #  从最高点回落百分之几
    parameters = ["long_period", "middle_period",
                  "short_period", "ma_distance",
                  "dis_ma_close", "dis_ma_close", "stop_loss", "stop_profit", "shock_area"]
    slope = 0.1
    slope_period = 2
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
        self.max_min_10 = 0
        self.high_loc = 0
        self.low_loc = 0
        self.ema_array = []
        self.bg5 = BarGenerator(self.on_bar, 5, self.on_5min_bar)
        self.am5 = ArrayManager()

        self.bg15 = BarGenerator(self.on_bar, 15, self.on_15min_bar)
        self.am15 = XlsArrayManager()
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
        self.load_bar(110)

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
        self.bg15.update_bar(bar)
        self.bg30.update_bar(bar)
        self.bgh.update_bar(bar)
        self.bgd.update_bar(bar)

    def on_5min_bar(self, bar: BarData):
        if not self.inited:
            self.am5.update_bar(bar)
            self.am15.update_bar(bar, finish=False)
            self.am30.update_bar(bar, finish=False)
            self.amh.update_bar(bar, finish=False)
            self.amd.update_bar(bar, finish=False)
            # return
            return
        self.am5.update_bar(bar)
        self.am15.update_bar(bar, finish=False)
        self.am30.update_bar(bar, finish=False)
        self.amh.update_bar(bar, finish=False)
        self.amd.update_bar(bar, finish=False)

        self.ema5_long = self.am5.ema(self.long_period, array=True)
        self.ema5_middle = self.am5.ema(self.middle_period, array=True)
        self.ema5_short = self.am5.ema(self.short_period, array=True)

        self.ema15_long = self.am15.ema(self.long_period, array=True)
        self.ema15_middle = self.am15.ema(self.middle_period, array=True)
        self.ema15_short = self.am15.ema(self.short_period, array=True)

        self.ema30_long = self.am30.ema(self.long_period, array=True)
        self.ema30_middle = self.am30.ema(self.middle_period, array=True)
        self.ema30_short = self.am30.ema(self.short_period, array=True)

        self.emah_long = self.amh.ema(self.long_period, array=True)
        self.emah_middle = self.amh.ema(self.middle_period, array=True)
        self.emah_short = self.amh.ema(self.short_period, array=True)

        self.emad_long = self.amd.ema(self.long_period, array=True)
        self.emad_middle = self.amd.ema(self.middle_period, array=True)
        self.emad_short = self.amd.ema(self.short_period, array=True)

        price_open = bar.close_price > np.mean(self.am5.close_array[-6:-2]) + self.break_value
        price_close = bar.close_price < np.mean(self.am5.close_array[-6:-2]) - self.break_value

        trend_d = np.array([[self.emad_long[-1] - self.emad_long[-2], self.emad_middle[-1] - self.emad_middle[-2],
                             self.emad_short[-1] - self.emad_short[-2]]])
        trend_h = np.array([[self.emah_long[-1] - self.emah_long[-2], self.emah_middle[-1] - self.emah_middle[-2],
                             self.emah_short[-1] - self.emah_short[-2]]])
        trend_30min = np.array([[self.ema30_long[-1] - self.ema30_long[-2],
                                 self.ema30_middle[-1] - self.ema30_middle[-2],
                                 self.ema30_short[-1] - self.ema30_short[-2]]])
        trend_15min = np.array([[self.ema15_long[-1] - self.ema15_long[-2],
                                 self.ema15_middle[-1] - self.ema15_middle[-2],
                                 self.ema15_short[-1] - self.ema15_short[-2]]])
        trend_5min = np.array([[self.ema5_long[-1] - self.ema5_long[-2], self.ema5_middle[-1] - self.ema5_middle[-2],
                                self.ema5_short[-1] - self.ema5_short[-2]]])
        trend = np.concatenate((trend_h, trend_30min, trend_15min, trend_5min), axis=0)

        # == the bar  located  of ma ===== scaled

        bar5_position = np.array([[bar.close_price - self.ema5_long[-1], bar.close_price - self.ema5_middle[-1],
                                   bar.close_price - self.ema5_short[-1]]]) / bar.close_price
        bar15_position = np.array([[bar.close_price - self.ema15_long[-1], bar.close_price - self.ema15_middle[-1],
                                    bar.close_price - self.ema15_short[-1]]]) / bar.close_price
        bar30_position = np.array([[bar.close_price - self.ema30_long[-1], bar.close_price - self.ema30_middle[-1],
                                    bar.close_price - self.ema30_short[-1]]]) / bar.close_price
        barh_position = np.array([[bar.close_price - self.emah_long[-1], bar.close_price - self.emah_middle[-1],
                                   bar.close_price - self.emah_short[-1]]]) / bar.close_price
        bard_position = np.array([[bar.close_price - self.emad_long[-1], bar.close_price - self.emad_middle[-1],
                                   bar.close_price - self.emad_short[-1]]]) / bar.close_price

        position = np.concatenate((barh_position, bar30_position, bar15_position, bar5_position), axis=0)
        position_judge_long = np.all([barh_position < self.dis_ma_close * 2, bar30_position < self.dis_ma_close * 2, bar15_position < self.dis_ma_close*2,
                                      bar5_position < self.dis_ma_close*2])
        position_judge_short = np.all([barh_position > -self.dis_ma_close * 2, bar30_position > -self.dis_ma_close * 2, bar15_position > -self.dis_ma_close*2,
                                       bar5_position > -self.dis_ma_close*2])

        # the volume for period

        # ========ma distance=========
        dis_d = abs(np.array([[self.emad_long[-1] - self.emad_middle[-1], self.emad_long[-1] - self.emad_short[-1],
                               self.emad_middle[-1] - self.emad_short[-1]]])) / bar.close_price
        dis_h = abs(np.array([[self.emah_long[-1] - self.emah_middle[-1], self.emah_long[-1] - self.emah_short[-1],
                               self.emah_middle[-1] - self.emah_short[-1]]])) / bar.close_price
        dis_5min = abs(np.array([[self.ema5_long[-1] - self.ema5_middle[-1], self.ema5_long[-1] - self.ema5_short[-1],
                                  self.ema5_middle[-1] - self.ema5_short[-1]]])) / bar.close_price
        dis_15min = abs(np.array([[self.ema15_long[-1] - self.ema15_middle[-1],
                                   self.ema15_long[-1] - self.ema15_short[-1],
                                   self.ema15_middle[-1] - self.ema15_short[-1]]])) / bar.close_price
        dis_30min = abs(np.array([[self.ema30_long[-1] - self.ema30_middle[-1],
                                   self.ema30_long[-1] - self.ema30_short[-1],
                                   self.ema30_middle[-1] - self.ema30_short[-1]]])) / bar.close_price
        dis_judge = np.all(
            [dis_h < self.ma_distance * 2, dis_30min < self.ma_distance * 2, dis_15min < self.ma_distance *2, dis_5min < self.ma_distance])

        trade_judge_long = bar.close_price > np.mean(self.am5.close_array[-6:-2]) + self.break_value and \
                           np.all(trend > 0) and np.all(position > 0) and position_judge_long and dis_judge
        trade_judge_short = bar.close_price < np.mean(self.am5.close_array[-6:-2]) - self.break_value and \
                            np.all(trend < 0) and np.all(position < 0) and position_judge_short and dis_judge

        slop_mad = np.mean((self.emad_long[-self.slope_period:] - self.emad_long[-self.slope_period - 1:-1])) / np.mean(
                self.emad_long[-self.slope_period:-1]) * 100

        if bar.datetime.strftime('%Y-%m-%d') in ['2017-06-28']:
            print(bar.datetime)
        if self.pos == 0:
            if trade_judge_long:
                if trade_judge_long:
                    self.open_method = 'open'
                    self.buy(bar.close_price+5,2)
            # if trade_judge_short:
            #     if (slop_mad < self.slope or slop_mad > -self.slope*2):
            #
            #         self.open_method = 'open'
            #         self.short(bar.close_price-5,2)
            self.pos_change = []
            self.max_min_close = bar.close_price
            self.move_profit = (max(self.amd.close_array[-10:]) - min(self.amd.close_array[-10:])) / bar.close_price
            self.high_loc = max(self.amd.close_array[-10:])
            self.low_loc = min(self.amd.close_array[-10:])

        if self.pos > 0:
            self.max_min_close =  max(bar.close_price, self.max_min_close)
            if self.open_method == 'open':
                if bar.close_price<self.emad_long[-1]<self.emad_long[-2] and \
                        (((self.max_min_close - self.open[0]) / bar.close_price > self.move_profit) or \
                    ((self.open[0] - bar.close_price) / bar.close_price > self.stop_loss*2)):
                    self.sell(bar.close_price - 20, self.pos)
                    return
                if self.open[0]>(self.high_loc+self.low_loc)/2:
                    if (self.max_min_close-self.open[0])/bar.close_price > self.move_profit/6:
                        if bar.close_price < self.max_min_close - (self.max_min_close - self.open[0]) * self.draw_back:
                            if 1 not in self.pos_change and self.pos > 1:
                                self.sell(bar.close_price - 20, 1)
                                self.pos_change.append(1)
                                self.move_max_min_close = 0
                else:
                    if (self.max_min_close-self.open[0])/bar.close_price > self.move_profit/2:
                        if bar.close_price < self.max_min_close - (self.max_min_close - self.open[0]) * self.draw_back:
                            if 1 not in self.pos_change and self.pos > 1:
                                self.sell(bar.close_price - 20, 1)
                                self.pos_change.append(1)
                                self.move_max_min_close = 0

                # if bar.close_price<self.emad_long[-1]<self.emad_long[-2] and \
                #         (((self.max_min_close - self.open[0]) / bar.close_price > self.move_profit) or \
                #     ((self.open[0] - bar.close_price) / bar.close_price > self.stop_loss*2)):
                #     self.sell(bar.close_price - 20, self.pos)





    def on_15min_bar(self, bar: BarData):

        self.am15.update_bar(bar, finish=True)
        if self.inited:
            self.ema15_long = self.am15.ema(self.long_period, array=True)
            self.ema15_middle = self.am15.ema(self.middle_period, array=True)
            self.ema15_short = self.am15.ema(self.short_period, array=True)
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
