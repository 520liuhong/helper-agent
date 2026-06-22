<template>
  <el-dialog
    :model-value="visible"
    title="设置"
    width="500px"
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-form label-width="100px">
      <el-form-item label="AI模型">
        <el-select v-model="localSettings.model" placeholder="选择AI模型">
          <el-option label="DeepSeek" value="deepseek" />
          <el-option label="Qwen" value="qwen" />
        </el-select>
      </el-form-item>
      <el-form-item label="温度参数">
        <el-slider
          v-model="localSettings.temperature"
          :min="0"
          :max="2"
          :step="0.1"
          show-input
        />
        <div class="hint">控制回复的随机性，较低的值更确定性，较高的值更有创造性</div>
      </el-form-item>
      <el-form-item label="最大Token数">
        <el-input-number
          v-model="localSettings.maxTokens"
          :min="100"
          :max="4000"
          :step="100"
        />
        <div class="hint">控制单次回复的最大长度</div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  settings: {
    type: Object,
    default: () => ({
      model: 'deepseek',
      temperature: 0.7,
      maxTokens: 2000,
    }),
  },
})

const emit = defineEmits(['update:visible', 'update:settings'])

const localSettings = ref({ ...props.settings })

watch(() => props.settings, (newSettings) => {
  localSettings.value = { ...newSettings }
}, { deep: true })

function handleSave() {
  emit('update:settings', localSettings.value)
  emit('update:visible', false)
}
</script>

<style scoped>
.hint {
  font-size: 12px;
  color: var(--text-color-secondary);
  margin-top: 4px;
}
</style>
