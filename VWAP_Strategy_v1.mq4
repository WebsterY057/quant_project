//+------------------------------------------------------------------+
//|                                            VWAP_Strategy_v1.mq4 |
//|                                                      Forex Strategy |
//|                                              https://example.com |
//+------------------------------------------------------------------+
#property copyright "Forex Strategy"
#property link      ""
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| 输入参数                                                        |
//+------------------------------------------------------------------+
input int    VWAP_Fast_Period = 20;       // VWAP快线周期
input int    VWAP_Slow_Period = 60;       // VWAP慢线周期
input int    Buy_Confirm_Bars = 1;        // 买入确认K线数
input int    Sell_Confirm_Bars = 4;       // 卖出确认K线数
input double Trend_Strength_Th = 0.0015;  // 趋势强度阈值
input int    QV_Window = 60;             // 成交额过滤窗口
input double QV_Quantile = 0.10;          // 成交额过滤分位

input double LotSize = 0.01;              // 交易手数
input double Spread = 1;                  // 点差（点）
input double Commission = 6.0;             // 每手手续费

input double Slippage = 3;                // 滑点点数

//+------------------------------------------------------------------+
//| 全局变量                                                        |
//+------------------------------------------------------------------+
double g_buy_signal = 0;
double g_sell_signal = 0;
double g_vwap_fast = 0;
double g_vwap_slow = 0;
double g_position = 0;

//+------------------------------------------------------------------+
//| 计算VWAP                                                        |
//+------------------------------------------------------------------+
double CalculateVWAP(int period)
{
    double sum_price_volume = 0;
    double sum_volume = 0;

    for(int i = 0; i < period; i++)
    {
        double price = Close[i];
        double volume = Volume[i];

        if(price > 0 && volume > 0)
        {
            sum_price_volume += price * volume;
            sum_volume += volume;
        }
    }

    if(sum_volume > 0)
        return sum_price_volume / sum_volume;
    else
        return 0;
}

//+------------------------------------------------------------------+
//| 计算成交额分位数                                                 |
//+------------------------------------------------------------------+
double CalculateQVQuantile(int window, double quantile)
{
    double volumes[];
    ArrayResize(volumes, window);

    for(int i = 0; i < window; i++)
    {
        volumes[i] = Volume[i] * Close[i];
    }

    ArraySort(volumes);
    int idx = (int)(window * quantile);
    if(idx >= window) idx = window - 1;
    if(idx < 0) idx = 0;

    return volumes[idx];
}

//+------------------------------------------------------------------+
//| 计算趋势强度                                                     |
//+------------------------------------------------------------------+
double CalculateTrendStrength()
{
    if(g_vwap_slow > 0)
        return (g_vwap_fast / g_vwap_slow - 1.0);
    else
        return 0;
}

//+------------------------------------------------------------------+
//| 生成交易信号                                                     |
//+------------------------------------------------------------------+
void GenerateSignals()
{
    g_vwap_fast = CalculateVWAP(VWAP_Fast_Period);
    g_vwap_slow = CalculateVWAP(VWAP_Slow_Period);

    double trend = CalculateTrendStrength();
    double qv_floor = CalculateQVQuantile(QV_Window, QV_Quantile);
    double current_qv = Volume[0] * Close[0];

    // 买入条件
    bool vwap_buy = (g_vwap_fast > g_vwap_slow);
    bool trend_pass = (trend >= Trend_Strength_Th);
    bool qv_pass = (current_qv >= qv_floor);

    // 卖出条件（VWAP死叉）
    bool vwap_sell = (g_vwap_fast < g_vwap_slow);

    // 统计连续确认K线
    static int buy_streak = 0;
    static int sell_streak = 0;

    if(vwap_buy && trend_pass && qv_pass)
        buy_streak++;
    else
        buy_streak = 0;

    if(vwap_sell)
        sell_streak++;
    else
        sell_streak = 0;

    // 信号确认
    g_buy_signal = (buy_streak >= Buy_Confirm_Bars) ? 1 : 0;
    g_sell_signal = (sell_streak >= Sell_Confirm_Bars) ? 1 : 0;
}

