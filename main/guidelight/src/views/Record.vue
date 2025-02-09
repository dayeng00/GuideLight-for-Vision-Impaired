<template>
    <el-table :data="historyRecords" style="width: 100%">
      <el-table-column prop="created_at" label="时间"></el-table-column>
      <el-table-column prop="category" label="操作"></el-table-column>
      <el-table-column prop="name" label="用户"></el-table-column>
      <el-table-column label="改动">
        <template v-slot="scope">
          <el-button size="small" @click="viewDetails(scope.row)">查看</el-button>
          <!-- <el-button size="small" type="danger" @click="deleteRecord(scope.row)">删除</el-button> -->
        </template>
      </el-table-column>
    </el-table>
  
    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="操作详情"
      width="30%"
    >
      <div v-if="selectedDetail" class="detail-content">
        <p><strong>时间：</strong>{{ selectedDetail.created_at }}</p>
        <p><strong>操作类型：</strong>{{ selectedDetail.category }}</p>
        <p><strong>状态：</strong>
          <el-tag :type="selectedDetail.status === '成功' ? 'success' : 'danger'">
            {{ "成功" }}
          </el-tag>
        </p>
        <p><strong>详细信息：</strong>这里是具体的操作详情描述...</p>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </template>
  
  <script setup>
  import { ref } from 'vue';
  import { ElTable, ElTableColumn, ElButton, ElDialog, ElTag } from 'element-plus';
  import { useUserStore } from '../store/userStore';
  const userStore = useUserStore();
  console.log(userStore.user);
  // 定义响应式数据
  const historyRecords = ref(userStore.user);

  // 详情对话框的显示状态
  const detailDialogVisible = ref(false);

  // 选中的记录详情
  const selectedDetail = ref(null);

  // 查看详情
  const viewDetails = (row) => {
    selectedDetail.value = row;
    detailDialogVisible.value = true;
  };

  // 删除记录
  const deleteRecord = (row) => {
    historyRecords.value = historyRecords.value.filter(record => record !== row);
  };
  </script>
  
  <style scoped>
  .detail-content p {
    margin: 10px 0;
    line-height: 1.6;
  }
  
  .detail-content strong {
    display: inline-block;
    width: 80px;
    color: #606266;
  }
  
  .el-tag {
    margin-left: 5px;
  }
  </style>