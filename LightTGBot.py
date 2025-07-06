# stop
import signal
import sys
import time
from datetime import datetime

from telebot import types


def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

from loguru import logger
import json

# loads config
with open("config.json", 'r') as file:
    config_json = json.loads(file.read())

authorized_users = config_json["BaseConfig"]["authorized_users"]
logName = 'LightTGBot.log'
logger.remove(handler_id=None)  # 清除之前的设置
logger.add(logName, rotation="15MB", encoding="utf-8", enqueue=True, retention="1 days")

import telebot

from LightWeightBase import Light

token = config_json["BaseConfig"]["TGBotAPI"]
bot = telebot.TeleBot(token)
bot.message_handler(commands=['help'])

LightsConfig = config_json["LightConfig"]

LightsFindID = {}
lights = []
for i in range(len(LightsConfig)):
    LightsFindID[LightsConfig[i]["name"]] = i
    lights.append(Light(LightsConfig[i]))


# 生成主菜单按钮布局
def generate_main_menu_markup():
    markup = types.InlineKeyboardMarkup()
    for config in LightsConfig:
        button = types.InlineKeyboardButton(config["name"], callback_data=f"server_{config['name']}")
        markup.add(button)
    exit_button = types.InlineKeyboardButton('退出菜单', callback_data='exit_menu')
    markup.add(exit_button)
    return markup


# 生成二级菜单按钮布局
def generate_secondary_menu_markup(server_name):
    markup = types.InlineKeyboardMarkup()

    button_dicts = [
        {"text": "开启机器", "callback_data": f'button{server_name}_1_{server_name}'},
        {"text": "关闭机器", "callback_data": f'button{server_name}_2_{server_name}'},
        {"text": "重启机器", "callback_data": f'button{server_name}_3_{server_name}'},
        {"text": "重置系统", "callback_data": f'button{server_name}_4_{server_name}'},
        {"text": "更改密码", "callback_data": f'button{server_name}_5_{server_name}'},
        {"text": "获得SSH登陆URL", "callback_data": f'button{server_name}_6_{server_name}'},
        {"text": "获得VNC登陆URL", "callback_data": f'button{server_name}_7_{server_name}'},
        {"text": "开启自动快照", "callback_data": f'button{server_name}_8_{server_name}'},
        {"text": "关闭自动快照", "callback_data": f'button{server_name}_9_{server_name}'},
        {"text": "自动快照策略状态", "callback_data": f'button{server_name}_10_{server_name}'},
        {"text": "查看使用流量", "callback_data": f'button{server_name}_11_{server_name}'},
        {"text": "手动快照", "callback_data": f'button{server_name}_12_{server_name}'},
        {"text": "删除快照", "callback_data": f'button{server_name}_13_{server_name}'},
        {"text": "开启所有流量入", "callback_data": f'button{server_name}_14_{server_name}'},
        {"text": "屏蔽所有流量入", "callback_data": f'button{server_name}_15_{server_name}'},
        {"text": "回滚快照", "callback_data": f'button{server_name}_16_{server_name}'},

    ]

    for button_info in button_dicts:
        button = types.InlineKeyboardButton(
            text=button_info["text"],
            callback_data=button_info["callback_data"]
        )
        markup.add(button)

    back_button = types.InlineKeyboardButton('返回上级菜单', callback_data='back_to_menu')
    exit_button = types.InlineKeyboardButton('退出菜单', callback_data='exit_menu')
    markup.add(back_button, exit_button)
    return markup


# 处理按钮点击事件
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:

        if call.data.startswith('server_'):
            server_name = call.data.split('_')[1]
            for config in LightsConfig:
                if config["name"] == server_name:
                    light = lights[LightsFindID[server_name]]
                    details = f"这是{server_name}的菜单"

                    # used=float(cdt.get_cdt_traffic())
                    # total=float(config['cdtMax'])
                    # # 计算进度百分比
                    # progress_percentage = (used / total) * 100
                    # # 手动绘制进度条
                    # bar_length = 20
                    # filled_length = int(bar_length * (used / total))
                    # progress_bar = "■" * filled_length + "□" * (bar_length - filled_length)
                    # details=""
                    # details+=f"{config['name']}   ({eip.get_ip()}) "
                    # details+=f"\n{progress_bar} {progress_percentage:.2f}%"
                    # details+=f"\n已使用流量: {used:.2f}GB / {total:.2f}GB"
                    # details+=f"\n实例IP类型 : {  'BGP(多线)' if config['Linetype']=='BGP' else 'BGP(多线)_精品'}"
                    # details+=f"\n实例地区 {config['region_id']}"
                    # details+=f"\n是否屏蔽所有流量入:  {  '已屏蔽' if eip.isdisableTraffic() else '未屏蔽'}"

                    markup = generate_secondary_menu_markup(server_name)
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text=details, reply_markup=markup)
                    break
        elif call.data.startswith('button'):
            parts = call.data.split('_')
            button_number = parts[1]
            server_name = parts[2]
            handle_button_operation(button_number, server_name, call)
        elif call.data.startswith('Snapshot'):
            logger.info(f"chick {call.data}")

            parts = call.data.split('_')
            SnapshotID = parts[2]
            server_name = parts[1]
            light = lights[LightsFindID[server_name]]
            msg = light.DeleteSnapshotByID(SnapshotID)
            bot.send_message(call.message.chat.id, msg)

            bot.delete_message(call.message.chat.id, call.message.message_id)

        elif call.data.startswith('Rollback'):
            logger.info(f"chick {call.data}")

            parts = call.data.split('_')
            SnapshotID = parts[2]
            server_name = parts[1]
            light = lights[LightsFindID[server_name]]
            msg = light.ResetDiskByID(SnapshotID)
            bot.send_message(call.message.chat.id, msg)

            bot.delete_message(call.message.chat.id, call.message.message_id)







        elif call.data == 'back_to_menu':
            logger.info("chick back_to_menu")
            markup = generate_main_menu_markup()
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='选择要操作的服务器', reply_markup=markup)
        elif call.data == 'exit_menu':
            logger.info("chick exit_menu")
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(call.message.chat.id, 'exit success')

    except Exception as e:
        print(f"处理回调时出错: {e}")