//+------------------------------------------------------------------+
//| 计算成本（点差+手续费）                                          |
//+------------------------------------------------------------------+
double CalculateCost()
{
    double spread_cost = Spread * Point;
    double commission_cost = Commission * Point * 10; // 0.01手对应手续费
    return spread_cost + commission_cost;
}

//+------------------------------------------------------------------+
//| 开仓                                                             |
//+------------------------------------------------------------------+
bool OpenPosition(int type)
{
    double cost = CalculateCost();
    double price = (type == OP_BUY) ? Ask : Bid;
    double sl = 0;
    double tp = 0;

    color clr = (type == OP_BUY) ? clrBlue : clrRed;

    if(type == OP_BUY)
    {
        price = Ask;
        // 多头止损
        sl = price - cost * 2;
    }
    else
    {
        price = Bid;
        // 空头止损
        sl = price + cost * 2;
    }

    bool result = OrderSend(Symbol(), type, LotSize, price, (int)Slippage, sl, tp, "VWAP_Strategy", 0, 0, clr);

    if(!result)
    {
        Print("开仓失败，错误: ", GetLastError());
        return false;
    }

    Print("开仓成功，类型: ", type == OP_BUY ? "买入" : "卖出", " 价格: ", price);
    return true;
}

//+------------------------------------------------------------------+
//| 平仓                                                             |
//+------------------------------------------------------------------+
bool ClosePosition()
{
    if(OrdersTotal() == 0)
        return true;

    if(!OrderSelect(0, SELECT_BY_POS, MODE_TRADES))
        return false;

    if(OrderType() == OP_BUY)
    {
        bool result = OrderClose(OrderTicket(), OrderLots(), Bid, (int)Slippage, clrWhite);
        if(!result)
        {
            Print("平仓失败，错误: ", GetLastError());
            return false;
        }
    }
    else if(OrderType() == OP_SELL)
    {
        bool result = OrderClose(OrderTicket(), OrderLots(), Ask, (int)Slippage, clrWhite);
        if(!result)
        {
            Print("平仓失败，错误: ", GetLastError());
            return false;
        }
    }

    Print("平仓成功");
    return true;
}

//+------------------------------------------------------------------+
//| 检查持仓状态                                                     |
//+------------------------------------------------------------------+
bool HasPosition()
{
    return (OrdersTotal() > 0);
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
    // 生成交易信号
    GenerateSignals();

    // 检查持仓
    bool hasPos = HasPosition();

    // 买入逻辑
    if(g_buy_signal > 0 && !hasPos)
    {
        OpenPosition(OP_BUY);
    }
    // 卖出逻辑
    else if(g_sell_signal > 0 && hasPos)
    {
        ClosePosition();
    }
}

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("VWAP策略 EA 初始化");
    Print("快速VWAP周期: ", VWAP_Fast_Period);
    Print("慢速VWAP周期: ", VWAP_Slow_Period);
    Print("买入确认K线: ", Buy_Confirm_Bars);
    Print("卖出确认K线: ", Sell_Confirm_Bars);
    Print("趋势阈值: ", Trend_Strength_Th);
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("VWAP策略 EA 卸载");
}

//+------------------------------------------------------------------+
//| Expert start function (called when a new bar is formed)           |
//+------------------------------------------------------------------+
void OnBar()
{
    OnTick();
}

//+------------------------------------------------------------------+
//| 订单跟踪（用于在订单关闭时记录结果）                               |
//+------------------------------------------------------------------+
void OnOrderPrint()
{
    // 可在这里添加订单日志记录
}

//+------------------------------------------------------------------+
//| 账户统计                                                         |
//+------------------------------------------------------------------+
void PrintAccountInfo()
{
    Print("----------------------------------------");
    Print("账户余额: ", AccountBalance());
    Print("账户净值: ", AccountEquity());
    Print("账户盈亏: ", AccountProfit());
    Print("----------------------------------------");
}