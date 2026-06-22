<template>
  <div class="message-bubble" :class="message.role">
    <div class="avatar">
      <el-icon v-if="message.role === 'user'" :size="24"><User /></el-icon>
      <el-icon v-else :size="24"><ChatDotRound /></el-icon>
    </div>
    <div class="content-wrapper">
      <div class="content">
        <span v-html="renderedContent"></span>
        <span v-if="showCursor" class="typewriter-cursor">|</span>
      </div>
      <div v-if="message.role === 'assistant' && message.content && !isActive" class="actions">
        <el-button size="small" text @click="$emit('retry')">重新生成</el-button>
        <el-button size="small" text @click="copyContent">复制</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, toRef, watch, ref } from 'vue'
import { User, ChatDotRound } from '@element-plus/icons-vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import { ElMessage } from 'element-plus'
import { useTypewriter } from '../composables/useTypewriter'

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
  isStreaming: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['retry', 'content-update'])

const isFinishing = ref(false)

const sourceContent = toRef(() => props.message.content)
const shouldAnimate = computed(() => props.isStreaming || isFinishing.value)
const { displayedText } = useTypewriter(sourceContent, {
  enabled: shouldAnimate,
})

const isActive = computed(() => props.isStreaming || isFinishing.value)

const showCursor = computed(() => {
  return isActive.value && props.message.content
})

watch(() => props.isStreaming, (streaming, wasStreaming) => {
  if (wasStreaming && !streaming) {
    const backlog = (props.message.content?.length || 0) - displayedText.value.length
    if (backlog > 0) {
      isFinishing.value = true
    }
  }
}, { flush: 'sync' })

watch(displayedText, () => {
  if (isFinishing.value && displayedText.value.length >= (props.message.content?.length || 0)) {
    isFinishing.value = false
    emit('content-update')
  }
  if (props.isStreaming) {
    emit('content-update')
  }
})

// 配置marked
marked.setOptions({
  highlight: function(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
})

const renderedContent = computed(() => {
  const text = shouldAnimate.value ? displayedText.value : props.message.content
  if (!text) return ''
  return marked(text)
})

function copyContent() {
  navigator.clipboard.writeText(props.message.content).then(() => {
    ElMessage.success('复制成功')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}
</script>

<style scoped>
.message-bubble {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.message-bubble.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-bubble.user .avatar {
  background: #409eff;
  color: #fff;
}

.message-bubble.assistant .avatar {
  background: #67c23a;
  color: #fff;
}

.content-wrapper {
  max-width: 70%;
}

.message-bubble.user .content-wrapper {
  align-items: flex-end;
}

.content {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.message-bubble.user .content {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant .content {
  background: var(--bg-color-secondary);
  color: var(--text-color);
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.content :deep(pre) {
  background: var(--bg-color);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.content :deep(code) {
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.content :deep(p) {
  margin: 8px 0;
}

.content :deep(ul),
.content :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.content :deep(blockquote) {
  border-left: 3px solid var(--border-color);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--text-color-secondary);
}

.actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  opacity: 0;
  transition: opacity 0.3s;
}

.content-wrapper:hover .actions {
  opacity: 1;
}

.typewriter-cursor {
  display: inline-block;
  margin-left: 2px;
  color: var(--text-color-secondary);
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
