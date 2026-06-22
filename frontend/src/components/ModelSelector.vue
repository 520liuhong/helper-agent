<template>
  <div class="model-selector">
    <el-dropdown trigger="click" @command="handleSelect">
      <el-button type="primary" plain>
        <span class="model-name">{{ currentModelName }}</span>
        <el-icon class="el-icon--right"><ArrowDown /></el-icon>
      </el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item
            v-for="model in models"
            :key="model.id"
            :command="model.id"
            :disabled="model.disabled"
          >
            <div class="model-option">
              <span>{{ model.name }}</span>
              <el-tag v-if="model.id === currentModel" size="small" type="success">当前</el-tag>
            </div>
            <div class="model-desc">{{ model.description }}</div>
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'

const props = defineProps({
  model: {
    type: String,
    default: 'deepseek',
  },
})

const emit = defineEmits(['update:model', 'change'])

const models = [
  { id: 'deepseek', name: 'DeepSeek', description: '深度求索AI助手' },
  { id: 'qwen', name: 'Qwen', description: '通义千问AI助手' },
]

const currentModelName = computed(() => {
  const found = models.find(m => m.id === props.model)
  return found ? found.name : '选择模型'
})

function handleSelect(modelId) {
  emit('update:model', modelId)
  emit('change', modelId)
}
</script>

<style scoped>
.model-selector {
  display: inline-block;
}

.model-name {
  margin-right: 4px;
}

.model-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}
</style>
