//+------------------------------------------------------------------+
//|                                      MultiTimeframe_Trend_Follower.mq4 |
//|                                  1min Execution, 5min Trend Filter |
//+------------------------------------------------------------------+
#property copyright "QuantUser"
#property link      ""
#property version   "1.00"
#property strict

//--- 输入参数
input double   LotSize = 0.01;             // 交易手数
input int      MaPeriod = 20;              // 5分钟均线周期
input double   RiskReward = 3.0;           // 固定盈亏比 (3.0 = 3:1)
input int      MagicNumber = 123456;       // 订单魔术号

//--- 全局变量
double maBuffer[];

//+------------------------------------------------------------------+
//| 专家程序启动函数                                                 |
//+------------------------------------------------------------------+
int OnInit()
  {
   // 初始化数组
   ArraySetAsSeries(maBuffer, true);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| 专家程序迭代函数                                                 |
//+------------------------------------------------------------------+
void OnTick()
  {
   // 1. 获取 5分钟 均线数据 (趋势过滤器)
   // 注意：这里指定 PERIOD_M5，即使本策略运行在 1分钟图上
   double ma5_Current = iMA(Symbol(), PERIOD_M5, MaPeriod, 0, MODE_SMA, PRICE_CLOSE, 0); // 当前5分钟K线MA
   double ma5_Prev = iMA(Symbol(), PERIOD_M5, MaPeriod, 0, MODE_SMA, PRICE_CLOSE, 1);    // 上一根5分钟K线MA
   
   // 获取 5分钟 收盘价用于判断方向
   double close5_Prev = iClose(_Symbol, PERIOD_M5, 1); 

   // 2. 获取 1分钟 数据 (执行与风控)
   // 1分钟 K线数据
   double prevClose1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double prevOpen1 = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double prevLow1 = iLow(_Symbol, PERIOD_CURRENT, 1);
   double prevHigh1 = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double prevVol1 = iVolume(_Symbol, PERIOD_CURRENT, 1);
   
   double prevPrevClose1 = iClose(_Symbol, PERIOD_CURRENT, 2);
   double prevPrevVol1 = iVolume(_Symbol, PERIOD_CURRENT, 2);

   // 3. 判断大周期趋势方向
   // 使用上一根完成的5分钟K线来判断，避免当前K线未完成的跳动
   bool isBigTrendUp = (close5_Prev > ma5_Prev);
   bool isBigTrendDown = (close5_Prev < ma5_Prev);

   // 4. 若已有持仓则不重复开仓（去掉 ATR 移动止盈后，保持单仓位逻辑）
   if(OrdersTotal() > 0)
     {
      for(int i = OrdersTotal() - 1; i >= 0; i--)
        {
         if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
           {
            if(OrderSymbol() == Symbol() && OrderMagicNumber() == MagicNumber)
              {
               return;
              }
           }
        }
     }

   // 5. 开仓逻辑 (1分钟执行)
   
   // --- 做多逻辑 ---
   // 条件：5分钟趋势向上 AND 1分钟出现买入信号
   if(isBigTrendUp)
     {
      // 1分钟信号：阳线 + 放量 + 实体饱满
      bool isBullish = prevClose1 > prevOpen1;
      bool volumeUp = prevVol1 > prevPrevVol1;
      if(isBullish && volumeUp)
        {
         double entry = Ask;
         double sl = prevLow1; // 固定止损：1分钟前低
         double riskDistance = entry - sl;
         if(riskDistance <= 0) return;
         double tp = entry + (riskDistance * RiskReward); // 3:1 固定止盈

         int ticket = OrderSend(Symbol(), OP_BUY, LotSize, entry, 3, sl, tp, "MTF_Buy", MagicNumber, 0, clrBlue);
         if(ticket > 0) Print("大周期看涨，1分钟买入: ", Ask);
        }
     }

   // --- 做空逻辑 ---
   // 条件：5分钟趋势向下 AND 1分钟出现卖出信号
   if(isBigTrendDown)
     {
      // 1分钟信号：阴线 + 放量 (或缩量滞涨)
      bool isBearish = prevClose1 < prevOpen1;
      bool volumeUp = prevVol1 > prevPrevVol1;
      
      // 这里简化为只做放量下跌，保证爆发力
      if(isBearish && volumeUp)
        {
         double entry = Bid;
         double sl = prevHigh1; // 固定止损：1分钟前高
         double riskDistance = sl - entry;
         if(riskDistance <= 0) return;
         double tp = entry - (riskDistance * RiskReward); // 3:1 固定止盈

         int ticket = OrderSend(Symbol(), OP_SELL, LotSize, entry, 3, sl, tp, "MTF_Sell", MagicNumber, 0, clrRed);
         if(ticket > 0) Print("大周期看跌，1分钟卖出: ", Bid);
        }
     }
  }
//+------------------------------------------------------------------+