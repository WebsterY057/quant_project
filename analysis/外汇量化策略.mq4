//+------------------------------------------------------------------+ // 分隔注释：MQL4 文件头常见的装饰性注释，便于阅读。
//|                                              DynamicTrendFollower.mq4 | // EA（Expert Advisor，智能交易程序）名称说明。
//|                                  Optimized for "Let Profits Run" | // 策略设计目标说明：让利润奔跑。
//+------------------------------------------------------------------+ // 分隔注释结束。
#property copyright "QuantUser" // `#property` 是预处理指令，用来声明程序属性；这里声明版权信息。
#property link      "" // `#property link` 声明作者链接，这里留空。
#property version   "1.00" // `#property version` 声明版本号。
#property strict // `strict` 表示启用更严格的编译检查，语法和类型要求更严。

//--- 输入参数 // `input` 表示可在 EA 参数面板中修改，但程序运行中不能直接改它。
input double   LotSize = 0.01; // `double` 是浮点数类型；这里定义下单手数，默认 0.01 手。
input int      MaPeriod = 20; // `int` 是整数类型；这里定义均线周期。
input int      AtrPeriod = 14; // ATR 指标周期，用来衡量波动率。
input double   AtrMultiplier = 1.5; // ATR 倍数，用来计算移动止损的距离。
input int      MinBarsForTrend = 50; // 计算策略前要求的最少 K 线数量，避免数据不足。

//--- 全局变量 // 全局变量定义在函数外，整个文件里都可以访问。
int ticket = 0; // 保存最近一次下单返回的订单号（ticket）。
int effectiveMinBars = 0; // 运行时使用的最小 K 线数量；单独定义是因为 `input` 变量不能被修改。
int magicNumber = 123456; // 魔术号：用于区分本 EA 下的订单。

//+------------------------------------------------------------------+ // 分隔注释：初始化函数区域开始。
//| 专家程序启动函数                                                 | // `OnInit()` 会在 EA 加载时执行一次。
//+------------------------------------------------------------------+ // 分隔注释结束。
int OnInit() // `int` 表示函数返回整数；`OnInit` 是 EA 的标准事件函数。
  { // 函数体开始，大括号 `{}` 用来包裹代码块。
   // 初始化检查：`input` 变量不能直接赋值，所以用一个运行时变量接收修正后的值。
   effectiveMinBars = MathMax(MinBarsForTrend, 100); // `MathMax(a,b)` 取较大值，确保至少使用 100 根 K 线。
   return(INIT_SUCCEEDED); // `return` 返回初始化成功状态；`INIT_SUCCEEDED` 是系统常量。
  } // `OnInit` 结束。

