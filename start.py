from core.ma200_bot import Ma200Bot

bot = Ma200Bot()


if __name__ == '__main__':
    try:
        bot.start()
        bot.stop()
    except KeyboardInterrupt:
        bot.stop()
        print('Stopped bot')