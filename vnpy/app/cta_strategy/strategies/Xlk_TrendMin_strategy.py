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
import datetime


class XlkTrendMinStrategy(CtaTemplate):
    """"""

    author = "Xlk"
    polyfit_window = 40
    box_window = 10
    daily_open = 0.0
    mark_buy = False
    mark_short = False
    fixed_size = 1
    trailing_percent = 0.8
    box_up = 0
    box_down = 0
    intra_trade_high = 0
    intra_trade_low = 0

    long_stop = 0
    short_stop = 0

    parameters = [
        "polyfit_window",
        "box_window",
        "fixed_size",
        "trailing_percent"
    ]
    variables = [
        "long_stop",
        "short_stop",
        "mark_buy",
        "mark_short"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # self.bg = BarGenerator(self.on_bar)
        self.bg = BarGenerator(self.on_bar, 30, self.on_30min_bar)
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

        self.bars.append(bar)
        if len(self.bars) <= 2:
            return
        else:
            self.bars.pop(0)
        last_bar = self.bars[-2]
        # polyfit_value = am.polyfit_coeff(self.polyfit_window)
        savgol_arr = am.savgol(self.polyfit_window, array=True)
        enter_time=bar.datetime
        # self.mark_buy = polyfit_value > 0.2 and bar.close_price > self.box_up
        # self.mark_short = polyfit_value < -0.2 and bar.close_price < self.box_down
        self.mark_buy = savgol_arr[-1] > savgol_arr[-2] and bar.close_price > self.box_up
        # if self.mark_buy:
        #     print(savgol_arr[-1], savgol_arr[-2], savgol_arr[-3])
        self.mark_short = savgol_arr[-1] < savgol_arr[-2] and bar.close_price < self.box_down

        # self.mark_buy = polyfit_value > 0.2
        # self.mark_short = polyfit_value < -0.2
        if self.pos == 0:
            self.intra_trade_high = bar.high_price
            self.intra_trade_low = bar.low_price
            if self.mark_buy:
                self.buy(bar.close_price + 5, self.fixed_size)
                enter_time = bar.datetime
            elif self.mark_short:
                self.short(bar.close_price - 5, self.fixed_size)
                enter_time = bar.datetime

        elif self.pos > 0:
            self.intra_trade_high = bar.high_price
            self.intra_trade_low = bar.low_price
            long_stop = self.intra_trade_high * (1 - self.trailing_percent / 100)
            self.sell(long_stop, abs(self.pos), stop=True)

        elif self.pos < 0:
            self.intra_trade_high = bar.high_price
            self.intra_trade_low = bar.low_price
            short_stop = self.intra_trade_low * (1 + self.trailing_percent / 100)
            self.cover(short_stop, abs(self.pos), stop=True)

        # if (bar.datetime-enter_time).days > 10:
        #     if self.pos > 0:
        #         self.sell(bar.close_price - 5, abs(self.pos))
        #     elif self.pos < 0:
        #         self.cover(bar.close_price + 5, abs(self.pos))
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
