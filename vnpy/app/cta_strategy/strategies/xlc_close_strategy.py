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

class XlcCloseStrategy(CtaTemplate):
    """"""
    author = "xlc"


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
    dis_ma_present = 100

    parameters = ["long_period", "middle_period",
                  "short_period", "ma_distance",
                  "dis_ma_close", "stop_loss", "dis_ma_present", "fun_period"]
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
        # self.pos_change = []
        self.maxpos = 0
        self.max_min_close = 0
        self.move_max_min_close = 0
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

        self.emah_long = self.amh.ema(self.long_period, array=True)
        self.emah_middle = self.amh.ema(self.middle_period, array=True)
        self.emah_short = self.amh.ema(self.short_period, array=True)

        self.emad_long = self.amd.ema(self.long_period, array=True)
        self.emad_middle = self.amd.ema(self.middle_period, array=True)
        self.emad_short = self.amd.ema(self.short_period, array=True)

        # 均线趋势向上，下,90d. 30d.10d.90h.30h.10h向上
        trend_d = np.array([[self.emad_long[-1] - self.emad_long[-2], self.emad_middle[-1] - self.emad_middle[-2],
                             self.emad_short[-1] - self.emad_short[-2]]])
        trend_d_close = np.array([[self.emad_long[-1] - self.emad_long[-2], self.emad_long[-2] - self.emad_long[-3],
                                   self.emad_long[-3] - self.emad_long[-4],self.emad_long[-4] - self.emad_long[-5],
                                   self.emad_long[-5] - self.emad_long[-6],self.emad_long[-6] - self.emad_long[-7],
                                   ]])
        trend_h = np.array([[self.emah_long[-1] - self.emah_long[-2], self.emah_middle[-1] - self.emah_middle[-2],
                             self.emah_short[-1] - self.emah_short[-2]]])
        trend_h_close = np.array([[self.emah_long[-1] - self.emah_long[-2], self.emah_long[-2] - self.emah_long[-3],
                                  self.emah_long[-4] - self.emah_long[-3]]])

        # 所有趋势汇总，用于判断向上向下
        trend = np.concatenate((trend_h), axis=0)

        # 判断K线在均线上下  当前k线在90d. 30d.10d.90h.30h.10h上方 按比例算
        # == the bar  located  of ma ===== scaled
        barh_position = np.array([[bar.close_price - self.emah_long[-1], bar.close_price - self.emah_middle[-1],
                                   bar.close_price - self.emah_short[-1]]]) / bar.close_price
        bard_position = np.array([[bar.close_price - self.emad_long[-1], bar.close_price - self.emad_middle[-1],
                                   bar.close_price - self.emad_short[-1]]]) / bar.close_price
        # K线在均线上下判断的汇总
        position = np.concatenate((bard_position, barh_position), axis=0)
        # 趋势向上的距离判断
        position_judge_long = np.all([bard_position < self.dis_ma_close*2, barh_position < self.dis_ma_close * 2])
        # 趋势向下的距离判断
        position_judge_short = np.all([bard_position > self.dis_ma_close*2, barh_position > -self.dis_ma_close * 2])

        # 均线长短中距离
        # the volume for period

        # ========ma distance=========
        dis_d = abs(np.array([[self.emad_long[-1] - self.emad_middle[-1],self.emad_middle[-1] - self.emad_short[-1]]]))\
                / bar.close_price
        dis_h = abs(np.array([[self.emah_long[-1] - self.emah_middle[-1],self.emah_middle[-1] - self.emah_short[-1]]])) \
                / bar.close_price
        compare_d = np.array([self.emad_long[-1] - self.emad_middle[-1], self.emad_middle[-1] - self.emad_short[-1]])\
                    / bar.close_price
        compare_h = np.array([self.emah_long[-1] - self.emah_middle[-1], self.emah_middle[-1] - self.emah_short[-1]])\
                    / bar.close_price
        # 买多，卖空价格与前面几根K线均值大小判断，用于过滤
        price_open = bar.close_price > np.mean(self.am5.close_array[-10:-2]) + self.break_value
        price_short = bar.close_price < np.mean(self.am5.close_array[-10:-2]) - self.break_value
        # 各周期均线靠的比较近
        dis_judge = np.all([dis_d < self.ma_distance*2, dis_h < self.ma_distance * 2])
        #### 上述个要素汇总判断多空买卖方向
        trade_judge_long = price_open and np.all(position > 0) and position_judge_long and dis_judge
        trade_judge_short = price_short and np.all(position < 0) and position_judge_short and dis_judge

        # 凹凸函数判定
        y = self.emad_long[-self.fun_period:]
        x = np.arange(len(y))
        clf = Pipeline([('poly', PolynomialFeatures(degree=2)),
                        ('linear', linear_model.LinearRegression(fit_intercept=False))])
        clf.fit(x[:, np.newaxis], y)  ## 自变量需要二维数组
        # 需要增加一个涨跌幅度的判定

        if self.pos == 0:
            # 买多                   clf.named_steps['linear'].coef_[-1] > 0
            if trade_judge_long and clf.named_steps['linear'].coef_[-1] > 0:
                self.buy(bar.close_price+5, 2)
                self.open_method = 'open1'
            elif trend_d_close.all() > 0:     # 趋势持续向上
                if  price_short and abs(bard_position[0][0]) < self.dis_ma_close * 2 and\
                        bar.close_price > self.emad_long[-1]:
                    self.buy(bar.close_price+5,1)
                    self.open_method = "open2"
                elif price_short and abs(bard_position[0][0]) > self.dis_ma_close * 2 and\
                        bar.close_price < self.emad_long[-1]:
                    self.buy(bar.close_price+5,1)
                    self.open_method = "open3"
            # 卖空
            if trade_judge_short and clf.named_steps['linear'].coef_[-1] < 0: # and bard_position[0][0]>-self.dis_ma_close * 3:
                self.short(bar.close_price-5, 2)
                self.open_method = 'open4'
            elif trend_d_close.all() < 0:
                if  price_open and abs(bard_position[0][0]) < self.dis_ma_close * 2 and\
                        bar.close_price < self.emad_long[-1]:
                    self.short(bar.close_price-5,1)
                    self.open_method = "open5"
                elif price_open and abs(bard_position[0][0]) > self.dis_ma_close * 2 and\
                        bar.close_price > self.emad_long[-1]:
                    self.short(bar.close_price-5,1)
                    self.open_method = "open6"


            self.pos_change = []
            self.max_min_close = bar.close_price

        if self.pos > 0:
            self.max_min_close = max(bar.close_price, self.max_min_close)
            if self.dict_account.get("open1"):
                if bar.close_price < self.dict_account.get("open1") - 100 or\
                        bar.close_price > self.dict_account.get("open1") +200:
                    self.sell(bar.close_price-5,self.pos)
                    self.dict_account['open1'] = None


            elif self.dict_account.get("open2"):
                if bar.close_price < self.dict_account.get("open2") -50 or\
                        bar.close_price > self.dict_account.get("open2") +100:
                    self.sell(self.dict_account.get("open2") - 5, self.pos)
                    self.dict_account['open2'] = None

            elif self.dict_account.get("open3"):
                if bar.close_price < self.dict_account.get("open3") -50 or \
                        bar.close_price > self.dict_account.get("open3") + 100:
                    self.sell(self.dict_account.get("open3")-5, self.pos)
                    self.dict_account['open3'] = None


        if self.pos < 0:
            self.max_min_close = min(bar.close_price, self.max_min_close)
            if self.dict_account.get("open4"):
                if bar.close_price > self.dict_account.get("open4") +100 or\
                        bar.close_price < self.dict_account.get("open4") -200:
                    self.cover(self.dict_account.get("open4") + 5, abs(self.pos))
                    self.dict_account['open4'] = None

            elif self.dict_account.get("open5"):
                if bar.close_price < self.dict_account.get("open5") + 50 or\
                        bar.close_price < self.dict_account.get("open5") - 100:
                    self.cover(self.dict_account.get("open5") + 5, abs(self.pos))
                    self.dict_account['open5'] = None

            elif self.dict_account.get("open6"):
                if bar.close_price < self.dict_account.get("open6") + 50 or\
                        bar.close_price < self.dict_account.get("open6") - 100:
                    self.cover(self.dict_account.get("open6") + 5, abs(self.pos))
                    self.dict_account['open6'] = None



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