//+------------------------------------------------------------------+ // 分隔注释：主逻辑函数区域开始。
//| 专家程序迭代函数                                                 | // `OnTick()` 每来一个新报价（tick）就会执行一次。
//+------------------------------------------------------------------+ // 分隔注释结束。
void OnTick() // `void` 表示函数不返回任何值。
  { // `OnTick` 函数体开始。
   if(Bars < effectiveMinBars) // `if(条件)` 是条件判断；当历史 K 线不足时直接退出。
     {
      return; // 数据不足时不执行后续逻辑，避免指标值无效。
     }

   // 1. 基础数据获取。
   double ask = Ask; // `Ask` 是当前卖价；买单通常按 Ask 成交。
   double bid = Bid; // `Bid` 是当前买价；卖单通常按 Bid 成交。
   double point = Point; // `Point` 是最小报价单位，例如 EURUSD 常见为 0.0001 或 0.00001。

   // 2. 指标值获取。
   // 说明：原代码使用了 MQL5 的“指标句柄 + CopyBuffer”写法，这在 MQL4 中通常会报错。
   // 这里改为 MQL4 常用写法：直接通过 `iMA` / `iATR` 取得某根 K 线上的指标值。
   double currentMA = iMA(_Symbol, PERIOD_CURRENT, MaPeriod, 0, MODE_SMA, PRICE_CLOSE, 1); // `iMA` 返回均线值；最后一个参数 `1` 表示上一根已收盘 K 线。
   double currentATR = iATR(_Symbol, PERIOD_CURRENT, AtrPeriod, 1); // `iATR` 返回 ATR 值；同样取上一根已完成 K 线。

   if(currentMA <= 0 || currentATR <= 0) // `||` 表示逻辑“或”；任一指标异常都不继续。
     {
      return; // 指标未准备好时退出。
     }

   // 3. 获取关键 K 线数据。
   // `iClose/iOpen/iLow/iHigh/iVolume` 都是按“品种 + 周期 + 位移”取历史数据。
   // 位移 `1` = 上一根已完成 K 线，位移 `2` = 上上根 K 线。
   double prevClose = iClose(_Symbol, PERIOD_CURRENT, 1); // 上一根 K 线的收盘价。
   double prevOpen = iOpen(_Symbol, PERIOD_CURRENT, 1); // 上一根 K 线的开盘价。
   double prevLow = iLow(_Symbol, PERIOD_CURRENT, 1); // 上一根 K 线的最低价。
   double prevHigh = iHigh(_Symbol, PERIOD_CURRENT, 1); // 上一根 K 线的最高价。
   double prevPrevClose = iClose(_Symbol, PERIOD_CURRENT, 2); // 上上根 K 线的收盘价，保留作教学注释示例。
   double prevPrevVol = iVolume(_Symbol, PERIOD_CURRENT, 2); // 上上根 K 线成交量。
   double currentVol = iVolume(_Symbol, PERIOD_CURRENT, 1); // 上一根 K 线成交量。

   if(prevClose == 0 || prevOpen == 0 || prevLow == 0 || prevHigh == 0) // 防御式判断：任一价格为 0 说明数据可能未取到。
     {
      return; // 数据异常时退出。
     }

   // 4. 检查现有订单的移动止盈（Trailing Stop）。
   // `OrdersTotal()` 返回当前终端里“交易池”中的订单数量。
   // 这里只要有本 EA 的持仓，就先处理止损移动，不再重复开新仓。
   if(OrdersTotal() > 0) // 当订单总数大于 0 时进入订单扫描逻辑。
     {
      for(int i = OrdersTotal() - 1; i >= 0; i--) // `for(初始化; 条件; 变化)` 是循环语法；这里倒序遍历订单。
        {
         if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) // `OrderSelect` 选中某个订单，后续 `Order...()` 函数都基于当前选中订单。
           {
            if(OrderSymbol() == _Symbol && OrderMagicNumber() == magicNumber) // `&&` 表示逻辑“且”；要求是当前品种且魔术号匹配。
              {
               if(OrderType() == OP_BUY) // 只对买单应用当前这套“向上抬止损”的移动止损逻辑。
                 {
                  double trailingStopPrice = bid - (currentATR * AtrMultiplier); // 新止损 = 当前 Bid - ATR * 倍数。
                  trailingStopPrice = NormalizeDouble(trailingStopPrice, Digits); // `NormalizeDouble` 按报价位数规范化价格，避免精度问题。

                  // 只有当新止损更高时才修改，这叫“只上不下”。
                  if(OrderStopLoss() == 0 || trailingStopPrice > OrderStopLoss() + point) // 给一个 `point` 缓冲，避免频繁无效修改。
                    {
                     OrderModify(OrderTicket(), OrderOpenPrice(), trailingStopPrice, OrderTakeProfit(), 0, clrNONE); // `OrderModify` 修改订单；这里只改止损。
                    }
                 }
               else if(OrderType() == OP_SELL) // `else if` 表示上一个条件不满足时，再判断卖单逻辑。
                 {
                  double trailingStopPrice = ask + (currentATR * AtrMultiplier); // 卖单止损 = 当前 Ask + ATR * 倍数。
                  trailingStopPrice = NormalizeDouble(trailingStopPrice, Digits); // 同样规范化价格精度。

                  // 卖单方向是“只下不上”，即新的止损必须比旧止损更低。
                  if(OrderStopLoss() == 0 || trailingStopPrice < OrderStopLoss() - point)
                    {
                      OrderModify(OrderTicket(), OrderOpenPrice(), trailingStopPrice, OrderTakeProfit(), 0, clrNONE); // 修改卖单止损。
                    }
                 }
              }
           }
        }
      return; // 如果已经有本 EA 持仓，处理完移动止损后直接返回，不再执行开仓逻辑。
     }

   // 5. 开仓逻辑（仅在当前没有持仓时执行）。

   // --- 买入条件 ---
   // 条件 1：趋势向上。
   bool isUptrend = prevClose > currentMA; // `bool` 是布尔类型，只能是 `true` 或 `false`。
   bool isBullishCandle = prevClose > prevOpen; // 阳线判断：收盘价大于开盘价。

   // 条件 2：量能确认。
   bool volumeConfirm = currentVol > prevPrevVol; // 当前量大于前一阶段量，认为量能增强。

   // 条件 3：实体强度过滤。
   double candleBody = prevClose - prevOpen; // 阳线实体长度 = 收盘价 - 开盘价。
   bool strongBody = candleBody > (currentATR * 0.5); // 实体至少达到 ATR 的一半，过滤掉过小波动。

   if(isUptrend && isBullishCandle && volumeConfirm && strongBody) // 多个条件同时满足才允许买入。
     {
      double sl = NormalizeDouble(prevLow, Digits); // 止损设在前一根 K 线低点。
      double tp = 0; // `0` 表示初始不设置固定止盈，后续交给移动止损处理。

      ticket = OrderSend(_Symbol, OP_BUY, LotSize, ask, 3, sl, tp, "TrendFollower", magicNumber, 0, clrBlue); // `OrderSend` 是下单函数：品种、方向、手数、价格、滑点、止损、止盈、注释、魔术号等。
      if(ticket > 0) // 如果返回的 ticket 大于 0，表示下单成功。
        {
         Print("买入开仓: 价格=", ask, " 止损=", sl, " 初始ATR=", currentATR, " 前收盘=", prevClose, " 前上根收盘=", prevPrevClose); // `Print` 用于在日志中输出调试信息。
        }
     }

   // --- 卖出条件（做空逻辑，如需只做多可删除） ---
   bool isDowntrend = prevClose < currentMA; // 下跌趋势：收盘价在均线下方。
   bool isBearishCandle = prevClose < prevOpen; // 阴线判断：收盘价小于开盘价。

   // 情况 A：放量下跌（恐慌盘）。
   bool heavyVolumeDrop = (currentVol > prevPrevVol * 1.5) && isBearishCandle; // 括号 `()` 用于控制运算优先级。

   // 情况 B：缩量滞涨。
   bool weakMomentum = (currentVol < prevPrevVol) && ((prevHigh - prevLow) < currentATR * 0.5); // 振幅过小且量能下降，认为上涨乏力。

   if(isDowntrend && (heavyVolumeDrop || weakMomentum)) // `||` 表示满足其中一个做空条件即可。
     {
      double sl = NormalizeDouble(prevHigh, Digits); // 做空止损设在前高。
      ticket = OrderSend(_Symbol, OP_SELL, LotSize, bid, 3, sl, 0, "TrendFollower", magicNumber, 0, clrRed); // 发出卖单。
      if(ticket > 0) // 判断卖单是否发送成功。
        {
         Print("卖出开仓: 价格=", bid, " 止损=", sl, " 前收盘=", prevClose, " 前上根收盘=", prevPrevClose); // 输出卖单日志。
        }
     }

  } // `OnTick` 函数结束。
//+------------------------------------------------------------------+ // 文件结束分隔注释。
