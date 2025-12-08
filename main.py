import asyncio
import json
import random
from typing import Sequence

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
from astrbot.api import AstrBotConfig

#147是唐
emoji_list = [
    # 系统表情（type=1，ID为数字，存储为整数）
    4, 5, 8, 9, 10, 12, 14, 16, 21, 23, 24, 25, 26, 27, 28, 29, 30, 32, 33, 34,
    38, 39, 41, 42, 43, 49, 53, 60, 63, 66, 74, 75, 76, 78, 79, 85, 89, 96, 97,
    98, 99, 100, 101, 102, 103, 104, 106, 109, 111, 116, 118, 120, 122, 123, 124,
    125, 129, 144, 147, 171, 173, 174, 175, 176, 179, 180, 181, 182, 183, 201,
    203, 212, 214, 219, 222, 227, 232, 240, 243, 246, 262, 264, 265, 266, 267,
    268, 269, 270, 271, 272, 273, 277, 278, 281, 282, 284, 285, 287, 289, 290,
    293, 294, 297, 298, 299, 305, 306, 307, 314, 315, 318, 319, 320, 322, 324, 326,
    # emoji表情（type=2，ID为文档中明确的数字编号，存储为字符串）
    '9728', '9749', '9786', '10024', '10060', '10068', '127801', '127817', '127822',
    '127827', '127836', '127838', '127847', '127866', '127867', '127881', '128027',
    '128046', '128051', '128053', '128074', '128076', '128077', '128079', '128089',
    '128102', '128104', '128147', '128157', '128164', '128166', '128168', '128170',
    '128235', '128293', '128513', '128514', '128516', '128522', '128524', '128527',
    '128530', '128531', '128532', '128536', '128538', '128540', '128541', '128557',
    '128560', '128563'
]

