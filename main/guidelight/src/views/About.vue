<template>
    <div class="about-us">
      <!-- Header Section -->
      <el-header>
        <div class="header-content">
          <h1>关于我们</h1>
          <p>了解更多关于我们团队和项目的背景</p>
        </div>
      </el-header>
  
      <!-- Main Content Section -->
      <el-container style="padding: 20px;">
        <el-row gutter={20}>
          <el-col :span="12">
            <div class="section">
              <h2>我们的使命</h2>
              <p>我们的使命是通过创新和技术改变世界，为用户提供更高效、更智能的解决方案。</p>
              <ul>
                <li><strong>推动技术创新</strong>：提供更高效、更智能的产品与服务。</li>
                <li><strong>提升用户体验</strong>：让每一位用户都能享受到流畅和舒适的使用体验。</li>
                <li><strong>促进社会发展</strong>：积极承担企业社会责任，为人民服务</li>
              </ul>
            </div>
          </el-col>
          
          <el-col :span="12">
            <div class="section">
              <h2>我们的团队</h2>
              <p>我们是一支由多元化背景的人才组成的团队，拥有共同的目标：实现技术创新并创造更好的用户体验。</p>
              <ul>
                <li><strong>团队成员 1：</strong>前端开发专家，致力于构建高效且友好的用户界面。</li>
                <li><strong>团队成员 2：</strong>后端开发专家，擅长系统架构和性能优化。</li>
                <li><strong>团队成员 3：</strong>产品经理，负责协调各部门工作，推动项目进展。</li>
              </ul>
            </div>
          </el-col>
        </el-row>
  
        <el-row>
          <el-col :span="24">
            <div class="section">
              <h2>我们的价值观</h2>
              <p>我们相信，技术不仅能改变人们的生活，还能帮助我们解决当前社会面临的许多挑战。</p>
              <ul>
                <li><strong>创新</strong>：我们始终致力于技术创新，推动行业发展。</li>
                <li><strong>合作</strong>：我们鼓励跨部门协作，发挥团队的最大潜力。</li>
                <li><strong>责任</strong>：我们注重社会责任，致力于创造可持续的技术解决方案。</li>
              </ul>
            </div>
          </el-col>
        </el-row>
      </el-container>
  
      <!-- Footer Section -->
      
    </div>
  </template>
  
  <script setup>
  import { ElContainer, ElHeader, ElFooter, ElRow, ElCol } from 'element-plus'
  </script>
  
  <style scoped>
  .about-us {
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
  
  .el-footer {
    background-color: #f4f4f4;
    padding: 10px;
    text-align: center;
  }
  
  .footer-content p {
    margin: 0;
    color: #666;
  }
  </style>
  