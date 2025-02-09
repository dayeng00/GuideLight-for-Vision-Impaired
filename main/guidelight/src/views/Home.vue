<template>
    <div class="home-page">
      <!-- Header Section -->
      <el-header>
        <div class="header-content">
          <h1>欢迎来到我们的项目主页</h1>
          <p>探索我们的创新点和项目背景</p>
        </div>
      </el-header>
  
      <!-- Main Content Section -->
      <el-container style="padding: 20px;">
        <el-row>
          <!-- Project Innovation -->
          <el-col :span="12">
            <div class="section">
              <h2>项目创新点与功用</h2>
              <p>我们的项目通过技术创新，提出了一种新设计及系统，将环境感知、导航及云端计算结合到一个系统之中。</p>
              <ul>
                <li><strong>创新算法</strong>：采用了深度学习技术，在海量数据中准确识别关键点。</li>
                <li><strong>自动化流程</strong>：通过智能化系统自动化处理，降低人工干预，提升处理速度。</li>
                <li><strong>实时反馈</strong>：系统可以根据用户需求提供实时反馈和建议，帮助优化决策。</li>
                <li><strong>用户体验</strong>：界面简洁，操作流畅，保证了用户的良好体验。</li>
              </ul>
            </div>
          </el-col>
  
          <!-- Project Background -->
          <el-col :span="12">
            <div class="section">
              <h2>项目背景</h2>
              <p>随着技术的不断进步，现有的解决方案逐渐显得无法满足市场日益增长的需求。我们的团队立足于以下背景展开研发：</p>
              <ul>
                <li><strong>行业需求</strong>：传统行业处理速度慢，无法做到让盲人实时规避风险</li>
                <li><strong>技术瓶颈</strong>：传统障碍物识别率不高，识别帧率据低不上</li>
                <li><strong>市场潜力</strong>：随着人工智能技术的发展，智能化解决方案具有巨大的市场空间。</li>
                <li><strong>社会影响</strong>：从盲人生活的不便之处入手，为彻底解决关于盲人的安全问题贡献了自己的力量</li>
              </ul>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="section">
              <h2>项目背景</h2>
              <p>随着技术的不断进步，现有的解决方案逐渐显得无法满足市场日益增长的需求。我们的团队立足于以下背景展开研发：</p>
              <ul>
                <li><strong>行业需求</strong>：传统行业处理速度慢，无法做到让盲人实时规避风险</li>
                <li><strong>技术瓶颈</strong>：传统障碍物识别率不高，识别帧率据低不上</li>
                <li><strong>市场潜力</strong>：随着人工智能技术的发展，智能化解决方案具有巨大的市场空间。</li>
                <li><strong>社会影响</strong>：从盲人生活的不便之处入手，为彻底解决关于盲人的安全问题贡献了自己的力量</li>
              </ul>
            </div>
          </el-col>
        </el-row>
      </el-container>
  
      
    </div>
  </template>
  
  <script setup>
  import { ElContainer, ElHeader, ElFooter, ElRow, ElCol } from 'element-plus'
  </script>
  
  <style scoped>
  .home-page {
    font-family: 'Arial', sans-serif;
  }
  
  .el-header {
    background-color: #409EFF;
    color: white;
    padding: 20px;
    text-align: center;
  }
  
  .header-content h1 {
    margin: 0;
    font-size: 36px;
  }
  
  .header-content p {
    margin: 10px 0;
    font-size: 18px;
  }
  
  .el-container {
    margin-top: 20px;
  }
  
  .section {
    padding: 20px;
    border: 1px solid #e4e4e4;
    margin-bottom: 20px;
    border-radius: 10px;
    text-align: left;
  }
  
  h2 {
    font-size: 24px;
    color: #333;
  }
  
  ul {
    list-style-type: disc;
    margin-left: 20px;
  }
  
  footer {
    background-color: #f4f4f4;
    padding: 10px;
    text-align: center;
  }
  
  .footer-content p {
    margin: 0;
    color: #666;
  }
  </style>
  