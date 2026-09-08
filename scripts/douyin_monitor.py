#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音账号视频监控脚本
监控"天堂2盟约官方"和"张胖子（天堂2盟约）"两个抖音账号的新视频
识别攻略内容并自动更新guides目录对应HTML页面
"""

import urllib.request
import urllib.parse
import json
import re
import os
import sys
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

# ========== 配置 ==========

# 抖音账号配置
DOUYIN_ACCOUNTS = [
    {
        "name": "天堂2盟约官方抖音",
        "sec_uid": "MS4wLjABAAAANkP9mUJf8n2ZKfQZ7fQZ7fQZ7fQZ7fQZ7fQZ7fQZ7fQZ7fQZ7fQ",  # 占位，实际使用时替换
        "home_url": "https://www.douyin.com/user/天堂2盟约",
        "is_official": True,
    },
    {
        "name": "张胖子（天堂2盟约）",
        "sec_uid": "MS4wLjABAAAANkP9mUJf8n2ZKfQZ7fQZ7fQZ7fQZ7fQZ7fQZ7fQZ7fQZ7fQZ7fQ",  # 占位，实际使用时替换
        "home_url": "https://www.douyin.com/user/张胖子",
        "is_official": False,
    },
]

# 攻略分类关键词映射（用于判断视频属于哪类攻略）
GUIDE_CATEGORIES = [
    {
        "name": "新手攻略",
        "page": "guide-newbie.html",
        "keywords": ["新手", "开荒", "入门", "首日", "第一天", "萌新", "开局", "起号", "新手教程"],
        "tag": "新手开荒",
    },
    {
        "name": "首日攻略",
        "page": "guide-day1.html",
        "keywords": ["首日", "第一天", "开区", "新服", "首发"],
        "tag": "新手开荒",
    },
    {
        "name": "职业攻略",
        "page": "guide-class.html",
        "keywords": ["职业", "职业推荐", "职业解析", "转职", "种族", "职业选择"],
        "tag": "职业攻略",
    },
    {
        "name": "骑士攻略",
        "page": "guide-knight.html",
        "keywords": ["骑士", "骑士职业", "骑士攻略", "人类骑士", "暗骑"],
        "tag": "职业攻略",
    },
    {
        "name": "弓手攻略",
        "page": "guide-bow.html",
        "keywords": ["弓手", "弓箭", "弓手职业", "银月游侠", "暗影游侠"],
        "tag": "职业攻略",
    },
    {
        "name": "刺客攻略",
        "page": "guide-dagger.html",
        "keywords": ["刺客", "匕首", "刺客职业", "深渊行者", "大地行者"],
        "tag": "职业攻略",
    },
    {
        "name": "双刀/斗士攻略",
        "page": "guide-dual.html",
        "keywords": ["双刀", "斗士", "剑斗士", "佣兵", "双手剑"],
        "tag": "职业攻略",
    },
    {
        "name": "法师攻略",
        "page": "guide-staff.html",
        "keywords": ["法师", "巫师", "术士", "咒术诗人", "狂咒术士"],
        "tag": "职业攻略",
    },
    {
        "name": "牧师攻略",
        "page": "guide-orb.html",
        "keywords": ["牧师", "神使", "主教", "长老", "奶妈", "辅助"],
        "tag": "职业攻略",
    },
    {
        "name": "长枪攻略",
        "page": "guide-spear.html",
        "keywords": ["长枪", "长矛", "枪职业", "枪兵"],
        "tag": "职业攻略",
    },
    {
        "name": "装备攻略",
        "page": "guide-equip.html",
        "keywords": ["装备", "强化", "精炼", "龙装", "蓝装", "紫装", "装备推荐", "装备搭配"],
        "tag": "装备攻略",
    },
    {
        "name": "副本攻略",
        "page": "guide-dungeon.html",
        "keywords": ["副本", "团本", "BOSS", "藏身处", "墓穴", "洞窟", "龙洞", "蚂蚁洞"],
        "tag": "副本攻略",
    },
    {
        "name": "搬砖攻略",
        "page": "guide-gold.html",
        "keywords": ["搬砖", "金币", "收益", "打金", "赚钱", "出金", "钻石", "氪金"],
        "tag": "搬砖攻略",
    },
    {
        "name": "挂机攻略",
        "page": "guide-afk.html",
        "keywords": ["挂机", "离线", "自动", "扫描", "挂机设置", "挂机点"],
        "tag": "攻略",
    },
    {
        "name": "职业卡攻略",
        "page": "guide-cards.html",
        "keywords": ["职业卡", "收藏", "卡牌"],
        "tag": "攻略",
    },
    {
        "name": "FAQ问答",
        "page": "guide-faq.html",
        "keywords": ["FAQ", "问答", "常见问题", "解答", "怎么", "如何"],
        "tag": "攻略",
    },
]

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
GUIDES_DIR = PROJECT_ROOT / "guides"
INDEX_FILE = PROJECT_ROOT / "index.html"

# 时间过滤：只处理最近N天内的视频
DAYS_THRESHOLD = 7


# ========== 工具函数 ==========

def get_known_video_ids():
    """从现有HTML文件中提取已有的抖音视频ID，用于去重"""
    known_ids = set()
    
    # 搜索所有guide页面中的抖音视频链接
    for html_file in GUIDES_DIR.glob("*.html"):
        try:
            content = html_file.read_text(encoding="utf-8")
            # 匹配抖音视频链接格式
            douyin_urls = re.findall(r'douyin\.com/(?:video|v)/(\d+)', content)
            known_ids.update(douyin_urls)
            # 匹配短链接（短链接无法直接提取ID，暂不处理）
        except Exception as e:
            print(f"读取 {html_file.name} 失败: {e}", file=sys.stderr)
    
    # 搜索index.html
    try:
        content = INDEX_FILE.read_text(encoding="utf-8")
        douyin_urls = re.findall(r'douyin\.com/(?:video|v)/(\d+)', content)
        known_ids.update(douyin_urls)
    except Exception as e:
        print(f"读取 index.html 失败: {e}", file=sys.stderr)
    
    return known_ids


def fetch_with_retry(url, max_retries=3, timeout=15):
    """带重试的HTTP请求"""
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"请求失败，{wait_time}秒后重试... ({attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise e


def classify_video(title, description=""):
    """
    根据视频标题和描述分类攻略类型
    返回: (分类名称, 对应页面, 标签)
    """
    text = f"{title} {description}"
    text_lower = text.lower()
    
    best_match = None
    max_keywords = 0
    
    for category in GUIDE_CATEGORIES:
        matched = sum(1 for kw in category["keywords"] if kw in text_lower)
        if matched > max_keywords:
            max_keywords = matched
            best_match = category
    
    if best_match and max_keywords > 0:
        return best_match["name"], best_match["page"], best_match["tag"]
    
    return None, None, "攻略"


def is_guide_video(title, description=""):
    """判断视频是否为攻略内容"""
    text = f"{title} {description}"
    text_lower = text.lower()
    
    # 攻略关键词
    guide_keywords = [
        "攻略", "教程", "教学", "指南", "解析", "推荐", "玩法",
        "怎么", "如何", "详解", "全解", "入门", "开荒", "搬砖",
        "装备", "职业", "副本", "强化", "挂机", "技巧", "避坑",
        "新手指南", "新手教程", "职业推荐", "装备搭配", "副本攻略"
    ]
    
    # 排除非攻略内容
    exclude_keywords = [
        "直播", "录播", "日常", "vlog", "闲聊", "吐槽", "搞笑",
        "音乐", "歌曲", "MV", "舞蹈", "开箱", "抽奖", "福利",
        "公告", "通知", "道歉", "声明", "招聘", "广告"
    ]
    
    # 检查是否包含排除关键词
    for kw in exclude_keywords:
        if kw in text_lower:
            return False
    
    # 检查是否包含攻略关键词
    for kw in guide_keywords:
        if kw in text_lower:
            return True
    
    return False


# ========== 抖音视频获取 ==========

def fetch_douyin_videos_api(sec_uid, max_count=20):
    """
    通过抖音API获取用户视频列表
    注意：抖音API需要签名，此函数为简化实现，可能需要根据实际情况调整
    """
    try:
        # 尝试使用抖音网页版API
        url = f"https://www.douyin.com/aweme/v1/web/aweme/post/?sec_user_id={sec_uid}&count={max_count}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("aweme_list"):
                videos = []
                for item in data["aweme_list"]:
                    video = {
                        "aweme_id": item.get("aweme_id", ""),
                        "title": item.get("desc", ""),
                        "create_time": item.get("create_time", 0),
                        "author": item.get("author", {}).get("nickname", ""),
                        "video_url": f"https://www.douyin.com/video/{item.get('aweme_id', '')}",
                        "stats": item.get("statistics", {}),
                        "cover": item.get("video", {}).get("cover", {}).get("url_list", [""])[0] if item.get("video") else "",
                    }
                    videos.append(video)
                return videos
    except Exception as e:
        print(f"API方式获取视频失败: {e}", file=sys.stderr)
    
    return []


def fetch_douyin_videos_scrape(user_url, account_name=""):
    """
    通过爬取用户主页获取视频列表
    从页面HTML中提取嵌入的JSON数据
    """
    videos = []
    try:
        html = fetch_with_retry(user_url)
        
        # 尝试从页面中提取 __UNIVERSAL_DATA_FOR_REHYDRATION__ 数据
        pattern = r'window\.__UNIVERSAL_DATA_FOR_REHYDRATION__\s*=\s*({.+?});'
        match = re.search(pattern, html, re.DOTALL)
        
        if match:
            try:
                data = json.loads(match.group(1))
                # 递归查找视频列表数据
                aweme_list = find_aweme_list(data)
                if aweme_list:
                    for item in aweme_list[:20]:  # 只取前20个
                        video = parse_aweme_item(item, account_name)
                        if video:
                            videos.append(video)
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}", file=sys.stderr)
    except Exception as e:
        print(f"爬取用户主页失败 {user_url}: {e}", file=sys.stderr)
    
    return videos


def find_aweme_list(data, path=""):
    """递归查找aweme_list"""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "aweme_list" and isinstance(value, list):
                return value
            result = find_aweme_list(value, f"{path}.{key}")
            if result:
                return result
    elif isinstance(data, list):
        for i, item in enumerate(data):
            result = find_aweme_list(item, f"{path}[{i}]")
            if result:
                return result
    return None


def parse_aweme_item(item, author_name=""):
    """解析单个视频项"""
    try:
        aweme_id = item.get("aweme_id", "")
        if not aweme_id:
            return None
        
        title = item.get("desc", "")
        create_time = item.get("create_time", 0)
        author = item.get("author", {}).get("nickname", author_name)
        stats = item.get("statistics", {})
        
        return {
            "aweme_id": aweme_id,
            "title": title,
            "create_time": create_time,
            "author": author,
            "video_url": f"https://www.douyin.com/video/{aweme_id}",
            "stats": stats,
            "cover": item.get("video", {}).get("cover", {}).get("url_list", [""])[0] if item.get("video") else "",
        }
    except Exception as e:
        print(f"解析视频项失败: {e}", file=sys.stderr)
        return None


def fetch_douyin_videos_rss(sec_uid):
    """
    通过RSSHub获取抖音用户视频（备用方案）
    需要部署RSSHub服务
    """
    videos = []
    try:
        rss_url = f"https://rsshub.app/douyin/user/{sec_uid}"
        # 简化实现，实际需要解析RSS
        print("RSS方式暂未实现", file=sys.stderr)
    except Exception as e:
        print(f"RSS方式获取失败: {e}", file=sys.stderr)
    
    return videos


def get_account_videos(account):
    """
    获取指定账号的视频列表（多种方式尝试）
    """
    videos = []
    
    # 方式1: API方式
    if account.get("sec_uid") and not account["sec_uid"].startswith("MS4wLjABAAAANkP9mUJf8n2"):
        print(f"  尝试API方式获取 {account['name']} 视频...")
        videos = fetch_douyin_videos_api(account["sec_uid"])
    
    # 方式2: 爬取主页
    if not videos and account.get("home_url"):
        print(f"  尝试爬取主页方式获取 {account['name']} 视频...")
        videos = fetch_douyin_videos_scrape(account["home_url"], account["name"])
    
    # 方式3: RSS（备用）
    if not videos and account.get("sec_uid"):
        print(f"  尝试RSS方式获取 {account['name']} 视频...")
        videos = fetch_douyin_videos_rss(account["sec_uid"])
    
    return videos


# ========== Guide页面更新 ==========

def update_guide_page(page_name, video_info, source_account):
    """
    更新指定guide页面，添加新的攻略章节
    返回: (是否成功, 变更描述)
    """
    page_path = GUIDES_DIR / page_name
    if not page_path.exists():
        print(f"  页面不存在: {page_name}", file=sys.stderr)
        return False, "页面不存在"
    
    try:
        content = page_path.read_text(encoding="utf-8")
        
        # 检查视频是否已存在
        if video_info["aweme_id"] in content:
            print(f"  视频已存在于 {page_name} 中")
            return False, "视频已存在"
        
        # 生成新章节标题
        chapter_title = video_info["title"]
        # 清理标题中的emoji和特殊字符
        chapter_title = re.sub(r'[^\w\s\u4e00-\u9fff，。！？、：；""''（）《》【】\-]', '', chapter_title)
        chapter_title = chapter_title.strip()
        if not chapter_title:
            chapter_title = "新攻略视频"
        
        # 生成章节编号
        # 查找当前最大章节号
        chapter_pattern = r'<h2[^\n]*?>\s*([一二三四五六七八九十]+)、'
        chapters = re.findall(chapter_pattern, content)
        
        # 中文数字映射
        cn_num_map = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
        }
        num_to_cn = {v: k for k, v in cn_num_map.items()}
        
        max_num = 0
        for ch in chapters:
            if ch in cn_num_map:
                max_num = max(max_num, cn_num_map[ch])
        
        next_num = max_num + 1
        chapter_num = num_to_cn.get(next_num, f"第{next_num}章")
        
        # 格式化发布时间
        pub_time = ""
        if video_info.get("create_time"):
            pub_time = datetime.fromtimestamp(video_info["create_time"]).strftime("%Y-%m-%d")
        else:
            pub_time = datetime.now().strftime("%Y-%m-%d")
        
        # 构建新章节HTML
        new_chapter = f'''
  <h2><span class="tag tag-new">NEW</span> {chapter_num}、{chapter_title}</h2>
  <div class="tip-box">
    <strong style="color:var(--gold)">视频攻略：</strong>本章节内容整理自{source_account}发布的视频攻略。
  </div>
  <p>视频标题：<span class="highlight">{video_info['title']}</span></p>
  <p>视频作者：{video_info.get('author', source_account)}</p>
  <p>视频链接：<a href="{video_info['video_url']}" target="_blank" style="color:var(--l2-primary);">点击观看原视频</a></p>
  <p style="color:var(--text-muted);font-size:12px;margin-top:16px;">
    {chapter_title}补充时间：{datetime.now().strftime("%Y年%m月%d日")} | 来源：{source_account}（{pub_time}发布）
  </p>
'''
        
        # 查找插入位置策略：
        # 1. 找到所有"时间/来源"标注段落（通用模式）
        # 2. 在最后一个标注段落之后插入新章节
        # 3. 如果找不到，找到最后一个h2章节后插入
        
        # 匹配所有时间标注段落（攻略更新时间、XX补充时间等）
        timestamp_pattern = r'<p style="color:var\(--text-muted\);font-size:12px;margin-top:16px;">[^<]*时间：'
        timestamp_matches = list(re.finditer(timestamp_pattern, content))
        
        if timestamp_matches:
            # 在最后一个时间标注段落的结束位置之后插入
            last_match = timestamp_matches[-1]
            p_end = content.find('</p>', last_match.start())
            if p_end > 0:
                insert_pos = p_end + len('</p>')
                new_content = content[:insert_pos] + "\n" + new_chapter + content[insert_pos:]
            else:
                insert_pos = last_match.start()
                new_content = content[:insert_pos] + new_chapter + "\n" + content[insert_pos:]
        else:
            # 找最后一个h2标题的位置
            h2_pattern = r'<h2[^\n]*?>.*?</h2>'
            h2_matches = list(re.finditer(h2_pattern, content, re.DOTALL))
            
            if h2_matches:
                last_h2 = h2_matches[-1]
                body_end = content.rfind('</body>')
                if body_end > last_h2.end():
                    new_content = content[:body_end] + new_chapter + "\n" + content[body_end:]
                else:
                    new_content = content[:last_h2.end()] + new_chapter + content[last_h2.end():]
            else:
                body_end = content.rfind('</body>')
                if body_end > 0:
                    new_content = content[:body_end] + new_chapter + "\n" + content[body_end:]
                else:
                    new_content = content + new_chapter
        
        if new_content == content:
            return False, "未找到插入位置"
        
        # 更新整页的攻略更新时间（如果存在）
        today_str = datetime.now().strftime("%Y年%m月%d日")
        if '攻略更新时间：' in new_content:
            new_content = re.sub(
                r'攻略更新时间：\d+年\d+月\d+日',
                f'攻略更新时间：{today_str}',
                new_content
            )
        
        page_path.write_text(new_content, encoding="utf-8")
        print(f"  已更新 {page_name}，添加章节：{chapter_title}")
        return True, f"新增章节：{chapter_title}"
        
    except Exception as e:
        print(f"  更新 {page_name} 失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False, str(e)


# ========== 主流程 ==========

def main():
    """主函数"""
    print("=" * 60)
    print("抖音攻略视频监控脚本")
    print(f"巡检时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 获取已知视频ID（用于去重）
    print("\n[1/5] 读取已有视频记录...")
    known_ids = get_known_video_ids()
    print(f"  已有抖音视频记录：{len(known_ids)} 个")
    
    # 2. 获取各账号视频
    print("\n[2/5] 获取抖音账号视频...")
    all_videos = []
    
    for account in DOUYIN_ACCOUNTS:
        print(f"\n  正在获取 {account['name']} 的视频...")
        videos = get_account_videos(account)
        print(f"  获取到 {len(videos)} 个视频")
        
        for v in videos:
            v["source_account"] = account["name"]
            v["is_official"] = account.get("is_official", False)
            all_videos.append(v)
        
        # 随机延时，避免请求过快
        time.sleep(random.uniform(1, 3))
    
    if not all_videos:
        print("\n⚠️  未能获取到任何视频数据")
        print("可能原因：抖音API限制、网络问题或账号配置不正确")
        print("建议：检查sec_uid配置，或手动提供视频链接")
        
        # 输出环境变量（GitHub Actions）
        with open(os.environ.get("GITHUB_OUTPUT", "nul"), "a") as f:
            f.write("has_new=false\n")
            f.write("count=0\n")
            f.write("status=no_videos_fetched\n")
        
        # 生成报告
        report = f"""## 🎬 抖音攻略视频巡检报告

