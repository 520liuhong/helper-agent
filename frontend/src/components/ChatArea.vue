<template>
  <div class="chat-area">
    <div class="chat-header">
      <h3>{{ session?.title || '新会话' }}</h3>
    </div>
    <div class="message-list" ref="messageListRef">
      <div v-if="!session?.messages?.length" class="empty-state">
        <el-empty description="开始对话吧">
          <el-button type="primary" @click="$emit('send-message', '你好，请介绍一下你自己')">
            发送问候
          </el-button>
        </el-empty>
      </div>
      <template v-else>
        <MessageBubble
          v-for="(message, index) in session.messages"
          :key="index"
          :message="message"
          :is-streaming="isTyping && index === session.messages.length - 1 && message.role === 'assistant'"
          @retry="$emit('retry-message', index)"
          @content-update="scrollToBottom"
        />
      </template>
      <div v-if="showTypingIndicator" class="typing-indicator">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
    <InputArea @send="$emit('send-message', $event)" />
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import MessageBubble from './MessageBubble.vue'
import InputArea from './InputArea.vue'

const props = defineProps({
  session: {
    type: Object,
    default: null,
  },
  isTyping: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['send-message', 'retry-message'])
const messageListRef = ref(null)

const showTypingIndicator = computed(() => {
  if (!props.isTyping) return false
  const messages = props.session?.messages
  if (!messages?.length) return true
  const last = messages[messages.length - 1]
  return last.role !== 'assistant' || !last.content
})

function debounce(fn, delay) {
  let timer
  return function(...args) {
    clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
    }, delay)

  }
}
function throttle(fn, delay) {
  let last = 0
  return function(...args){
    const now = Date.now()
    if (now >= last + delay) {
      last = now
      fn.apply(this, args)
    }
  }
}

watch(() => props.session?.messages?.length, () => {
  nextTick(scrollToBottom)
})

watch(
  () => props.session?.messages?.[props.session.messages.length - 1]?.content,
  () => {
    nextTick(scrollToBottom)
  }
)

watch(() => props.isTyping, () => {
  nextTick(() => {
    scrollToBottom()
  })
})

function scrollToBottom() {
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}
</script>

<style scoped>
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
  overflow: hidden;
}

.chat-header {
  padding: 16px 24px;
  background: var(--bg-color-secondary);
  border-bottom: 1px solid var(--border-color);
}

.chat-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color);
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px 16px;
  background: var(--bg-color-secondary);
  border-radius: 12px;
  width: fit-content;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: var(--text-color-secondary);
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}
</style>
