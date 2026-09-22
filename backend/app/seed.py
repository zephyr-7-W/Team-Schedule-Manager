"""模拟初始数据：团队成员 + 演示日程（用户表为空时写入一次）。"""

from datetime import date, timedelta

from .database import db_cursor

MEMBERS = [
    {"name": "张三", "role": "产品经理", "color": "#5470c6"},
    {"name": "李四", "role": "前端开发", "color": "#91cc75"},
    {"name": "王五", "role": "后端开发", "color": "#fac858"},
    {"name": "赵六", "role": "UI 设计", "color": "#ee6666"},
    {"name": "孙七", "role": "测试工程师", "color": "#73c0de"},
    {"name": "周八", "role": "算法工程师", "color": "#3ba272"},
]

# (day_offset, 姓名, 标题, 开始, 结束, 地点)
DEMO_SCHEDULES = [
    (0, "张三", "每日站会", "09:30", "10:15", "会议室 A"),
    (0, "李四", "每日站会", "09:30", "10:15", "会议室 A"),
    (0, "王五", "后端联调", "10:00", "12:00", "线上"),
    (0, "张三", "需求评审", "10:30", "11:30", "会议室 B"),
    (0, "李四", "前端页面开发", "14:00", "15:30", "工位"),
    (0, "李四", "进度复盘", "15:00", "16:00", "工位"),
    (0, "赵六", "UI 走查", "14:00", "15:00", "会议室 C"),
    (0, "周八", "算法周会", "16:00", "17:00", "线上"),
    (1, "孙七", "用例评审", "10:00", "11:00", "会议室 A"),
    (1, "李四", "联调测试", "15:00", "16:30", "测试环境"),
    (2, "王五", "技术分享", "13:30", "15:00", "大会议室"),
]


def seed_if_empty() -> None:
    """users 表为空时写入成员并生成演示日程。"""
    with db_cursor(commit=True) as cur:
        count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count:
            return

        name_to_id: dict[str, int] = {}
        for member in MEMBERS:
            cur.execute(
                "INSERT INTO users (name, role, color) VALUES (?, ?, ?)",
                (member["name"], member["role"], member["color"]),
            )
            name_to_id[member["name"]] = cur.lastrowid

        for day_offset, name, title, start_time, end_time, location in DEMO_SCHEDULES:
            day = (date.today() + timedelta(days=day_offset)).isoformat()
            cur.execute(
                """
                INSERT INTO schedules
                    (user_id, title, date, start_time, end_time, location, note, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name_to_id[name], title, day, start_time, end_time, location,
                 "演示数据，可在页面直接编辑或删除", "seed"),
            )