**巡检时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}

### ⚠️ 巡检结果

未能获取到抖音视频数据。

**可能原因**：
1. 抖音API访问限制
2. 网络连接问题
3. 账号sec_uid配置不正确

**建议**：
- 检查账号sec_uid配置
- 确认网络可以访问抖音
- 可手动提供视频链接进行更新

---
*自动巡检脚本*
"""
        with open(PROJECT_ROOT / "report.md", "w", encoding="utf-8") as f:
            f.write(report)
        
        sys.exit(0)
    
    # 3. 过滤新视频（去重 + 时间过滤）
    print("\n[3/5] 过滤新视频...")
    new_videos = []
    time_threshold = time.time() - DAYS_THRESHOLD * 24 * 3600
    
    for video in all_videos:
        # 去重检查
        if video["aweme_id"] in known_ids:
            continue
        
        # 时间过滤
        if video.get("create_time", 0) and video["create_time"] < time_threshold:
            continue
        
        new_videos.append(video)
    
    print(f"  发现新视频：{len(new_videos)} 个")
    
    # 4. 识别攻略内容并分类
    print("\n[4/5] 识别攻略内容...")
    guide_videos = []
    
    for video in new_videos:
        title = video.get("title", "")
        is_guide = is_guide_video(title)
        
        if is_guide:
            category_name, page_name, tag = classify_video(title)
            video["category"] = category_name or "其他攻略"
            video["target_page"] = page_name
            video["guide_tag"] = tag
            guide_videos.append(video)
            print(f"  ✅ [{category_name or '其他'}] {title[:40]}...")
        else:
            print(f"  ❌ [非攻略] {title[:40]}...")
    
    print(f"\n  其中攻略视频：{len(guide_videos)} 个")
    
    if not guide_videos:
        print("\n✅ 没有发现新的攻略视频")
        
        with open(os.environ.get("GITHUB_OUTPUT", "nul"), "a") as f:
            f.write("has_new=false\n")
            f.write("count=0\n")
        
        report = f"""## 🎬 抖音攻略视频巡检报告