# 定义处理 button 操作的函数
def handle_button_operation(button_number, server_name, call):
    try:

        light = lights[LightsFindID[server_name]]

        if button_number == "1":
            logger.info("check 开启机器")

            msg = light.StartInstance()

            bot.send_message(call.message.chat.id, msg)


        elif button_number == "2":
            logger.info("chick 关闭机器")
            msg = light.StopInstance()
            bot.send_message(call.message.chat.id, msg)


        elif button_number == "3":
            logger.info("chick 重启机器")
            msg = light.RebootInstance()
            bot.send_message(call.message.chat.id, msg)


        elif button_number == "4":
            logger.info("chick 重置系统")
            msg = light.ResetSystem()
            bot.send_message(call.message.chat.id, msg)



        elif button_number == "5":
            logger.info("chick 更改密码")
            msg = light.UpdateInstancePassward()
            bot.send_message(call.message.chat.id, msg)




        elif button_number == "6":
            logger.info("chick 获得SSH登陆URL")
            msg = light.LoginInstanceSshUrl()
            bot.send_message(call.message.chat.id, msg)




        elif button_number == "7":
            logger.info("chick 获得VNC登陆URL")
            msg = light.LoginInstanceVncUrl()
            bot.send_message(call.message.chat.id, msg)



        elif button_number == "8":
            logger.info("chick 开启自动快照")
            light.start_timer("AutoSnapshot")
            msg = "开启自动快照成功"
            bot.send_message(call.message.chat.id, msg)



        elif button_number == "9":
            logger.info("chick 关闭自动快照")
            light.stop_timer("AutoSnapshot")
            msg = "关闭自动快照成功"
            bot.send_message(call.message.chat.id, msg)


        elif button_number == "10":
            logger.info("check 自动快照策略状态")
            if light.is_timer_running("AutoSnapshot"):
                msg = "自动快照策略已开启 crontab is {}".format(light.SnapshotCrons)
            else:
                msg = "自动快照策略已关闭"
            bot.send_message(call.message.chat.id, msg)


        elif button_number == "11":
            logger.info("check 查看使用流量")
            msg = light.ListInstancesTrafficPackages()
            bot.send_message(call.message.chat.id, msg)

        elif button_number == "12":
            logger.info("check 手动快照")
            msg = light.CreateSnapshot("Snapshot_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
            bot.send_message(call.message.chat.id, msg)

        elif button_number == "13":
            logger.info("chick 删除快照")
            markup = types.InlineKeyboardMarkup()

            Snapshots = light.ShowSnapshots()
            logger.info(Snapshots)
            for Snapshotname, SnapshotID in Snapshots.items():
                button = types.InlineKeyboardButton(Snapshotname, callback_data=f"Snapshot_{server_name}_{SnapshotID}")
                markup.add(button)
            markup.add(types.InlineKeyboardButton('退出菜单', callback_data='exit_menu'))

            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='选择要删除的快照', reply_markup=markup)

            # eip.enableTraffic()
            # msg = "enableTraffic success!"
            # bot.send_message(call.message.chat.id, msg)

        elif button_number == "14":
            logger.info("chick 开启所有流量入")
            light.CreateFirewallTemplateRules()
            msg = "开启所有流量入成功"
            bot.send_message(call.message.chat.id, msg)



        elif button_number == "15":
            logger.info("chick 关闭所有流量入")

            light.DeleteFirewallTemplateRules()
            light.DeleteFirewallTemplates()
            light.DeleteFirewallRules()
            msg = "关闭所有流量入成功"
            bot.send_message(call.message.chat.id, msg)
        elif button_number == "16":
            logger.info("chick 回滚快照")
            markup = types.InlineKeyboardMarkup()
            Snapshots = light.ShowSnapshots()
            logger.info(Snapshots)
            for Snapshotname, SnapshotID in Snapshots.items():
                button = types.InlineKeyboardButton(Snapshotname, callback_data=f"Rollback_{server_name}_{SnapshotID}")
                markup.add(button)
            markup.add(types.InlineKeyboardButton('退出菜单', callback_data='exit_menu'))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='选择要回滚的快照', reply_markup=markup)

        if button_number != "13" and button_number != "16":
            bot.delete_message(call.message.chat.id, call.message.message_id)

    except Exception as e:
        print(f"处理操作时出错: {e}")


@bot.message_handler(commands=['menu'])
def menu_command(message):
    if is_authorized(message.from_user):
        markup = generate_main_menu_markup()
        bot.send_message(message.chat.id, '选择要操作的服务器', reply_markup=markup)
    else:
        bot.reply_to(message, f"You are not authorized to use this bot. id is {message.from_user.id}"
                              f"username is {message.from_user.username}")


def is_authorized(user_identifier):
    # 检查用户 ID 或用户名是否在授权用户列表中

    if str(user_identifier.id) in authorized_users:
        return True
    elif user_identifier.username in authorized_users:
        return True
    return False


if __name__ == '__main__':
    bot.infinity_polling()
