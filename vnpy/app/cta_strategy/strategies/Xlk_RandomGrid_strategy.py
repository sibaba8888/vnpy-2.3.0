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


class XlkRandomGridStrategy(CtaTemplate):
    """"""

    author = "Xlk"
    polyfit_window = 360

    daily_open = 0.0
    mark_buy = True
    mark_short = True
    number_iter = 1
    number_iter1 = 1
    price_buy = 0.0

    price_short = 0.0

    number_trade1 = 1
    number_trade2 = 1
    number_trade3 = 1
    number_trade4 = 1

    buy_start = 40
    short_start = 40
    sell_start = 80
    cover_start = 80
    step = 20
    trailing = 3.5

    parameters = [
        "polyfit_window",
        "number_trade1",
        "number_trade2",
        "number_trade3",
        "number_trade4",
        "buy_start",
        "short_start",
        "sell_start",
        "cover_start",
        "step",
        "trailing"
    ]
    variables = [
        "number_iter",
        "mark_buy",
        "mark_short"
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
            self.number_iter = 1
            self.number_iter1 = 1
            polyfit_value = am.polyfit_coeff(self.polyfit_window)
            self.mark_buy = polyfit_value > 0 and True
            self.mark_short = polyfit_value < 0 and True
            # self.mark_buy = True
            # self.mark_short = True
        if self.daily_open != 0:

            if bar.datetime.hour < 14 or (bar.datetime.hour == 14 and bar.datetime.minute < 59):
                if self.mark_buy:
                    if self.number_iter == 1 and bar.close_price < self.daily_open - self.buy_start:
                        self.buy(bar.close_price + 5, self.number_trade1)
                        self.number_iter = self.number_iter + 1
                        self.price_buy = bar.close_price
                    elif self.number_iter == 2 and bar.close_price < self.daily_open - self.buy_start - self.step:
                        self.buy(bar.close_price + 5, self.number_trade2)
                        self.number_iter = self.number_iter + 1
                    elif self.number_iter == 3 and bar.close_price < self.daily_open - self.buy_start - 2 * self.step:
                        self.buy(bar.close_price + 5, self.number_trade3)
                        self.number_iter = self.number_iter + 1
                    elif self.number_iter == 4 and bar.close_price < self.daily_open - self.buy_start - 3 * self.step:
                        self.buy(bar.close_price + 5, self.number_trade4)
                        self.number_iter = self.number_iter + 1
                elif self.mark_short:
                    if self.number_iter == 1 and bar.close_price > self.daily_open + self.short_start:
                        self.short(bar.close_price - 5, self.number_trade1)
                        self.number_iter = self.number_iter + 1
                        self.price_short = bar.close_price

                    elif self.number_iter == 2 and bar.close_price > self.daily_open + self.short_start + self.step:
                        self.short(bar.close_price - 5, self.number_trade2)
                        self.number_iter = self.number_iter + 1

                    elif self.number_iter == 3 and bar.close_price > self.daily_open + self.short_start + 2 * self.step:
                        self.short(bar.close_price - 5, self.number_trade3)
                        self.number_iter = self.number_iter + 1

                    elif self.number_iter == 4 and bar.close_price > self.daily_open + self.short_start + 3 * self.step:
                        self.short(bar.close_price - 5, self.number_trade4)
                        self.number_iter = self.number_iter + 1

                if self.pos > 0:
                    self.sell(self.daily_open * (1-self.trailing/100), abs(self.pos), stop=True)

                    if self.number_iter == 5:
                        if self.number_iter1 == 1 and bar.close_price > self.price_buy + self.sell_start:
                            self.sell(bar.close_price - 5, self.number_trade1)
                            self.number_iter1 = self.number_iter1 + 1
                        elif self.number_iter == 2 and bar.close_price > self.price_buy + self.sell_start + self.step:
                            self.sell(bar.close_price - 5, self.number_trade2)
                            self.number_iter1 = self.number_iter1 + 1
                        elif self.number_iter1 == 3 and bar.close_price > self.price_buy + self.sell_start + 2 * self.step:
                            self.sell(bar.close_price - 5, self.number_trade3)
                            self.number_iter1 = self.number_iter1 + 1
                        elif self.number_iter1 == 4 and bar.close_price > self.price_buy + self.sell_start + 3 * self.step:
                            self.sell(bar.close_price - 5, self.number_trade4)
                            self.number_iter1 = self.number_iter1 + 1
                    elif self.number_iter == 4:
                        if self.number_iter1 == 1 and bar.close_price > self.price_buy + self.sell_start:
                            self.sell(bar.close_price - 5, self.number_trade1)
                            self.number_iter1 = self.number_iter1 + 1
                        elif self.number_iter == 2 and bar.close_price > self.price_buy + self.sell_start + self.step:
                            self.sell(bar.close_price - 5, self.number_trade2)
                            self.number_iter1 = self.number_iter1 + 1
                        elif self.number_iter1 == 3 and bar.close_price > self.price_buy + self.sell_start + 2 * self.step:
                            self.sell(bar.close_price - 5, self.number_trade3)
                            self.number_iter1 = self.number_iter1 + 1
                    elif self.number_iter == 3:
                        if self.number_iter1 == 1 and bar.close_price > self.price_buy + self.sell_start:
                            self.sell(bar.close_price - 5, self.number_trade1)
                            self.number_iter1 = self.number_iter1 + 1
                        elif self.number_iter == 2 and bar.close_price > self.price_buy + self.sell_start + self.step:
                            self.sell(bar.close_price - 5, self.number_trade2)
                            self.number_iter1 = self.number_iter1 + 1
                    elif self.number_iter == 2:
                        if self.number_iter1 == 1 and bar.close_price > self.price_buy + self.sell_start:
                            self.sell(bar.close_price - 5, self.number_trade1)
                            self.number_iter1 = self.number_iter1 + 1

                elif self.pos < 0:
                    self.cover(self.daily_open * (1+self.trailing/100), abs(self.pos), stop=True)
                    if self.number_iter == 5:
                        if self.number_iter1 == 1 and bar.close_price < self.price_short - self.sell_start:
                            self.cover(bar.close_price + 5, self.number_trade1)
                            self.number_iter1 = self.number_iter1 + 1
                        elif self.number_iter1 == 2 and bar.close_price < self.price_short - self.sell_start - self.step:
                            self.cover(bar.close_price + 5, self.number_trade2)
                            self.number_iter1 = self.number_iter1 + 1
                        elif self.number_iter1 == 3 and bar.close_price < self.price_short - self.sell_start - 2 * self.step:
                            self.cover(bar.close_price + 5, self.number_trade3)
                            self.number_iter1 = self.number_iter1 + 1
                        elif self.number_iter1 == 4 and bar.close_price < self.price_short - self.sell_start - 3 * self.step:
                            self.cover(bar.close_price + 5, self.number_trade4)
                            self.number_iter1 = self.number_iter1 + 1
                    elif self.number_iter == 4:
                        if self.number_iter1 == 1 and bar.close_price < self.price_short - self.sell_start:
                            self.cover(bar.close_price + 5, self.number_trade1)
                            self.number_iter1 = self.number_iter1 + 1
                        elif self.number_iter1 == 2 and bar.close_price < self.price_short - self.sell_start - self.step:
                            self.cover(bar.close_price + 5, self.number_trade2)
                            self.number_iter1 = self.number_iter1 + 1
                        elif self.number_iter1 == 3 and bar.close_price < self.price_short - self.sell_start - 2 * self.step:
                            self.cover(bar.close_price + 5, self.number_trade3)
                            self.number_iter1 = self.number_iter1 + 1

                    elif self.number_iter == 3:
                        if self.number_iter1 == 1 and bar.close_price < self.price_short - self.sell_start:
                            self.cover(bar.close_price + 5, self.number_trade1)
                            self.number_iter1 = self.number_iter1 + 1
                        elif self.number_iter1 == 2 and bar.close_price < self.price_short - self.sell_start - self.step:
                            self.cover(bar.close_price + 5, self.number_trade2)
                            self.number_iter1 = self.number_iter1 + 1

                    elif self.number_iter == 2:
                        if self.number_iter1 == 1 and bar.close_price < self.price_short - self.sell_start:
                            self.cover(bar.close_price + 5, self.number_trade1)
                            self.number_iter1 = self.number_iter1 + 1
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
