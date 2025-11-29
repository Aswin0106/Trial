import os
import asyncio
import ccxt
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

class ArbitrageBot:
    def __init__(self):
        self.exchanges = {
            'binance': ccxt.binance(),
            'kucoin': ccxt.kucoin(),
            'huobi': ccxt.huobi(),
            'okx': ccxt.okx(),
        }
        
        # Configure exchanges with error handling
        for name, exchange in self.exchanges.items():
            try:
                exchange.load_markets()
                logger.info(f"✅ {name} loaded successfully")
            except Exception as e:
                logger.error(f"❌ Failed to load {name}: {e}")

    async def get_arbitrage_opportunities(self, symbol='BTC/USDT'):
        opportunities = []
        
        try:
            prices = {}
            for name, exchange in self.exchanges.items():
                try:
                    ticker = exchange.fetch_ticker(symbol)
                    if ticker['bid'] and ticker['ask']:
                        prices[name] = {
                            'bid': ticker['bid'],
                            'ask': ticker['ask'],
                            'last': ticker['last']
                        }
                        logger.debug(f"✅ {name} - {symbol}: Bid {ticker['bid']}, Ask {ticker['ask']}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not fetch {symbol} from {name}: {e}")
                    continue
            
            if len(prices) >= 2:
                lowest_ask_exchange = min(prices.keys(), key=lambda x: prices[x]['ask'])
                highest_bid_exchange = max(prices.keys(), key=lambda x: prices[x]['bid'])
                
                lowest_ask = prices[lowest_ask_exchange]['ask']
                highest_bid = prices[highest_bid_exchange]['bid']
                
                if lowest_ask > 0 and highest_bid > lowest_ask:
                    arbitrage_percent = ((highest_bid - lowest_ask) / lowest_ask) * 100
                    
                    if arbitrage_percent > 0.1:
                        opportunity = {
                            'buy_at': lowest_ask_exchange,
                            'sell_at': highest_bid_exchange,
                            'buy_price': lowest_ask,
                            'sell_price': highest_bid,
                            'profit_percent': arbitrage_percent,
                            'symbol': symbol
                        }
                        opportunities.append(opportunity)
                        logger.info(f"💰 Found arbitrage: {symbol} - {arbitrage_percent:.2f}%")
                        
        except Exception as e:
            logger.error(f"❌ Error in arbitrage calculation: {e}")
        
        return opportunities

    async def scan_multiple_pairs(self):
        common_pairs = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'DOT/USDT', 'LINK/USDT']
        
        all_opportunities = []
        for pair in common_pairs:
            try:
                opportunities = await self.get_arbitrage_opportunities(pair)
                all_opportunities.extend(opportunities)
                await asyncio.sleep(0.1)  # Small delay to avoid rate limits
            except Exception as e:
                logger.error(f"❌ Error scanning {pair}: {e}")
        
        all_opportunities.sort(key=lambda x: x['profit_percent'], reverse=True)
        return all_opportunities[:5]

# Initialize bot
arbitrage_bot = ArbitrageBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🤖 Hello {user.first_name}!\n\n"
        "Crypto Arbitrage Bot is ready!\n\n"
        "Available commands:\n"
        "/scan - Scan BTC/USDT for arbitrage\n"
        "/scan_all - Scan multiple trading pairs\n"
        "/status - Check bot status\n"
        "/help - Show this help message"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Help Guide:\n\n"
        "/scan - Find arbitrage for BTC/USDT\n"
        "/scan_all - Scan top 5 trading pairs\n"
        "/status - Check exchange connections\n\n"
        "The bot checks prices across:\n"
        "• Binance • KuCoin • Huobi • OKX"
    )

async def scan_arbitrage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning BTC/USDT for arbitrage...")
    
    try:
        opportunities = await arbitrage_bot.get_arbitrage_opportunities('BTC/USDT')
        
        if not opportunities:
            await update.message.reply_text("❌ No arbitrage opportunities found for BTC/USDT.")
            return
        
        message = "💰 BTC/USDT Arbitrage Opportunities:\n\n"
        for opp in opportunities:
            message += (
                f"Buy at: {opp['buy_at']}\n"
                f"Price: ${opp['buy_price']:.2f}\n"
                f"Sell at: {opp['sell_at']}\n"
                f"Price: ${opp['sell_price']:.2f}\n"
                f"Profit: {opp['profit_percent']:.3f}%\n"
                f"────────────────────\n"
            )
        
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def scan_all_pairs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning multiple trading pairs...")
    
    try:
        opportunities = await arbitrage_bot.scan_multiple_pairs()
        
        if not opportunities:
            await update.message.reply_text("❌ No arbitrage opportunities found.")
            return
        
        message = "💰 Top Arbitrage Opportunities:\n\n"
        for i, opp in enumerate(opportunities, 1):
            message += (
                f"{i}. {opp['symbol']}\n"
                f"   📥 Buy: {opp['buy_at']} (${opp['buy_price']:.4f})\n"
                f"   📤 Sell: {opp['sell_at']} (${opp['sell_price']:.4f})\n"
                f"   💰 Profit: {opp['profit_percent']:.3f}%\n\n"
            )
        
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_exchanges = []
    for name, exchange in arbitrage_bot.exchanges.items():
        try:
            # Test if exchange is working
            exchange.fetch_ticker('BTC/USDT')
            active_exchanges.append(f"✅ {name}")
        except:
            active_exchanges.append(f"❌ {name}")
    
    status_msg = (
        "🤖 Bot Status:\n"
        f"Exchanges: {len(active_exchanges)}\n"
        f"Status: {'✅ Running' if active_exchanges else '❌ Issues'}\n\n"
        "Exchange Status:\n" + "\n".join(active_exchanges)
    )
    
    await update.message.reply_text(status_msg)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found!")
        return
    
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("scan", scan_arbitrage))
    application.add_handler(CommandHandler("scan_all", scan_all_pairs))
    application.add_handler(CommandHandler("status", status))
    
    application.add_error_handler(error_handler)
    
    logger.info("🤖 Bot starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
