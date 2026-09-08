#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动添加抖音攻略视频脚本
通过提供抖音视频链接，自动解析视频信息并更新到对应guide页面
支持批量添加多个视频
"""

import urllib.request
import urllib.parse
import json
import re
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
GUIDES_DIR = PROJECT_ROOT / "guides"

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/",
}

# 攻略分类映射
CATEGORY_MAP = [
    {"name": "新手攻略", "page": "guide-newbie.html", "keywords": ["新手", "开荒", "入门", "萌新", "开局", "起号"]},
    {"name": "首日攻略", "page": "guide-day1.html", "keywords": ["首日", "第一天", "开区", "新服", "首发"]},
    {"name": "职业攻略", "page": "guide-class.html", "keywords": ["职业", "职业推荐", "职业解析", "转职", "种族"]},
    {"name": "骑士攻略", "page": "guide-knight.html", "keywords": ["骑士", "暗骑", "圣骑士"]},
    {"name": "弓手攻略", "page": "guide-bow.html", "keywords": ["弓手", "弓箭", "银月游侠", "暗影游侠"]},
    {"name": "刺客攻略", "page": "guide-dagger.html", "keywords": ["刺客", "匕首", "深渊行者", "大地行者"]},
    {"name": "双刀/斗士攻略", "page": "guide-dual.html", "keywords": ["双刀", "斗士", "剑斗士", "佣兵", "双手剑"]},
    {"name": "法师攻略", "page": "guide-staff.html", "keywords": ["法师", "巫师", "术士", "咒术诗人", "狂咒术士"]},
    {"name": "牧师攻略", "page": "guide-orb.html", "keywords": ["牧师", "神使", "主教", "长老", "奶妈", "辅助"]},
    {"name": "长枪攻略", "page": "guide-spear.html", "keywords": ["长枪", "长矛", "枪兵"]},
    {"name": "装备攻略", "page": "guide-equip.html", "keywords": ["装备", "强化", "精炼", "龙装", "蓝装", "紫装"]},
    {"name": "副本攻略", "page": "guide-dungeon.html", "keywords": ["副本", "团本", "BOSS", "藏身处", "墓穴", "洞窟", "龙洞"]},
    {"name": "搬砖攻略", "page": "guide-gold.html", "keywords": ["搬砖", "金币", "收益", "打金", "赚钱", "钻石", "氪金"]},
    {"name": "挂机攻略", "page": "guide-afk.html", "keywords": ["挂机", "离线", "自动", "扫描", "挂机设置"]},
    {"name": "职业卡攻略", "page": "guide-cards.html", "keywords": ["职业卡", "收藏", "卡牌"]},
    {"name": "FAQ问答", "page": "guide-faq.html", "keywords": ["FAQ", "问答", "常见问题", "解答"]},
]


def extract_video_id(url):
    """从抖音视频链接中提取视频ID"""
    # 处理完整链接: https://www.douyin.com/video/7670898598539791652
    match = re.search(r'douyin\.com/(?:video|v)/(\d+)', url)
    if match:
        return match.group(1)
    
    # 处理短链接: https://v.douyin.com/iJ8xQf/ （需要重定向获取）
    if 'v.douyin.com' in url:
        try:
            req = urllib.request.Request(url, headers=HEADERS, method='HEAD')
            with urllib.request.urlopen(req, timeout=10) as resp:
                final_url = resp.geturl()
                match = re.search(r'douyin\.com/(?:video|v)/(\d+)', final_url)
                if match:
                    return match.group(1)
        except Exception as e:
            print(f"  短链接解析失败: {e}", file=sys.stderr)
    
    return None


def fetch_video_info(video_id):
    """
    通过视频ID获取视频信息
    尝试多种方式获取视频标题等信息
    """
    video_url = f"https://www.douyin.com/video/{video_id}"
    
    # 方式1: 爬取视频页面
    try:
        req = urllib.request.Request(video_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8")
            
            # 尝试从页面中提取视频信息
            # 方法A: 从 __UNIVERSAL_DATA_FOR_REHYDRATION__ 中提取
            pattern = r'window\.__UNIVERSAL_DATA_FOR_REHYDRATION__\s*=\s*({.+?});'
            match = re.search(pattern, html, re.DOTALL)
            
            if match:
                try:
                    data = json.loads(match.group(1))
                    aweme_detail = find_aweme_detail(data)
                    if aweme_detail:
                        return parse_aweme_detail(aweme_detail, video_id, video_url)
                except json.JSONDecodeError:
                    pass
            
            # 方法B: 从meta标签中提取
            title = extract_meta_content(html, 'og:title') or extract_meta_content(html, 'description')
            author = extract_meta_content(html, 'og:author') or ""
            
            if title:
                return {
                    "aweme_id": video_id,
                    "title": title.strip(),
                    "author": author.strip() if author else "未知作者",
                    "video_url": video_url,
                    "create_time": int(time.time()),  # 无法获取时用当前时间
                    "stats": {},
                }
    except Exception as e:
        print(f"  获取视频页面失败: {e}", file=sys.stderr)
    
    # 返回基本信息
    return {
        "aweme_id": video_id,
        "title": f"抖音视频_{video_id}",
        "author": "未知作者",
        "video_url": video_url,
        "create_time": int(time.time()),
        "stats": {},
    }


def find_aweme_detail(data, depth=0):
    """递归查找aweme_detail"""
    if depth > 10:
        return None
    
    if isinstance(data, dict):
        if 'aweme_detail' in data and isinstance(data['aweme_detail'], dict):
            return data['aweme_detail']
        for value in data.values():
            result = find_aweme_detail(value, depth + 1)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_aweme_detail(item, depth + 1)
            if result:
                return result
    
    return None


def parse_aweme_detail(detail, video_id, video_url):
    """解析视频详情"""
    try:
        return {
            "aweme_id": detail.get("aweme_id", video_id),
            "title": detail.get("desc", f"抖音视频_{video_id}"),
            "author": detail.get("author", {}).get("nickname", "未知作者"),
            "video_url": video_url,
            "create_time": detail.get("create_time", int(time.time())),
            "stats": detail.get("statistics", {}),
            "cover": detail.get("video", {}).get("cover", {}).get("url_list", [""])[0] if detail.get("video") else "",
        }
    except Exception as e:
        print(f"  解析视频详情失败: {e}", file=sys.stderr)
        return {
            "aweme_id": video_id,
            "title": f"抖音视频_{video_id}",
            "author": "未知作者",
            "video_url": video_url,
            "create_time": int(time.time()),
            "stats": {},
        }


def extract_meta_content(html, property_name):
    """从HTML中提取meta标签内容"""
    pattern = rf'<meta[^>]+property=["\']{property_name}["\'][^>]+content=["\']([^"\']+)["\']'
    match = re.search(pattern, html)
    if match:
        return match.group(1)
    
    # 尝试name属性
    pattern2 = rf'<meta[^>]+name=["\']{property_name}["\'][^>]+content=["\']([^"\']+)["\']'
    match2 = re.search(pattern2, html)
    if match2:
        return match2.group(1)
    
    return None


def classify_video(title):
    """根据视频标题分类攻略类型"""
    text_lower = title.lower()
    
    best_match = None
    max_keywords = 0
    
    for category in CATEGORY_MAP:
        matched = sum(1 for kw in category["keywords"] if kw in text_lower)
        if matched > max_keywords:
            max_keywords = matched
            best_match = category
    
    if best_match and max_keywords > 0:
        return best_match["name"], best_match["page"]
    
    return "其他攻略", "guide-newbie.html"  # 默认放到新手攻略


def determine_source_account(title, author):
    """判断视频来源账号"""
    text = f"{title} {author}".lower()
    
    if "天堂2盟约" in text and ("官方" in text or "官网" in text):
        return "天堂2盟约官方抖音"
    elif "张胖子" in text:
        return "张胖子（天堂2盟约）"
    elif author and "张胖子" in author:
        return "张胖子（天堂2盟约）"
    else:
        return "抖音攻略达人"


def is_guide_video(title):
    """判断是否为攻略视频"""
    text_lower = title.lower()
    
    guide_keywords = [
        "攻略", "教程", "教学", "指南", "解析", "推荐", "玩法",
        "怎么", "如何", "详解", "全解", "入门", "开荒", "搬砖",
        "装备", "职业", "副本", "强化", "挂机", "技巧", "避坑",
    ]
    
    exclude_keywords = [
        "直播", "录播", "日常", "vlog", "闲聊", "吐槽", "搞笑",
        "音乐", "舞蹈", "开箱", "抽奖", "公告", "通知",
    ]
    
    for kw in exclude_keywords:
        if kw in text_lower:
            return False
    
    for kw in guide_keywords:
        if kw in text_lower:
            return True
    
    return False


def get_known_video_ids():
    """获取已有视频ID（去重用）"""
    known_ids = set()
    
    for html_file in GUIDES_DIR.glob("*.html"):
        try:
            content = html_file.read_text(encoding="utf-8")
            douyin_urls = re.findall(r'douyin\.com/(?:video|v)/(\d+)', content)
            known_ids.update(douyin_urls)
        except Exception:
            pass
    
    index_file = PROJECT_ROOT / "index.html"
    if index_file.exists():
        try:
            content = index_file.read_text(encoding="utf-8")
            douyin_urls = re.findall(r'douyin\.com/(?:video|v)/(\d+)', content)
            known_ids.update(douyin_urls)
        except Exception:
            pass
    
    return known_ids


def update_guide_page(page_name, video_info, source_account):
    """更新guide页面，添加新章节"""
    page_path = GUIDES_DIR / page_name
    if not page_path.exists():
        print(f"  页面不存在: {page_name}", file=sys.stderr)
        return False, "页面不存在"
    
    try:
        content = page_path.read_text(encoding="utf-8")
        
        # 去重检查
        if video_info["aweme_id"] in content:
            print(f"  视频已存在于 {page_name} 中")
            return False, "视频已存在"
        
        # 生成章节标题（清理特殊字符）
        chapter_title = video_info["title"]
        chapter_title = re.sub(r'[^\w\s\u4e00-\u9fff，。！？、：；""''（）《》【】\-]', '', chapter_title)
        chapter_title = chapter_title.strip()
        if not chapter_title:
            chapter_title = "新攻略视频"
        
        # 查找当前最大章节号
        chapter_pattern = r'<h2[^\n]*?>\s*(?:<span[^>]*>[^<]*</span>\s*)?([一二三四五六七八九十]+)、'
        chapters = re.findall(chapter_pattern, content)
        
        cn_num_map = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
            '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
        }
        num_to_cn = {v: k for k, v in cn_num_map.items()}
        
        max_num = 0
        for ch in chapters:
            if ch in cn_num_map:
                max_num = max(max_num, cn_num_map[ch])
        
        next_num = max_num + 1
        chapter_num = num_to_cn.get(next_num, f"第{next_num}章")
        
        # 发布时间
        pub_time = ""
        if video_info.get("create_time"):
            pub_time = datetime.fromtimestamp(video_info["create_time"]).strftime("%Y-%m-%d")
        else:
            pub_time = datetime.now().strftime("%Y-%m-%d")
        
        # 构建新章节HTML
        new_chapter = f'''
  <h2><span class="tag tag-new">NEW</span> {chapter_num}、{chapter_title}</h2>
  <div class="tip-box">
    <strong style="color:var(--gold)">视频攻略：</strong>本章节内容整理自{source_account}发布的视频攻略，点击下方链接观看原视频。
  </div>
  <p>视频标题：<span class="highlight">{video_info['title']}</span></p>
  <p>视频作者：{video_info.get('author', source_account)}</p>
  <p>视频链接：<a href="{video_info['video_url']}" target="_blank" style="color:var(--l2-primary);">点击观看原视频 →</a></p>
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
            # 先找到这个段落的闭合 </p>
            last_match = timestamp_matches[-1]
            # 从匹配位置开始找 </p>
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
                # 在最后一个h2之后的内容末尾插入
                # 找到 </body> 之前的位置
                body_end = content.rfind('</body>')
                if body_end > last_h2.end():
                    # 在body结束前插入
                    new_content = content[:body_end] + new_chapter + "\n" + content[body_end:]
                else:
                    new_content = content[:last_h2.end()] + new_chapter + content[last_h2.end():]
            else:
                # 没有h2，直接在body前插入
                body_end = content.rfind('</body>')
                if body_end > 0:
                    new_content = content[:body_end] + new_chapter + "\n" + content[body_end:]
                else:
                    new_content = content + new_chapter
        
        if new_content == content:
            return False, "未找到插入位置"
        
        # 更新整页的攻略更新时间（如果存在的话）
        today_str = datetime.now().strftime("%Y年%m月%d日")
        if '攻略更新时间：' in new_content:
            new_content = re.sub(
                r'攻略更新时间：\d+年\d+月\d+日',
                f'攻略更新时间：{today_str}',
                new_content
            )
        
        page_path.write_text(new_content, encoding="utf-8")
        print(f"  ✅ 已更新 {page_name}")
        return True, f"新增章节：{chapter_title}"
        
    except Exception as e:
        print(f"  ❌ 更新 {page_name} 失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False, str(e)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="添加抖音攻略视频到网站")
    parser.add_argument("--urls", nargs="+", help="抖音视频链接列表（空格分隔）")
    parser.add_argument("--source", help="视频来源账号（如：天堂2盟约官方抖音、张胖子（天堂2盟约））")
    parser.add_argument("--category", help="指定分类页面（如：guide-newbie.html）")
    parser.add_argument("--file", help="从文本文件读取视频链接（每行一个）")
    
    args = parser.parse_args()
    
    # 收集视频链接
    video_urls = []
    
    if args.urls:
        video_urls.extend(args.urls)
    
    if args.file:
        file_path = Path(args.file)
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        video_urls.append(line)
    
    if not video_urls:
        print("错误：请提供视频链接（使用 --urls 或 --file 参数）")
        parser.print_help()
        sys.exit(1)
    
    print("=" * 60)
    print("抖音攻略视频添加工具")
    print(f"处理时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"待处理视频：{len(video_urls)} 个")
    print("=" * 60)
    
    # 获取已有视频ID
    known_ids = get_known_video_ids()
    print(f"\n已有视频记录：{len(known_ids)} 个")
    
    # 处理每个视频
    results = []
    
    for i, url in enumerate(video_urls, 1):
        url = url.strip()
        print(f"\n[{i}/{len(video_urls)}] 处理: {url[:60]}...")
        
        # 提取视频ID
        video_id = extract_video_id(url)
        if not video_id:
            print(f"  ❌ 无法提取视频ID")
            results.append({"url": url, "success": False, "message": "无法提取视频ID"})
            continue
        
        # 去重检查
        if video_id in known_ids:
            print(f"  ⏭️  视频已存在，跳过")
            results.append({"url": url, "video_id": video_id, "success": False, "message": "视频已存在"})
            continue
        
        # 获取视频信息
        print(f"  视频ID: {video_id}")
        print(f"  获取视频信息...", end=" ")
        video_info = fetch_video_info(video_id)
        print(f"完成")
        print(f"  标题: {video_info['title'][:50]}")
        print(f"  作者: {video_info['author']}")
        
        # 判断是否为攻略视频
        if not is_guide_video(video_info['title']):
            print(f"  ⚠️  可能不是攻略视频，仍将添加")
        
        # 确定来源账号
        source = args.source or determine_source_account(video_info['title'], video_info['author'])
        print(f"  来源: {source}")
        
        # 分类
        if args.category:
            category_name = "自定义分类"
            target_page = args.category
        else:
            category_name, target_page = classify_video(video_info['title'])
        print(f"  分类: {category_name} → {target_page}")
        
        # 更新页面
        success, message = update_guide_page(target_page, video_info, source)
        
        results.append({
            "url": url,
            "video_id": video_id,
            "title": video_info['title'],
            "author": video_info['author'],
            "source": source,
            "category": category_name,
            "target_page": target_page,
            "success": success,
            "message": message,
        })
        
        time.sleep(1)  # 避免请求过快
    
    # 统计结果
    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count
    
    print(f"\n{'=' * 60}")
    print(f"处理完成！成功: {success_count}, 失败/跳过: {fail_count}")
    print("=" * 60)
    
    # 生成报告
    report_lines = [
        "## 🎬 抖音攻略视频添加报告",
        "",
        f"**处理时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"### 📊 统计",
        "",
        f"- **总视频数**：{len(results)} 个",
        f"- **成功添加**：{success_count} 个",
        f"- **失败/跳过**：{fail_count} 个",
        "",
    ]
    
    if success_count > 0:
        report_lines.append("### ✅ 成功添加")
        report_lines.append("")
        for i, r in enumerate([r for r in results if r["success"]], 1):
            report_lines.append(f"#### {i}. {r['title']}")
            report_lines.append(f"- **来源**：{r['source']}")
            report_lines.append(f"- **分类**：{r['category']}")
            report_lines.append(f"- **更新页面**：`{r['target_page']}`")
            report_lines.append(f"- **视频链接**：{r['url']}")
            report_lines.append("")
    
    if fail_count > 0:
        report_lines.append("### ⚠️ 失败/跳过")
        report_lines.append("")
        for r in [r for r in results if not r["success"]]:
            report_lines.append(f"- {r.get('title', r['url'][:50])}: {r['message']}")
        report_lines.append("")
    
    report_lines.append("---")
    report_lines.append("*抖音攻略视频添加工具*")
    
    report = "\n".join(report_lines)
    
    with open(PROJECT_ROOT / "report.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    # 输出GitHub Actions环境变量
    with open(os.environ.get("GITHUB_OUTPUT", "nul"), "a") as f:
        f.write(f"has_new={'true' if success_count > 0 else 'false'}\n")
        f.write(f"count={success_count}\n")
    
    print("\n报告已生成: report.md")
    
    return success_count > 0


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n脚本执行出错: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
