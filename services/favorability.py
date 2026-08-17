def get_fav_info(fav: int):
    if fav < 20:
        return 1, "LV1 【傲娇小喵】", "防备度较高，容易被戏弄炸毛"
    if fav < 50:
        return 2, "LV2 【温顺猫娘】", "关系熟络，喜欢主动被主人摸摸头"
    if fav < 100:
        return 3, "LV3 【娇软猫咪】", "对你十分依赖，会主动蹭蹭求抱抱"
    return 4, "LV4 【专属小猫】", "好感满级！全世界最喜欢主人的喵"
