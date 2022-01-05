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


class XlkWaveletRandomStrategy(CtaTemplate):
    """"""

    author = "Xlk"

    wavelet_window = 40
    wavelet_value0 = 0.0
    wavelet_value1 = 0.0
    wavelet_value2 = 0.0
    pho_mean = 40.0
    plo_mean = 40.0
    pho_sigma = 80.0
    plo_sigma = 80.0
    daily_open = 0.0
    mark_buy = False
    mark_short = False
    number_trade = False
    fixed_size = 1

    long_stop = 0
    short_stop = 0

    parameters = [
        "wavelet_window",
        "pho_mean",
        "plo_mean",
        "pho_sigma",
        "plo_sigma",
        "fixed_size"
    ]
    variables = [
        "wavelet_value0",
        "wavelet_value1",
        "wavelet_value2",
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
        self.am = ArrayManager()

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

        if bar.datetime.hour == 9 and bar.datetime.minute == 1:
            self.daily_open = bar.open_price
            self.number_trade = True
        #    print("daily_open", self.daily_open)
        if self.daily_open != 0:
            wavelet_array = am.wavelet_noising(self.wavelet_window, array=True)
            self.wavelet_value0 = wavelet_array[-1]
            self.wavelet_value1 = wavelet_array[-2]
            self.wavelet_value2 = wavelet_array[-3]
            # 回调购买方法----------------------------------
            # # 当价格低于（开盘价-最低价与开盘价差的均值（绝对值）），且小波信号转向上方时买多
            # mark_buy = bar.close_price < self.daily_open - self.plo_mean and \
            #            self.wavelet_value0 > self.wavelet_value1 and self.wavelet_value2 > self.wavelet_value1
            # # 当价格高于（开盘价+最高价与开盘价差的均值（绝对值）），且小波信号转向下方时买入
            # mark_short = bar.close_price > self.daily_open + self.pho_mean and \
            #              self.wavelet_value0 < self.wavelet_value1 and self.wavelet_value2 < self.wavelet_value1

            # 趋势购买方法----------------------------------
            # 当价格低于（开盘价-最低价与开盘价差的均值（绝对值）），且小波信号转向向下时卖空
            mark_short = bar.close_price < self.daily_open - self.plo_mean and \
                         self.wavelet_value0 < self.wavelet_value1 < self.wavelet_value2
            # 当价格高于（开盘价+最高价与开盘价差的均值（绝对值）），且小波信号转向上方时买多
            mark_buy = bar.close_price > self.daily_open + self.pho_mean and \
                       self.wavelet_value0 > self.wavelet_value1 > self.wavelet_value1

            if bar.datetime.hour < 14 or (bar.datetime.hour == 14 and bar.datetime.minute < 59):
                if self.pos == 0:
                    if self.number_trade:  # 一天只交易一次
                        if mark_buy:
                            self.buy(bar.close_price + 5, self.fixed_size)
                            self.number_trade = False
                        elif mark_short:
                            self.short(bar.close_price - 5, self.fixed_size)
                            self.number_trade = False
                elif self.pos > 0:
                    long_stop = self.daily_open - self.plo_mean - self.plo_sigma
                    self.sell(long_stop, abs(self.pos), stop=True)
                elif self.pos < 0:
                    short_stop = self.daily_open + self.pho_mean + self.pho_sigma
                    self.cover(short_stop, abs(self.pos), stop=True)
            if bar.datetime.hour == 14 and bar.datetime.minute == 59:
                if self.pos > 0:
                    self.sell(bar.close_price - 5, abs(self.pos))
                elif self.pos < 0:
                    self.cover(bar.close_price + 5, abs(self.pos))
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
