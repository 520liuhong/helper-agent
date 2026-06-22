<template>
  <div class="upload-button">
    <el-upload
      ref="uploadRef"
      :action="uploadUrl"
      :before-upload="handleBeforeUpload"
      :on-success="handleSuccess"
      :on-error="handleError"
      :show-file-list="false"
      :disabled="uploading"
    >
      <el-button 
        :icon="Upload" 
        circle 
        :loading="uploading"
        :title="uploading ? '上传中...' : '上传文件'"
      />
    </el-upload>
    <el-input
      v-if="uploadedUrl"
      v-model="uploadedUrl"
      placeholder="文件URL"
      size="small"
      class="url-input"
      readonly
    >
      <template #append>
        <el-button :icon="CopyDocument" @click="copyUrl" />
      </template>
    </el-input>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Upload, CopyDocument } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { uploadApi } from '../api'

const emit = defineEmits(['uploaded'])

const uploadRef = ref(null)
const uploading = ref(false)
const uploadedUrl = ref('')
const uploadUrl = '/api/upload'

async function handleBeforeUpload(file) {
  // 检查文件大小 (10MB)
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过10MB')
    return false
  }
  
  uploading.value = true
  
  try {
    const result = await uploadApi.upload(file)
    uploadedUrl.value = result.url
    emit('uploaded', result)
    ElMessage.success('上传成功')
    return false // 阻止默认上传
  } catch (error) {
    console.error('上传失败:', error)
    ElMessage.error('上传失败，请重试')
    return false
  } finally {
    uploading.value = false
  }
}

function handleSuccess(response, file) {
  console.log('上传成功:', response)
}

function handleError(error) {
  console.error('上传错误:', error)
  ElMessage.error('上传失败')
}

function copyUrl() {
  if (uploadedUrl.value) {
    navigator.clipboard.writeText(uploadedUrl.value).then(() => {
      ElMessage.success('URL已复制到剪贴板')
    }).catch(() => {
      ElMessage.error('复制失败')
    })
  }
}
</script>

<style scoped>
.upload-button {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.url-input {
  width: 300px;
  font-size: 12px;
}
</style>