@register("astrbot_qqemotionreply", "QiChen", "让bot给消息回应表情", "1.1.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        #读取配置文件
        self.config = config
        print(self.config)

        random_tang_cfg = config.get('random_tang') or {}

        self.config["default_emoji_num"] = config.get('default_emoji_num') or 20
        self.time_interval = config.get('time_interval') or 0.5
        self.open_admin_mode = config.get('open_admin_mode', False)
        special_list = config.get('special_qq_list') or []
        self.special_qq_list = [str(qq) for qq in special_list]
        self.enable_tang = config.get('enable_tang', False)
        self.random_tang_isOpen = random_tang_cfg.get('isOpen', False)
        self.random_tang_probability = random_tang_cfg.get('probability', 0)
        self.wolfKill = config.get('tangWolfKill', False)

        self.lastMessageChain=""

        #读取astrbot配置中的管理员id
        astrbot_config = self.context.get_config()
        self.admin_list = getattr(astrbot_config, 'admins_id', []) or []

        #读取tangrank.json，获取当前贴糖的排名
        with open('data/plugins/astrbot_qqemotionreply/tangrank.json', 'r', encoding='utf-8') as f:
            self.tang_rank = json.load(f)

    #使用指令的方式贴表情
    @filter.command("贴表情", alias={'fill', '贴'})
    async def replyMessage(self, event: AstrMessageEvent,emojiNum:int=-1):
        #如果用户未输入参数,读取配置文件默认值
        keyed_num = emojiNum != -1
        if not keyed_num:
            emojiNum = self.config["default_emoji_num"]

        replyID=await self.get_reply_id(event)
        receiverID=await self.get_receiver_id(event)
        should_send=True

        #管理员模式对应逻辑
        if self.open_admin_mode:
            if receiverID in self.admin_list:
                should_send=False
            elif not keyed_num:
                emojiNum=20

        if emojiNum > 20:
            emojiNum = 20
            yield event.plain_result("贴表情数量超出上限,已设为20")

        if replyID and should_send:
            # 调用贴表情函数，这里可以传入不同的表情 ID
            #随机发送指定数量的表情
            rand_emoji_list=random.sample(emoji_list,emojiNum)
            for emoji_id in rand_emoji_list:
                await self._send_emoji_with_delay(event, replyID, emoji_id)

    @filter.command("erhelp", alias={'贴表情帮助', '表情帮助'})
    async def showHelp(self,event:AstrMessageEvent):
        help_text="""
贴表情帮助:
1. 贴表情 [数量]: 给回复的消息贴表情,数量默认20个,上限20个
2. 查看唐人列表: 查看当前唐人列表
3. 唐人排行榜: 查看当前唐人排行榜
4. 开关唐人: 开启或关闭自动贴唐人功能
5. 开关随机唐人: 开启或关闭随机贴唐人功能
6. 设置随机唐人概率 [概率]: 设置随机贴唐人概率(0-100)
7. 清空唐人: 清空当前唐人列表
8. 唐 [QQ号]: 添加特殊QQ为唐人,将会一直被贴糖
9. 取消糖 [QQ号]: 移除特殊QQ,将不再被贴糖
10. 随机唐人: 从群成员中随机选择一个添加为唐人
11. 唐人杀: 开启后，全群的人都是唐人，都有可能被贴糖
注意: 以上3-11指令仅系统管理员可用

"""
        yield event.plain_result(help_text)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("switchtang", alias={'开关唐人'})
    async def switchTang(self,event:AstrMessageEvent):
        result = self._toggle_flag('enable_tang', 'enable_tang', "自动贴唐人功能")
        yield event.plain_result(result)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("switchrandomtang", alias={'开关随机唐人'})
    async def switchRandomTang(self,event:AstrMessageEvent):
        result = self._toggle_flag('random_tang_isOpen', ('random_tang', 'isOpen'), "随机贴唐人功能")
        yield event.plain_result(result)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("setProbability", alias={'设置随机唐人概率'})
    async def setProbability(self,event:AstrMessageEvent,probability:int):
        if probability<0 or probability>100:
            yield event.plain_result("请输入0-100之间的数值")
            return
        self.random_tang_probability=probability
        self._set_config_value(('random_tang', 'probability'), self.random_tang_probability)
        yield event.plain_result(f"已将随机贴唐人概率设置为{probability}%")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("showspecialqq", alias={'查看唐人'})
    async def showSpecialQQ(self,event:AstrMessageEvent):
        if not self.special_qq_list:
            yield event.plain_result("当前无唐人")
            return

        qq_list_str="\n".join(self.special_qq_list)
        yield event.plain_result(f"当前唐人:\n{qq_list_str}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("clearspecialqq", alias={'清空唐人'})
    async def clearSpecialQQ(self,event:AstrMessageEvent):
        self.special_qq_list.clear()
        self._set_config_value('special_qq_list', self.special_qq_list)
        yield event.plain_result("已清空唐人列表")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("tang", alias={'糖'})
    async def addSpecialQQ(self,event:AstrMessageEvent,qqID:str):
        if not self._is_valid_qq(qqID):
            yield event.plain_result("请输入正确的QQ号")
            return

        if qqID not in self.special_qq_list:
            self.special_qq_list.append(qqID)
            self._set_config_value('special_qq_list', self.special_qq_list)
            yield event.plain_result(f"已添加QQ:{qqID},将会一直被贴糖")
        else:
            yield event.plain_result(f"QQ:{qqID}已在特殊QQ列表中")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("untang", alias={'取消糖'})
    async def removeSpecialQQ(self,event:AstrMessageEvent,qqID:str):
        if not self._is_valid_qq(qqID):
            yield event.plain_result("请输入正确的QQ号")
            return

        if qqID in self.special_qq_list:
            self.special_qq_list.remove(qqID)
            self._set_config_value('special_qq_list', self.special_qq_list)
            yield event.plain_result(f"已移除QQ:{qqID}，将不再被贴糖")
        else:
            yield event.plain_result(f"QQ:{qqID}不在特殊QQ列表中")


    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("randomtang", alias={'随机唐人'})
    async def randomTangList(self,event:AstrMessageEvent):
        group_id = event.get_group_id()
        member_list = await self.get_group_member_list(event, group_id)
        if not member_list:
            yield event.plain_result("获取群成员列表失败")
            return

        candidates = [member for member in member_list if member not in self.special_qq_list]
        if not candidates:
            yield event.plain_result("群成员均已在唐人列表中")
            return

        rand_member = random.choice(candidates)
        self.special_qq_list.append(rand_member)
        self._set_config_value('special_qq_list', self.special_qq_list)
        yield event.plain_result(f"已随机添加唐人QQ:{rand_member}，你是很甜的饱饱！")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("tangwolfkill", alias={'唐人杀', '糖人杀'})
    async def tangWolfKill(self,event:AstrMessageEvent):
        result = self._toggle_flag('wolfKill', 'tangWolfKill', "唐人杀模式")
        yield event.plain_result(result)


    @filter.command("seeTang", alias={'查看唐人列表'})
    async def seeTangList(self,event:AstrMessageEvent):
        if not self.special_qq_list:
            yield event.plain_result("当前唐人列表为空")
            return

        tang_text = "\n".join(self.special_qq_list)
        yield event.plain_result(f"当前唐人列表:\n{tang_text}")

    @filter.command("showTangRank", alias={'唐人排行榜','糖人排行榜'})
    async def showTangRank(self,event:AstrMessageEvent):
        if not self.tang_rank:
            yield event.plain_result("当前无唐人排行榜数据")
            return

        # 按照贴糖数量排序
        sorted_rank = sorted(self.tang_rank.items(), key=lambda x: x[1], reverse=True)
        rank_text = "唐人排行榜:\n"
        for i, (qqid, count) in enumerate(sorted_rank, start=1):
            rank_text += f"{i}. QQ:{qqid} - 贴糖次数: {count}\n"
        yield event.plain_result(rank_text)

    def _toggle_flag(self, attr_name: str, config_path: str | Sequence[str], feature_label: str) -> str:
        new_value = not getattr(self, attr_name)
        setattr(self, attr_name, new_value)
        self._set_config_value(config_path, new_value)
        status = "开启" if new_value else "关闭"
        return f"已{status}{feature_label}"

    def _set_config_value(self, keys: str | Sequence[str], value) -> None:
        if isinstance(keys, str):
            self.config[keys] = value
            return

        target = self.config
        *parents, last_key = keys
        for key in parents:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
            target = target[key]
        target[last_key] = value

    @staticmethod
    def _is_valid_qq(qq_id: str) -> bool:
        return bool(qq_id and qq_id.isdigit())

    async def _send_emoji_with_delay(self, event, message_id, emoji_id):
        await self.send_emoji(event, message_id, emoji_id)
        await asyncio.sleep(self.time_interval)

    #获取转发消息id
    async def get_reply_id(self,event):
        message_chain = event.message_obj.message
        # 获取转发消息的消息 ID
        replyID = None
        for message in message_chain:
            if message.type == "Reply":
                replyID = message.id
                break
        return replyID

    #获取接收者id(返回为str类型)
    async def get_receiver_id(self,event):
        message_chain = event.message_obj.message
        #获取接收者id
        receiverID=None
        for message in message_chain:
            if message.type=="Reply":
                receiverID=message.sender_id
                break
        return str(receiverID)

    async def get_sender_id(self,event):
        senderID = str(event.get_sender_id())
        return senderID

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_message(self, event: AstrMessageEvent):
        """
        监听群消息，并对特殊QQ列表中的用户自动贴表情

        """
        if not self.switchTang:
            return

        if event.message_obj.message == self.lastMessageChain:
            await self._send_emoji_with_delay(event, event.message_obj.message_id, 147)
            return

        if event.message_obj.message != self.lastMessageChain:
            print(event.message_obj.message)
            self.lastMessageChain = event.message_obj.message

        if "Face(type=<ComponentType.Face: 'Face'>, id=147)" in str(event.message_obj.message):
            await self._send_emoji_with_delay(event, event.message_obj.message_id, 147)
            return

        tanglist = ["🍭", "🍬","糖","唐","表情:147","tang"]
        # print(event.message_obj.message)
        message_text = event.message_str
        for tang_keyword in tanglist:
            if tang_keyword in message_text:
                await self._send_emoji_with_delay(event, event.message_obj.message_id, 147)
                return

        if self.wolfKill:
            if self.random_tang_isOpen:
                rand_value=random.uniform(0,100)
                if rand_value>self.random_tang_probability:
                    return

                message_id = event.message_obj.message_id
                await self._send_emoji_with_delay(event, message_id, 147)
                return

        senderID = str(event.get_sender_id())
        if self.enable_tang:
            if self.random_tang_isOpen:
                rand_value=random.uniform(0,100)
                if rand_value>self.random_tang_probability:
                    return

            if senderID in self.special_qq_list:
                message_id = event.message_obj.message_id
                await self._send_emoji_with_delay(event, message_id, 147)


    async def send_emoji(self, event, message_id, emoji_id):
        # 调用 napcat 的 api 发送贴表情请求
        if event.get_platform_name() == "aiocqhttp":
            # qq
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot  # 得到 client
            payloads = {
                "message_id": message_id,
                "emoji_id": emoji_id,
                "set": True
            }
            ret = await client.api.call_action('set_msg_emoji_like', **payloads)  # 调用 协议端  API
            logger.info(f"表情ID:{emoji_id}")
            logger.info(f"贴表情返回结果: {ret}")
            post_result = ret['result']
            if post_result == 0:
                logger.info("请求贴表情成功")
                qqid = str(event.get_sender_id())
                self.tang_rank[qqid] = self.tang_rank.get(qqid, 0) + 1
            elif post_result == 65002:
                logger.error("已经回应过该表情")
            elif post_result == 65001:
                logger.error("表情已达上限，无法添加新的表情")
            else:
                logger.error("未知错误")

    async def get_group_member_list(self, event, group_id):
        if event.get_platform_name() == "aiocqhttp":
            # qq
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot
            payloads = {
                "group_id": group_id
            }
            ret = await client.api.call_action('get_group_member_list', **payloads)
            # logger.info(f"获取群成员列表返回结果: {ret}")
            member_list = []
            for member in ret:
                member_list.append(str(member['user_id']))
            # logger.info(f"群成员列表: {member_list}")
            return member_list


    async def terminate(self):
        self.config.save_config()
        print(self.config)

        with open('data/plugins/astrbot_qqemotionreply/tangrank.json', 'w', encoding='utf-8') as f:
            json.dump(self.tang_rank, f, ensure_ascii=False, indent=4)