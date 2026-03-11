const { execSync } = require('child_process');
const fs = require('fs');

async function generateAndPushBriefing() {
  console.log('开始生成每日简报...');
  
  try {
    // 获取当前日期
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    
    // 创建目录结构
    const dirPath = `2026/${month}/${day}`;
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
    }
    
    // 获取天气数据
    const weatherCmd = 'curl -s "http://api.weatherapi.com/v1/current.json?key=720572f27ba2493f98a31443260102&q=Hangzhou&aqi=no"';
    const weatherData = JSON.parse(execSync(weatherCmd, { encoding: 'utf-8' }));
    
    // 获取GitHub trending数据
    const trendingCmd = 'cd /root/.openclaw/workspace/skills/explorer && python3 scripts/github_projects.py --days 7 --limit 10 --sort stars';
    const trendingOutput = execSync(trendingCmd, { encoding: 'utf-8' });
    
    // 解析trending数据
    const repos = [];
    const lines = trendingOutput.split('\n');
    let currentRepo = null;
    
    for (const line of lines) {
      if (line.match(/^\d+\.\s*\*\*/)) {
        // 新仓库条目
        const match = line.match(/^\d+\.\s*\*\*(.*?)\*\*/);
        if (match) {
          currentRepo = { name: match[1].trim() };
          repos.push(currentRepo);
        }
      } else if (currentRepo && line.includes('- 描述:')) {
        const descMatch = line.match(/- 描述:\s*(.*)/);
        if (descMatch) currentRepo.description = descMatch[1];
      } else if (currentRepo && line.includes('- 语言:')) {
        const langMatch = line.match(/- 语言:\s*(.*)/);
        if (langMatch) currentRepo.language = langMatch[1];
      } else if (currentRepo && line.includes('- Star数:')) {
        const starMatch = line.match(/- Star数:\s*(.*)/);
        if (starMatch) currentRepo.stars = starMatch[1];
      } else if (currentRepo && line.includes('- 链接:')) {
        const linkMatch = line.match(/- 链接:\s*(.*)/);
        if (linkMatch) currentRepo.link = linkMatch[1];
      }
    }
    
    // 构建简报内容
    let briefingContent = `# 今日简报（${year}年${month}月${day}日）\n\n`;
    
    briefingContent += `## 1. 杭州天气及穿搭指南\n\n`;
    briefingContent += `**当前天气**: 杭州，浙江省，中国\n`;
    briefingContent += `- 温度: ${weatherData.current.temp_c}°C (体感温度${weatherData.current.feelslike_c}°C)\n`;
    briefingContent += `- 天气状况: ${weatherData.current.condition.text}\n`;
    briefingContent += `- 湿度: ${weatherData.current.humidity}%\n`;
    briefingContent += `- 风速: ${weatherData.current.wind_kph} km/h，方向${weatherData.current.wind_dir}\n`;
    briefingContent += `- 气压: ${weatherData.current.pressure_mb} mb\n`;
    briefingContent += `- 能见度: ${weatherData.current.vis_km} km\n`;
    briefingContent += `- 紫外线指数: ${weatherData.current.uv}\n`;
    briefingContent += `- 降水量: ${weatherData.current.precip_mm} mm\n\n`;
    
    briefingContent += `**穿搭建议**: \n`;
    briefingContent += `- 当前温度${weatherData.current.temp_c}°C，建议穿着适合的衣物\n`;
    briefingContent += `- ${weatherData.current.condition.text}天气，合理搭配外套\n`;
    briefingContent += `- 湿度${weatherData.current.humidity}%，注意舒适度\n`;
    briefingContent += `- 风速${weatherData.current.wind_kph} km/h，注意防风\n\n`;
    
    briefingContent += `## 2. GitHub上最近7天最热门的仓库（按Star增长排序）\n\n`;
    
    for (let i = 0; i < Math.min(10, repos.length); i++) {
      const repo = repos[i];
      briefingContent += `${i + 1}. **${repo.name || 'N/A'}**\n`;
      briefingContent += `   - 描述: ${repo.description || 'N/A'}\n`;
      briefingContent += `   - 语言: ${repo.language || 'N/A'}\n`;
      briefingContent += `   - Star数: ${repo.stars || 'N/A'}\n`;
      briefingContent += `   - 链接: ${repo.link || 'N/A'}\n\n`;
    }
    
    briefingContent += `## 3. 软件开发创意点子与功能建议\n\n`;
    briefingContent += `1. **AI辅助开发工具**\n   - 利用当前热门的AI技术提升开发效率\n\n`;
    briefingContent += `2. **开源项目贡献**\n   - 关注并参与热门的开源项目\n\n`;
    briefingContent += `3. **技术趋势跟踪**\n   - 跟进GitHub上最新的技术趋势\n\n`;
    briefingContent += `生成时间: ${now.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}\n`;
    
    // 将简报写入文件
    const fileName = `briefing_${year}${month}${day}.md`;
    const filePath = `${dirPath}/${fileName}`;
    fs.writeFileSync(filePath, briefingContent);
    
    console.log(`简报已生成: ${filePath}`);
    
    // 上传到GitHub
    const accessToken = process.env.GITHUB_TOKEN || '';
    const repoOwner = 'KingYSoft';
    const repoName = 'openClawBlog';
    
    // 读取文件内容并编码
    const fileContent = fs.readFileSync(filePath, 'utf8');
    const encodedContent = Buffer.from(fileContent, 'utf8').toString('base64');
    
    // 获取当前文件SHA（如果存在）
    let sha = null;
    try {
      const shaResponse = execSync(`curl -s -H "Authorization: Bearer ${accessToken}" "https://api.github.com/repos/${repoOwner}/${repoName}/contents/${filePath}?ref=main"`, { encoding: 'utf-8' });
      const shaJson = JSON.parse(shaResponse);
      if (shaJson.sha) {
        sha = shaJson.sha;
      }
    } catch (e) {
      console.log('文件不存在，将创建新文件');
    }
    
    // 准备提交数据
    const commitMessage = `Auto-update daily briefing for ${year}-${month}-${day}`;
    const apiUrl = `https://api.github.com/repos/${repoOwner}/${repoName}/contents/${filePath}`;
    
    const uploadPayload = {
      message: commitMessage,
      content: encodedContent
    };
    
    if (sha) {
      uploadPayload.sha = sha;
    }
    
    // 上传文件
    const curlCommand = `curl -X ${
      sha ? 'PUT' : 'PUT'
    } \\
      -H "Authorization: Bearer ${accessToken}" \\
      -H "Accept: application/vnd.github.v3+json" \\
      -d '${JSON.stringify(uploadPayload)}' \\
      "${apiUrl}"`;
    
    const result = execSync(curlCommand, { encoding: 'utf-8' });
    console.log('简报已成功上传到GitHub:', result);
    
    console.log('每日简报生成和推送完成！');
  } catch (error) {
    console.error('生成简报时出错:', error.message);
    throw error;
  }
}

// 执行函数
generateAndPushBriefing().catch(err => {
  console.error('脚本执行失败:', err);
  process.exit(1);
});