**巡检时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}

### ✅ 巡检结果

本次巡检未发现新的攻略视频。

**监控账号**：
- 天堂2盟约官方抖音
- 张胖子（天堂2盟约）

**巡检范围**：最近 {DAYS_THRESHOLD} 天发布的视频
**获取视频总数**：{len(all_videos)} 个
**新视频数量**：{len(new_videos)} 个
**攻略视频数量**：{len(guide_videos)} 个

---
*自动巡检脚本*
"""
        with open(PROJECT_ROOT / "report.md", "w", encoding="utf-8") as f:
            f.write(report)
        
        sys.exit(0)
    
    # 5. 更新guide页面
    print("\n[5/5] 更新攻略页面...")
    updated_pages = []
    failed_updates = []
    
    for video in guide_videos:
        page_name = video.get("target_page")
        source = video["source_account"]
        
        if page_name:
            print(f"\n  处理: {video['title'][:50]}...")
            print(f"  目标页面: {page_name}")
            success, msg = update_guide_page(page_name, video, source)
            if success:
                updated_pages.append({
                    "page": page_name,
                    "video": video,
                    "message": msg,
                })
            else:
                failed_updates.append({
                    "page": page_name,
                    "video": video,
                    "message": msg,
                })
        else:
            # 没有明确分类的攻略，默认添加到新手攻略页
            print(f"\n  处理（未分类）: {video['title'][:50]}...")
            print(f"  默认页面: guide-newbie.html")
            success, msg = update_guide_page("guide-newbie.html", video, source)
            if success:
                updated_pages.append({
                    "page": "guide-newbie.html",
                    "video": video,
                    "message": msg,
                })
    
    print(f"\n{'=' * 60}")
    print(f"更新完成！成功更新 {len(updated_pages)} 个页面")
    if failed_updates:
        print(f"失败 {len(failed_updates)} 个")
    
    # 生成报告
    report_lines = [
        "## 🎬 抖音攻略视频巡检报告",
        "",
        f"**巡检时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"### 📊 数据统计",
        "",
        f"- **监控账号**：天堂2盟约官方抖音、张胖子（天堂2盟约）",
        f"- **获取视频总数**：{len(all_videos)} 个",
        f"- **新视频数量**：{len(new_videos)} 个",
        f"- **攻略视频数量**：{len(guide_videos)} 个",
        f"- **成功更新页面**：{len(updated_pages)} 个",
        "",
    ]
    
    if updated_pages:
        report_lines.append("### ✅ 已更新内容")
        report_lines.append("")
        for i, item in enumerate(updated_pages, 1):
            v = item["video"]
            report_lines.append(f"#### {i}. {v['title']}")
            report_lines.append(f"- **来源**：{v['source_account']}")
            report_lines.append(f"- **分类**：{v.get('category', '未分类')}")
            report_lines.append(f"- **更新页面**：`{item['page']}`")
            report_lines.append(f"- **视频链接**：{v['video_url']}")
            pub_time = ""
            if v.get("create_time"):
                pub_time = datetime.fromtimestamp(v["create_time"]).strftime("%Y-%m-%d")
            report_lines.append(f"- **发布时间**：{pub_time or '未知'}")
            report_lines.append("")
    
    if failed_updates:
        report_lines.append("### ⚠️ 更新失败")
        report_lines.append("")
        for item in failed_updates:
            v = item["video"]
            report_lines.append(f"- {v['title']} ({item['page']}): {item['message']}")
        report_lines.append("")
    
    report_lines.append("---")
    report_lines.append("*自动巡检脚本 - 抖音攻略监控*")
    
    report = "\n".join(report_lines)
    
    with open(PROJECT_ROOT / "report.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    # 输出GitHub Actions环境变量
    with open(os.environ.get("GITHUB_OUTPUT", "nul"), "a") as f:
        f.write(f"has_new={'true' if updated_pages else 'false'}\n")
        f.write(f"count={len(updated_pages)}\n")
    
    print("\n报告已生成: report.md")
    return len(updated_pages) > 0


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n脚本执行出错: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
