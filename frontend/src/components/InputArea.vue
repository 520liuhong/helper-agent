<template>
  <div class="input-area">
    <!-- 上传文件预览 -->
    <div v-if="uploadedFiles.length > 0" class="upload-preview">
      <div v-for="(file, index) in uploadedFiles" :key="index" class="uploaded-file">
        <el-icon><Document /></el-icon>
        <span class="filename">{{ file.filename }}</span>
        <el-button type="danger" :icon="Delete" size="small" circle @click="removeFile(index)" />
      </div>
    </div>
    
    <div class="input-wrapper">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="3"
        placeholder="输入消息，Shift+Enter换行，Enter发送..."
        @keydown="handleKeydown"
        resize="none"
      />
      <div class="input-actions">
        <div class="action-buttons">
          <el-upload
            ref="uploadRef"
            :action="uploadUrl"
            :before-upload="handleBeforeUpload"
            :show-file-list="false"
            :disabled="uploading"
          >
            <el-button 
              :icon="Upload" 
              circle 
              :loading="uploading"
              title="上传文件"
            />
          </el-upload>
          <el-button 
            type="primary" 
            :disabled="!canSend" 
            @click="handleSend"
            title="发送消息"
          >
            发送
          </el-button>
        </div>
      </div>
    </div>
    <div class="input-hint">
      <span>按 Enter 发送，Shift + Enter 换行 | 支持上传文件</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Upload, Delete, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { uploadApi } from '../api'

const emit = defineEmits(['send'])
const inputText = ref('')
const uploadedFiles = ref([])
const uploading = ref(false)
const uploadRef = ref(null)
const uploadUrl = '/api/upload'

const canSend = computed(() => {
  return inputText.value.trim() || uploadedFiles.value.length > 0
})

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
    uploadedFiles.value.push(result)
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

function removeFile(index) {
  uploadedFiles.value.splice(index, 1)
}

function handleSend() {
  const text = inputText.value.trim()
  const attachments = uploadedFiles.value.map(f => ({
    url: f.url,
    filename: f.filename,
    type: isImageFile(f.filename) ? 'image' : 'file',
  }))

  // 构建展示用文本（含文件链接）
  let displayContent = text
  if (uploadedFiles.value.length > 0) {
    const fileRefs = uploadedFiles.value.map(f => `[文件: ${f.filename}](${f.url})`).join('\n')
    displayContent = text ? `${text}\n\n${fileRefs}` : fileRefs
  }

  if (displayContent || attachments.length > 0) {
    emit('send', { content: displayContent, attachments })
    inputText.value = ''
    uploadedFiles.value = []
  }
}

function isImageFile(filename) {
  return /\.(jpe?g|png|gif|webp|bmp)$/i.test(filename)
}

function handleKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}
</script>

<style scoped>
.input-area {
  padding: 16px 24px;
  background: var(--bg-color-secondary);
  border-top: 1px solid var(--border-color);
}

.upload-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  padding: 8px;
  background: var(--bg-color);
  border-radius: 8px;
}

.uploaded-file {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: var(--bg-color-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 12px;
}

.uploaded-file .filename {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-wrapper :deep(.el-textarea__inner) {
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 14px;
  background: var(--bg-color);
  color: var(--text-color);
  border-color: var(--border-color);
}

.input-wrapper :deep(.el-textarea__inner:focus) {
  border-color: #409eff;
}

.input-actions {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-buttons .el-button {
  width: 80px;
}

.input-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-color-secondary);
  text-align: center;
}
</style>
