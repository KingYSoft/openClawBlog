#!/bin/bash

# Daily Briefing Automation Script
# This script generates and pushes the daily briefing to the GitHub blog_bot repository

# Configuration
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
REPO_OWNER="KingYSoft"
REPO_NAME="openClawBlog"
BRANCH="master"

# Get today's date components
YEAR=$(date +%Y)
MONTH=$(date +%m)
DAY=$(date +%d)

# Create directory structure if it doesn't exist
mkdir -p "/tmp/briefing_${YEAR}_${MONTH}_${DAY}"

# Generate the daily briefing content
generate_briefing() {
  # Get current weather for Hangzhou
  WEATHER_DATA=$(curl -s "http://api.weatherapi.com/v1/current.json?key=720572f27ba2493f98a31443260102&q=Hangzhou&aqi=no")
  
  # Extract weather information
  TEMP_C=$(echo $WEATHER_DATA | grep -o '"temp_c":[^,}]*' | head -1 | cut -d':' -f2)
  CONDITION=$(echo $WEATHER_DATA | grep -o '"text":"[^"]*' | head -1 | cut -d'"' -f4)
  HUMIDITY=$(echo $WEATHER_DATA | grep -o '"humidity":[^,}]*' | head -1 | cut -d':' -f2)
  WIND_KPH=$(echo $WEATHER_DATA | grep -o '"wind_kph":[^,}]*' | head -1 | cut -d':' -f2)
  PRESSURE=$(echo $WEATHER_DATA | grep -o '"pressure_mb":[^,}]*' | head -1 | cut -d':' -f2)
  
  # Get GitHub trending data
  cd /root/.openclaw/workspace/skills/explorer
  TRENDING_DATA=$(python3 scripts/github_projects.py --days 7 --limit 10 --sort stars 2>/dev/null)
  
  # Create the briefing content
  cat << EOF
# 今日简报（$(date +"%Y年%m月%d日")）

## 1. 杭州天气及穿搭指南

**当前天气**: 杭州，浙江省，中国
- 温度: ${TEMP_C}°C (体感温度${TEMP_C}°C)
- 天气状况: ${CONDITION}
- 湿度: ${HUMIDITY}%
- 风速: ${WIND_KPH} km/h
- 气压: ${PRESSURE} mb

**穿搭建议**: 
- 当前温度${TEMP_C}°C，建议穿着适合的衣物
- 根据${CONDITION}天气情况，合理搭配外套
- 湿度${HUMIDITY}%，注意舒适度

## 2. GitHub上最近7天最热门的仓库（按Star增长排序）

$(echo "$TRENDING_DATA" | grep -A 100 "🔥 找到" | grep -E "^\d+\." | head -10)

## 3. 软件开发创意点子与功能建议

1. **AI辅助开发工具**
   - 利用当前热门的AI技术提升开发效率
   
2. **开源项目贡献**
   - 关注并参与热门的开源项目

3. **技术趋势跟踪**
   - 跟进GitHub上最新的技术趋势

$(date)
EOF
}

# Push briefing to GitHub
push_to_github() {
  local briefing_content="$1"
  local filepath="2026/02/12/briefing_$(date +%Y%m%d).md"
  
  # Encode content to base64
  local encoded_content=$(echo -n "$briefing_content" | base64 -w 0)
  
  # Get current file SHA if it exists
  local sha_response=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
    "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/contents/$filepath?ref=$BRANCH")
  
  local sha=""
  if echo "$sha_response" | grep -q '"sha"'; then
    sha=$(echo "$sha_response" | grep -o '"sha":"[^"]*"' | head -1 | cut -d'"' -f4)
  fi
  
  # Prepare commit message
  local message="Auto-update daily briefing for $(date +%Y-%m-%d)"
  
  # Prepare the payload
  local payload
  if [ -n "$sha" ]; then
    payload=$(jq -n --arg msg "$message" --arg content "$encoded_content" --arg file_sha "$sha" \
      '{"message": $msg, "content": $content, "sha": $file_sha}')
  else
    payload=$(jq -n --arg msg "$message" --arg content "$encoded_content" \
      '{"message": $msg, "content": $content}')
  fi
  
  # Upload the file to GitHub
  curl -X PUT \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    -d "$payload" \
    "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/contents/$filepath"
}

# Main execution
briefing_content=$(generate_briefing)
push_to_github "$briefing_content"

echo "Daily briefing generated and pushed to GitHub successfully."