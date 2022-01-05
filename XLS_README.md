####配置文件
    C:\Users\xls\.vntrader
####vnpy 架构
    api: 各个交易所提供的API接口，负责与VNPY通信，C++与python结合
    app: vnpy的功能实现
    chart ：K线图表
    event: 事件驱动主程序
    gateway：交易接口
    rpc：rpc服务
    trader：交易模块
        databse：数据库相关
        ui：UI界面
        
####vnpy 各个模块说明，见  docs  就是vnpy文档
    algos_trader.md 交易模块
    chart_wizard.md K线图表
    cta_backtester.md 回测
    cta_strategy.md 策略模块
    data_manager.md  历史数据管理模块
    data_recoder.md  行情记录模块
    database.md 数据库配置
    excel_rtd.md  暂时不知道
    gateway.md  各个交易所 交易模块
    market_rader.md  市场信号雷达模块（MarketRadar） 不知道有啥用 暂时
    option_master.md 期权波动率交易模块
    paper_account.md 本地模拟交易模块（PaperAccount)
    portfolio_manager.md 投资组合管理模块
    portfolio_strategy.md 多合约组合策略模块
    quickstart.md ui界面解释模块
    risk_manager.md  风控模块
    rpc_service.md  RPC模块
    script_trader.md 脚本策略
    spread_trading.md  价差交易模块

##DEBUG
  ####连接gateway 如 连接CTP：
    widget.py   button.clicked.connect(self.connect) 551行 -->connet函数 556 行
       save_json 保存配置文件 有保存的json数据，保存的名字。保存路径(在utility.py 的get_file_path配置)
       connect 连接gateway ,经过mainengine(即trander/engine.Mainengine).连接相应的gateway.如：跳转到ctp_gateway.py
  ### 数据管理 datamanager：
    下载数据应该是RQdata 账号才能玩
    下载数据 一系列设置窗口,设置完成选择 代码交易所等 click下载 --> data_manager/widget.py download 函数  578 -->
    ManagerEngine.download_bar_data(此处选择的hour)
    采取从csv加载数据来处理
    click 导入数据  data_manager/widget.py select_file 设置文件过滤  xls添加 Excel格式 520 行  点击确定-->
    data_manager/widget.py import_data 198行 -->data_manager/engine import_data_from_csv
    xls添加 import_from_excel没找到免费数据，只有通达信,将通达信excel，存成csv
  #### 回测 backtesting
    cta_backtester/ui/widget.py  backBacktesterManager    初始化一堆东西
    包括cta_backtester_setting.json 可修改此文件，设置默认策略以及数据
    根据ui点击设置，click 开始回测 --> ta_backtester/ui/widget.py start_backtesting 298行
        其中331行 设置策略参数
    随后跳转 --> app/cat_backtester/engine.py start_backtesting 190  行 开启线程 target
    -->run_backtesting 128行
    -->加载数据  cta_strategy/backtesting.py  load_data 211行
    -->开始回测 cta_strategy/backtesting.py  run_backtesting 264行
        -->相应策略中进行 strategy init
            --> 策略中的 load_bar 加载初始化数据 -->cta_strategy/template.py load_bar 设置回测的callback-->
            backtesting.py load_bar
  # 事件驱动
    初始化的时候MainEngine  
    MainEngine  函数addEngine添加引擎。参数为各个主要引擎。进入初始化各引擎
    然后各引擎 初始化时候 注册注册事件监听 register_event 
    然后加载各gateway, 比如ctpgateway  继承于主gateway 其中主要进行事件推送
    比如ctpgateway  on_event(EVENT_TICK) 这个tick 事件，，cat_strategy 里面 有        
    self.event_engine.register(EVENT_TICK, self.process_tick_event)
    进行了此事件监听。则每个 tick  cta_strategy 里面都会进行相应的处理
  #### xls 

     修改回测，utility  添加 XlsArrayManager 使其每分钟更新1，5,15,30，hour，daily close_prise
     strategy 中添加 XlsArrayManager.  cta_strategy/__init__.py 添加XlsArrayManager 
     utility将update_bar进行了修改，源代码参vnpy官网的vnpy2.3的uility
     
    
    
    
  #### 版本区别
    这一堆是之前修改的。2.3版本暂时不改
     xls 修改cta_bactester/ui/widget.py  使其可以显示1。5.15 30 hour 的K线数据
     添加 cta_bactester/ui/widget.py    产生ma均线 单均线  指标添加 可看 论坛 搜索 K线图表 
     （https://www.vnpy.com/forum/topic/4621-wei-kxian-tu-biao-tian-zhuan-jia-wa-yi-ge-wan-zheng-de-kxian-tu-biao）
         SmaItem.clear_all()
         添加 self.chart.add_item(SmaItem, 'sma', 'candle')
     chart/item.py  添加SmaItem class 
     chart/__init__.py  添加 from .item import  SmaItem    