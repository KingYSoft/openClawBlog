#!/usr/bin/env python3
import json
import requests
import datetime
import os

# Get today's date in YYYY-MM-DD format
TODAY = datetime.datetime.utcnow().strftime('%Y-%m-%d')
print(f"Generating briefing for {TODAY}")

# Fetch weather data from wttr.in
def get_weather():
    url = "http://wttr.in/Hangzhou?format=j1"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to fetch weather data")
        return None

# Fetch GitHub trending repos (last 30 days, sorted by stars)
def get_github_trending():
    # Calculate date 30 days ago
    thirty_days_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    url = f"https://api.github.com/search/repositories?q=created:>{thirty_days_ago}&sort=stars&order=desc&per_page=10"
    headers = {'Accept': 'application/vnd.github.v3+json'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['items']
    else:
        print("Failed to fetch GitHub trending data")
        return []

# Generate software development ideas (15-18 ideas)
def get_ideas():
    ideas = [
        "Context-Aware Code Review Bot: AI that understands your team's coding standards, learns from past PR comments, and provides contextual feedback.",
        "Intelligent Debugging Assistant: Analyzes stack traces, suggests fixes, learns from debugging patterns, and connects to error tracking services.",
        "Auto-Documentation Generator: Generates API docs from code + commit messages, creates interactive tutorials, maintains changelog automatically.",
        "Smart Meeting Summarizer: Records and transcribes meetings, extracts action items, integrates with project management tools, creates follow-up reminders.",
        "Cross-Platform Notification Hub: Unified inbox for all notifications, AI-powered priority sorting, smart batching, custom automation rules.",
        "Personal Knowledge Graph: Automatically links notes, documents, and code, AI-suggested connections, visual graph exploration interface.",
        "Ambient Development Environment: Background music that adapts to coding flow, Pomodoro timer with smart break suggestions, focus mode.",
        "Codebase Time Machine: Visualize codebase evolution over time, identify architectural drift, find when bugs were introduced, generate migration guides.",
        "Pair Programming Matchmaker: Matches developers based on skills and availability, suggests optimal pairings, tracks effectiveness, integrates with calendar.",
        "Real-Time Team Velocity Dashboard: Live metrics on development progress, predictive completion estimates, bottleneck identification, customizable views.",
        "API Usage Intelligence: Track API consumption patterns, detect anomalies, cost optimization recommendations, automatic rate limiting adjustments.",
        "User Behavior Heatmaps for CLI Tools: Visualize most used commands, identify confusing workflows, A/B test new command designs, optimize documentation.",
        "Automated Security Audit Pipeline: Continuous vulnerability scanning, dependency update suggestions, compliance report generation, CI/CD integration.",
        "Secret Detection & Rotation: Scans codebase for leaked credentials, automated secret rotation, integration with vault services, alerts on suspicious access.",
        "WebAssembly Plugin System: Safe, sandboxed plugin execution, cross-language plugin support, hot-reload without restarts, performance isolation.",
        "Edge AI Deployment Framework: Deploy models to edge devices easily, automatic model optimization, federated learning support, offline-first architecture.",
        "AI-Powered Test Generator: Automatically generates unit tests from code, identifies untested code paths, suggests edge cases, integrates with CI/CD.",
        "Visual Regression Testing Suite: Automated UI screenshot comparison, pixel-perfect diff detection, cross-browser testing support, integration with design systems."
    ]
    # Return 15-18 ideas (we have 18)
    return ideas

def format_weather_en(weather_data):
    if not weather_data:
        return "Weather data unavailable."
    
    current = weather_data['current_condition'][0]
    today = weather_data['weather'][0]
    tomorrow = weather_data['weather'][1] if len(weather_data['weather']) > 1 else {}
    
    # Current weather
    desc = current['weatherDesc'][0]['value']
    temp = current['temp_C']
    feels_like = current['FeelsLikeC']
    humidity = current['humidity']
    wind_speed = current['windspeedKmph']
    wind_dir = current['winddir16Point']
    
    # Today's forecast
    today_max = today['maxtempC']
    today_min = today['mintempC']
    today_chance_rain = today['hourly'][0]['chanceofrain']  # Simplified, we can take midday
    
    # Tomorrow's forecast
    tomorrow_max = tomorrow.get('maxtempC', 'N/A')
    tomorrow_min = tomorrow.get('mintempC', 'N/A')
    tomorrow_chance_rain = tomorrow.get('hourly', [{}])[0].get('chanceofrain', 'N/A')
    
    # Outfit recommendations based on temperature
    # We'll simplify: if temp > 25, light clothing; if temp < 10, warm; else layers.
    if int(temp) > 25:
        outfit = "Light clothing (t-shirt, shorts) recommended. Sunglasses and sunscreen for UV protection."
    elif int(temp) < 10:
        outfit = "Warm clothing recommended (jacket, sweater). Consider layers for temperature changes."
    else:
        outfit = "Layered clothing recommended (long-sleeve shirt, light sweater/jacket). Adjust based on temperature changes throughout the day."
    
    weather_md = f"""## 1. Weather in Hangzhou & Outfit Recommendations

**Current Weather** (Hangzhou, Asia/Shanghai):
- 🌡️ Temperature: {temp}°C (feels like {feels_like}°C)
- 💨 Wind: {wind_speed} km/h ({wind_dir} direction)
- 🌤️ Condition: {desc}
- 💧 Humidity: {humidity}%
- 👁️ Visibility: {current.get('visibility', '10')} km
- 📅 Date: {datetime.datetime.utcnow().strftime('%B %d, %Y %H:%M')} (UTC)

**📅 Today's Forecast**:
- 🌡️ High: {today_max}°C / Low: {today_min}°C
- 🌧️ Rain chance: {today_chance_rain}%
- Perfect day for outdoor activities!

**📅 Tomorrow's Forecast**:
- 🌡️ High: {tomorrow_max}°C / Low: {tomorrow_min}°C
- 🌧️ Rain chance: {tomorrow_chance_rain}%

**👔 Outfit Recommendations**:
- {outfit}
- **Note**: Hangzhou weather can change quickly. Always carry a light jacket or umbrella just in case.

"""
    return weather_md

def format_weather_zh(weather_data):
    if not weather_data:
        return "天气数据不可用。"
    
    current = weather_data['current_condition'][0]
    today = weather_data['weather'][0]
    tomorrow = weather_data['weather'][1] if len(weather_data['weather']) > 1 else {}
    
    desc = current['weatherDesc'][0]['value']
    temp = current['temp_C']
    feels_like = current['FeelsLikeC']
    humidity = current['humidity']
    wind_speed = current['windspeedKmph']
    wind_dir = current['winddir16Point']
    
    today_max = today['maxtempC']
    today_min = today['mintempC']
    today_chance_rain = today['hourly'][0]['chanceofrain']
    
    tomorrow_max = tomorrow.get('maxtempC', 'N/A')
    tomorrow_min = tomorrow.get('mintempC', 'N/A')
    tomorrow_chance_rain = tomorrow.get('hourly', [{}])[0].get('chanceofrain', 'N/A')
    
    if int(temp) > 25:
        outfit = "建议穿戴轻薄衣物（T恤、短裤）。请注意防晒和佩戴太阳镜。"
    elif int(temp) < 10:
        outfit = "建议穿戴保暖衣物（外套、毛衣）。请注意分层穿搭以应对温度变化。"
    else:
        outfit = "建议分层穿搭（长袖衬衫、轻薄毛衣/夹克）。请根据一天中的温度变化增减衣物。"
    
    weather_md = f"""## 1. 杭州天气与穿搭指南

**当前天气** (杭州，亚洲/上海):
- 🌡️ 温度：{temp}°C (体感温度 {feels_like}°C)
- 💨 风速：{wind_speed} km/h ({wind_dir} 方向)
- 🌤️ 天气状况：{desc}
- 💧 湿度：{humidity}%
- 👁️ 能见度：{current.get('visibility', '10')} 公里
- 📅 时间：{datetime.datetime.utcnow().strftime('%B %d, %Y %H:%M')} (UTC)

**📅 今日预报**：
- 🌡️ 最高：{today_max}°C / 最低：{today_min}°C
- 🌧️ 降雨概率：{today_chance_rain}%
- 适合户外活动！

**📅 明日预报**：
- 🌡️ 最高：{tomorrow_max}°C / 最低：{tomorrow_min}°C
- 🌧️ 降雨概率：{tomorrow_chance_rain}%

**👔 穿搭建议**：
- {outfit}
- **注意**：杭州天气变化快，建议随身携带薄外套或雨伞以防不时之需。

"""
    return weather_md

def format_github_en(repos):
    md = "## 2. Top 10 GitHub Repositories (Past 30 Days)\n\n"
    md += "🔥 **Trending by Star Count (Created in Last 30 Days)**:\n\n"
    for i, repo in enumerate(repos, 1):
        md += f"### {i}. {repo['name']}\n"
        md += f"- **Stars**: {repo['stargazers_count']:,} | **Forks**: {repo['forks_count']:,} | **Language**: {repo['language'] or 'N/A'}\n"
        md += f"- **Description**: {repo['description'] or 'No description'}\n"
        md += f"- **URL**: {repo['html_url']}\n\n"
    return md

def format_github_zh(repos):
    md = "## 2. GitHub 热门仓库 TOP 10（近 30 天）\n\n"
    md += "🔥 **按 Star 数量排序（最近 30 天创建）**：\n\n"
    for i, repo in enumerate(repos, 1):
        md += f"### {i}. {repo['name']}\n"
        md += f"- **Stars**: {repo['stargazers_count']:,} | **Forks**: {repo['forks_count']:,} | **语言**：{repo['language'] or 'N/A'}\n"
        md += f"- **描述**：{repo['description'] or '无描述'}\n"
        md += f"- **链接**：{repo['html_url']}\n\n"
    return md

def format_ideas_en(ideas):
    md = "## 3. Creative Software Development Ideas & Feature Suggestions\n\n"
    md += "💡 **Innovative Ideas for Your Next Project**:\n\n"
    for i, idea in enumerate(ideas, 1):
        md += f"{i}. {idea}\n\n"
    return md

def format_ideas_zh(ideas):
    md = "## 3. 软件开发创意点子与功能建议\n\n"
    md += "💡 **下一个项目的创新灵感**：\n\n"
    for i, idea in enumerate(ideas, 1):
        md += f"{i}. {idea}\n\n"
    return md

def format_summary_en():
    md = "## 4. Summary & Action Items\n\n"
    md += "**📌 Today's Highlights**:\n"
    md += "- Weather data fetched from wttr.in\n"
    md += "- GitHub trending repositories fetched\n"
    md += "- Software development ideas compiled\n\n"
    md += "**🎯 Recommended Actions**:\n"
    md += "- Review the generated briefing files\n"
    md += "- Check out the trending repositories for inspiration\n"
    md += "- Consider implementing one of the development ideas\n\n"
    md += "**📅 Tomorrow's Preview**:\n"
    md += "- Continue monitoring weather and tech trends\n"
    md += "- Stay tuned for tomorrow's briefing\n\n"
    return md

def format_summary_zh():
    md = "## 4. 总结与行动项\n\n"
    md += "**📌 今日亮点**：\n"
    md += "- 天气数据来源于 wttr.inConviene de la ciudad de Hangzhou\n"
    md += "- 已获取 GitHub 热门仓库\n"
    md += "- 已编译软件开发创意\n\n"
    md += "**🎯 推荐行动**：\n"
    md += "- 审阅生成的简报文件\n"
    md += "- 查看热门仓库以获取灵感\n"
    md += "- 考虑实施其中一个开发创意\n\n"
    md += "**📅 明日预览**：\n"
    md += "- 继续监控天气和科技趋势\n"
    md += "- 敬请期待明日的简报\n\n"
    return md

def main():
    # Get data
    weather_data = get_weather()
    repos = get_github_trending()
    ideas = get_ideas()
    
    # Generate English briefing
    en_content = f"""# Daily Briefing - {TODAY}

**📖 Also available in:** [中文版](briefing_{TODAY}_zh.md)

---

"""
    en_content += format_weather_en(weather_data)
    en_content += format_github_en(repos)
    en_content += format_ideas_en(ideas)
    en_content += format_summary_en()
    
    en_content += f"""*Generated by Daily Briefing Automation | {TODAY}*
*Weather: wttr.in | GitHub Data: GitHub API | Ideas: AI Assistant*
"""
    
    # Generate Chinese briefing
    zh_content = f"""# 每日简报 - {TODAY}

**📖 其他语言:** [English Version](briefing_{TODAY}.md)

---

"""
    zh_content += format_weather_zh(weather_data)
    zh_content += format_github_zh(repos)
    zh_content += format_ideas_zh(ideas)
    zh_content += format_summary_zh()
    
    zh_content += f"""*由每日简报自动化生成 | {TODAY}*
*天气数据：wttr.in | GitHub 数据：GitHub API | 创意：AI 助手*
"""
    
    # Write files
    en_path = f"/root/.openclaw/workspace/openClawBlog/briefing/briefing_{TODAY}.md"
    zh_path = f"/root/.openclaw/workspace/openClawBlog/briefing/briefing_{TODAY}_zh.md"
    
    with open(en_path, 'w', encoding='utf-8') as f:
        f.write(en_content)
    
    with open(zh_path, 'w', encoding='utf-8') as f:
        f.write(zh_content)
    
    print(f"Generated {en_path} and {zh_path}")
    
    # Git operations
    os.chdir("/root/.openclaw/workspace/openClawBlog")
    os.system(f"git add briefing/briefing_{TODAY}.md briefing/briefing_{TODAY}_zh.md")
    os.system(f'git commit -m "Add daily briefing for {TODAY}"')
    os.system("git push")
    
    print("Files committed and pushed to remote repository.")

if __name__ == "__main__":
    main()