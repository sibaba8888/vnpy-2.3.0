from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)
import matplotlib.pyplot as plt


class XlkIndayTrendMinStrategy(CtaTemplate):
    """"""

    author = "Xlk"

    # wavelet_window = 40
    # wavelet_value0 = 0.0
    # wavelet_value1 = 0.0
    # wavelet_value2 = 0.0
    polyfit_window = 50
    p_mean = 35.0
    daily_open = 0.0
    mark_buy = False
    mark_short = False
    number_trade = False
    fixed_size = 1
    trailing_percent = 0.8

    intra_trade_high = 0
    intra_trade_low = 0

    long_stop = 0
    short_stop = 0

    parameters = [
        "polyfit_window",
        "p_mean",
        "fixed_size",
        "trailing_percent"
    ]
    variables = [
        "long_stop",
        "short_stop",
        "mark_buy",
        "mark_short",
        "number_trade"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar)
        # self.bg = BarGenerator(self.on_bar, 15, self.on_5min_bar)
        self.am = ArrayManager()
        self.bars = []

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        self.load_bar(10)

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
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):

        """
        Callback of new bar data update.
        """
        self.cancel_all()

        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        self.bars.append(bar)
        if len(self.bars) <= 2:
            return
        else:
            self.bars.pop(0)
        last_bar = self.bars[-2]

        if last_bar.datetime.date() != bar.datetime.date():

            self.daily_open = bar.open_price
            self.number_trade = True

        else:

            polyfit_value = am.polyfit_coeff(self.polyfit_window)
            # 回调购买方法----------------------------------
            # # 当价格低于（开盘价-最低价与开盘价差的均值（绝对值）），且小波信号转向上方时买多
            # mark_buy = bar.close_price < self.daily_open - self.p_mean and \
            #            self.wavelet_value0 > self.wavelet_value1 and self.wavelet_value2 > self.wavelet_value1
            # # 当价格高于（开盘价+最高价与开盘价差的均值（绝对值）），且小波信号转向下方时买入
            # mark_short = bar.close_price > self.daily_open + self.p_mean and \
            #              self.wavelet_value0 < self.wavelet_value1 and self.wavelet_value2 < self.wavelet_value1

            # 趋势购买方法----------------------------------

            # 当价格高于（开盘价+最高价与开盘价差的均值（绝对值）），且小波信号转向上方时买多
            # mark_buy = bar.close_price > self.daily_open + self.p_mean and \
            #            self.wavelet_value0 > self.wavelet_value1 > self.wavelet_value1
            self.mark_buy = bar.close_price > self.daily_open + self.p_mean and polyfit_value > 0
            # print('polyfit_value：',polyfit_value)
            # 当价格低于（开盘价-最低价与开盘价差的均值（绝对值）），且小波信号转向向下时卖空
            # mark_short = bar.close_price < self.daily_open - self.p_mean and \
            #              self.wavelet_value0 < self.wavelet_value1 < self.wavelet_value2
            self.mark_short = bar.close_price < self.daily_open - self.p_mean and polyfit_value < 0
            # self.mark_buy = bar.close_price > self.daily_open + self.p_mean and bar.close_price > self.box_up
            # self.mark_short = bar.close_price < self.daily_open - self.p_mean and bar.close_price < self.box_down

            # self.mark_buy1 = self.box_down < bar.close_price < self.box_up and self.daily_open - self.p_mean*0.5 \
            # > bar.close_price > last_bar.close_price
            #
            # self.mark_short1 = self.box_down < bar.close_price < self.box_up and self.daily_open + self.p_mean*0.5 \
            # < bar.close_price < last_bar.close_price

            if bar.datetime.hour < 14 or (bar.datetime.hour == 14 and bar.datetime.minute < 59):
                if self.pos == 0:
                    self.intra_trade_high = bar.high_price
                    self.intra_trade_low = bar.low_price
                    if self.number_trade:  # 一天只交易一次
                        if self.mark_buy:
                            self.buy(bar.close_price + 5, self.fixed_size)
                            self.number_trade = False
                        elif self.mark_short:
                            self.short(bar.close_price - 5, self.fixed_size)
                            self.number_trade = False
                elif self.pos > 0:
                    self.intra_trade_high = bar.high_price
                    self.intra_trade_low = bar.low_price
                    # long_stop = self.daily_open - self.p_mean - self.plo_sigma
                    long_stop = self.intra_trade_high * \
                                (1 - self.trailing_percent / 100)
                    self.sell(long_stop, abs(self.pos), stop=True)
                    # win_stop = self.intra_trade_high * (1 + self.win_percent / 100)
                    # self.sell(win_stop, abs(self.pos), stop=True)

                elif self.pos < 0:
                    self.intra_trade_high = bar.high_price
                    self.intra_trade_low = bar.low_price
                    # short_stop = self.daily_open + self.p_mean + self.p_sigma
                    short_stop = self.intra_trade_low * \
                                 (1 + self.trailing_percent / 100)
                    self.cover(short_stop, abs(self.pos), stop=True)
                    # win_stop1 = self.intra_trade_low * (1 - self.win_percent / 100)
                    # self.cover(win_stop1, abs(self.pos), stop=True)

            if bar.datetime.hour == 14 and bar.datetime.minute == 59:
                if self.pos > 0:
                    self.sell(bar.close_price - 5, abs(self.pos))
                elif self.pos < 0:
                    self.cover(bar.close_price + 5, abs(self.pos))
        # self.box_up, self.box_down = am.box(self.box_window)

        self.put_event()

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
