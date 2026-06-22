import { ref, watch, onUnmounted, unref, isRef } from 'vue'

/**
 * 打字机效果：将 source 中的文本逐字显示到 displayedText
 * 流式 chunk 到达时先写入 source，展示层平滑追赶
 */
export function useTypewriter(source, options = {}) {
  const enabled = isRef(options.enabled) ? options.enabled : ref(options.enabled ?? true)
  const displayedText = ref('')
  let rafId = null

  function getStep(backlog) {
    if (backlog <= 0) return 0
    if (backlog < 20) return 1
    if (backlog < 80) return 2
    if (backlog < 200) return 4
    return Math.min(12, Math.ceil(backlog / 20))
  }

  function tick() {
    rafId = null
    const target = unref(source) || ''

    if (!unref(enabled)) {
      displayedText.value = target
      return
    }

    const backlog = target.length - displayedText.value.length
    if (backlog > 0) {
      const step = getStep(backlog)
      displayedText.value = target.slice(0, displayedText.value.length + step)
      rafId = requestAnimationFrame(tick)
    }
  }

  function schedule() {
    if (!rafId) {
      rafId = requestAnimationFrame(tick)
    }
  }

  function flush() {
    if (rafId) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
    displayedText.value = unref(source) || ''
  }

  watch(source, (newVal) => {
    if (!unref(enabled)) {
      if (displayedText.value.length === 0) {
        displayedText.value = newVal || ''
      }
      return
    }
    schedule()
  }, { immediate: true })

  watch(enabled, (active) => {
    if (active) {
      schedule()
    }
  })

  onUnmounted(() => {
    if (rafId) {
      cancelAnimationFrame(rafId)
    }
  })

  return { displayedText, flush }
}
