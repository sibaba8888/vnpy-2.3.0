import numpy as np

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
from numpy import polyfit, poly1d
from vnpy.trader.constant import Interval, Offset


class XlkWaveletTrendStrategy(CtaTemplate):
    """"""

    author = "Xlk"

    savgol_window = 100

    trailing_percent = 2.0
    intra_trade_high = 0
    intra_trade_low = 0

    mark_buy = False
    mark_short = False
    mark_sell = False
    mark_cover = False
    fixed_size = 1

    parameters = [
        "savgol_window",
        "trailing_percent",
        "fixed_size"
    ]
    variables = [
        "mark_buy",
        "mark_short",
        "mark_sell",
        "mark_cover",
        "intra_trade_high",
        "intra_trade_low"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar, 30, self.on_30min_bar)
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
        self.bg.update_bar(bar)

    def on_30min_bar(self, bar: BarData):

        """
        Callback of new bar data update.
        """
        self.cancel_all()

        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        # savgol_value = am.wavelet_noising(self.savgol_window, array=True)
        # self.wavelet_value0 = wavelet_array[-1]
        # self.wavelet_value1 = wavelet_array[-2]
        # coeff = polyfit(range(1, len(wavelet_array) + 1, 1), wavelet_array, 1)

        # polyfit_value = am.polyfit_coeff(self.polyfit_window)
        # fast_ma = am.sma(self.fast_window, array=True)
        # self.fast_ma0 = fast_ma[-1]
        # self.fast_ma1 = fast_ma[-2]
        # self.wavelet_value0 = wavelet_array[-1]
        # self.wavelet_value1 = wavelet_array[-2]
        #
        # coeff = polyfit(range(1, len(wavelet_array) + 1, 1), wavelet_array, 1)
        savgol_value = am.savgol(self.savgol_window, array=True)
        mark_buy = savgol_value[-1] > savgol_value[-2]
        mark_short = savgol_value[-1] < savgol_value[-2]
        mark_sell = savgol_value[-1] < savgol_value[-2]
        mark_cover = savgol_value[-1] > savgol_value[-2]

        if self.pos == 0:
            self.intra_trade_high = bar.high_price
            self.intra_trade_low = bar.low_price
            if mark_buy:
                self.buy(bar.close_price + 5, self.fixed_size)

            elif mark_short:
                self.short(bar.close_price - 5, self.fixed_size)

        elif self.pos > 0:
            self.intra_trade_high = bar.high_price
            self.intra_trade_low = bar.low_price
            long_stop = self.intra_trade_high * \
                        (1 - self.trailing_percent / 100)
            self.sell(long_stop, abs(self.pos), stop=True)
            if mark_sell:
                self.sell(bar.close_price - 5, abs(self.pos))
        elif self.pos < 0:
            self.intra_trade_high = bar.high_price
            self.intra_trade_low = bar.low_price
            short_stop = self.intra_trade_low * \
                         (1 + self.trailing_percent / 100)
            self.cover(short_stop, abs(self.pos), stop=True)
            if mark_cover:
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
